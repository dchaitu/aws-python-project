import boto3
import json
from typing import Optional, Dict, Any

from api_resource import APIResource


class APIGateway:
    """
    A class to manage AWS API Gateway resources.
    Handles creation and management of REST APIs and their resources.
    """

    def __init__(self, region="us-east-1") -> None:
        """
        Initialize the APIGateway client.

        Args:
            region: AWS region to use for API Gateway
        """
        self.region = region
        self.apigateway = boto3.client("apigateway", region_name=region)
        self.iam = boto3.client("iam", region_name=region)
        self.api_id = None
        self.resources = {}  # Cache of resource_id -> APIResource

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

    def create_rest_api_gateway(
        self, name, description="Created using API Gateway CLI"
    ) -> Dict[str, Any]:
        """
        Create a new REST API Gateway.

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

            # Initialize the root resource
            self._init_root_resource()
            return response

        except Exception as e:
            print(f"Failed to create API Gateway: {str(e)}")
            raise

    def get_api_gateway(self, api_gateway_id):
        """
        Get an existing API Gateway by id.

        Args:
            api_gateway_id: ID of the API Gateway to find

        Returns:
            self if found, None otherwise
        """
        self.api_id = self.apigateway.get_rest_api(restApiId=api_gateway_id)["id"]
        return self

    def _init_root_resource(self) -> None:
        """Initialize the root resource for the API."""
        if not self.api_id:
            raise ValueError(
                "API Gateway not created. Call create_rest_api_gateway first."
            )

        resources = self.apigateway.get_resources(restApiId=self.api_id)

        # Find the root resource (the one with path "/")
        root_resource = None
        for resource in resources["items"]:
            if resource["path"] == "/":
                root_resource = resource
                break

        if not root_resource:
            raise ValueError(
                "Root resource (path='/') not found in API Gateway resources"
            )

        self.root_resource = APIResource(
            self.apigateway, self.api_id, root_resource["id"], "/"
        )
        self.resources[root_resource["id"]] = self.root_resource

    def get_api_details(self) -> Dict[str, Any]:
        """
        Get the API Gateway details.

        Returns:
            dict: API Gateway details
        """
        if not self.api_id:
            raise ValueError(
                "API Gateway not created. Call create_rest_api_gateway first."
            )
        return self.apigateway.get_rest_api(restApiId=self.api_id)

    def get_root_resource(self) -> "APIResource":
        """
        Get the root resource of the API.

        Returns:
            APIResource: The root resource
        """
        if not hasattr(self, "root_resource"):
            self._init_root_resource()
        return self.root_resource

    def create_resource(
        self, parent: "APIResource", path_part, **kwargs
    ) -> "APIResource":
        """
        Create a new resource under the specified parent.
        If a resource with the same path part already exists under the parent, returns the existing resource.

        Args:
            parent: Parent APIResource object
            path_part: Path part for the resource (can include {param} for path parameters)
            **kwargs: Additional parameters for create_resource

        Returns:
            APIResource: The created or existing resource
        """
        if not self.api_id:
            raise ValueError(
                "API Gateway not created. Call create_rest_api_gateway first."
            )

        # First, check if resource already exists
        try:
            resources = self.apigateway.get_resources(restApiId=self.api_id, limit=500)
            for item in resources.get("items", []):
                if (
                    item.get("parentId") == parent.resource_id
                    and item.get("pathPart") == path_part
                ):
                    return APIResource(
                        self.apigateway, self.api_id, item["id"], item.get("path", "")
                    )

            # If we get here, resource doesn't exist, so create it
            response = self.apigateway.create_resource(
                restApiId=self.api_id,
                parentId=parent.resource_id,
                pathPart=path_part,
                **kwargs,
            )

            # Build the full path
            full_path = (
                f"{parent.path.rstrip('/')}/{path_part}"
                if parent.path != "/"
                else f"/{path_part}"
            )

            # Create and cache the new resource
            resource = APIResource(
                self.apigateway, self.api_id, response["id"], full_path
            )
            self.resources[response["id"]] = resource

            print(f"Created resource: {full_path}")
            return resource

        except Exception as e:
            print(f"Failed to create resource {path_part}: {str(e)}")
            raise

    def deploy_to_stage(
        self,
        stage_name,
        stage_description="",
        description="Deployment",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Deploy the API to a stage.

        Args:
            stage_name: Name of the stage to deploy to (e.g., 'dev', 'prod')
            stage_description: Description for the stage
            description: Description for the deployment
            **kwargs: Additional parameters for create_deployment

        Returns:
            dict: Deployment response with deployment and stage information
        """
        if not self.api_id:
            raise ValueError(
                "API Gateway not created. Call create_rest_api_gateway first."
            )

        try:
            # Create deployment
            deployment = self.apigateway.create_deployment(
                restApiId=self.api_id, description=description, **kwargs
            )

            # Check if stage exists
            try:
                # Try to get the stage
                stage = self.apigateway.get_stage(
                    restApiId=self.api_id, stageName=stage_name
                )

                # If we get here, stage exists - update it
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

            except self.apigateway.exceptions.NotFoundException:
                # Stage doesn't exist - create it
                stage = self.apigateway.create_stage(
                    restApiId=self.api_id,
                    stageName=stage_name,
                    deploymentId=deployment["id"],
                    description=stage_description,
                )
                print(f"Created new stage: {stage_name}")

            print(f"Successfully deployed to stage: {stage_name}")
            return {
                "deployment": deployment,
                "stage": stage,
                "url": f"https://{self.api_id}.execute-api.{self.region}.amazonaws.com/{stage_name}",
            }

        except Exception as e:
            print(f"Failed to deploy API: {str(e)}")
            raise

    def get_resources(self, restApiId):
        return self.apigateway.get_resources(restApiId=restApiId)

    def get_resource(self, restApiId, resourceId):
        response = self.apigateway.get_resource(restApiId=restApiId, resourceId=resourceId)
        # Create and return an APIResource object
        return APIResource(
            self.apigateway,
            restApiId,
            response["id"],
            response["path"]
        )


