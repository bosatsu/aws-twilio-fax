from __future__ import print_function
import boto3
import json
import urllib
import os

s3_client = boto3.client('s3')

# Get the table name from the Lambda Environment Variable
phone_number = os.environ['PHONE_NUMBER']


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
    except Exception as e:
        print("Error processing object {} from bucket {}. Event {}".format(key, bucket, json.dumps(event, indent=2)))
        raise e
