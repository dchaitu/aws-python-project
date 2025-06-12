import boto3
import json
from typing import Optional, Dict, Any


class APIGateway:

    # Create an API Gateway with resources with connect with dynamoDB
    def __init__(self, region="us-east-1") -> None:
        self.region = region
        self.apigateway = boto3.client("apigateway", region_name=region)
        self.iam = boto3.client("iam", region_name=region)

    def create_gateway_role_with_policy(self, role_name="api_gateway_role"):
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"Service": "apigateway.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        job_details_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "VisualEditor0",
                    "Effect": "Allow",
                    "Action": ["dynamodb:PutItem", "dynamodb:GetItem"],
                    "Resource": "arn:aws:dynamodb:us-east-1:924305315075:table/job_portals",
                },
                {
                    "Effect": "Allow",
                    "Action": ["logs:*"],
                    "Resource": "*",
                },
            ],
        }
        role = self.iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
        )
        self.iam.put_role_policy(
            RoleName=role_name,
            PolicyName="job_details_policy",
            PolicyDocument=json.dumps(job_details_policy),
        )
        print(f"Created role {role_name}")
        return role["Role"]["Arn"]

    def create_api(
        self, name: str, description: str = "API Gateway for job portal"
    ) -> Dict[str, Any]:
        """
        Create a new API Gateway

        Args:
            name: Name of the API Gateway
            description: Description of the API Gateway

        Returns:
            dict: API Gateway creation response
        """
        try:
            response = self.apigateway.create_rest_api(
                name=name,
                description=description,
                endpointConfiguration={"types": ["REGIONAL"]},
            )
            self.api_id = response["id"]
            print(f"Created API Gateway: {name} (ID: {self.api_id})")
            return response
        except Exception as e:
            print(f"Failed to create API Gateway: {str(e)}")
            raise

    def get_root_resource_id(self) -> str:
        """Get the root resource ID of the API Gateway"""
        try:
            resources = self.apigateway.get_resources(restApiId=self.api_id)
            return resources["items"][0]["id"]
        except Exception as e:
            print(f"Failed to get root resource ID: {str(e)}")
            raise

    def create_resource(
        self, parent_id: str, path_part: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new resource in API Gateway

        Args:
            parent_id: ID of the parent resource
            path_part: Path part for the resource (can include {param} for path parameters)
            **kwargs: Additional parameters for create_resource

        Returns:
            dict: Resource creation response
        """
        try:
            response = self.apigateway.create_resource(
                restApiId=self.api_id, parentId=parent_id, pathPart=path_part, **kwargs
            )
            print(f"Created resource: {path_part} under parent {parent_id}")
            return response
        except Exception as e:
            print(f"Failed to create resource {path_part}: {str(e)}")
            raise

    def add_method(
        self,
        resource_id: str,
        http_method: str,
        authorization_type: str = "NONE",
        request_parameters: Optional[Dict[str, bool]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Add a method to a resource

        Args:
            resource_id: ID of the resource
            http_method: HTTP method (GET, POST, etc.)
            authorization_type: Type of authorization (NONE, AWS_IAM, etc.)
            request_parameters: Request parameters mapping
            **kwargs: Additional parameters for put_method

        Returns:
            dict: Method creation response
        """
        if request_parameters is None:
            request_parameters = {}

        try:
            response = self.apigateway.put_method(
                restApiId=self.api_id,
                resourceId=resource_id,
                httpMethod=http_method.upper(),
                authorizationType=authorization_type,
                requestParameters=request_parameters,
                **kwargs,
            )
            print(f"Added {http_method} method to resource {resource_id}")
            return response
        except Exception as e:
            print(f"Failed to add {http_method} method: {str(e)}")
            raise

    def deploy_to_stage(
        self,
        stage_name: str,
        stage_description: str = "",
        description: str = "Deployment",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Deploy the API to a stage

        Args:
            stage_name: Name of the stage to deploy to (e.g., 'dev', 'prod')
            stage_description: Description for the stage
            description: Description for the deployment
            **kwargs: Additional parameters for create_deployment

        Returns:
            dict: Deployment response with deployment and stage information
        """
        try:
            # Create deployment
            deployment = self.apigateway.create_deployment(
                restApiId=self.api_id, description=description, **kwargs
            )

            # Create or update stage
            #  If stage exists, update it
            #  If stage does not exist, create it
            # Check if stage exists
            response = self.apigateway.get_stages(restApiId=self.api_id)
            stages = response["item"]
            stage_exists = any(stage["stageName"] == stage_name for stage in stages)
            if stage_exists:
                # Stage exists, update it
                stage = self.apigateway.update_stage(
                    restApiId=self.api_id,
                    stageName=stage_name,
                    patchOperations=[
                        {
                            "op": "replace",
                            "path": "/deploymentId",
                            "value": deployment["id"],
                        }
                    ],
                )
                print(f"Updated existing stage: {stage_name}")
            else:
                # Stage does not exist, create it
                stage = self.apigateway.create_stage(
                    restApiId=self.api_id,
                    stageName=stage_name,
                    description=stage_description,
                    deploymentId=deployment["id"],
                )
                print(f"Created new stage: {stage_name}")

            print(f"Successfully deployed to stage: {stage_name}")
            return {"deployment": deployment, "stage": stage}

        except Exception as e:
            print(f"Failed to deploy API: {str(e)}")
            raise


if __name__ == "__main__":
    # Initialize the API Gateway client

    api_name = input("Enter API name: ")
    api_description = input("Enter API description: ")
    stage_name = input("Enter stage name: ")
    stage_description = input("Enter stage description: ")
    region = input("Enter region (default: us-east-1): ")

    # if region is empty use us-east-1
    if region == "":
        region = "us-east-1"
    api_gateway = APIGateway(region=region)
    api_response = api_gateway.create_api(api_name, api_description)
    root_id = api_gateway.get_root_resource_id()
    print(f"API created: {api_response['id']}")

    # Create a resource with static name
    resource_name = input("Enter resource name: ")
    jobs_resource = api_gateway.create_resource(
        parent_id=root_id, path_part=resource_name
    )

    # Create a resource with dynamic path parameter
    # job_resource = api_gateway.create_resource(
    #     parent_id=jobs_resource['id'],
    #     path_part="{jobId}"
    # )

    # Add methods to resources
    method_name = input("Enter method name: ")
    api_gateway.add_method(
        resource_id=jobs_resource["id"],
        http_method=method_name,
        authorization_type="NONE",
    )

    # Deploy the API
    deployment = api_gateway.deploy_to_stage(
        stage_name=stage_name,
        stage_description=stage_description,
        description="Initial deployment",
    )

    print(f"API deployed successfully!")
    print(f"API ID: {api_gateway.api_id}")
    print(
        f"Stage URL: https://{api_gateway.api_id}.execute-api.{api_gateway.region}.amazonaws.com/dev"
    )
