#!/usr/bin/env python
#for testing: python delete-aws-egress.py --profile celidor --region eu-west-1 --dry_run
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

    print("Searching for ec2 resources")

    self.session = boto3.session.Session(profile_name=self.profile)
    self.client = self.session.client('ec2', region_name=region)

    templates = self.client.describe_launch_templates()['LaunchTemplates']
    for template in templates:
        if "Tags" in template:
          for tag in template['Tags']:
            if (tag['Key'] == "Name" and tag['Value'].startswith('aws-egress')) or (tag['Key'] == "Name" and tag['Value'].startswith('discrimiNAT')):      
              print("Deleting launch template %s" % template['LaunchTemplateName'])
              if self.dry_run is None:
                self.client.delete_launch_template(LaunchTemplateId=template['LaunchTemplateId'])
    
    reservations = self.client.describe_instances()['Reservations']
    for reservation in reservations:
      for inst in reservation['Instances']:
        if "Tags" in inst and inst['State']['Name'] != "terminated":
          for tag in inst['Tags']:
            if (tag['Key'] == "Name" and tag['Value'].startswith('aws-egress')) or (tag['Key'] == "Name" and tag['Value'].startswith('discrimiNAT')):      
              print("Terminating instance %s" % inst['InstanceId'])
              if self.dry_run is None:
                self.client.terminate_instances(InstanceIds=[ inst['InstanceId'] ])
                while self.client.describe_instances(InstanceIds=[ inst['InstanceId'] ])['Reservations'][0]['Instances'][0]['State']['Name'] != 'terminated': print("waiting for instance termination..")
                time.sleep(5)
              time.sleep(20)

    gateways = self.client.describe_nat_gateways()['NatGateways']
    for gateway in gateways:
        if "Tags" in gateway:
          for tag in gateway['Tags']:
            if (tag['Key'] == "Name" and tag['Value'].startswith('aws-egress') and gateway['State'] != 'deleted'):      
              print("Deleting NAT Gateway %s" % tag['Value'])
              if self.dry_run is None:
                self.client.delete_nat_gateway(NatGatewayId=gateway['NatGatewayId'])
                while self.client.describe_nat_gateways(NatGatewayIds=[gateway['NatGatewayId']])['NatGateways'][0]['State'] != 'deleted': print("waiting for NAT Gateway deletion..")
                time.sleep(5)
              time.sleep(20)

    nics = self.client.describe_network_interfaces()['NetworkInterfaces']
    for nic in nics:
        if "TagSet" in nic:
          for tag in nic['TagSet']:
            if (tag['Key'] == "Name" and tag['Value'].startswith('aws-egress')) or (tag['Key'] == "Name" and tag['Value'].startswith('discrimiNAT')):      
              print("Deleting network interface %s" % tag['Value'])
              if self.dry_run is None:
                self.client.delete_network_interface(NetworkInterfaceId=nic['NetworkInterfaceId'])

    endpoints = self.client.describe_vpc_endpoints()['VpcEndpoints']
    for endpoint in endpoints:
        if "Tags" in endpoint:
          for tag in endpoint['Tags']:
            if (tag['Key'] == "Name" and tag['Value'].startswith('aws-egress') and endpoint['State'] != 'deleted'):      
              print("Deleting VPC Endpoint %s" % tag['Value'])
              if self.dry_run is None:
                self.client.delete_vpc_endpoints(VpcEndpointIds=[endpoint['VpcEndpointId']])
                while self.client.describe_vpc_endpoints(VpcEndpointIds=[endpoint['VpcEndpointId']])['VpcEndpoints'][0]['State'] != 'deleted': print("waiting for VPC Endpoint deletion..")
                time.sleep(5)
              time.sleep(20)

    igs = self.client.describe_internet_gateways()['InternetGateways']
    vpcs = self.client.describe_vpcs()['Vpcs']

    for vpc in vpcs:
      if "Tags" in vpc:
        for tag in vpc['Tags']:
          if (tag['Key'] == "Name" and tag['Value'].startswith('aws-egress')):
            
            acls = self.client.describe_network_acls(Filters=[{'Name': 'vpc-id', 'Values': [ vpc['VpcId'] ] } ])['NetworkAcls']
            for acl in acls:
              if acl['IsDefault'] != True:
                print("Deleting network acl %s" % acl['NetworkAclId'])
                if self.dry_run is None:
                  self.client.delete_network_acl(NetworkAclId=acl['NetworkAclId'])

            for ig in igs:
              for att in ig['Attachments']:
                if att['VpcId'] == vpc['VpcId']:
                  print("Deleting ig %s" % ig['InternetGatewayId'])
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
                  print("Dissassociating Route Table %s" % assoc['RouteTableAssociationId'])
                  if self.dry_run is None:
                    self.client.disassociate_route_table(AssociationId=assoc['RouteTableAssociationId'])
              for route in rt['Routes']:
                if 'GatewayId' in route and route['GatewayId'] != 'local':
                  print("Deleting route: %s (destination: %s)" % (rt['RouteTableId'], route['DestinationCidrBlock']))
                  if self.dry_run is None:
                    self.client.delete_route(RouteTableId=rt['RouteTableId'], DestinationCidrBlock=route['DestinationCidrBlock'])
              myassoc = 0
              for assoc in rt['Associations']:
                if assoc['Main'] is True:
                  myassoc = 1
              if myassoc == 0:
                print("Delete Route Table: %s" % rt['RouteTableId'])
                if self.dry_run is None:
                  self.client.delete_route_table(RouteTableId=rt['RouteTableId'])

            subnets = self.client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [ vpc['VpcId'] ] } ])['Subnets']
            for subnet in subnets:
              print("Deleting subnet %s" % subnet['SubnetId'])
              #print json.dumps(subnet, sort_keys=True, indent=2, default=json_serial)
              if self.dry_run is None:
                self.client.delete_subnet(SubnetId=subnet['SubnetId'])          

            sgs = self.client.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [ vpc['VpcId'] ] } ])['SecurityGroups']
            for sg in sgs:
              if "Tags" in sg:
                for tag in sg['Tags']:
                  if (tag['Key'] == "Name" and tag['Value'].startswith('aws-egress')):
                    #print("==========")
                    #print(json.dumps(sg, sort_keys=True, indent=2, default=json_serial))
                    #print("==========")
                    print("Deleting sg %s" % sg['GroupName'])
                    if self.dry_run is None:
                      for i in range(0, 20):
                        try:
                          self.client.delete_security_group(GroupId=sg['GroupId'])
                          print("deleted %s" % sg['GroupName'])
                          break
                        except ClientError as e:
                          print("retrying: (error: %s)" % e)
                          time.sleep(10)
                          continue

            print("Deleting vpc %s" % vpc['VpcId'])
            if self.dry_run is None:
              for i in range(0, 20):
                try:
                  self.client.delete_vpc(VpcId=vpc['VpcId'])
                  print("deleted %s" % vpc['VpcId'])
                  break
                except ClientError as e:
                  print("retrying: (error: %s)" % e)
                  time.sleep(10)
                  continue

