import base64
import email
import logging
import json
import os
import urllib

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

# Get email params
admin_email_resp = ssm_client.get_parameter(Name='/prod/admin_email', WithDecryption=True)
ses_email_resp = ssm_client.get_parameter(Name='/prod/validated_ses_email', WithDecryption=True)


def send_email(recipient, sender, subject, charset, body_html, body_text):
    logger.info(f"Attempting to send email to {recipient} with subject: {subject}")
    try:
        ses_client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
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
            Source=sender,
        )
        logger.info(f"Email send successfully")

    except ClientError as e:
        logger.error(e.response['Error']['Message'])


# --------------- Main handler ------------------
def lambda_handler(event, context):
    logger.info("Received event.")
    logger.info(event)

    # Get the object from the event.
    email_to_fax_bucket = event['Records'][0]['s3']['bucket']['name']
    object_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    s3_response = s3_client.get_object(Bucket=email_to_fax_bucket, Key=object_key,)
    msg = email.message_from_bytes(s3_response['Body'].read())
    to_address = email.utils.parseaddr(msg['To'])[1]

    # Check if sender is not in the approved senders list
    # If not, log sender address and send email to admin
    if to_address not in approved_fax_senders.keys():
        logger.warn(f"Received email from unapproved sender: {to_address}")

        # Notify admin that an email was received by non approved sender
        sender = ses_email_resp['Parameter']['Value']
        recipient = admin_email_resp['Parameter']['Value']
        subject = "Received email from non-approved sender"
        charset = "utf-8"
        body_text = (
            f"You have recieved an email from non approved sender: {to_address}."
            f"The message is in the {email_to_fax_bucket} bucket, named {object_key}."
        )
        body_html = f"""
            <html>
            <head></head>
            <body>
            <p>You have recieved an email from non approved sender: {to_address}.</p>
            <p>The message is in the {email_to_fax_bucket} bucket, named {object_key}.</p>
            </body>
            </html>
            """
        send_email(recipient, sender, subject, charset, body_html, body_text)

        return False

    # Parse msg object, if pdf exists, save to SendFax bucket
    for part in msg.walk():
        if part.get_content_type() == 'application/pdf':
            from_email = email.utils.parseaddr(msg['From'])[1]
            from_phone = approved_fax_senders[from_email]
            to_phone = msg['Subject']
            date = email.utils.parsedate_to_datetime(msg['Date']).date().strftime("%Y-%d-%m")
            time = email.utils.parsedate_to_datetime(msg['Date']).time().strftime("%H:%M:%S")
            filename = part.get_filename()
            pdf_name = "_".join([from_email, date, time]) + ".pdf"
            pdf_object = base64.b64decode(part.get_payload())
            send_fax_bucket = os.environ['BUCKET_NAME']
            try:
                logger.info(f"Creating pdf file name {pdf_name}")
                s3_client.put_object(
                    ACL='private',
                    Body=pdf_object,
                    Bucket=send_fax_bucket,
                    ContentType='application/pdf',
                    Key=pdf_name,
                    Metadata={
                        'from_email': from_email,
                        'from_phone': from_phone,
                        'to_phone': to_phone,
                        'date': date,
                        'time': time,
                        'filename': filename
                    },
                )
                logger.info(f"Successfully saved pdf to {send_fax_bucket} bucket.")

                return True

            except ClientError as e:
                logger.warn("Error occurred")
                logger.error(e)

                return False

        # If pdf doesn't exist send email to sender.
        else:
            logger.warn("Recieved email with no PDF, notifying sender")

            # Notify admin that an email was received by non approved sender
            sender = ses_email_resp['Parameter']['Value']
            recipient = email.utils.parseaddr(msg['From'])[1]
            subject = "Recieved email with no PDF"
            charset = "utf-8"
            body_text = "Recieved email with no PDF, no fax sent."
            body_html = """
                <html>
                <head></head>
                <body>
                <p>Recieved email with no PDF, no fax sent.</p>
                </body>
                </html>
                """
            send_email(recipient, sender, subject, charset, body_html, body_text)

            return False
