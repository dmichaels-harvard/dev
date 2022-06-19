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
from .aws_functions import AwsFunctions
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
    args_parser.add_argument("--identity", type=str, required=False)
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
    aws = AwsFunctions(custom_aws_creds_dir, args.access_key, args.secret_key, args.region)

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
