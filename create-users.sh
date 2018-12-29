#!/bin/bash
#set user passwords from file user-passwords.sh using format below
#ensure passwords comply with the account password policy
#PASSWORD_1="xxxxxxxxxxxxxxxxxxxxxxxxxxx"
#PASSWORD_2="xxxxxxxxxxxxxxxxxxxxxxxxxxx"
source user-passwords.sh
ACCOUNTID=$(aws sts get-caller-identity --output text --query 'Account' --profile celidor)
echo "Creating users for AWS Account ${ACCOUNTID}"
for i in `seq 15 20`;
do
  echo "creating user csa$i"
  aws iam create-user --user-name csa$i

  PASSWORD="PASSWORD_$i"  
  PASSWORD=${!PASSWORD}
  aws iam create-login-profile --user-name csa$i --password $PASSWORD
done
