import boto3
import json
import yaml

client = boto3.client('ssm')

ses_param = {
    'name': '/prod/ses_active_rule_set',
}

with open(r'secrets.yaml') as f:
    parameters = yaml.full_load(f)

parameters.append(ses_param)

for param in parameters:
    response = client.delete_parameter(
            Name=param['name'],
    )
    print(json.dumps(response, sort_keys=True, indent=4))
