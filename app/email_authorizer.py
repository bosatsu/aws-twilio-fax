from email import utils
import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize aws clients
s3_client = boto3.client('s3')
ssm_client = boto3.client('ssm')
ses_client = boto3.client('ses', os.environ['AWS_REGION'])

# Get ssm parameters
approved_fax_senders_resp = ssm_client.get_parameter(Name='/prod/approved_fax_senders', WithDecryption=True)
approved_fax_senders = json.loads(approved_fax_senders_resp['Parameter']['Value'])
ses_email_resp = ssm_client.get_parameter(Name='/prod/validated_ses_email', WithDecryption=True)


def lambda_handler(event, context):
    logger.info("Received event.")
    logger.info(event)

    from_email = event["Records"][0]["ses"]["mail"]["source"]
    to_email = ses_email_resp['Parameter']['Value']

    if from_email in approved_fax_senders.keys():
        from_phone = approved_fax_senders[from_email]
        to_phone = event["Records"][0]["ses"]["mail"]["commonHeaders"]["subject"]
        email_date = event["Records"][0]["ses"]["mail"]["commonHeaders"]["date"]
        date = utils.parsedate_to_datetime(email_date).date().strftime("%Y-%d-%m")
        time = utils.parsedate_to_datetime(email_date).time().strftime("%H:%M:%S")
        object_name = "_".join([from_email, date, time]) + ".pdf"
        send_fax_bucket = os.environ['BUCKET_NAME']

        logger.info(f"Attempting to generate presigned upload url")
        try:
            upload_url = s3_client.generate_presigned_post(
                send_fax_bucket,
                object_name,
                Fields={
                    'Content-Type': 'application/pdf',
                    'x-amz-meta-from_email': from_email,
                    'x-amz-meta-from_phone': from_phone,
                    'x-amz-meta-to_phone': to_phone,
                    'x-amz-meta-date': date,
                    'x-amz-meta-time': time
                },
                Conditions=None,
                ExpiresIn=3600
            )
        except ClientError as e:
            logger.info("Error occurred")
            logger.error(e)

            return False

        logger.info(f"Created presigned upload url successfully")
        logger.info(f"Attempting to send upload url to {from_email}.")

        subject = f"Upload link for fax to {to_phone}"
        charset = "utf-8"
        body_text = (
            f"Please upload a pdf that you would like to fax to {to_phone}\n"
            f"{upload_url}"
        )

        body_html = f"""
        <html>
        <head></head>
        <body>
        <p>Please upload a pdf that you would like to fax to {to_phone}\n</p>
        <p>{upload_url}</p>
        </body>
        </html>
        """

        try:
            ses_client.send_email(
                Destination={
                    'ToAddresses': [
                        from_email,
                    ],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': charset,
                            'Data': body_html,
                        },
                        'Text': {
                            'Charset': charset,
                            'Data': body_text,
                        },
                    },
                    'Subject': {
                        'Charset': charset,
                        'Data': subject,
                    },
                },
                Source=to_email,
            )
            logger.info(f"Email send successfully")

        # Display an error if something goes wrong.
        except ClientError as e:
            logger.error(e.response['Error']['Message'])

    return True
