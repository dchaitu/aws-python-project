import boto3
from api_gateway import APIGateway


def main():
    # Initialize API Gateway in the given region
    region = "us-east-1"
    api_gateway = APIGateway(region=region)

    if input("Do you want to create a new API Gateway (y/n)") == "y":
        api_name = input("Enter API Gateway name: ")
        api_gateway.create_rest_api_gateway(api_name)
    else:
        api_id = input("Enter API Gateway ID: ")
        existing_api = api_gateway.get_api_gateway(api_id)
        print(f"Using existing API Gateway: {existing_api}")

    integration_type = input("Enter integration type: AWS_PROXY, AWS, HTTP: ")
    # Get root resource
    if input("Is resource root is main resource (y/n)").lower() == "y":
        root_resource = api_gateway.get_root_resource()
        resource_name = input("Enter new resource name: ").strip()
        current_resource = api_gateway.create_resource(root_resource, resource_name)
        print(f"Successfully created resource: {resource_name}")
    else:
        resource_id = input("Enter parent resource id: ")
        current_resource = api_gateway.get_resource(restApiId=api_id, resourceId=resource_id)
        print(f"Using parent resource: {current_resource.path}")

        if input(f"Want to create new resource from {current_resource.path} (y/n)").lower() == "y":
            resource_name = input("Enter new resource name: ").strip()
            current_resource = api_gateway.create_resource(current_resource, resource_name)
            print(f"Successfully created resource: {resource_name}")

    http_method = input("Enter HTTP method: GET, POST, PUT, DELETE: ").upper()
    current_resource.add_method(http_method=http_method, authorization_type="NONE")
    integration_http_method = input("Enter integration HTTP method: ")

    # Add Lambda integration
    lambda_arn = "arn:aws:lambda:us-east-1:924305315075:function:printHelloWorld"
    lambda_uri = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

    # state_machine_arn = (
    #     "arn:aws:states:us-east-1:924305315075:stateMachine:MyStateMachine"
    # )
    # action_arn = "arn:aws:apigateway:<region>:<service>:action/<ActionName>
    action_name = input(
        "Enter action name for dynamo db: GetItem, PutItem, DeleteItem, UpdateItem\n"
    )
    dynamo_db_action_arn = f"arn:aws:apigateway:us-east-1:dynamodb:action/{action_name}"
    dynamo_db_template = '{"TableName": "job_portals", "Item": $input.json("$")}'

    if integration_type == "AWS_PROXY":
        current_resource.add_integration(
            http_method=http_method,
            integration_type=integration_type,
            integration_http_method=integration_http_method,
            uri=lambda_uri,
        )
    elif integration_type == "AWS":
        current_resource.add_integration(
            http_method=http_method,
            integration_type=integration_type,
            integration_http_method=integration_http_method,
            uri=f"{dynamo_db_action_arn}",
            credentials="arn:aws:iam::924305315075:role/api_gateway_role",
            request_parameters={
                "integration.request.header.Content-Type": "'application/x-amz-json-1.0'",
            },
            request_templates={"application/json": dynamo_db_template},
            passthrough_behavior="WHEN_NO_TEMPLATES",
            timeout_in_millis=29000,
        )
    elif integration_type == "HTTP":
        current_resource.add_integration(
            http_method=http_method,
            integration_type=integration_type,
            integration_http_method=integration_http_method,
            uri=lambda_uri,
            credentials="arn:aws:iam::924305315075:role/api_gateway_role",
        )

    # Deploy the API
    # print("Deploying API...")
    # deployment = api_gateway.deploy_to_stage(
    #     stage_name='dev',
    #     description='Initial deployment'
    # )

    # print(f"\nAPI deployed successfully!")
    # print(f"Endpoint: {deployment['url'].rstrip('/')}/code")
    # print("Deployed at stage 'dev'")


if __name__ == "__main__":
    main()
