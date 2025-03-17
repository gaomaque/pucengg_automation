import logging
import json
import boto3
from pathlib import Path
import typing as t
from os import environ
from botocore.exceptions import ClientError, WaiterError
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

UPDATE_VALID_STATUS = ["CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"]
PARAMETERS = {
    "$ACCFULL": "account_name_caps",  # RSSE03DEV
    "$accfull": "account_name",  # rsse03dev
    "$ACCNUM": "aws_account_number",
    "$IDENTIFIER": "account_identifier",  # RSSE03 /RSSECN03
    "$ENV": "nvs_environment",  # "PGB/GB/DEV/TST"
    "$LABENV": "lab_env",  # PPRD/PRD/DEV/TST
    "$LAB": "lab",  # PRD/PRD/DEVGB/TST
    "$REGION": "aws_region",  # 'us-east-1'
    "$AlarmThreshold1": "alarm_threshold1",
    "$AlarmThreshold": "alarm_threshold",
    "$DomainName": "domain_name",
    "$DNS": "domain_server",
    "$SecondaryVPCRequired": "secondary_cidr_required",
    "$VPCCIDR": "vpc_cidr",
    "$SHORTREGION": "short_region",  # USNV, EUIE
    "$S3RegionCode": "s3_region_code",  # usnv/ ie
    "$NVSAccountAbbr": "nvs_account_abbr",  # RSSR/ RDRAR
    "$NVSAccountName": "nvs_account_name",  # RSS/ DRA
    "$VPCEndpointID": "vpc_endpoint_service_id",
    "$BillingContact": "billing_contact",
    "$Owner": "owner",
    "$CostCenter": "cost_center",
    "$ClarityID": "clarity_id",
    "$IAMENV": "appadm_role_env",  # DEV/PRD/QA
    "$AWSENV": "cfnstackset_aws_env",  # DEVGB/PRD
    "$NVSENV": "cfnstackset_nvs_env",  # PGB/GB
    "$MasterPortfolio": "portfolio_id",
    "$EC2WindowsID": "ec2_windowsproduct_id",
    "$EC2RHELID": "ec2_rhelproduct_id",
    "$EC2AmazonLinuxID": "ec2_amazonlinuxproduct_id",
    "$EBSVolumeID": "ebs_volumeproduct_id",
    "$ENIProductID": "eniproductid",
    "$ECRProductID": "ecrproductid",
    "$DocumentDBID": "documentdbproductid",
    "$AmazonFSXLustreID": "amazonfsxlustreproductid",
    "$AmazonMQBrokerID": "amazon_mqbrokerproductid",
    "$AmazonSSMDocumentID": "amazon_ssmdocumentproductid",
    "$AuroraMySQLMasterID": "auroramysqlmasterproductid",
    "$AuroraMySQLMasterReplicaID": "auroramysqlmasterreplicaid",
    "$AuroraPostgreSQLID": "aurora_product_id",
    "$RDSMariaDBProductID": "rdsmariadbproductid",
    "$RDSMySQLProductID": "rdsmysqlproductid",
    "$RDSPSQLProductID": "rdspsqlproductid",
    "$EKSClusterProductID": "eksclusterproductid",
    "$EKSWorkerNodeProductID": "eksworkernodeproductid",
    "$AWSPARTITION": "aws_partition",  # aws/aws-cn
    "$SecretManagerBucket": "secret_manager_bucket",
    "$ChinaID": "china_id",  # CN
    "$TGWEP": "tgw_id",
}

