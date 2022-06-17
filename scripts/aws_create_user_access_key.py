# ----------------------------------------------------------------------------------------------------------------------
# Simple script to create AWS a user access key pair.
#
# usage: aws-create-user-access-key [--name user-name]
# ----------------------------------------------------------------------------------------------------------------------

import argparse
import boto3
import re
from aws_utils import (obfuscate, validate_aws)


def create_aws_user_access_key(name: str,
                               access_key: str = None, secret_key: str = None, region: str = None):

    iam = boto3.resource('iam', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    user = [user for user in iam.users.all() if user.name == name]
    if not user or len(user) <= 0:
        print("AWS user not found: {name}")
        return False
    if len(user) > 1:
        print("Too many AWS users found for: {name}")
        return False
    user = user[0]
    sts = boto3.client('sts', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    print(f"Creating AWS security credentials access key pair for user: {user.name}")
    print(f"The access key and secret will be displayed in plaintext.")
    yes_or_no = input("Do you want to continue? [yes/no] ").strip().lower()
    if yes_or_no == "yes":
        key_pair = user.create_access_key_pair()
        print(f"AWS Access Key ID ({user.name}): {key_pair.id}")
        print(f"AWS Secret Access Key ({user.name}): {key_pair.secret}")
    return True


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--name", type=str, required=True)
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args = args_parser.parse_args()

    print(f"AWS User Access Key Create Utility | {args.name}")

    access_key, secret_key, region = validate_aws(args.access_key, args.secret_key, args.region)

    create_aws_user_access_key(args.name, access_key, secret_key, region)


if __name__ == "__main__":
    main()
