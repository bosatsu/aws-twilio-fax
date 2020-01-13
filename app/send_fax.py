# TODO: Write code to generate presigned URL for S3 PDF object
# TODO: Look up how to log to cloudwatch from Python
# TODO: Test parameter store lookup


from __future__ import print_function
import boto3
import json
import urllib
import time

from twilio.rest import Client

# Initialize AWS clients
s3_client = boto3.client('s3')
ssm_client = boto3.client('ssm')


# Fetch all parameters
account_sid = ssm_client.get_paramter(Name='account_sid')
auth_token = ssm_client.get_paramter(Name='auth_token')
to_number = ssm_client.get_paramter(Name='to_number')
from_number = ssm_client.get_paramter(Name='from_number')


def send_fax(self, url):
    '''
    Function for sending a fax
    '''
    client = Client(account_sid, auth_token)
    fax = client.fax.faxes.create(
        from_=from_number,
        to=to_number,
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
        print(
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
        print("FAILED: Sending fax timed out while waiting for Twilio service to initialize.")
        return False
    elif status in ["queued", "processing", "sending"]:
        print("FAILED: Sending fax timed out with status code: {}.")
        return False
    else:
        print("FAILED: Sending fax failed with status code: {}".format(self.status))
        return False


# --------------- Main handler ------------------
def lambda_handler(event, context):
    '''
    Send any PDF uploaded to S3 bucket SendFaxBucket to a specific number.
    '''
    # Log the the received event locally.
    # print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event.
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    try:
        print(bucket, key)
        print("{account_sid}")
        print("{auth_token}")
        print("{to_number}")
        print("{from_number}")
    except Exception as e:
        print("Error processing object {} from bucket {}. Event {}".format(key, bucket, json.dumps(event, indent=2)))
        raise e
