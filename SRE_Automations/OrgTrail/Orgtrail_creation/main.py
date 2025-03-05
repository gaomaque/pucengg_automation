'''
Author: Novartis
Contributor: Chandana Sama

The code will be used to create/ modify custom security group
'''
import os
from os import environ
from os import getenv, environ as env
import logging
from pathlib import Path
import boto3
import json
import multiprocessing
import argparse
import base64
from json import JSONDecodeError
from concurrent.futures import ThreadPoolExecutor, Future
from multiprocessing import Process, Queue


LOGGER = logging.getLogger(__name__)
LOGFORMAT = "%(levelname)s: %(message)s"
LOGLEVEL = os.environ.get("logLevel", "INFO")
logging.basicConfig(format=LOGFORMAT, level=LOGLEVEL)
LOGGER.setLevel(logging.getLevelName(LOGLEVEL))

class DeleteCloudtrailStack:
    """
    summary - this is the main class which inturn calls either 
    Addsgrules or CreateSecurityGroup as per the input
    """
    def load_file(self,path):
        with open(path) as fileobj:
            try:
                data= json.load(fileobj)
            except JSONDecodeError:
                file_name = os.path.basename(path)
                LOGGER.error('The JSON file {} doesnot contain a valid JSON'.format(file_name))
                raise
        return data
    def __init__(self):
        """
        summary - Gets the value from enviormental variables to work with and intialise ec2 client
        """
        if args.region_type == 'china':
            self.all_regions = [
            "cn-north-1",
            "cn-northwest-1"
        ]
        else:
            self.all_regions = [
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "eu-west-1",
            "eu-west-2",
            "eu-west-3",
            "eu-central-1",
            "eu-north-1",
            "ap-south-1",
            "ap-northeast-1",
            "ap-northeast-2",
            "ap-southeast-1",
            "ap-southeast-2",
            "ca-central-1",
            "sa-east-1",
            "ap-northeast-3"
        ]        
        self.env_variables_dict = {}
        
        for key, value in os.environ.items():
            self.env_variables_dict[key]= value
        #self.current_path= Path(Path.cwd(),"SRE_Automations/OrgTrail/Orgtrail_creation/templates/"+self.env_variables_dict['AccountType']+"/cft")
        #self.template_path = str(self.current_path)+".json"
        #self.param_file =  Path(Path.cwd(),"SRE_Automations/OrgTrail/Orgtrail_creation/templates/"+self.env_variables_dict['AccountType']+"/params")
        #self.params_file =str(self.param_file)+".json"
        self.sts_client =boto3.client('sts',
                                aws_access_key_id=env["AWS_ACCESS_KEY_ID"],
                                aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
                                aws_session_token=env["AWS_SESSION_TOKEN"],
                                region_name=args.region)
        self.accountlistpath = environ.get("accountlistpath")
        self.accounts_dict = DeleteCloudtrailStack.load_file(self,self.accountlistpath)
        self.accounts_list = next(iter(self.accounts_dict.values()))
       
    def process_account(self,LOGGER,client,region):        
        self.delete_stack(client)

    def describe_stack(self, stack):
        """Describe the given stack."""
        resp = {}
        try:
            resp = self.cfn_client.describe_stacks(StackName=stack)
            print("in describe start")
        except Exception as exc:
            if exc.response["Error"]["Code"] == "ValidationError":
                LOGGER.info(f"Stack {stack!r} does not exist")
            else:
                LOGGER.exception(f"Error while describing stack: {exc}")
        else:
            LOGGER.info(f"Stack {stack!r} status: {resp['Stacks'][0]['StackStatus']}")
        print("in describe end")
        return resp["Stacks"]
    

    def create_stack(self,stack,template,params,region,capabilities,cfn_client):
        
    #def create_stack(self, stack: str, template: str, tags=[], params=[]):
        """Create stack for given template and params if doesn't exist.
        Log events in case of failure and delete the stack.
        """
        is_created = True
        #stack_details = self.describe_stack(stack)
        print("in create stack start")

        '''if stack_details:
            LOGGER.warning(f"Stack {stack!r} already exists, skipping creation.")
            return is_created'''
        LOGGER.debug(f"Creating the stack {stack}")
        try:
            resp = cfn_client.create_stack(
                    StackName=stack,
                    TemplateBody=template,
                    Parameters=params,
                    Capabilities=capabilities,
                    OnFailure="ROLLBACK",
            )
            print("in create stack try")
        except Exception as e:
            LOGGER.info(f" errror in creating stack:{e} in region {region}")

    
    def fetch_cloudformation(self,path):
        """Collect cloudformation template."""
        with open(path) as json_data:
            return json_data.read()
        

    def aws_client(self,LOGGER,sts_client,accno,region,region_type):

        count=0
        cloudformation_client=""
        try:
            
            #Rolearn="arn:aws:iam::"+accno+":role/RRCC_AWS_INVENTORY"
            #LOGGER.info(Rolearn)            
            if region_type == "china":
                Rolearn="arn:aws-cn:iam::"+accno+":role/RIDY_AWS_AWSGLOBALJITCN01"
            else:
                Rolearn="arn:aws:iam::"+accno+":role/RIDY_AWS_AWSGLOBALJIT01"
            if accno in ["290804939824","485323999369"]:
                cloudformation_client = boto3.client("cloudformation", region)

            else:
                response = sts_client.assume_role(RoleArn=Rolearn,
                                                RoleSessionName="TempAccess2")
                credentials =response['Credentials']
                aws_access_key_id = credentials["AccessKeyId"]
                aws_secret_access_key = credentials["SecretAccessKey"]
                aws_session_token = credentials["SessionToken"]
                cloudformation_client = boto3.client("cloudformation", region, aws_access_key_id=aws_access_key_id,
                                        aws_secret_access_key=aws_secret_access_key, aws_session_token=aws_session_token)
            LOGGER.info("In account {}".format(accno))
            

        except Exception as e:
            LOGGER.info("ERROR IN ASSUMING {}".format(accno))
            count=1

        return cloudformation_client,count
     
    def delete_stack(self,cfn_client):
        """Delete the given stack."""
        try:
            #describe stacks, filter stacks,deletion
            paginator = cfn_client.get_paginator('list_stacks')
            page_iterator = paginator.paginate(StackStatusFilter=[
            'CREATE_IN_PROGRESS','CREATE_FAILED','CREATE_COMPLETE','ROLLBACK_IN_PROGRESS','ROLLBACK_FAILED','ROLLBACK_COMPLETE','DELETE_IN_PROGRESS','DELETE_FAILED','UPDATE_IN_PROGRESS','UPDATE_COMPLETE_CLEANUP_IN_PROGRESS','UPDATE_COMPLETE','UPDATE_FAILED','UPDATE_ROLLBACK_IN_PROGRESS','UPDATE_ROLLBACK_FAILED','UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS','UPDATE_ROLLBACK_COMPLETE','REVIEW_IN_PROGRESS','IMPORT_IN_PROGRESS','IMPORT_COMPLETE','IMPORT_ROLLBACK_IN_PROGRESS','IMPORT_ROLLBACK_FAILED','IMPORT_ROLLBACK_COMPLETE'
            ])
            for page in page_iterator:
                stack_summaries = page.get('StackSummaries', [])
                for summary in stack_summaries:
                    #LOGGER.info(summary['StackName'])
                    if summary['StackName'] not in ["NVSGISMST-ORGCLOUDTRAIL","NVGISMSTCN-CLOUDTRAIL-ORG"]:
                        if (
                            "CTR-TST-ENC" in summary['StackName'] or                            
                            "CTR-ENC" in summary['StackName'] or
                            "NVSGISBCK-KMS" in summary['StackName'] or
                            "CLOUDTRAIL" in summary['StackName'] or
                            "NVSGISADT-KMS" in summary['StackName'] or
                            "NVSGISADT-NonKMS" in summary['StackName']):                            
                        #if "CTR-TST-ENC" in summary['StackName'] "CTR-KMS" in summary['StackName'] or "CTR-ENC" in summary['StackName'] or "NVSGISBCK-KMS" in summary['StackName'] or "CLOUDTRAIL" in summary['StackName'] or "NVSGISADT-KMS" in summary['StackName'] or "NVSGISADT-NonKMS" in summary['StackName']:
                            cfn_client.delete_stack(StackName=summary['StackName'])
                            LOGGER.info(f"Stack name queued for deletion is {summary['StackName']}")
                            #deleted = self.is_operation_successful(stack, "stack_delete_complete",cfn_client)
        except Exception as exc:
            LOGGER.exception(f"Error while deleting the stack {exc}")

    def delete_stack_parallel(self):
        processes=[]
        for account_number in self.accounts_list:
            
            self.client,count=self.aws_client(LOGGER,self.sts_client,account_number,args.region,args.region_type)
            if count==0:
                p = Process(target=self.process_account, args=(LOGGER, self.client, args.region))
                processes.append(p)
                p.start()

        for p in processes:
            p.join()
    
    def cloudtrail_stack(self):
        try:
            stack_name = "NVSGIS"+self.env_variables_dict['AccountType'].upper()+"CLOUDTRAIL"
            stack_name = stack_name.replace("_","-")
            cfn_template = self.fetch_cloudformation(self.template_path)
            params = self.fetch_cloudformation(self.params_file)
            params = json.loads(params)
            all_regions = self.all_regions
            with ThreadPoolExecutor() as executor:
                futures_by_region = {}
                for region in all_regions:
                    cfn_client = boto3.client("cloudformation", region_name = region)
                    
                    if self.env_variables_dict['Action'] =='create':
                        func = self.create_stack
                        future: Future = executor.submit(
                            func,
                            stack_name,
                            cfn_template,
                            params[region],
                            region,
                            ["CAPABILITY_AUTO_EXPAND", "CAPABILITY_NAMED_IAM"],
                            cfn_client
                        )
                        futures_by_region[region] = future
                   

            is_success = all([future.result() for future in futures_by_region.values()])
            '''
            for region in all_regions:
                param= params[region]
                cfn_client = boto3.client("cloudformation", region_name = region)
                self.create_stack(
                    stack_name,
                    cfn_template,
                    param,
                    region,
                    ["CAPABILITY_AUTO_EXPAND", "CAPABILITY_NAMED_IAM"],
                    cfn_client
                )
            '''
        except Exception:
            is_success = False
            raise

    def main(self):

        
        # can add conditional for delete in later cases
        if self.env_variables_dict['Action'] =='create':
            self.cloudtrail_stack()
        elif self.env_variables_dict['Action']=='delete':
            self.delete_stack_parallel()


if __name__ =="__main__":
    try: 
        parser = argparse.ArgumentParser(description="Delete cloudtrail stacks")
        parser.add_argument("--region", "-r", required=True, help="Region name")
        parser.add_argument("--region_type", "-rt", required=True, help="Region Type")
        #parser.add_argument("--account", "-r", required=True, help="Account name")
        args = parser.parse_args()
        DeleteCloudtrailStack_object = DeleteCloudtrailStack() 
        DeleteCloudtrailStack_object.main()
    except Exception as error:
        LOGGER.info(str(error))
        exit(1)

