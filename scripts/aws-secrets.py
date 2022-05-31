# --------------------------------------------------------------------------------------------------
# Simple script to view AWS secrets info.
# By default prints all secrets names.
#
# usage: aws-secrets [--secret secret-name-pattern] [--secrets] [--show]
#
# If --name with a simple pattern is given then limit secrets to those
# whose name contains the specified simple pattern (case-insensitive).
#
# If --secrets is given then the secret keys/values are printed for each secret.
# Secret values with names that look senstive ("secret" or "password" etc) are obfuscated.
#
# If --secret with a simple pattern is given then limit secret key/values
# to those whose key contains the specified simple pattern (case-insensitive).
#
# If --show is given the prints obfuscated values in plaintext.
# --------------------------------------------------------------------------------------------------

import boto3
import json
import argparse

args_parser = argparse.ArgumentParser()
args_parser.add_argument("--name", type=str, required=False)
args_parser.add_argument("--secret", type=str, required=False)
args_parser.add_argument("--secrets", action="store_true", required=False)
args_parser.add_argument("--show", action="store_true", required=False)
args = args_parser.parse_args()

def should_obfuscate_secret(key: str) -> bool:
    key = key.lower()
    return "secret" in key or "password" in key or "passwd" in key or "crypt" in key

def obfuscate(value: str) -> str:
    return value[0:1] + "*******" if value is not None and len(value) > 0 else ""

def print_aws_secrets():

    print("AWS Secrets", end = "")
    if args.name:
        print(" / name containing: " + args.name, end = "")
    if args.secret:
        print(" / secret keys containing: " + args.secret, end = "")
    print()

    c4 = boto3.client('secretsmanager')
    for secret in sorted(c4.list_secrets()["SecretList"], key=lambda key: key["Name"].lower()):
        secret_name = secret["Name"]
        if args.name and not args.name.lower() in secret_name.lower():
            continue
        print(secret_name)
        if args.secret or args.secrets:
            secret_value = c4.get_secret_value(SecretId=secret_name)
            secret_value_json = json.loads(secret_value["SecretString"])
            for secret_key in sorted(secret_value_json.keys(), key=lambda key: key.lower()):
                if args.secret and not args.secret.lower() in secret_key.lower():
                    continue
                secret_value = secret_value_json[secret_key]
                if should_obfuscate_secret(secret_key) and not args.show:
                    secret_value = obfuscate(secret_value)
                print(f"- {secret_key}: {secret_value}")

if __name__ == "__main__":
    print_aws_secrets()
