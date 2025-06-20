import boto3
import json


def create_iam_role(role_name="api_gateway_role"):
    iam = boto3.client("iam")
    # iam.create_user(UserName="api_gateway_role")
    # Create role
    role = iam.get_role(RoleName=role_name)
    if not role:
        # for API Gateway Trust Policy
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "apigateway.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )
    # Attach policy to role
    attach_policy = True
    while attach_policy:
        policy_name = input("Enter policy name: ")
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=get_iam_policy_arn(policy_name),
        )
        if input("Press Y to attach policy to role or N to skip: ") == "Y":
            attach_policy = True
            policy_name = input("Enter policy name: ")
        else:
            attach_policy = False
            break

    print(f"Created role {role['Role']['Arn']}")
    return role["Role"]["Arn"]


def create_iam_policy(policy_name):
    iam = boto3.client("iam")
    policy = iam.create_policy(
        PolicyName=policy_name,
        PolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["logs:*"],
                        "Resource": "*",
                    }
                ],
            }
        ),
    )
    print(f"Created policy {policy['Policy']['Arn']}")
    return policy["Policy"]["Arn"]


def get_iam_policy_arn(policy_name):
    iam = boto3.client("iam")
    policy = iam.get_policy(PolicyArn=policy_name)
    return policy["Policy"]["Arn"]


if __name__ == "__main__":
    create_iam_role()
