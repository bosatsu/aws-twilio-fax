import boto3
import json
import yaml

client = boto3.client('ssm')


def main():
    with open(r'secrets.yaml') as f:
        parameters = yaml.full_load(f)

    for param in parameters:
        ssm_response = client.get_parameter(Name=param['name'])
        print(json.dumps(ssm_response, sort_keys=True, indent=4, default=str))

        if param['name'] == '/prod/aws_email':
            ses_client = boto3.client('ses', param['aws_region'])
            ses_response = ses_client.describe_active_receipt_rule_set()
            rule_set_name = ses_response['Metadata']['Name']
            print(json.dumps(ses_response['Metadata'], sort_keys=True, indent=4, default=str))

            receipt_rule_response = ses_client.describe_receipt_rule(
                RuleSetName=rule_set_name,
                RuleName='emailtofax-rule-1'
            )
            print(json.dumps(receipt_rule_response, sort_keys=True, indent=4, default=str))


if __name__ == "__main__":
    main()
