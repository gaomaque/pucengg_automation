import boto3


class Client:


    def aws_client(self,LOGGER,sts_client,accno,region,region_type):

        count=0
        cloudtrail_client=""
        try:
            
            #Rolearn="arn:aws:iam::"+accno+":role/RRCC_AWS_INVENTORY"
            #LOGGER.info(Rolearn)
            Rolearn="arn:aws:iam::"+accno+":role/RIDY_AWS_AWSGLOBALJIT01"
            
            response = sts_client.assume_role(RoleArn=Rolearn,
                                              RoleSessionName="TempAccess2")
            credentials =response['Credentials']
            aws_access_key_id = credentials["AccessKeyId"]
            aws_secret_access_key = credentials["SecretAccessKey"]
            aws_session_token = credentials["SessionToken"]
            cloudtrail_client = boto3.client("cloudtrail", region, aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key, aws_session_token=aws_session_token)
            LOGGER.info("In account {}".format(accno))
            

        except Exception as e:
            LOGGER.info("ERROR IN ASSUMING {}".format(accno))
            count=1

        return cloudtrail_client,count
