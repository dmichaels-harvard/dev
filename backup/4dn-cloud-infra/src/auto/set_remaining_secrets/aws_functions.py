import boto3
import json
import re
from .aws_context import AwsContext
from .utils import (obfuscate, should_obfuscate)

class AwsFunctions(AwsContext):

    def find_secret_name(self, secret_name_pattern: str) -> str:
        """
        Returns the first secret name in the AWS secrets manager which
        matches the given (regular expression) pattern.
        :param secret_name_pattern: Regular expression for secret name.
        :return: Matched secret name or None if none found.
        """
        with super().establish_credentials():
            secrets_manager = boto3.client('secretsmanager')
            for secret in secrets_manager.list_secrets()["SecretList"]:
                secret_name = secret["Name"]
                if re.search(secret_name_pattern, secret_name):
                    return secret_name
        return None

    def get_secret_value(self, secret_name: str, secret_key_name: str) -> str:
        """
        Returns the value of the given secret key name
        within the given secret name in the AWS secrets manager.
        :param secret_name: AWS secret name.
        :param secret_key_name: AWS secret key name.
        :return: Secret key value if found or None if not found.
        """
        with super().establish_credentials():
            secrets_manager = boto3.client('secretsmanager')
            secret_values = secrets_manager.get_secret_value(SecretId=secret_name)
            secret_values_json = json.loads(secret_values["SecretString"])
            secret_key_value = secret_values_json.get(secret_key_name)
            return secret_key_value

    def update_secret_key_value(self,
                                secret_name: str,
                                secret_key_name: str,
                                secret_key_value: str) -> bool:
        """
        Updates the AWS secret value for the given secret key name within the given secret name.
        If the given secret key value does not yet exist it will be created.
        If the given secret key value is None then the given secret key will be deleted.
        This is an command-line interactive process, prompting the user for info/confirmation.
        :param secrets_manager: AWS secrets manager ala boto3.
        :param secret_name: AWS secret name.
        :param secret_key_name: AWS secret key name to update.
        :param secret_key_value: AWS secret key value to update to. If None then the secret key will be deleted.
        :return: True if succeeded otherwise false.
        """
        with super().establish_credentials():
            secrets_manager = boto3.client('secretsmanager')
            try:
                # To update an individual secret key value we need to get the entire JSON
                # associated with the given secret name, update the specific element for
                # the given secret key name with the new given value, and write the updated
                # JSON back as the secret value for the given secret name.
                try:
                    secret_value = secrets_manager.get_secret_value(SecretId=secret_name)
                except:
                    print(f"AWS secret name does not exist: {secret_name}")
                    return False
                secret_value_json = json.loads(secret_value["SecretString"])
                secret_key_value_current = secret_value_json.get(secret_key_name)
                if secret_key_value is None:
                    if secret_key_value_current is None:
                        print(f"AWS secret {secret_name}.{secret_key_name} does not exist. Nothing to delete.")
                        return False
                    action = "delete"
                else:
                    if secret_key_value_current is None:
                        print(f"AWS secret {secret_name}.{secret_key_name} does not yet exist.")
                        action = "create"
                    else:
                        if should_obfuscate(secret_key_name):
                            print(f"Current value of AWS secret looks like it is sensitive: {secret_name}.{secret_key_name}")
                            yes_or_no = input("Show in plaintext? [yes/no] ").strip().lower()
                            if yes_or_no:
                                print(f"Current value of AWS secret {secret_name}.{secret_key_name} is: {secret_key_value_current}")
                            else:
                                print(f"Current value of AWS secret {secret_name}.{secret_key_name} is: {obfuscate(secret_key_value_current)}")
                        else:
                            print(f"Current value of AWS secret {secret_name}.{secret_key_name} is: {secret_key_value_current}")
                        action = "update"
                    print(f"New value of AWS secret {secret_name}.{secret_key_name} is: {secret_key_value}")
                    if secret_key_value_current == secret_key_value:
                        print("Values are not different. Nothing to update.")
                        return False
                yes_or_no = input(f"Are you sure you want to {action} AWS secret {secret_name}.{secret_key_name}? [yes/no] ").strip().lower()
                if yes_or_no == "yes":
                    if secret_key_value is None:
                        del secret_value_json[secret_key_name]
                    else:
                        secret_value_json[secret_key_name] = secret_key_value
                    secrets_manager.update_secret(SecretId=secret_name, SecretString=json.dumps(secret_value_json))
                    return True
            except Exception as e:
                print(f"EXCEPTION: {str(e)}")
            return False

    def find_iam_user_name(self, user_name_pattern: str) -> str:
        """
        Returns the first AWS IAM user name in which
        matches the given (regular expression) pattern.
        :param user_name_pattern: Regular expression for user name.
        :return: Matched user name or None if none found.
        """
        with super().establish_credentials():
            iam = boto3.resource('iam')
            users = iam.users.all()
            for user in sorted(users, key=lambda user: user.name):
                user_name = user.name
                if not re.search(user_name_pattern, user_name):
                    continue
                return user_name
        return None

    def get_federated_user_name(self):
        # TODO: For our anticipated use case (setting up remaining secrets for 4dn-cloud-infra deploy),
        # we will use the IAM user with a name containing "ApplicationS3Federator" where this string
        # comes from logical_id in 4dn-cloud-infra/src/parts/iam.py/ecs_s3_iam_user(),
        # so we will want to factor that out into a common/shared file.
        # Or, can get this from the C4IAMMainECSS3IAMUser outputs of the "main" stack,
        # where the name C4IAMMainECSS3IAMUser is from C4IAMExports.S3_IAM_USER but
        # really from self.output_assumed_iam_role_or_user(s3_iam_user, export_name=C4IAMExports.S3_IAM_USER)
        # in 4dn-cloud-infra/src/parts/iam.py/build_template(). 
        # federator_user_name_pattern = "ApplicationS3Federator"
        # return aws_find_iam_user(custom_dir, federator_user_name_pattern)
        federated_user_name_pattern = "ApplicationS3Federator"
        return self.find_iam_user_name(federated_user_name_pattern)

    def get_customer_managed_kms_keys(self):
        """
        Returns the customer managed AWS KMS key IDs.
        :return: List of customer managed KMS key IDs; empty list of none found.
        """
        result_keys = []
        with super().establish_credentials():
            kms = boto3.client("kms")
            for key in kms.list_keys()["Keys"]:
                key_id = key["KeyId"]
                key_description = kms.describe_key(KeyId=key_id)
                key_metadata = key_description["KeyMetadata"]
                key_manager = key_metadata["KeyManager"]
                if key_manager == "CUSTOMER":
                    result_keys.append(key_id)
        return result_keys

    def get_opensearch_endpoint(self, aws_credentials_name: str):
        """
        Returns the endpoint (host:port) for the ElasticSearch instance associated
        with the given AWS credentials name (e.g. cgap-supertest).
        :return: Endpoint (host:port) for ElasticSearch or None if not found.
        """
        with super().establish_credentials():
            # TODO: Get this name from somewhere in 4dn-cloud-infra.
            opensearch_instance_name = f"es-{aws_credentials_name}"
            opensearch = boto3.client('opensearch')
            domain_names = opensearch.list_domain_names()["DomainNames"]
            domain_name = [domain_name for domain_name in domain_names if domain_name["DomainName"] == opensearch_instance_name]
            if domain_name is None or len(domain_name) != 1:
                return None
            domain_name = domain_name[0]["DomainName"]
            domain_description = opensearch.describe_domain(DomainName=domain_name)
            domain_status = domain_description["DomainStatus"]
            domain_endpoints = domain_status["Endpoints"]
            domain_endpoint_options = domain_status["DomainEndpointOptions"]
            domain_endpoint_vpc = domain_endpoints["vpc"]
            domain_endpoint_https = domain_endpoint_options["EnforceHTTPS"]
            if domain_endpoint_https:
                domain_endpoint = f"{domain_endpoint_vpc}:443"
            else:
                domain_endpoint = f"{domain_endpoint_vpc}:80"
            return domain_endpoint

    def create_user_access_key(self, user_name: str) -> [str,str]:
        """
        Create an AWS security credentials access key pair for the given IAM user name.
        This is an command-line interactive process, prompting the user for info/confirmation.
        And, the secret part of the access key pair will be printed in plaintext,
        because this is the only time it will ever be available.
        :param user_name: AWS IAM user name.
        :return: Tuple containing the access key ID and associated secret.
        """
        with super().establish_credentials():
            iam = boto3.resource('iam')
            user = [user for user in iam.users.all() if user.name == user_name]
            if not user or len(user) <= 0:
                print("AWS user not found: {user_name}")
                return None, None
            if len(user) > 1:
                print("Too many AWS users found for: {user_name}")
                return None, None
            user = user[0]
            print(f"Creating AWS security credentials access key pair for user: {user.name}")
            existing_keys = boto3.client('iam').list_access_keys(UserName=user.name)
            if existing_keys:
                existing_keys = existing_keys.get("AccessKeyMetadata")
                if existing_keys and len(existing_keys) > 0:
                    if len(existing_keys) ==  1:
                        print(f"This user ({user.name}) already has an access key defined:")
                    else:
                        print(f"This user ({user.name}) already has {len(existing_keys)} access keys defined:")
                    for existing_key in existing_keys:
                        existing_access_key_id = existing_key["AccessKeyId"]
                        existing_access_key_create_date = existing_key["CreateDate"]
                        print(f"- {existing_access_key_id} (created: {existing_access_key_create_date.astimezone().strftime('%Y-%m-%d %H:%M:%S')})")
                        yes_or_no = input("Do you still want to create a new access key? [yes/no] ").strip().lower()
                        if yes_or_no != "yes":
                            return None, None
            print(f"The created access key and secret will be displayed in plaintext.")
            yes_or_no = input("Do you want to continue? [yes/no] ").strip().lower()
            if yes_or_no == "yes":
                key_pair = user.create_access_key_pair()
                print(f"AWS Access Key ID ({user.name}): {key_pair.id}")
                print(f"AWS Secret Access Key ({user.name}): {key_pair.secret}")
                return key_pair.id, key_pair.secret
            return None, None
