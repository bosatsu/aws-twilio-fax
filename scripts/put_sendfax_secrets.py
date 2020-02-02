import boto3
import json
import yaml

ssm_client = boto3.client('ssm')
ses_client = boto3.client('ses')

ses_response = ses_client.describe_active_receipt_rule_set()
if 'Metadata' in ses_response.keys():
    rule_set_name = ses_response['Metadata']['Name']
else:
    rule_set_name = 'default-rule-set'
    ses_client.create_receipt_rule_set(RuleSetName=rule_set_name)
    ses_client.set_active_receipt_rule_set(RuleSetName=rule_set_name)

ses_param = {
    'name': '/prod/ses_active_rule_set',
    'description': 'Name of active receipt rule set in SES',
    'value': rule_set_name
}

with open(r'secrets.yaml') as f:
    parameters = yaml.full_load(f)

parameters.append(ses_param)

for param in parameters:
    response = ssm_client.put_parameter(
        Name=param['name'],
        Description=param['description'],
        Value=json.dumps(param['value']),
        Type='SecureString',
        Overwrite=True,
        Tier='Standard',
    )
    print(f"\nRequested put for {param['name']}")
    print(json.dumps(response, sort_keys=True, indent=4))

    if param['name'] == '/prod/fax_to_email':
        ses_client = boto3.client('ses')
        response = ses_client.verify_email_address(
            EmailAddress=param['value']['receive_email']
        )
        print(f"\nRequested verficiation for {param['value']['source_email']}")
        print(json.dumps(response, sort_keys=True, indent=4))
