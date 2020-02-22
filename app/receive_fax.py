from datetime import datetime
import logging
import os
from urllib.parse import parse_qs

import boto3
from botocore.exceptions import ClientError
import requests


# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ssm_client = boto3.client('ssm')

# Create generic 403 response
return_403 = {
    "statusCode": 403,
    "headers": {"Content-Type": 'application/json'},
    "body": {"message": "Missing Authentication Token"}
}


def lambda_handler(event, context):
    logger.info("Received event.")
    logger.info(event)

    method = event['httpMethod']
    path = event['path']

    # handle posts to /fax/check endpoint, starting point for Twilio communication
    # returns endpoint where Twilio should send the fax
    if method == 'POST' and path == '/fax/check':
        twiml = """
            <Response>
                <Receive action="/Prod/fax/receive"/>
            </Response>
        """

        logger.info("Executed /fax/check endpoint, returned twiml code")

        return {
            "statusCode": 200,
            "headers": {"Content-Type": 'text/xml'},
            "body": twiml
        }

    # handle posts to /fax/receive endpoint
    # fetch pdf from twilio s3 bucket and save in s3 bucket in this account
    # return empty body back to Twilio
    if method == 'POST' and path == '/fax/receive':

        # Parse media url
        params_list = parse_qs(event['body'])
        to_number = params_list['To'][0]
        from_number = params_list['From'][0]
        pages = params_list['NumPages'][0]
        media_url = params_list['MediaUrl'][0]
        logger.info(f"Received pdf location at: {media_url}")

        # Get PDF from Twilio
        response = requests.get(media_url)
        pdf_object = response.content
        logger.info("Successfully retrieved pdf.")
        now = datetime.now().strftime("%Y-%d-%m_%H:%M:%S")
        pdf_name = f"Fax_{now}.pdf"

        # Save PDF in S3 Bucket
        bucket_name = os.environ['BUCKET_NAME']
        logger.info(f"Got bucket name {bucket_name}")
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket_name)
        logger.info(f"Got bucket {bucket}")
        try:
            logger.info(f"Creating pdf file name {pdf_name}")
            bucket.put_object(
                ACL='private',
                Body=pdf_object,
                ContentType='application/pdf',
                Key=pdf_name,
                Metadata={
                    'to_number': to_number,
                    'from_number': from_number,
                    'pages': pages
                }
            )
            logger.info(f"Successfully saved pdf to RecieveFaxBucket bucket.")

            return {
                "statusCode": 200,
                "headers": {"Content-Type": 'application/json'},
                "body": ""
            }

        except ClientError as e:
            logger.error(f"Error occurred saving PDF to S3 bucket, media url is {media_url}")
            logger.error(e)

            return {
                "statusCode": 200,
                "headers": {"Content-Type": 'application/json'},
                "body": ""
            }

    return return_403
