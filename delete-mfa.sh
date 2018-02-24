#!/bin/bash
ACCOUNTID=$(aws sts get-caller-identity --output text --query 'Account' --profile celidor)
echo "AWS Account ${ACCOUNTID}"
for i in `seq 1 14`;
do
  echo "deleting MFA device for user csa$i"
  aws iam deactivate-mfa-device --user-name csa$i --serial-number "arn:aws:iam::${ACCOUNTID}:mfa/csa$i"
done
