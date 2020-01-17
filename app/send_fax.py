import boto3
import json
import urllib
import time
import logging

from twilio.rest import Client

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
ssm_client = boto3.client('ssm')

# Fetch all parameters
account_sid = ssm_client.get_parameter(Name='/prod/send_fax/account_sid', WithDecryption=True)
auth_token = ssm_client.get_parameter(Name='/prod/send_fax/auth_token', WithDecryption=True)
to_number = ssm_client.get_parameter(Name='/prod/send_fax/to_number', WithDecryption=True)
from_number = ssm_client.get_parameter(Name='/prod/send_fax/from_number', WithDecryption=True)


def send_fax(url):
    '''
    Function for sending a fax
    '''
    client = Client(account_sid['Parameter']['Value'], auth_token['Parameter']['Value'])
    fax = client.fax.faxes.create(
        from_=from_number['Parameter']['Value'],
        to=to_number['Parameter']['Value'],
        quality="standard",
        media_url=url
    )
    timeout = time.time() + 60*5   # 5 minutes from now
    completed = False
    status = "started"
    while not completed or time.time() < timeout:
        # Check status based on status listed on Twilio's site:
        # https://www.twilio.com/docs/fax/api/faxes#fax-status-values
        status = fax.status
        if status in ["delivered", "no-answer", "busy", "failed", "canceled"]:
            completed = True
        else:
            time.sleep(5)
    if status == "delivered":
        logger.info(
            "SUCCESS: Sending fax completed successfully."
            "fax_id = {fax.sid}"
            "fax_from = {fax.from_}"
            "fax_to = {fax.to}"
            "fax_quality = {fax.quality}"
            "fax_num_pages = {fax.num_pages}"
            "fax_duration = {fax.duration}"
            "fax_price = {fax.price}"
            "fax_price_unit = {fax.price_unit}"
            "fax_date_created = {fax.date_created}"
        )
        return True
    elif status == "started":
        logger.error("FAILED: Sending fax timed out while waiting for Twilio service to initialize.")
        return False
    elif status in ["queued", "processing", "sending"]:
        logger.error(f"FAILED: Sending fax timed out with status code: {status}.")
        return False
    else:
        logger.error(f"FAILED: Sending fax failed with status code: {status}")
        return False


# --------------- Main handler ------------------
def lambda_handler(event, context):
    '''
    Send any PDF uploaded to S3 bucket SendFaxBucket to a specific number.
    '''
    # Log the the received event locally.
    # print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event.
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    try:
        logger.info(f"{bucket_name}, {object_key}")
        media_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=3600
        )

        # send_fax(media_url)
        logger.info(f"Created media url {media_url}")
        return None

    except Exception as err:
        logger.error(
            f"Error processing object {object_key} from bucket {bucket_name}. Event {json.dumps(event, indent=2)}"
        )
        raise err
