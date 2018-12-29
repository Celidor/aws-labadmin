# aws-labadmin
Scripts for administration of AWS security labs

# overview
This script performs the following actions:
* Deletes access keys from users in named groups
* Deletes MFA devices from users csa1 - csa14
* Deletes static web sites built using S3 buckets and CloudFormation
* Terminates EC2 instances built from the aws-security repository
* Deletes ELBs built from the aws-security repository

# usage - general
After cloning the repository:
* edit the profile name in the scripts to match your AWS credentials file
```
$ ./destroy-awslab.sh
```
# usage - DevSecOps Serverless Lab
Example for profile "celidor":
```
python delete-serverlesstraining.py --profile celidor --dry_run --dry_run
python delete-serverlesstraining.py --profile celidor --dry_run
```

# Create AWS users
After cloning the repository:
* create a file user-passwords.sh with executable permissions
* enter passwords to the file in the format below
* ensure passwords comply with the account password policy
```
PASSWORD_1="my-secure-password-for-user-1"
PASSWORD_2="my-secure-password-for-user-2"
```
* to create users and assign passwords:
```
$ ./create-users.sh
```

# prerequisites
Minimum prerequisites
* Linux based operating system
* Git 2.10.1
* AWS CLI 1.11.59, AWS access and secret keys
* AWS access and secret keys in AWS credentials file
* Cloud Custodian 0.8.27.0

Cloud Custodian install reference:
http://www.capitalone.io/cloud-custodian/docs/quickstart/index.html
