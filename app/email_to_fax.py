import base64
import email
import logging
import json
import os
import urllib

import boto3
from botocore.exceptions import ClientError
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize aws clients
s3_client = boto3.client('s3')
ssm_client = boto3.client('ssm')
ses_client = boto3.client('ses')

# Get ssm parameters
admin_email = ssm_client.get_parameter(Name='/prod/admin_email', WithDecryption=True)
aws_email = ssm_client.get_parameter(Name='/prod/aws_email', WithDecryption=True)
fax_emails_resp = ssm_client.get_parameter(Name='/prod/fax_emails', WithDecryption=True)
fax_emails = json.loads(fax_emails_resp['Parameter']['Value'])
twilio_ssm_response = ssm_client.get_parameter(Name='/prod/twilio', WithDecryption=True)
twilio_params = json.loads(twilio_ssm_response['Parameter']['Value'])


def check_number(to_phone):
    twilio_client = Client(twilio_params['twilio_account_id'], twilio_params['twilio_api_key'])
    try:
        twilio_client.lookups.phone_numbers(to_phone).fetch()
        return True
    except TwilioRestException:
        return False


def check_from_email(from_email):
    from_number = False
    for item in fax_emails.items():
        if from_email in item:
            from_number = item[0]
            break
    return from_number


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
        logger.info(f"Email sent successfully")

    except ClientError as e:
        logger.error(f"Email failed to send")
        logger.error(e)


# --------------- Main handler ------------------
def lambda_handler(event, context):
    logger.info("Received event.")
    logger.info(event)

    # Get the object from the event.
    email_to_fax_bucket = event['Records'][0]['s3']['bucket']['name']
    object_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    s3_response = s3_client.get_object(Bucket=email_to_fax_bucket, Key=object_key,)
    msg = email.message_from_bytes(s3_response['Body'].read())
    from_email = email.utils.parseaddr(msg['From'])[1]
    date = email.utils.parsedate_to_datetime(msg['Date']).date().strftime("%Y-%d-%m")
    time = email.utils.parsedate_to_datetime(msg['Date']).time().strftime("%H:%M:%S")
    to_phone = msg['Subject']
    from_phone = check_from_email(from_email)

    # Check if sender is not in the approved senders list
    # If not, log sender address and send email to admin
    if from_phone is False:
        logger.warn(f"Received email from unapproved sender: {from_email}")
        sender = aws_email['Parameter']['Value'].strip('/"')
        recipient = admin_email['Parameter']['Value'].strip('/"')
        subject = "Received email from non-approved sender"
        charset = "utf-8"
        body_text = (
            f"You have recieved an email from non approved sender: {from_email}. "
            f"The message is in the {email_to_fax_bucket} bucket, named {object_key}."
        )
        body_html = f"""
            <html>
            <head></head>
            <body>
            <p>{body_text}</p>
            </body>
            </html>
            """
        send_email(recipient, sender, subject, charset, body_html, body_text)

        return False

    # Check if phone number is valid
    # If not, log sender phone nmumber and send email to sender
    number_valid = check_number(to_phone)
    if number_valid is False:
        logger.warn(f"Unable to verify destination fax number: {to_phone}")
        sender = aws_email['Parameter']['Value'].strip('/"')
        recipient = admin_email['Parameter']['Value'].strip('/"')
        subject = f"RE: {to_phone}"
        charset = "utf-8"
        body_text = (
            f"We were unable to verify the destination fax number: {to_phone}. "
            f"Please review the number and send again."
        )
        body_html = f"""
            <html>
            <head></head>
            <body>
            <p>{body_text}</p>
            </body>
            </html>
            """
        send_email(recipient, sender, subject, charset, body_html, body_text)

        return False

    # Parse msg object, if pdf exists, save to SendFax bucket
    for part in msg.walk():
        if part.get_content_type() == 'application/pdf':
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
                logger.error(f"Failed to save PDF to S3 bucket {send_fax_bucket}")
                logger.error(e)

                return False

        # If pdf doesn't exist send email to sender.
        else:
            logger.warn("Recieved email with no PDF, notifying sender")

            # Notify admin that an email was received by non approved sender
            sender = aws_email['Parameter']['Value'].strip('/"')
            recipient = email.utils.parseaddr(msg['From'])[1]
            subject = "Recieved email with no PDF"
            charset = "utf-8"
            body_text = f"Recieved email with subject {to_phone} on {date} at {time} with no PDF.  No fax sent."
            body_html = f"""
                <html>
                <head></head>
                <body>
                <p>{body_text}</p>
                </body>
                </html>
                """
            send_email(recipient, sender, subject, charset, body_html, body_text)

            return False