if __name__ == "__main__":
    # Example usage of the refactored API Gateway client
    try:
        # Configuration
        api_name = "job-portal-api-3"
        api_description = "API for Job Portal Application"
        stage_name = "dev"
        region = "us-east-1"

        # Initialize the API Gateway client
        print(f"Initializing API Gateway in {region}...")
        api_gateway = APIGateway(region=region)

        # Create a new REST API
        print(f"Creating API: {api_name}")
        api_gateway.create_rest_api_gateway(api_name, api_description)

        # Get the root resource
        root_resource = api_gateway.get_root_resource()

        # Create a resource for jobs
        print("Creating 'jobs' resource...")
        jobs_resource = api_gateway.create_resource(root_resource, "tasks")

        # Add GET method to jobs resource with MOCK integration
        print("Adding GET method to 'tasks' resource with MOCK integration...")
        jobs_resource.add_method("GET")
        jobs_resource.add_integration(
            http_method="GET",
            integration_type="MOCK",
            request_templates={"application/json": '{"statusCode": 200}'},
        )

        # Example: Add a dynamic resource for a specific job
        print("Creating dynamic 'tasks/{taskId}' resource...")
        job_resource = api_gateway.create_resource(jobs_resource, "{taskId}")

        # Add GET method to the dynamic job resource with MOCK integration
        print("Adding GET method to 'tasks/{taskId}' resource with MOCK integration...")
        job_resource.add_method("GET")
        job_resource.add_integration(
            http_method="GET",
            integration_type="MOCK",
            request_templates={
                "application/json": '{"statusCode": 200, "jobId": "$input.params(\'taskId\')"}'
            },
        )

        # Example: Add a POST method to jobs resource with MOCK integration
        print("Adding POST method to 'jobs' resource with MOCK integration...")
        jobs_resource.add_method(
            "POST", request_parameters={"method.request.header.Content-Type": True}
        )
        jobs_resource.add_integration(
            http_method="POST",
            integration_type="MOCK",
            requestTemplates={
                "application/json": '{"statusCode": 200, "message": "Job created successfully"}'
            },
            passthrough_behavior="WHEN_NO_MATCH",
        )

        # Deploy the API
        print(f"Deploying API to stage: {stage_name}")
        deployment = api_gateway.deploy_to_stage(
            stage_name=stage_name, description="Initial deployment"
        )

        # Print deployment information
        print("\n--- Deployment Successful ---")
        print(f"API ID: {api_gateway.api_id}")
        print(f"Stage: {stage_name}")
        print(f"API URL: {deployment['url']}")
        print(f"Jobs Endpoint: {deployment['url'].rstrip('/')}/tasks")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
