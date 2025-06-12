import boto3
import base64
import json
import argparse
from botocore.exceptions import ClientError

# secret_name = "test/demodbMySql"
#     region_name = "us-east-1"
parser = argparse.ArgumentParser()
parser.add_argument("--secret", type = str, required=True)
parser.add_argument("--region", type = str, required=False)
args = parser.parse_args()


def get_secret(s,r):


    secret_name = s
    region_name = r


    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # Get the secret value as a dictionary, checking for exceptions
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return json.loads(secret) # returns the secret as dictionary
        else:
            # decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return json.loads(secret) # returns the secret as dictionary


def main():
    secret_name = args.secret
    region_name = args.region
    password=get_secret(secret_name,region_name)
    # add code here to access the database
    print("@@Result=" + str(password))

if __name__ == '__main__':
    main()