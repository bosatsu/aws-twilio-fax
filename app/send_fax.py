import json
import logging
import urllib
import time

import boto3
from twilio.rest import Client

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
ssm_client = boto3.client('ssm')

# Fetch ssm parameters
ssm_response = ssm_client.get_parameter(Name='/prod/twilio', WithDecryption=True)
ssm_params = json.loads(ssm_response['Parameter']['Value'])


def send_fax(from_phone, to_phone, media_url):
    '''
    Function for sending a fax
    '''
    twilio_client = Client(ssm_params['twilio_account_id'], ssm_params['twilio_api_key'])
    fax = twilio_client.fax.faxes.create(
        from_=from_phone,
        to=to_phone,
        quality="standard",
        media_url=media_url
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

        s3_resource = boto3.resource('s3')
        s3_object = s3_resource.Object(bucket_name, object_key)
        from_phone = s3_object.metadata['from_phone']
        to_phone = s3_object.metadata['to_phone']
        send_fax(from_phone, to_phone, media_url)
        logger.info(f"Created media url {media_url}")

        return True

    except Exception as e:
        logger.info(
            f"Error processing object {object_key} from bucket {bucket_name}. Event {json.dumps(event, indent=2)}"
        )
        logger.error(e)

        return False
