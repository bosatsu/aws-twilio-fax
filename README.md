# aws_fax

# To-Do List

## Email to fax
### Switch to email authorizer and send generate_presigned_post
- Write email authorizer
- Remove email_to_fax.py
- Remove bucket
- Update ruleset
- Write Cloudformation custom resource to set active rule set
- Add library to verify phone number

## Fax to Email
- Use Cloudformation to create API key
- Write CloudFormation custom resource to return value of API Key
- Create output with api domain and query string of id and key value
- Write Lambda authorizer
https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html

