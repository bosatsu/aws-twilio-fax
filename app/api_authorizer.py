import logging

import boto3
from botocore.exceptions import ClientError

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def build_auth_policy(effect):
    auth_policy = {
        "principalId": "*",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": "*"
                }
            ]
        }
    }
    return auth_policy


def lambda_handler(event, context):
    logger.info("Received event.")
    logger.info(event)

    api_client = boto3.client('apigateway')
    request_key_id = event['queryStringParameters']['id']
    request_key_value = event['queryStringParameters']['key']
    auth_policy = build_auth_policy('Deny')

    try:
        api_key = api_client.get_api_key(
            apiKey=request_key_id,
            includeValue=True
        )

        if api_key['value'] == request_key_value:
            auth_policy = build_auth_policy('Allow')

    except ClientError as e:
        logger.info(f"Unable to retrieve api key with id {request_key_id}")
        logger.error(e.response['Error']['Message'])

    return auth_policy