class autoscaling:
  def __init__(self, profile, region, dry_run):

    self.profile = profile
    self.dry_run = dry_run

    print("Searching for autoscaling resources")

    self.session = boto3.session.Session(profile_name=self.profile)
    self.client = self.session.client('autoscaling', region_name=region)

    groups = self.client.describe_auto_scaling_groups()['AutoScalingGroups']
    for group in groups:
        if group['AutoScalingGroupName'].startswith('discriminat') or group['AutoScalingGroupName'].startswith('aws-egress'):
          print("Deleting autoscaling group %s" % group['AutoScalingGroupName'])
          if self.dry_run is None:
            self.client.delete_auto_scaling_group(AutoScalingGroupName=group['AutoScalingGroupName'])

class iam:
  def __init__(self, profile, dry_run):

    self.profile = profile
    self.dry_run = dry_run

    print("Searching for IAM roles")

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
      if role['RoleName'].startswith('aws-egress'):
        #print json.dumps(role, sort_keys=True, indent=2, default=json_serial)
        for role_policy in role ['RolePolicyList']:
          print("Delete inline role policy %s from role %s" % (role_policy['PolicyName'], role['RoleName']))
          if self.dry_run is None:
            self.client.delete_role_policy(RoleName=role ['RoleName'], PolicyName= role_policy['PolicyName'])
        for policy in role['AttachedManagedPolicies']:
          print("Detach policy %s from role %s" % (policy['PolicyArn'], role['RoleName']))
          if self.dry_run is None:
            self.client.detach_role_policy(RoleName=role['RoleName'], PolicyArn=policy['PolicyArn'])
        for instanceprofile in role['InstanceProfileList']:
          print("Remove role %s from instance profile %s" % (role['RoleName'], instanceprofile['InstanceProfileName']))
          if self.dry_run is None:
            self.client.remove_role_from_instance_profile(InstanceProfileName=instanceprofile['InstanceProfileName'], RoleName=role['RoleName'])
          print("Delete instance profile %s" % (instanceprofile['InstanceProfileName']))
          if self.dry_run is None:
            self.client.delete_instance_profile(InstanceProfileName=instanceprofile['InstanceProfileName'])
        print("Delete role %s" % role['RoleName'])
        if self.dry_run is None:
          self.client.delete_role(RoleName=role['RoleName'])

    print("Searching for IAM policies")
    for policy in allpolicies:
      if policy['PolicyName'].startswith('aws-egress') and policy['PolicyName'] != "aws-egress-deploy":
        print("Delete policy %s" % (policy['Arn']))
        if self.dry_run is None:
          self.client.delete_policy(PolicyArn=policy['Arn'])


class logs:
  def __init__(self, profile, region, dry_run):

    self.profile = profile
    self.dry_run = dry_run

    print("Searching for Cloudwatch log groups")

    self.session = boto3.session.Session(profile_name=self.profile)
    self.client = self.session.client('logs', region_name=region)

    log_groups = self.client.describe_log_groups()['logGroups']
    for log_group in log_groups:
        if log_group['logGroupName'].startswith('/aws-egress'):
          print("Deleting Cloudwatch log group %s" % log_group['logGroupName'])
          if self.dry_run is None:
            self.client.delete_log_group(logGroupName=log_group['logGroupName'])

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="Delete AWS Egress")
  parser.add_argument('--profile', required=True)
  parser.add_argument('--region', required=True)
  parser.add_argument('--dry_run', action='count')

  args = parser.parse_args()

  profile = args.profile
  region = args.region
  dry_run = args.dry_run

  ec2(profile, region, dry_run)
  autoscaling(profile, region, dry_run)
  logs(profile, region, dry_run)
  iam(profile, dry_run)
