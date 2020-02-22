# aws_fax

# To-Do List

## Email to fax
### Switch to email authorizer and send generate_presigned_post
- Write Cloudformation custom resource to set active rule set
- Refactor SendFax to send fax with callback
- Add library to verify phone number being sent to


## Fax to Email
- Change to HTTP api instead of REST
- Use Cloudformation to create API key
- Refactor code to be one function per api endpoint.
- Write CloudFormation custom resource to return value of API Key
- Create output with api domain and query string of id and key value
- Write basic authorizer:
https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-request-validation.html

- Write Lambda authorizer
https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html

