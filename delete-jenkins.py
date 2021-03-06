#!/usr/bin/env python
#initiate from destroy-awslab script
#for testing: python delete-jenkins.py --profile celidor --region eu-west-1 --dry_run
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
          time.sleep(20)

    targetgroups = self.client.describe_target_groups()['TargetGroups']
    #print json.dumps(targetgroups, sort_keys=True, indent=2, default=json_serial)

    for targetgroup in targetgroups:
      if targetgroup['TargetGroupName'].startswith('jenkins'):
        #print json.dumps(targetgroup, sort_keys=True, indent=2, default=json_serial)
        print "Deleting target group %s" % targetgroup['TargetGroupName']
        if self.dry_run is None:
          self.client.delete_target_group(TargetGroupArn=targetgroup['TargetGroupArn'])

class ec2:
  def __init__(self, profile, region, dry_run):

    self.profile = profile
    self.dry_run = dry_run

    print "Searching for ec2 resources"

    self.session = boto3.session.Session(profile_name=self.profile)
    self.client = self.session.client('ec2', region_name=region)

    igs = self.client.describe_internet_gateways()['InternetGateways']
    vpcs = self.client.describe_vpcs()['Vpcs']

    for vpc in vpcs:
      if "Tags" in vpc:
        for tag in vpc['Tags']:
          if tag['Key'] == "Name" and tag['Value'].startswith('jenkins'):
            ngws = self.client.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [ vpc['VpcId'] ] } ])['NatGateways']
            for ngw in ngws:
              print "Deleting ngw %s" % ngw['NatGatewayId']
              if self.dry_run is None:
                self.client.delete_nat_gateway(NatGatewayId=ngw['NatGatewayId'])

            insts = self.client.describe_instances(Filters=[{'Name': 'vpc-id', 'Values': [ vpc['VpcId'] ] }, {'Name':'instance-state-name', 'Values':[ 'running' ]}])['Reservations']
            #print json.dumps(insts, sort_keys=True, indent=2, default=json_serial)
            for inc in insts:
              for inst in inc['Instances']:
                print "Terminating instance %s" % inst['InstanceId']
                if self.dry_run is None:
                  self.client.terminate_instances(InstanceIds=[ inst['InstanceId'] ])
                  while self.client.describe_instances(InstanceIds=[ inst['InstanceId'] ])['Reservations'][0]['Instances'][0]['State']['Name'] != 'terminated':                        print "waiting for instance termination.."
                  time.sleep(5)
                time.sleep(20)

            acls = self.client.describe_network_acls(Filters=[{'Name': 'vpc-id', 'Values': [ vpc['VpcId'] ] } ])['NetworkAcls']
            for acl in acls:
              if acl['IsDefault'] != True:
                print "Deleting network acl %s" % acl['NetworkAclId']
                if self.dry_run is None:
                  self.client.delete_network_acl(NetworkAclId=acl['NetworkAclId'])

            sgs = self.client.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [ vpc['VpcId'] ] } ])['SecurityGroups']
            for sg in sgs:
              if sg['GroupName'] != 'default':
                #print "=========="
                #print json.dumps(sg, sort_keys=True, indent=2, default=json_serial)
                #print "=========="
                print "Deleting sg %s" % sg['GroupName']
                if self.dry_run is None:
                  for i in xrange(0, 20):
                    try:
                      self.client.delete_security_group(GroupId=sg['GroupId'])
                      print "deleted %s" % sg['GroupName']
                      break
                    except ClientError as e:
                      print "retrying: (error: %s)" % e
                      time.sleep(10)
                      continue

            for ig in igs:
              for att in ig['Attachments']:
                if att['VpcId'] == vpc['VpcId']:
                  print "Deleting ig %s" % ig['InternetGatewayId']
                  if self.dry_run is None:
                    self.client.detach_internet_gateway(InternetGatewayId=ig['InternetGatewayId'], VpcId=vpc['VpcId'])
                    self.client.delete_internet_gateway(InternetGatewayId=ig['InternetGatewayId'])

            rts = self.client.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [ vpc['VpcId'] ] } ])['RouteTables']
            for rt in rts:
              #print "=========="
              #print json.dumps(rt, sort_keys=True, indent=2, default=json_serial)
              #print "=========="
              for assoc in rt['Associations']:
                if assoc['Main'] is not True:
                  print "Dissassociating Route Table %s" % assoc['RouteTableAssociationId']
                  if self.dry_run is None:
                    self.client.disassociate_route_table(AssociationId=assoc['RouteTableAssociationId'])
              for route in rt['Routes']:
                if 'GatewayId' in route and route['GatewayId'] != 'local':
                  print "Deleting route: %s (destination: %s)" % (rt['RouteTableId'], route['DestinationCidrBlock'])
                  if self.dry_run is None:
                    self.client.delete_route(RouteTableId=rt['RouteTableId'], DestinationCidrBlock=route['DestinationCidrBlock'])
              myassoc = 0
              for assoc in rt['Associations']:
                if assoc['Main'] is True:
                  myassoc = 1
              if myassoc == 0:
                print "Delete Route Table: %s" % rt['RouteTableId']
                if self.dry_run is None:
                  self.client.delete_route_table(RouteTableId=rt['RouteTableId'])
              vpcp = self.client.describe_vpc_peering_connections(Filters=[{'Name': 'requester-vpc-info.vpc-id', 'Values': [ vpc['VpcId'] ]}])['VpcPeeringConnections']
              if len(vpcp) > 0:
                print "Delete vpc peering connection %s" % vpcp[0]['VpcPeeringConnectionId']
                if self.dry_run is None:
                  self.client.delete_vpc_peering_connection(VpcPeeringConnectionId=vpcp[0]['VpcPeeringConnectionId'])

            subnets = self.client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [ vpc['VpcId'] ] } ])['Subnets']
            for subnet in subnets:
              print "Deleting subnet %s" % subnet['SubnetId']
              #print json.dumps(subnet, sort_keys=True, indent=2, default=json_serial)
              if self.dry_run is None:
                self.client.delete_subnet(SubnetId=subnet['SubnetId'])

        for vpc in vpcs:
          if "Tags" in vpc:
            for tag in vpc['Tags']:
              if tag['Key'] == "Name" and tag['Value'].startswith('jenkins'):
                print "Deleting vpc %s" % vpc['VpcId']
                if self.dry_run is None:
                  for i in xrange(0, 20):
                    try:
                      self.client.delete_vpc(VpcId=vpc['VpcId'])
                      print "deleted %s" % vpc['VpcId']
                      break
                    except ClientError as e:
                      print "retrying: (error: %s)" % e
                      time.sleep(10)
                      continue
      
    keypairs = self.client.describe_key_pairs()['KeyPairs']
    #print json.dumps(keypairs, sort_keys=True, indent=2, default=json_serial)

    for keypair in keypairs:
      if keypair['KeyName'].startswith('jenkins'):
        #print json.dumps(targetgroup, sort_keys=True, indent=2, default=json_serial)
        print "Deleting key pair %s" % keypair['KeyName']
        if self.dry_run is None:
          self.client.delete_key_pair(KeyName=keypair['KeyName'])

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
