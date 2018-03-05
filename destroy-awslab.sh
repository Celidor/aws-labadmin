#!/bin/bash
#prerequisites: Python 2.7, AWS CLI, Cloud Custodian
#usage: ./destroy-awslab.sh

echo "Deleting user access keys ... "
custodian run -s. --region=us-east-1 --profile=celidor --cache-period=0 access_key_delete.yml
echo "User access keys deleted"
./delete-mfa.sh
echo "Deleting Static Web Sites ... "
python delete-staticwebsite.py --profile celidor
echo "Deleting environments with the repository tag"
custodian run -s. --region=eu-west-1 --profile=celidor --cache-period=0 aws_security_delete.yml
echo "Use the console to delete VPCs and Route53 entries"
