#!/usr/bin/env python3
#
# This script updates circle-CI with stored secrets from production
# Secret Manager.
# Dennis DeMarco 1/5/2023

# In AWS Secrets manager create a secret name that matches the contexts
# name in organization settings. All secret values (key/value) in AWS will
# be updated in CircleCI under that same context name.

# Requires an aws profile with secret access and CircleAPI Token/Account ID
# defined in config.ini

import boto3, json
from botocore.exceptions import ClientError
import configparser
import http.client

class SecretMgr():
    def __init__(self) -> None:

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        # setup the AWS boto3 client
        self.session=boto3.Session(profile_name=self.config['DEFAULT']['PROFILE'])
        self.sm_client = self.session.client(
            service_name = 'secretsmanager',
            region_name = self.config['DEFAULT']['REGION']
        ) 
   
    def get_aws_env_secrets(self, id):
        try: 
            response = self.sm_client.get_secret_value(
                SecretId=id
            )
        except ClientError as e:
            raise e
        return json.loads(response['SecretString'])

    def get_aws_secrets(self,tags=['']):

        filters=[ { 'Key': 'tag-key', 
                    'Values': tags }
                ]

        try:
            response = self.sm_client.list_secrets(Filters=filters,MaxResults=100)
        except ClientError as e:
            raise e

        return response['SecretList']
   

    def get_circle_contexts(self):
        headers = { 'Circle-Token': self.config['DEFAULT']['CIRCLE_TOKEN'] }
        
        conn = http.client.HTTPSConnection('circleci.com')
        conn.request('GET', 
                     '/api/v2/context?owner-slug=bitbucket/onedayhq&page-token=NEXT_PAGE_TOKEN',
                      headers=headers)
        
        res = conn.getresponse()
        data = res.read()
    
        return json.loads(data.decode('utf-8'))

    def create_circle_context(self, context='default'):
        headers = { 'content-type' : "application/json",
                    'Circle-Token' : self.config['DEFAULT']['CIRCLE_TOKEN'] 
                  }
        payload = { 'name': context,
                    'owner': { 'id': self.config['DEFAULT']['ACCOUNT_ID]'],
                               'type': 'organization'
                             }
                  }
    
        conn = http.client.HTTPSConnection('circleci.com')
        conn.request("POST", "/api/v2/context",json.dumps(payload),headers)


        res = conn.getresponse()
        data = res.read()
        return data.decode('utf-8')
    
    def get_context_id(self,contexts,context):   
        for c in contexts['items']:
            if context in c['name']:
                return (c['id'])
        return None

    def delete_circle_context(self, context='default'):
        headers = { 'content-type' : "application/json",
                    'Circle-Token' : self.config['DEFAULT']['CIRCLE_TOKEN'] 
                  }

        contexts = self.get_circle_contexts()       
        context_id = self.get_context_id(contexts,context)
        
        if context_id:
           conn = http.client.HTTPSConnection('circleci.com')
           conn.request("DELETE", 
                        f"/api/v2/context/{context_id}", headers=headers)
           conn.getresponse()

    def add_circleci_env_variable(self,context_id,context,env_name,env_value):
        headers = { 'content-type' : "application/json",
                    'Circle-Token' : self.config['DEFAULT']['CIRCLE_TOKEN'] 
                  }

        payload = {'value': env_value}
        conn = http.client.HTTPSConnection('circleci.com')
        
        if context_id:
           conn.request("PUT", 
                     f"/api/v2/context/{context_id}/environment-variable/{env_name}", 
                     json.dumps(payload), headers
                     )

        conn.getresponse()

    def sync_circle(self):

        # Lets get the names from AWS secret manager and make them Contexts in CircleCI
        secrets = self.get_aws_secrets(['CIRCLECI'])
        
        for secret in secrets:
            context = secret['Name']
            print(f"Creating context: {context}")
            self.create_circle_context(context)

        # Getting the ID's for the contexts we just made
        contexts = self.get_circle_contexts()

        # Lets go through each secret name and set the environment variables from the secret into
        # each circle context
        
        for secret in secrets:
            context = secret['Name']
            print(f"Updating environment variables for {context}")
            envs_pairs = self.get_aws_env_secrets(context)

            for key, value in envs_pairs.items():
                context_id = self.get_context_id(contexts,context)
                self.add_circleci_env_variable(context_id,context,key,value)

def main():
    secrets = SecretMgr()
    secrets.sync_circle()

if __name__ == "__main__":
    main()