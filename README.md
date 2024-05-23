This script will sync aws secrets to circleci. AWS will be the single authority for keys and secrets. 


# Requirements
  * AWS access key setup in your environment.
  * CircleCI personal access token.
  * Python boto3 libaries installed.


# Usage
Edit the config.ini with the required settings. 

<pre>
# ./update-circle.py
</pre>>

Output shows the secrets that are synced to circleCi. Secrets in AWS tagged as CIRCLECI are synced.
 
# Limitations
There is a max limit of 100 secrets/context catagories that will sync. Ajust script if you have more.

# Additional information
