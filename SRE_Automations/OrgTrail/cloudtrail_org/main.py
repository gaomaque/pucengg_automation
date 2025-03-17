
from manage import ManageStack
from os import environ
import boto3
import os
import logging
import json

LOGGER = logging.getLogger(__name__)
LOGFORMAT = "%(levelname)s: %(message)s"
LOGLEVEL = environ.get("logLevel", "INFO")
logging.basicConfig(format=LOGFORMAT, level=LOGLEVEL)
LOGGER.setLevel(logging.getLevelName(LOGLEVEL))


manage_stack = ManageStack()

'''
parameters = [
    {'ParameterKey': 'PrimaryKeyElementName',
        'ParameterValue': 'opsOQRRunPrimaryKeyName'
    },
    {'ParameterKey': 'PrimaryKeyElementType',
        'ParameterValue': 'S'
    },
    {'ParameterKey': 'SortKeyElementName',
        'ParameterValue': 'OPSOQR338RUN'
    },
    {'ParameterKey': 'SortKeyElementType',
        'ParameterValue': 'S'
    },
    {'ParameterKey': 'DynamoDBTableName',
        'ParameterValue': 'OPSOQR338RUN'
    },
    {'ParameterKey': 'ReadCapacityUnits',
        'ParameterValue': '1'
    },
    {'ParameterKey': 'WriteCapacityUnits',
        'ParameterValue': '1'
    },
    {'ParameterKey': 'GlobalTable',
        'ParameterValue': 'None'
    },
    {'ParameterKey': 'EnableSortKey',
        'ParameterValue': 'false'
    },
    {'ParameterKey': 'PointInTimeRecovery',
        'ParameterValue': 'true'
    },
    {'ParameterKey': 'DynamodbEncryptionKey',
        'ParameterValue': 'OPSOQR338RUN'
    },
    {'ParameterKey': 'DynamodbEncryptionKeyReplica',
        'ParameterValue': ""
    },
    {'ParameterKey': 'ReplicationRegion',
        'ParameterValue': "none"
    },
]


with open('template_tst.json', 'r') as file_:
    template = file_.read()




'''
if environ['Account'] == 'MST':
    with open('../../../MST/cloudtrail_org/templates/cloudformation.json') as templ:
        template = templ.read()
    with open('../../../MST/cloudtrail_org/templates/params.json') as params:
        parameters = json.load(params)[environ['Region']]

if environ['Account'] in ['MSTCN','MSTTSTCN']:
    with open('../../../MST/cloudtrail_org_cn/templates/cloudformation.json') as templ:
        template = templ.read()
    with open('../../../MST/cloudtrail_org_cn/templates/params.json') as params:
        parameters = json.load(params)[environ['Region']]

if environ['Account'] == 'CTR':
    with open('../CTR/orgctr_s3/templates/cloudformation.json') as templ:
        template = templ.read()
    with open('../CTR/orgctr_s3/templates/params.json') as params:
        parameters = json.load(params)[environ['Region']]

if environ['Account'] == 'CTRTST':
    with open('../CTR/orgctr_s3_tst/templates/cloudformation.json') as templ:
        template = templ.read()
    with open('../CTR/orgctr_s3/templates/params.json') as params:
        parameters = json.load(params)[environ['Region']]

LOGGER.info('template')
LOGGER.info(template)
LOGGER.info('parameters')
LOGGER.info(parameters)

if environ['Action'] =='create':
    manage_stack.create_stack(
        environ['StackName'],
        template=template,
        parameters=parameters,
        region=environ['Region'],
        service='Cloudtrail',
        capabilities=[],
        tags=[]
        )
elif environ['Action'] == 'update':
    
    manage_stack.update_stack(
        environ['StackName'],
        template=template,
        parameters=parameters,
        region=environ['Region'],
        service='Cloudtrail',
        capabilities=[],
        tags=[],
        use_previous_template =False,
        )
