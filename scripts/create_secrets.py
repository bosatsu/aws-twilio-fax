import json
import yaml

import boto3

ssm_client = boto3.client('ssm')
cf_client = boto3.resource('cloudformation')
ses_client = boto3.client('ses')


def create_ssm_param(param):
    response = ssm_client.put_parameter(
        Name=param['name'],
        Description=param['description'],
        Value=json.dumps(param['value']),
        Type='SecureString',
        Overwrite=True,
        Tier='Standard',
    )

    return response


def create_ses_receipt_rule(email):
    fax_stack = cf_client.Stack('aws-fax')
    outputs = fax_stack.outputs
    email_to_fax_bucket_name = ''
    for output in outputs:
        if output['OutputKey'] == 'EmailToFaxBucket':
            email_to_fax_bucket_name = output['OutputValue']
            break
    if email_to_fax_bucket_name == '':
        return False

    ses_response = ses_client.describe_active_receipt_rule_set()
    if 'Metadata' in ses_response.keys():
        rule_set_name = ses_response['Metadata']['Name']
    else:
        rule_set_name = 'default-rule-set'
        ses_client.create_receipt_rule_set(RuleSetName=rule_set_name)
        ses_client.set_active_receipt_rule_set(RuleSetName=rule_set_name)

    try:
        ses_response = ses_client.create_receipt_rule(
            RuleSetName=rule_set_name,
            Rule={
                'Name': 'emailtofax-rule-1',
                'Enabled': True,
                'Recipients': [email],
                'ScanEnabled': True,
                'Actions': [
                    {
                        'S3Action': {
                            'BucketName': email_to_fax_bucket_name,
                        },
                    }
                ]
            }
        )
    except ses_client.exceptions.AlreadyExistsException:
        ses_response = ses_client.describe_receipt_rule(
            RuleSetName=rule_set_name,
            RuleName='emailtofax-rule-1'
        )

    return ses_response


def verify_email(email):
    check_email_response = ses_client.get_identity_verification_attributes(
        Identities=[email]
    )
    if check_email_response['VerificationAttributes'] == {}:
        verify_email_response = ses_client.verify_email_address(
            EmailAddress=email
        )
        return verify_email_response
    else:
        return check_email_response


def main():

    with open(r'secrets.yaml') as f:
        parameters = yaml.full_load(f)

    for param in parameters:
        ssm_response = create_ssm_param(param)
        print(f"\nAttempted creating ssm parameter for {param['name']}")
        print(json.dumps(ssm_response, sort_keys=True, indent=4))

        if param['name'] == '/prod/aws_email':
            ses_response = create_ses_receipt_rule(param['value'])
            print(f"\nAttempted creating ses receipt rule for {param['value']}")
            print(json.dumps(ses_response, sort_keys=True, indent=4))

            verify_response = verify_email(param['value'])
            print(f"\nAttempted verifying email for {param['value']}")
            print(json.dumps(verify_response, sort_keys=True, indent=4))

        if param['name'] == '/prod/fax_emails':
            for email in param['value'].items():
                verify_response = verify_email(email[1])
                print(f"\nAttempted verifying email for {param['value']}")
                print(json.dumps(verify_response, sort_keys=True, indent=4))


if __name__ == "__main__":
    main()
