from api_gateway import APIGateway


def main():
    # Initialize API Gateway
    api_gateway = APIGateway(region='us-east-1')
    
    # Use existing API
    api_id = 'losmzq9w5m'  # Your API Gateway ID
    api_gateway.api_id = api_id
    
    # Get root resource
    root_resource = api_gateway.get_root_resource()
    print("Root resource:", root_resource.resource_id, root_resource.__dict__)
    
    # Create a new resource under root
    print("Creating 'code' resource...")
    code_resource = api_gateway.create_resource(root_resource, 'code')
    
    # Add POST method to the code resource
    print("Adding POST method to 'code' resource...")
    code_resource.add_method(http_method='POST', authorization_type='NONE')
    
    # Add Lambda integration
    lambda_arn = 'arn:aws:lambda:us-east-1:924305315075:function:printHelloWorld'
    code_resource.add_integration(
        http_method='POST',
        integration_type='AWS_PROXY',
        integration_http_method='POST',
        uri=f'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
    )
    
    # Deploy the API
    print("Deploying API...")
    deployment = api_gateway.deploy_to_stage(
        stage_name='dev',
        description='Initial deployment'
    )
    
    print(f"\nAPI deployed successfully!")
    print(f"Endpoint: {deployment['url'].rstrip('/')}/code")


if __name__ == "__main__":
    main()
print("Deployed at stage 'dev'")




