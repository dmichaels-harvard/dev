# Script for 4dn-cloud-infra to update KMS key policy for Foursight.

import argparse
import boto3
import contextlib
import io
import json
import os
import re
from typing import Optional
from dcicutils.command_utils import yes_or_no
from dcicutils.misc_utils import PRINT
from .defs import (InfraDirectories, InfraFiles)
from ..setup_remaining_secrets.aws_functions import AwsFunctions
from ..setup_remaining_secrets.utils import (exit_with_no_action, obfuscate, print_dictionary_as_table, should_obfuscate)
    

def get_config_file_value(name: str, config_file: str, fallback: str = None) -> str:
    with io.open(config_file, "r") as config_fp:
        config_json = json.load(config_fp)
        value = config_json.get(name)
        return value if value else fallback
    return None


def validate_custom_dir(custom_dir: str) -> str:
    custom_dir = InfraDirectories.get_custom_dir(custom_dir)
    if not custom_dir:
        exit_with_no_action("ERROR: No custom directory specified.")
    if not os.path.isdir(custom_dir):
        exit_with_no_action(f"ERROR: Custom directory does not exist: {custom_dir}")
    config_file = InfraFiles.get_config_file(custom_dir)
    if not os.path.isfile(config_file):
        exit_with_no_action(f"ERROR: Custom config file does not exist: {config_file}")
    return custom_dir, config_file


def validate_aws_credentials_name(aws_credentials_name: str, config_file: str) -> str:
    if not aws_credentials_name:
        aws_credentials_name = get_config_file_value("ENCODED_ENV_NAME", config_file)
        if not aws_credentials_name:
            exit_with_no_action("ERROR: Cannot determine AWS credentials name")
    return aws_credentials_name


def validate_aws_credentials_dir(aws_credentials_dir: str, custom_dir: str) -> str:
    if not aws_credentials_dir:
        aws_credentials_dir = InfraDirectories.get_custom_aws_creds_dir(custom_dir)
    if aws_credentials_dir:
        if not os.path.isdir(aws_credentials_dir):
            exit_with_no_action(f"ERROR: AWS credentials directory does not exist: {aws_credentials_dir}")
    return aws_credentials_dir


def validate_aws_credentials(access_key_id: str, secret_access_key: str, default_region, credentials_dir: str, show: bool = False) -> [AwsFunctions,object]:

    if not access_key_id or not secret_access_key:
        credentials_dir_symlink_target = os.readlink(credentials_dir) if os.path.islink(credentials_dir) else None
        if credentials_dir_symlink_target:
            PRINT(f"Your AWS credentials directory (link): {credentials_dir}@ ->")
            PRINT(f"Your AWS credentials directory (real): {credentials_dir_symlink_target}")
        else:
            PRINT(f"Your AWS credentials directory: {credentials_dir}")

    # Get AWS credentials context object.
    aws = AwsFunctions(credentials_dir, access_key_id, secret_access_key, default_region)

    # Verify the AWS credentials context and get the associated AWS credentials number.
    with aws.establish_credentials() as credentials:
        PRINT(f"Your AWS account number: {credentials.account_number}")
        PRINT(f"Your AWS access key: {credentials.access_key_id}")
        PRINT(f"Your AWS access secret: {credentials.secret_access_key if show else obfuscate(credentials.secret_access_key)}")
        PRINT(f"Your AWS default region: {credentials.default_region}")
        PRINT(f"Your AWS account number: {credentials.account_number}")
        PRINT(f"Your AWS account user ARN: {credentials.user_arn}")
        return aws, credentials


def update_kms_policy(args) -> None:

    # Intialize the dictionary secrets to set, which we will collect here.
    secrets_to_update = {}

    # Gather the basic info.
    custom_dir, config_file = validate_custom_dir(args.custom_dir)
    aws_credentials_name = validate_aws_credentials_name(args.aws_credentials_name, config_file)
    aws_credentials_dir = validate_aws_credentials_dir(args.aws_credentials_dir, custom_dir)

    # Print header and basic info.
    PRINT(f"Updating 4dn-cloud-infra KMS policy remaining")
    PRINT(f"Your custom directory: {custom_dir}")
    PRINT(f"Your custom config file: {config_file}")
    PRINT(f"Your AWS credentials name: {aws_credentials_name}")

    # Validate and print basic AWS credentials info.
    aws, aws_credentials = validate_aws_credentials(args.aws_access_key_id,
                                                    args.aws_secret_access_key,
                                                    args.aws_default_region,
                                                    aws_credentials_dir,
                                                    args.show)
    # TODO
    s3_encrypt_kms_keys = aws.get_customer_managed_kms_keys()
    s3_encrypt_kms_key = s3_encrypt_kms_keys[0]
    PRINT(f"Application KMS key ID: {s3_encrypt_kms_key}")

    s3_encrypt_kms_key_sid_pattern = "Allow use of the key"
    foursight_role_names_pattern = ".*foursight.*"
    s3_encrypt_kms_key_additional_roles = aws.find_iam_role_names(foursight_role_names_pattern)
    aws.update_kms_key_policy(s3_encrypt_kms_key, s3_encrypt_kms_key_sid_pattern, s3_encrypt_kms_key_additional_roles)


def main(override_argv: Optional[list] = None) -> None:

    argp = argparse.ArgumentParser()
    argp.add_argument("--aws-access-key-id", required=False,
                      dest="aws_access_key_id",
                      help=f"Your AWS access key ID; also requires --aws-access-secret-key.")
    argp.add_argument("--aws-credentials-dir", required=False,
                      dest="aws_credentials_dir",
                      help=f"Alternate full path to your custom AWS credentials directory.")
    argp.add_argument("--aws-credentials-name", required=False,
                      dest="aws_credentials_name",
                      help=f"The name of your AWS credentials,"
                           f"e.g. <aws-credentials-name> from {InfraDirectories.AWS_DIR}.<aws-credentials-name>.")
    argp.add_argument("--aws-secret-access-key", required=False,
                      dest="aws_secret_access_key",
                      help=f"Your AWS access key ID; also requires --aws-access-key-id.")
    argp.add_argument("--custom-dir", required=False, default=InfraDirectories.CUSTOM_DIR,
                      dest="custom_dir",
                      help=f"Alternate custom config directory to default: {InfraDirectories.CUSTOM_DIR}.")
    argp.add_argument("--no-confirm", required=False,
                      dest="confirm", action="store_false", 
                      help="Behave as if all confirmation questions were answered yes.")
    argp.add_argument("--aws-default-region", required=False,
                      dest="aws_default_region",
                      help="The default AWS region.")
    argp.add_argument("--show", action="store_true", required=False)
    args = argp.parse_args(override_argv)

    if (args.aws_access_key_id or args.aws_secret_access_key) and not (args.aws_access_key_id and args.aws_secret_access_key):
        exit_with_no_action("Either none or both --aws-access-key-id and --aws-secret-access-key must be specified.")

    update_kms_policy(args)


if __name__ == "__main__":
    main()
