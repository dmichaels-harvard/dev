# --------------------------------------------------------------------------------------------------
# Simple script to view AWS secrets info.
#
# By default prints just (all) the names of the secrets available,
# e.g. C4DatastoreCgapSupertestApplicationConfiguration. Use the --secrets
# option to see the actualy secret keys/values for each secret name.
# Values are obfuscated if they look like they represent true secrets.
#
# usage: aws-secrets [--names secret-name-pattern] [--secrets [secret-key-pattern]] [--show]
#
# If --name with a simple pattern is given then limit secrets to those
# whose name contains the specified simple pattern (case-insensitive).
#
# If --secrets is given then the secret keys/values are printed for each secret.
# If a simple pattern is given after this then limit secret keys/values 
# to those whose key contains the specified simple pattern (case-insensitive).
#
# N.B. Secret values with names that look senstive ("secret" or "password" etc) are obfuscated.
#
# If --show is given the prints obfuscated values in plaintext.
# --------------------------------------------------------------------------------------------------

import argparse
import boto3
import json
import re
from aws_utils import (obfuscate, should_obfuscate, validate_aws)


def print_aws_secrets(secret_name_pattern: str = None,
                      secret_key_name_pattern: str = None,
                      access_key: str = None, secret_key: str = None, region: str = None,
                      show: bool = False):
    """
    Prints (to stdout) AWS secrets for the currently active AWS credentials.

    By default prints just (all) the *names* of the secrets available, e.g.
    C4DatastoreCgapSupertestRDSSecret. Use :param:`secret_name_pattern`
    to limit these secret names. Use :param:`secret_key_name_pattern` set to '*'
    to print all secret keys/values (for each secret name), or to some pattern to
    limit to keys matching that pattern. Secret values with key name which *look*
    secret will obfuscated by default; use :param:`show` to print them in plaintext.
    See SECRET_KEY_NAMES_FOR_OBFUSCATION above for what looks like a secret key name. 

    :param secret_name_pattern: If None then prints all secrets name,
      otherwise only those that contain the given pattern.
    :param secret_key_name_pattern: If None then does not print any secret keys/values;
      otherwise prints only for keys that contain the given pattern; use '*' for all.
    :param show: If False (default) then obfuscates secret values with key name that look
      secret, e.g. containing 'password' or 'secret', otherwise prints values in plaintext.
    """

    # Just to allow simple '*' (at the beginning, or alone) as the patterns for convenience.
    # otherwise get: re.error: nothing to repeat at position 0
    #
    if secret_name_pattern and secret_name_pattern.startswith("*"):
        secret_name_pattern = ".*" + secret_name_pattern[1:]
    if secret_key_name_pattern and secret_key_name_pattern.startswith("*"):
        secret_key_name_pattern = ".*" + secret_key_name_pattern[1:]

    c4 = boto3.client('secretsmanager', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    for secret in sorted(c4.list_secrets()["SecretList"], key=lambda key: key["Name"].lower()):
        #
        # This secret_name is the secret *name* (in contrast to a secret *key* name).
        #
        secret_name = secret["Name"]
        if secret_name_pattern and not re.search(secret_name_pattern, secret_name, re.IGNORECASE):
            continue
        print(secret_name)
        if secret_key_name_pattern:
            secret_values = c4.get_secret_value(SecretId=secret_name)
            secret_values_json = json.loads(secret_values["SecretString"])
            for secret_key_name in sorted(secret_values_json.keys(), key=lambda key: key.lower()):
                #
                # This secret_key_name is an individual secret key name (for the given secret_name).
                #
                if not re.search(secret_key_name_pattern, secret_key_name, re.IGNORECASE):
                    continue
                secret_value = secret_values_json[secret_key_name]
                if should_obfuscate(secret_key_name) and not show:
                    secret_value = obfuscate(secret_value)
                if secret_value is None:
                    print(f"- {secret_key_name}: <no-value-exists>")
                else:
                    print(f"- {secret_key_name}: {secret_value}")


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--name", type=str, required=False)
    args_parser.add_argument('--secrets', type=str, const='.*', nargs='?')
    args_parser.add_argument("--show", action="store_true", required=False)
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args = args_parser.parse_args()

    print("AWS Secrets Utility", end = "")
    if args.name and args.name != ".*":
        print(" | names containing: " + args.name, end = "")
    if args.secrets and args.secrets != ".*":
        print(" | secret keys containing: " + args.secrets, end = "")
    print("")

    access_key, secret_key, region = validate_aws(args.access_key, args.secret_key, args.region, True)

    print_aws_secrets(secret_name_pattern=args.name,
                      secret_key_name_pattern=args.secrets,
                      access_key=access_key, secret_key=secret_key, region=region,
                      show=args.show)


if __name__ == "__main__":
    main()
