# ----------------------------------------------------------------------------------------------------------------------
# Simple script to view AWS user info.
#
# usage: aws-users [--name user-name-pattern] ] [--verbose]
# ----------------------------------------------------------------------------------------------------------------------

import argparse
import boto3
import re
from aws_utils import (obfuscate, validate_aws)


def print_aws_users(name: str,
                    keys: bool = False,
                    verbose: bool = False,
                    access_key: str = None, secret_key: str = None, region: str = None):
    iam = boto3.resource('iam', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    users = iam.users.all()
    for user in sorted(users, key=lambda user: user.name):
        user_name = user.name
        if name and not re.search(name, user_name):
            continue
        if verbose:
            print(f"- {user_name} ({user.arn})")
        else:
            print(f"- {user_name}")
        if keys:
            for key in sorted(user.access_keys.all(), key=lambda key: key.id):
                print(f"  access key: {key.id}")


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--name", type=str, required=False)
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args_parser.add_argument("--keys", action="store_true", required=False)
    args_parser.add_argument("--verbose", action="store_true", required=False)
    args = args_parser.parse_args()

    print(f"AWS Users Utility", end = "")
    if args.name:
        print(" | names containing: " + args.name, end = "")
    print()

    access_key, secret_key, region = validate_aws(args.access_key, args.secret_key, args.region)

    print_aws_users(args.name, args.keys, args.verbose, access_key, secret_key, region)


if __name__ == "__main__":
    main()
