#!/usr/bin/env python
#initiate from destroy-awslab script
#for testing: python delete-jenkis.py --profile celidor --region eu-west-1 --dry_run
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

class ec2:
  def __init__(self, profile, region, dry_run):

    self.profile = profile
    self.dry_run = dry_run

    print "Searching for ec2 resources"
    self.session = boto3.session.Session(profile_name=self.profile)
    self.client = self.session.client('ec2', region_name=region)

    instances = self.client.describe_instances()['Reservations']
    #print json.dumps(instances, sort_keys=True, indent=2, default=json_serial)
    for inc in instances:
      for instance in inc['Instances']:
        if instance['KeyName'].startswith('jenkins'):
            print "Terminating instance %s" % instance['InstanceId']
            if self.dry_run is None:
              self.client.terminate_instances(InstanceIds=[ instance['InstanceId'] ])
              while self.client.describe_instances(InstanceIds=[ instance['InstanceId'] ])['Reservations'][0]['Instances'][0]['State']['Name'] != 'terminated':
                print "waiting for instance termination.."
                time.sleep(5)

class elb:
  def __init__(self, profile, region, dry_run):

    self.profile = profile
    self.dry_run = dry_run

    self.session = boto3.session.Session(profile_name=self.profile)
    self.client = self.session.client('elbv2', region_name=region)

    elbs = self.client.describe_load_balancers()['LoadBalancers']
    #print json.dumps(elbs, sort_keys=True, indent=2, default=json_serial)

    for elb in elbs:
      if elb['LoadBalancerName'].startswith('jenkins'):
        #print json.dumps(elb, sort_keys=True, indent=2, default=json_serial)
        print "Deleting elb %s" % elb['LoadBalancerName']
        if self.dry_run is None:
          self.client.delete_load_balancer(LoadBalancerArn=elb['LoadBalancerArn'])

class iam:
  def __init__(self, profile, dry_run):

    self.profile = profile
    self.dry_run = dry_run

    print "Searching for IAM roles"

    self.session = boto3.session.Session(profile_name=self.profile)
    self.client = self.session.client('iam')

    allroles = []
    allpolicies = []
    allusers = []

    response = self.client.get_account_authorization_details(MaxItems=1000)
    #print json.dumps(response, sort_keys=True, indent=2, default=json_serial)

    allroles    = response['RoleDetailList']
    allusers    = response['UserDetailList']

    while response['IsTruncated'] == True:
      marker = response['Marker']
      response = self.client.get_account_authorization_details(Marker=marker)
      allroles.extend(response['RoleDetailList'])
      allusers.extend(response['UserDetailList'])

    for role in allroles:
      if role['RoleName'].startswith('jenkins'):
        #print json.dumps(role, sort_keys=True, indent=2, default=json_serial)
        for role_policy in role ['RolePolicyList']:
          print "Delete inline role policy %s from role %s" % (role_policy['PolicyName'], role['RoleName'])
          if self.dry_run is None:
            self.client.delete_role_policy(RoleName=role ['RoleName'], PolicyName= role_policy['PolicyName'])
        for policy in role['AttachedManagedPolicies']:
          print "Detach policy %s from role %s" % (policy['PolicyArn'], role['RoleName'])
          if self.dry_run is None:
            self.client.detach_role_policy(RoleName=role['RoleName'], PolicyArn=policy['PolicyArn'])
        for policy in role['AttachedManagedPolicies']:
          if policy['PolicyName'].startswith('jenkins'):
            print "Delete policy %s" % (policy['PolicyArn'])
          if self.dry_run is None:
            self.client.Policy.delete(PolicyArn=policy['PolicyArn'])
        for instanceprofile in role['InstanceProfileList']:
          print "Remove role %s from instance profile %s" % (role['RoleName'], instanceprofile['InstanceProfileName'])
          if self.dry_run is None:
            self.client.remove_role_from_instance_profile(InstanceProfileName=instanceprofile['InstanceProfileName'], RoleName=role['RoleName'])
        for instanceprofile in role['InstanceProfileList']:
          print "Deleting instance profile %s" % (instanceprofile['InstanceProfileName'])
          if self.dry_run is None:
            self.client.InstanceProfile.delete(Name=instanceprofile['InstanceProfileName'])
        print "Delete role %s" % role['RoleName']
        if self.dry_run is None:
          self.client.delete_role(RoleName=role['RoleName'])


if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="Delete Jenkins")
  parser.add_argument('--profile', required=True)
  parser.add_argument('--region', required=True)
  parser.add_argument('--dry_run', action='count')

  args = parser.parse_args()

  profile = args.profile
  region = args.region
  dry_run = args.dry_run

  ec2(profile, region, dry_run)
  elb(profile, region, dry_run)
  iam(profile, dry_run)