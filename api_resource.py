class APIResource:
    def __init__(self, apigateway_client, api_id, resource_id, path):
        """
        Initialize a new API Resource.

        Args:
            apigateway_client: Boto3 API Gateway client
            api_id: ID of the API Gateway
            resource_id: ID of this resource
            path: Path of this resource
        """
        self.apigateway = apigateway_client
        self.api_id = api_id
        self.resource_id = resource_id
        self.path = path
        self.methods = {}

    def add_method(
        self,
        http_method,
        authorization_type="NONE",
        request_parameters=None,
        **kwargs,
    ):
        """
        Add an HTTP method to this resource.

        Args:
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
                resourceId=self.resource_id,
                httpMethod=http_method.upper(),
                authorizationType=authorization_type,
                requestParameters=request_parameters,
                **kwargs,
            )
            print(f"Added {http_method} method to resource {self.path}")
            self.methods[http_method.upper()] = response
            self.apigateway.put_method_response(
                restApiId=self.api_id,
                resourceId=self.resource_id,
                httpMethod=http_method.upper(),
                statusCode="200",
            )
            return response
        except Exception as e:
            print(f"Failed to add {http_method} method: {str(e)}")
            raise

    def create_resource(self, path_part, **kwargs):
        self.apigateway.get_resources(
            restApiId=self.api_id,
            parentId=self.resource_id,
        )

        return self.apigateway.create_resource(
            restApiId=self.api_id,
            parentId=self.resource_id,
            pathPart=path_part,
            **kwargs,
        )

    def add_integration(
        self,
        http_method,
        integration_type,
        integration_http_method=None,
        uri=None,
        credentials=None,
        **kwargs,
    ):
        """
        Add an integration to a method of this resource.

        Args:
            http_method: HTTP method to add integration to
            integration_type: Type of integration (AWS, AWS_PROXY, HTTP, etc.)
            integration_http_method: HTTP method for the integration
            uri: URI for the integration
            credentials: IAM role ARN for the integration
            **kwargs: Additional parameters for put_integration

        Returns:
            dict: Integration creation response
        """

        if http_method.upper() not in self.methods:
            raise ValueError(f"Method {http_method} not found on resource {self.path}")

        try:
            integration_http_method = integration_http_method or http_method.upper()

            params = {
                "restApiId": self.api_id,
                "resourceId": self.resource_id,
                "httpMethod": http_method.upper(),
                "type": integration_type,
            }

            if uri:
                params["uri"] = uri
            if integration_http_method:
                params["integrationHttpMethod"] = integration_http_method
            if credentials:
                params["credentials"] = credentials

            snake_to_camel = {
                "connection_type": "connectionType",
                "connection_id": "connectionId",
                "request_parameters": "requestParameters",
                "request_templates": "requestTemplates",
                "passthrough_behavior": "passthroughBehavior",
                "cache_namespace": "cacheNamespace",
                "cache_key_parameters": "cacheKeyParameters",
                "content_handling": "contentHandling",
                "timeout_in_millis": "timeoutInMillis",
                "tls_config": "tlsConfig",
            }

            valid_params = set(snake_to_camel.values())
            # Only add kwargs that are valid API Gateway parameters
            for key, value in kwargs.items():
                camel_key = snake_to_camel.get(key, key)
                if camel_key in valid_params:
                    params[camel_key] = value
                else:
                    print(
                        f"Warning: Ignoring invalid parameter '{key}' for put_integration"
                    )

            response = self.apigateway.put_integration(**params)
            print(
                f"Added {integration_type} integration to {http_method} method on resource {self.path}"
            )
            # Configure default integration response
            self.apigateway.put_integration_response(
                restApiId=self.api_id,
                resourceId=self.resource_id,
                httpMethod=http_method.upper(),
                statusCode="200",
                responseTemplates={"application/json": ""},
            )

            return response
        except Exception as e:
            print(f"Failed to add integration: {str(e)}")
            raise
