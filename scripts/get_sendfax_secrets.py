import boto3
from pprint import pprint
import yaml

client = boto3.client('ssm')

with open(r'scripts/secrets.yaml') as f:
    parameters = yaml.full_load(f)

for param in parameters:
    response = client.get_parameter(
        Name=param['name'],
        WithDecryption=True
    )
    pprint(response)
