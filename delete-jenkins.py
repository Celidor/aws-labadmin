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

class elb:
  def __init__(self, profile, region, dry_run):

    self.profile = profile
    self.dry_run = dry_run

    print "Searching for ELBs"

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

    sgs = self.client.describe_security_groups()['SecurityGroups']
    for sg in sgs:
      if sg['GroupName'].startswith('jenkins'):
        #print "=========="
        #print json.dumps(sg, sort_keys=True, indent=2, default=json_serial)
        #print "=========="
        print "Deleting sg %s" % sg['GroupName']
        if self.dry_run is None:
          for i in xrange(0, 20):
            try:
              self.client.delete_security_group(GroupId=sg['GroupId'])
              print "deleted security group %s" % sg['GroupName']
              break
            except ClientError as e:
              print "retrying: (error: %s)" % e
              time.sleep(10)
              continue

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

    response = self.client.get_account_authorization_details(Filter=[
      'Role','LocalManagedPolicy','AWSManagedPolicy'],MaxItems=1000)
    print json.dumps(response, sort_keys=True, indent=2, default=json_serial)

    allroles    = response['RoleDetailList']
    allpolicies = response['Policies']

    while response['IsTruncated'] == True:
      marker = response['Marker']
      response = self.client.get_account_authorization_details(Marker=marker)
      allroles.extend(response['RoleDetailList'])
      allpolicies.extend(response['Policies'])

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
        for instanceprofile in role['InstanceProfileList']:
          print "Remove role %s from instance profile %s" % (role['RoleName'], instanceprofile['InstanceProfileName'])
          if self.dry_run is None:
            self.client.remove_role_from_instance_profile(InstanceProfileName=instanceprofile['InstanceProfileName'], RoleName=role['RoleName'])
          print "Delete instance profile %s" % (instanceprofile['InstanceProfileName'])
          if self.dry_run is None:
            self.client.delete_instance_profile(InstanceProfileName=instanceprofile['InstanceProfileName'])
        print "Delete role %s" % role['RoleName']
        if self.dry_run is None:
          self.client.delete_role(RoleName=role['RoleName'])

    print "Searching for IAM policies"
    for policy in allpolicies:
      if policy['PolicyName'].startswith('jenkins'):
        print "Delete policy %s" % (policy['Arn'])
        if self.dry_run is None:
          self.client.delete_policy(PolicyArn=policy['Arn'])

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="Delete Jenkins")
  parser.add_argument('--profile', required=True)
  parser.add_argument('--region', required=True)
  parser.add_argument('--dry_run', action='count')

  args = parser.parse_args()

  profile = args.profile
  region = args.region
  dry_run = args.dry_run

  elb(profile, region, dry_run)
  ec2(profile, region, dry_run)
  iam(profile, dry_run)
