import json
import logging
import os
import urllib

import boto3
from botocore.exceptions import ClientError


# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    '''
    Send any PDF uploaded to S3 bucket ReceiveFaxBucket to a specific email.
    '''
    logger.info("Received event.")
    logger.info(event)

    # Fetch ssm parameters
    ssm_client = boto3.client('ssm')
    ssm_params = ssm_client.get_parameter(Name='/prod/fax_to_email', WithDecryption=True)
    json_params = json.loads(ssm_params['Parameter']['Value'])

    # Get the object from the event.
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    # Get fax metadata
    s3 = boto3.resource('s3')
    fax_metadata = s3.Object(bucket_name, object_key).metadata

    # Generate presigned url
    s3_client = boto3.client('s3')
    media_url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': bucket_name,
            'Key': object_key
        },
        ExpiresIn=604800
    )

    # Create email parameters
    SENDER = json_params['source_email']
    RECIPIENT = json_params['destination_email']
    SUBJECT = f"New fax from: {fax_metadata['from_number']}"
    CHARSET = "utf-8"
    BODY_TEXT = (
        "You have received a new fax!"
        f"From: {fax_metadata['from_number']}\n"
        f"To: {fax_metadata['to_number']}\n"
        f"Pages: {fax_metadata['pages']}\n\n"
        "To view or download please go to the url below, this link will be active for 7 days.\n"
        f"{media_url}"
    )

    BODY_HTML = f"""
    <html>
    <head></head>
    <body>
    <h1>Email Verification Receipt</h1>
    <p>You have received a new fax!</p>
    <p>From: {fax_metadata['from_number']}</p>
    <p>To: {fax_metadata['to_number']}</p>
    <p>Pages: {fax_metadata['pages']}</p>
    <p>To view or download please go to the url below, this link will be active for 7 days.</p>
    <p>{media_url}</p>
    </body>
    </html>
    """

    # Create a new SES resource and specify a region.
    ses_client = boto3.client('ses', os.environ['AWS_REGION'])

    # Try to send the email.
    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        logger.error(e.response['Error']['Message'])
    else:
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
