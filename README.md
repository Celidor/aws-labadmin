# aws-labadmin
Scripts for administration of AWS security labs

# overview
This script performs the following actions:
* Deletes access keys from users in named groups
* Deletes MFA devices from users csa1 - csa14
* Terminates EC2 instances built from the aws-security repository
* Deletes ELBs built from the aws-security repository

# usage
After cloning the repository:
* edit the profile name in the scripts to match your AWS credentials file
```
$ ./destroy-awslab.sh
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
