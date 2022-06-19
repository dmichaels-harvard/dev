# EXPERIEMENT IN PROGRESS
# Script for 4dn-cloud-infra to fill out remaining secrets in GAC aftere datastore setup.

import argparse
import boto3
import contextlib
import io
import json
import os
import re
from ..init_custom_dir.defs import (InfraDirectories, InfraFiles)
from .aws_context import AwsContext
from ...names import Names

# QUESTION:
# Where to get AWS credentials from?
# 1. custom/aws_creds (credentials, config)
#    To get boto3 to point to file other than ~/.aws/credentials
#    set environment variable: AWS_SHARED_CREDENTIALS_FILE
#    To get boto3 to point to file other than ~/.aws/config
#    set environment variable: AWS_CONFIG_FILE


def get_custom_dir(custom_dir: str = None):
    if not custom_dir:
        custom_dir = InfraDirectories.CUSTOM_DIR
    return InfraDirectories.get_custom_dir(custom_dir)


def get_custom_aws_creds_dir(custom_dir: str = None):
    custom_dir = get_custom_dir(custom_dir)
    return InfraDirectories.get_custom_aws_creds_dir(custom_dir)


def get_custom_config_file(custom_dir: str = None):
    custom_dir = get_custom_dir(custom_dir)
    return InfraFiles.get_config_file(custom_dir)


class Aws(AwsContext):

    def find_secret_name(self, secret_name_pattern: str) -> str:
        with super().establish_credentials():
            secrets_manager = boto3.client('secretsmanager')
            for secret in secrets_manager.list_secrets()["SecretList"]:
                secret_name = secret["Name"]
                if re.search(secret_name_pattern, secret_name):
                    return secret_name
        return None

    def get_secret_value(self, secret_name: str, secret_key_name: str) -> str:
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
        :param secrets_manager: AWS secrets manager ala boto3.
        :param secret_name: AWS secret name.
        :param secret_key_name: AWS secret key name to update.
        :param secret_key_value: AWS secret key value to update to. If None then the secret key will be deleted.
        :param prompt: Prompt for confirmation (from stdin) if True otherwise silent.
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
                action = None
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
        federated_iam_user_name_pattern = "ApplicationS3Federator"
        with super().establish_credentials():
            iam = boto3.resource('iam')
            iam_users = iam.users.all()
            for iam_user in sorted(iam_users, key=lambda user: user.name):
                iam_user_name = iam_user.name
                if not re.search(federated_iam_user_name_pattern, iam_user_name):
                    continue
                return iam_user_name
            return None

    def get_kms_keys(self, customer: bool):
        result_keys = []
        with super().establish_credentials():
            kms = boto3.client("kms")
            for key in kms.list_keys()["Keys"]:
                key_id = key["KeyId"]
                key_description = kms.describe_key(KeyId=key_id)
                key_metadata = key_description["KeyMetadata"]
                key_manager = key_metadata["KeyManager"]
                if not customer or key_manager == "CUSTOMER":
                    result_keys.append(key_id)
        return result_keys

    def get_opensearch_endpoint(self, aws_credentials_name: str):
        with super().establish_credentials():
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


def get_custom_config_file_value(name: str):
    custom_config_file = get_custom_config_file()
    custom_config_json = None
    with io.open(custom_config_file, "r") as custom_config_fp:
        custom_config_json = json.load(custom_config_fp)
        return custom_config_json.get(name)
    return None


def get_account_number_from_config_file():
    return get_custom_config_file_value("account_number")


def get_aws_credentials_name(custom_dir: str = None):
    return get_custom_config_file_value("ENCODED_ENV_NAME")


def get_identity(aws_credentials_name: str) -> str:
    """
    Obtains/returns the 'identity', i.e. the global application configuration name using
    the same code that 4dn-cloud-infra code does (see C4Datastore.application_configuration_secret).
    Had to do some refactoring to get this working (see names.py).

    :param aws_credentials_name: AWS credentials name (e.g. cgap-supertest).
    :return: Identity (global application configuration name) as gotten from the main 4dn-cloud-infra code.
    """
    try:
        identity_value = Names.application_configuration_secret(aws_credentials_name)
    except Exception:
        identity_value = None
    return identity_value


def should_obfuscate(key: str) -> bool:
    """
    Returns True if the given key looks like it represents a secret value.
    N.B.: Dumb implementation. Just sees if it contains "secret" or "password"
    or "crypt" some obvious variants (case-insensitive), i.e. whatever is
    in the SECRET_KEY_NAMES_FOR_OBFUSCATION list, which can be a regular
    expression. Add more to SECRET_KEY_NAMES_FOR_OBFUSCATION if/when needed.
    """
    SECRET_KEY_NAMES_FOR_OBFUSCATION = [
        ".*secret.*",
        ".*secrt.*",
        ".*password.*",
        ".*passwd.*",
        ".*crypt.*"
    ]
    secret_key_names_regex = map(lambda regex: re.compile(regex, re.IGNORECASE), SECRET_KEY_NAMES_FOR_OBFUSCATION)
    return any(regex.match(key) for regex in secret_key_names_regex)