class ManageStack:

    def __init__(self):
        self.deploy_service = environ.get("deploy_service")
        self.nvs_account_name = "NVGIS" + environ.get("Account")
        self.templates_path_with_service = Path(self.deploy_service, "templates")
        self.templates_path_with_account_name = Path(
            self.deploy_service,
            self.nvs_account_name.lower(),
            "templates",
        )
        self.region = environ.get('Region')
        self.cfn_client = boto3.client('cloudformation', region_name=self.region)
        logger.info(f"AWS CloudFormation client initialized for region: {self.region}")

    def read_file(self, path: t.Union[str, Path]) -> str:
        """Read the file from given path."""
        try:
            with open(path) as fp:
                return fp.read()
        except Exception as exc:
            logger.exception(f"Error while reading the file {path}: {exc}")
            raise

    def update(self, path: t.Optional[t.Union[str, Path]] = None) -> dict:
        if not path:
            path = self.templates_path_with_service / "params.json"
        try:
            params = self.read_file(path)
            if "$" not in params:
                # No placeholders to replace in the file
                return json.loads(params)

            for old, new in PARAMETERS.items():
                params = params.replace(old, getattr(self.configs, new, new))
        except Exception as exc:
            logger.exception(f"Error while updating placeholders in {path}: {exc}")
            raise

        if "$" in params:
            logger.warning(f"Looks like not all placeholders got updated in {path}")
        else:
            logger.debug(f"Placeholders are updated successfully in the file {path}")

        return json.loads(params)
    
    def is_operation_successful(
        self, stack: str, operation: str, delay: int = 20, max_attempts: int = 200
    ):
        """Waiter to check expected state until reached or timeout."""
        try:
            waiter = self.cfn_client.get_waiter(operation)
            waiter_resp = waiter.wait(
                StackName=stack,
                WaiterConfig={"Delay": delay, "MaxAttempts": max_attempts},
            )
            return waiter_resp is None
        except WaiterError as exc:
            logger.exception(str(exc))
            return False
        
    def describe_stack_events(self, stack_name: str) -> list:
        """Describe the stack events and return its response"""
        desc_stack = self.describe_stack(stack_name)
        if not desc_stack:
            logger.error(f"Unable to describe stack events. Stack {stack_name} does not exist")
            return []

        try:
            desc_event = self.cfn_client.describe_stack_events(StackName=stack_name)
        except ClientError as exc:
            msg = f"Exception occurred while describing stack event {exc}"
            logger.exception(msg)
            raise

        return desc_event["StackEvents"]
        
    def log_failed_events(self, stack: str):
        events = self.describe_stack_events(stack)
        for event in events:
            # Don't log initiation events, to avoid abundance of logs.
            if (
                event.get("ResourceStatusReason")
                and "Initiated" not in event["ResourceStatusReason"]
            ):
                logger.error(f"Resource {event['LogicalResourceId']!r} failed. Details: {event}")
        
    def describe_stack(self, stack: str) -> list:
        """Describe the given stack."""
        logger.debug(f"Describing stack: {stack} in region: {self.cfn_client.meta.region_name}")
        resp = {}
        try:
            resp = self.cfn_client.describe_stacks(StackName=stack)
            logger.info(f"Stack {stack!r} status: {resp['Stacks'][0]['StackStatus']}")
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ValidationError":
                logger.info(f"Stack {stack!r} does not exist: {exc}")
                return []
            else:
                logger.exception(f"Error while describing stack: {exc}")
                return []
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return []
        return resp.get("Stacks", [])

    def create_stack(
        self,
        stack: str,
        template: str,
        parameters: list,
        region: str,
        service: str,
        capabilities: list,
        tags: list = []
    ):
        """Create stack for given template and params if doesn't exist.
        Log events in case of failure and delete the stack.
        """
        is_created = True
        stack_details = self.describe_stack(stack)
        if stack_details:
            logger.warning(f"Stack {stack!r} already exists in region {region}, skipping creation.")
            return is_created

        logger.debug(f"Creating the stack {stack} in region {region}")
        try:
            resp = self.cfn_client.create_stack(
                StackName=stack,
                TemplateBody=template,
                Parameters=parameters,
                OnFailure="ROLLBACK",
                Capabilities=capabilities,
                Tags=tags
            )
            is_created = self.is_operation_successful(stack, "stack_create_complete")
        except Exception as exc:
            logger.exception(f"Error occurred while stack creation: {exc}")
            is_created = False
            raise
        finally:
            if not is_created:
                logger.error(f"Looks like some resources failed to create.")
                self.log_failed_events(stack)
                self.delete_stack(stack)
                logger.error("Unable to create stack, check logs for the errors.")
                raise

            else:
                logger.info(
                    f"Successfully created stack: {stack!r} in region {region} "
                    f"|| StackId: {resp['StackId']}"
                )

        return is_created

    def update_stack(
        self,
        stack: str,
        template: str,
        parameters: list,
        region: str,
        service: str,
        capabilities: list,
        tags: list = [],
        use_previous_template: bool = False
    ):
        """
        To determine whether stack is in updatable state and update it.
        """
        is_updated = False
        stack_details = self.describe_stack(stack)
        print("breakpoint01")
        print("Stack Name:", stack)
        print("Stack Details:", stack_details)
        if stack_details:
            print("Stack Status:", stack_details[0]["StackStatus"])
        if not stack_details or stack_details[0]["StackStatus"] not in UPDATE_VALID_STATUS:
            msg = (
                f"Unable to update stack {stack} in {region}: Either stack does not exist or "
                f"not in one of the status {UPDATE_VALID_STATUS}"
            )
            logger.error(msg)
            raise Exception(msg)

        logger.debug(f"Updating the stack {stack} in region {region}")
        try:
            if use_previous_template:
                self.cfn_client.update_stack(
                    StackName=stack,
                    UsePreviousTemplate=True,
                    Parameters=parameters,
                    Capabilities=capabilities,
                )
            else:
                self.cfn_client.update_stack(
                    StackName=stack,
                    TemplateBody=template,
                    Parameters=parameters,
                    Tags=tags,
                    Capabilities=capabilities,
                )

            if service == "vpc":
                self.process_tgw_vpc_attachment(stack, parameters)

            is_updated = self.is_operation_successful(stack, "stack_update_complete")
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ValidationError":
                logger.warning(f"No updates are to be performed on stack {stack!r}: {exc}")
                is_updated = True
            else:
                logger.exception(f"Error occurred while stack {stack!r} update: {exc}")
                is_updated = False
        finally:
            if not is_updated:
                logger.error(f"Looks like some resources failed to update.")
                self.log_failed_events(stack)
                raise Exception(f"Unable to update stack {stack!r}, check logs for errors.")
            else:
                logger.info(f"Successfully updated the stack {stack!r} in region {region}")
        return is_updated

    def delete_stack(self, stack: str):
        """Delete the given stack."""
        deleted = False
        try:
            self.cfn_client.delete_stack(StackName=stack)
            deleted = self.is_operation_successful(stack, "stack_delete_complete")
        except ClientError as exc:
            logger.exception(f"Error while deleting the stack {exc}")
            raise
        if deleted:
            logger.info(f"Stack {stack} deleted successfully.")
        return deleted
