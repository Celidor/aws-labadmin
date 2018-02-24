#!/bin/bash
#prerequisites: Python 2.7, AWS CLI, Cloud Custodian
#usage: ./destroy-awslab.sh

echo "Deleting user access keys ... "
custodian run -s. --region=us-east-1 --profile=celidor --cache-period=0 access_key_delete.yml
echo "User access keys deleted"
./delete-mfa.sh