def obfuscate(value: str) -> str:
    """
    Obfuscates and returns the given string value.

    :param value: Value to obfuscate.
    :return: Obfuscated value or empty string if not a string or empty.
    """
    return value[0] + "*******" if isinstance(value, str) else "********"


def main():

    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--custom-dir", type=str, required=False)
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args_parser.add_argument("--show", action="store_true", required=False)
    args = args_parser.parse_args()

    # Intialize the dictionary secrets to set, which we will collect here.
    secrets_to_update = {}

    # Gather the basic info.
    custom_dir = "custom"
    custom_dir = get_custom_dir(custom_dir)
    custom_aws_creds_dir = get_custom_aws_creds_dir(custom_dir)
    custom_config_file = get_custom_config_file(custom_dir)
    aws_credentials_name = get_aws_credentials_name()

    # Get AWS credentials context object.
    aws = Aws(custom_aws_creds_dir, args.access_key, args.secret_key, args.region)

    # Get the "identity" name, i.e. the global application confguration (GAC) secret name.
    identity = get_identity(aws_credentials_name)

    print(f"Setting up 4dn-cloud-infra remaining AWS secrets for: {identity}")

    print(f"Your custom directory: {custom_dir}")
    print(f"Your custom config file: {custom_config_file}")
    print(f"Your AWS credentials directory: {custom_aws_creds_dir}")
    print(f"Your AWS credentials name: {aws_credentials_name}")

    # Get the ACCOUNT_NUMBER.
    account_number = get_account_number_from_config_file()
    print(f"Your AWS account number: {account_number}")

    # Sanity check ACCOUNT_NUMBER with what AWS tells us it is.
    with aws.establish_credentials():
        print(f"Your AWS access key: {aws.access_key_id}")
        print(f"Your AWS access secret: {obfuscate(aws.secret_access_key)}")
        if account_number != aws.account_number:
            custom_config_file = get_custom_config_file()
            print(f"WARNING: Account number from your config file ({account_number}) not the same AWS credentials account ({aws.account_number}).")
        secrets_to_update["ACCOUNT_NUMBER"] = aws.account_number

    # Get the IAM "federator" user name.
    iam_federator_user_name = aws.get_federated_user_name()
    print(f"Federated AWS user: {iam_federator_user_name}")

    # Create the security credentials access key/secret pait for the IAM "federator" user.
    key_id, key_secret = aws.create_user_access_key(iam_federator_user_name)
    secrets_to_update["S3_AWS_ACCESS_KEY_ID"] = key_id
    secrets_to_update["S3_AWS_SECRET_ACCESS_KEY"] = key_secret

    # Get the ElasticSearch server/host name.
    es_server = aws.get_opensearch_endpoint(aws_credentials_name)
    secrets_to_update["ENCODED_ES_SERVER"] = es_server

    # Get the RDS hostname and password,
    # This is from the secret keys named "host" and "password" in
    # within the secret name ending in "RDSSecret" in the secrets manager;
    # the "password" is from src/parts/datastore.py/C4Datastore.rds_secret;
    # not sure where "host" is from;
    # the secret name (RDSSecret) is from src/parts/datastore.py/C4Datastore.RDS_SECRET_NAME_SUFFIX;
    # these could/should be factored out.
    rds_secret_name = aws.find_secret_name("C4DatastoreCgapSupertestRDSSecret")
    print(f"RDS secret name is: {rds_secret_name}")
    rds_hostname = aws.get_secret_value(rds_secret_name, "host")
    print(f"RDS host name is: {rds_hostname}")
    rds_password = aws.get_secret_value(rds_secret_name, "password")
    print(f"RDS host password is: {obfuscate(rds_password)}")
    secrets_to_update["RDS_HOST"] = rds_hostname
    secrets_to_update["RDS_PASSWORD"] = rds_password

    # Get the ENCODED_S3_ENCRYPT_KEY_ID from KMS.
    # TODO: what to do if more than one exists?
    s3_encrypt_key_id = aws.get_kms_keys(True)
    secrets_to_update["ENCODED_S3_ENCRYPT_KEY_ID"] = s3_encrypt_key_id[0]

    print(f"Here are the secrets which will be set for secret: {identity}")
    for secret_key, secret_value in secrets_to_update.items():
        if should_obfuscate(secret_key):
            print(f"- {secret_key}: {obfuscate(secret_value)}")
        else:
            print(f"- {secret_key}: {secret_value}")
    yes_or_no = input("Do you want to go ahead and set these secrets in AWS? [yes/no] ").strip().lower()
    if yes_or_no == "yes":
        for secret_key_name, secret_key_value in secrets_to_update.items():
            print(f"Updating {identity}.{secret_key_name} to: {secret_key_value}")
            yes_or_no = input("Really? [yes/no] ")
            aws.update_secret_key_value(identity, secret_key_name, secret_key_value)
        print("Not actually setting now. Testing.")
    else:
        print("No action taken.")


if __name__ == "__main__":
    main()
