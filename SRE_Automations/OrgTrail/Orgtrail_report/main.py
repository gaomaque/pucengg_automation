'''
Author: Novartis
Contributors: Rohan T
Date: 28-Aug-2023 (Initial Version)

The below code is to get the report of logging status of cloudtrails
'''
import os
from os import environ
from os import getenv, environ as env
import time
import logging
import botocore
import boto3
import sys
import csv
import pandas as pd
import pathlib
import argparse
import multiprocessing
import json
import base64
from json import JSONDecodeError
from multiprocessing import Process, Queue
from collections import defaultdict

from src.client import Client
from src.describe_trails import describetrails
from src.describe_logging import describelogging



LOGGER = logging.getLogger(__name__)
LOGFORMAT = "%(levelname)s: %(message)s"
LOGLEVEL = environ.get("logLevel", "INFO")
logging.basicConfig(format=LOGFORMAT, level=LOGLEVEL)
LOGGER.setLevel(logging.getLevelName(LOGLEVEL))

consolidated_report = []




def process_account(self,LOGGER,client,account_number,region,result_queue):
        LOGGER.info("In Process Account Function")
        
        self.trails=describetrails.trail_describe(self,LOGGER,client,args.region)
        self.logstatus,self.finaltrails=describelogging.trail_logging(self,LOGGER,client,self.trails)    
        

        result = {
        "Account": account_number,
        "Region": region,
        "CloudTrail": self.trails,  
        "IsLogging": self.logstatus
        }

        # Put the result in the queue
        result_queue.put(result)

class UpdateTrail:

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
        Gets the value from enviormental(Jenkins) variables to work with and intialise EC2
        """
        self.LOGGER = logging.getLogger(__name__)
        self.LOGFORMAT = "%(levelname)s: %(message)s"
        self.LOGLEVEL = environ.get("logLevel", "INFO")
        self.LOGGER.setLevel(logging.getLevelName(self.LOGLEVEL))
        logging.basicConfig(format=self.LOGFORMAT, level=self.LOGLEVEL)
        
        self.accountlistpath = environ.get("accountlistpath")
        self.accounts_dict = UpdateTrail.load_file(self,self.accountlistpath)
        self.accounts_list = next(iter(self.accounts_dict.values()))
    
        self.sts_client = boto3.client('sts',
                                aws_access_key_id=env["AWS_ACCESS_KEY_ID"],
                                aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
                                aws_session_token=env["AWS_SESSION_TOKEN"],
                                region_name=args.region
                                )
        
        self.LOGGER.info("INITIALIZED")
                  


    def set_attribute_values(self):
        """
        For setting up the variables used in function
        """  
        #self.Account_List=["66214021555","485518300401","215485818234","289676472149","293577579344","801916421549","683694183969","89962357244","929185228312","738194899855","79269666815","136372785879","286010100817","918755377869","351265263734","800721823318","236004352979","41152793177","564307765449","298872915353","638195538514","130110251512","968951650846","281744559589","686113166178","924176944518","513316938575","337115876117","404582736962","101584274730","601781466253","890919258594","517878202833","388460930217","688036914566","892169486769","158303954326","521080405158","298928099744","778668486846","523656734260","991424192255","993993906334","459852492820","137092925428","576138682393","453979371446","753035392779","388460930217","688036914566","892169486769","158303954326","521080405158","298928099744","534276381798","960102464491","645600662282","266975581066","532533260525","529618256711","473483320493","501973795670","773150721372","783858292221","128010802554","607108443833","714287346229","720243969453","782671389447","501152149066","720243969453","782671389447","501152149066","304512965277","900804374729"]
        #self.Account_List=["304512965277","128010802554","866919043554"]
 
        processes=[]
        results=[]

        # Create a pool of worker processes
        #pool = multiprocessing.Pool()
        result_queue = multiprocessing.Queue()  # Create a queue to collect results

        
        for account_number in self.accounts_list:
            
            self.client,count=Client.aws_client(self,LOGGER,self.sts_client,account_number,args.region,args.region_type)
            if count==0:
                p = Process(target=process_account, args=(self, LOGGER, self.client, account_number, args.region, result_queue))
                processes.append(p)
                p.start()

        for p in processes:
            p.join()

        # Collect results from the queue
        while not result_queue.empty():
            result = result_queue.get()
            consolidated_report.append(result)
        
        print(consolidated_report)  


        
        # Generate a CSV report
        csv_filename = "Unfiltered_Report.csv"
        with open(csv_filename, "a", newline="") as csvfile:
            fieldnames = ["Account", "Region", "CloudTrail", "IsLogging"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write the header only if the file is empty
            if csvfile.tell() == 0:
                writer.writeheader()
            for result in consolidated_report:
                writer.writerow(result)


        
        # Read the CSV file into a DataFrame
        df = pd.read_csv('Unfiltered_Report.csv')
        # Group by 'Account' and aggregate 'Region' and 'Status'
        grouped = df.groupby('Account').agg({'Region': list, 'CloudTrail': list, 'IsLogging': list}).reset_index()
        # Create a new DataFrame to store the reorganized data
        reorganized_df = pd.DataFrame(columns=['Account', 'Region', 'CloudTrail', 'IsLogging'])
        # Populate the new DataFrame
        for idx, row in grouped.iterrows():
            account = row['Account']
            regions = row['Region']
            cloudtrails = row['CloudTrail']
            loggings = row['IsLogging']

'''                        
            for i, region in enumerate(regions):
                               
                if i == 0:                      #so that account number doesn't print multiple times
                    new_row = reorganized_df.concat({'Account': account, 'Region': region, 'CloudTrail': cloudtrails[i].replace("[",'').replace("]",'').replace("'",''), 'IsLogging': loggings[i].replace("[",'').replace("]",'')}, ignore_index=True)
                    reorganized_df = pd.concat([reorganized_df, new_row], ignore_index=True)
                else:
                    new_row = reorganized_df.concat({'Account': '', 'Region': region, 'CloudTrail': cloudtrails[i].replace("[",'').replace("]",'').replace("'",''), 'IsLogging': loggings[i].replace("[",'').replace("]",'')}, ignore_index=True)
                    reorganized_df = pd.concat([reorganized_df, new_row], ignore_index=True)

        # Save the reorganized DataFrame to a new CSV file
        reorganized_df.to_csv('Consolidated_Report.csv', index=False)
'''                

            for i, region in enumerate(regions):
                                
                if i == 0:                      #so that account number doesn't print multiple times
                    reorganized_df = reorganized_df.append({'Account': account, 'Region': region, 'CloudTrail': cloudtrails[i].replace("[",'').replace("]",'').replace("'",''), 'IsLogging': loggings[i].replace("[",'').replace("]",'')}, ignore_index=True)
                else:
                    reorganized_df = reorganized_df.append({'Account': '', 'Region': region, 'CloudTrail': cloudtrails[i].replace("[",'').replace("]",'').replace("'",''), 'IsLogging': loggings[i].replace("[",'').replace("]",'')}, ignore_index=True)

    def main(self):
        self.set_attribute_values()
        

if __name__ == "__main__":

    try: 
        parser = argparse.ArgumentParser(description="Start/Stop logging in cloudtrail")
        parser.add_argument("--region", "-r", required=True, help="Region name")
        parser.add_argument("--region_type", "-rt", required=True, help="Region Type")
        #parser.add_argument("--account", "-r", required=True, help="Account name")
        args = parser.parse_args()
        UpdateTrail_object = UpdateTrail() 
        UpdateTrail_object.main()
    except Exception as error:
        print(str(error))
        exit(1)
