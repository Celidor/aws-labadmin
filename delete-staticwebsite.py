#!/usr/bin/env python
#initiate from destroy-custodian script
#for testing: python delete-cn7.py --profile celidor --dry_run
import boto3
import sys
import time
import json
import argparse

from botocore.exceptions import ClientError
from datetime import datetime

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")

class s3:
  def __init__(self, profile, dry_run):
    self.profile = profile
    self.dry_run = dry_run

    print "Searching for S3 buckets"
    self.session = boto3.session.Session(profile_name=self.profile)
    self.client = self.session.client('s3')
    buckets = self.client.list_buckets()['Buckets']
    for bucket in buckets:
        if bucket['Name'].startswith('csa'):
            print "Deleting objects in S3 bucket %s" % (bucket['Name'])
            bucketobjects = self.client.list_objects_v2(bucket=bucket)
            for bucketobject in bucketobjects:
                if self.dry_run is None:
                    self.client.delete_object(Name=bucketobject['Name'])

class cloudformation:
  def __init__(self, profile, dry_run):
    self.profile = profile
    self.dry_run = dry_run

    print "Searching for CloudFormation stacks in us-east-1 region"
    self.session = boto3.session.Session(profile_name=self.profile, region_name='us-east-1')
    self.client = self.session.client('cloudformation', region_name='us-east-1')
    stacks = self.client.list_stacks()['StackSummaries']
    for stack in stacks:
        if stack['StackName'].startswith('csa'):
            print "Deleting CloudFormation stack %s in us-east-1 region" % (stack['StackName'])
            if self.dry_run is None:
                self.client.delete_stack(StackName=stack['StackName'])

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="Delete AWS Lab")
  parser.add_argument('--profile', required=True)
  parser.add_argument('--dry_run', action='count')
  args = parser.parse_args()
  profile = args.profile
  dry_run = args.dry_run

  s3(profile, dry_run)
  cloudformation(profile, dry_run)
