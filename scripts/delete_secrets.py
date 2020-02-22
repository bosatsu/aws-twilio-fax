import boto3
import json
import yaml

ssm_client = boto3.client('ssm')
ses_client = boto3.client('ses')


def main():
    with open(r'secrets.yaml') as f:
        parameters = yaml.full_load(f)

    for param in parameters:
        try:
            ssm_response = ssm_client.delete_parameter(Name=param['name'])
            print(f"\nAttempted deleting ssm parameter for {param['name']}")
            print(json.dumps(ssm_response, sort_keys=True, indent=4))
        except ssm_client.exceptions.ParameterNotFound:
            pass

        if param['name'] == '/prod/aws_email':
            ses_response = ses_client.describe_active_receipt_rule_set()
            rule_set_name = ses_response['Metadata']['Name']

            try:
                receipt_rule_response = ses_client.delete_receipt_rule(
                    RuleSetName=rule_set_name,
                    RuleName='emailtofax-rule-1'
                )
                print(f"\nAttempted deleting receipt rule for {param['value']}")
                print(json.dumps(receipt_rule_response, sort_keys=True, indent=4))
            except ses_client.exceptions.ParameterNotFound:
                pass

            delete_identity_response = ses_client.delete_identity(Identity=param['value'])
            print(f"\nAttempted deleting email identity for {param['value']}")
            print(json.dumps(delete_identity_response, sort_keys=True, indent=4))

        if param['name'] == '/prod/fax_emails':
            for email in param['value'].items():
                delete_identity_response = ses_client.delete_identity(Identity=email[1])
                print(f"\nAttempted deleting email identity for {param['value']}")
                print(json.dumps(delete_identity_response, sort_keys=True, indent=4))


if __name__ == "__main__":
    main()
