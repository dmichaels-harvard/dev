# --------------------------------------------------------------------------------------------------
# Simple script to view AWS secrets info.
#
# By default prints just (all) the names of the secrets available,
# e.g. C4DatastoreCgapSupertestApplicationConfiguration. Use the --secrets
# option to see the actualy secret keys/values for each secret name.
# Values are obfuscated if they look like they represent true secrets.
#
# usage: aws-secrets [--names secret-name-pattern] [--secrets] [--show]
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

import argparse
import boto3
import json
import re

def print_aws_secrets(secret_name_pattern: str = None, secret_key_name_pattern: str = None, show: bool = False):
    """
    Prints (to stdout) AWS secrets for the currently active AWS credentials.

    By default prints just (all) the *names* of the secrets available,
    e.g. C4DatastoreCgapSupertestApplicationConfiguration. Use :param:`secret_name_pattern`
    to limit the secret names. Use :param:`secret_key_name_pattern` set to '*' or to some
    pattern to either print all secret keys/values (for each secret name) or to limit
    to those matching that pattern. Secret values with key name which look secret will
    be obfuscated by default; use :param:`show` to print them in plaintext.

    :param secret_name_pattern: If None then prints all secrets name,
      otherwise only those that contain the given pattern.
    :param secret_key_name_pattern: If None then does not print any secret keys/values;
      otherwise prints only those that contain the given pattern; use '*' for all.
    :param show: If False then obfuscates secret values with key name that look secret,
      e.g. containing 'password' or 'secret', otherwise prints all values in plaintext.
    """

    # Adjust/amend this as necessary.
    #
    SECRET_KEY_NAMES_FOR_OBFUSCATION = [ ".*secret.*", ".*secrt.*", ".*password.*", ".*passwd.*", ".*crypt.*" ]

    def should_obfuscate_secret(key: str) -> bool:
        """
        Returns True if the given key looks like it represents a secret value.
        N.B.: Dumb implementation. Just sees if it contains "secret" or "password"
        or "crypt" some obvious variants (case-insensitive), i.e. whatever is
        in the secret_key_names list, which can be a regular expression.
        Add more to secret_key_names if/when needed.
        """
        secret_key_names_regex = map(lambda regex: re.compile(regex, re.IGNORECASE), SECRET_KEY_NAMES_FOR_OBFUSCATION)
        return any(regex.match(key) for regex in secret_key_names_regex)

    def obfuscate(value: str) -> str:
        return value[0:1] + "*******" if value is not None and len(value) > 0 else ""

    # Just to allow simple '*' (at the beginning, or alone) as the patterns for convenience.
    # otherwise get: re.error: nothing to repeat at position 0
    #
    if secret_name_pattern and secret_name_pattern.startswith("*"):
        secret_name_pattern = ".*" + secret_name_pattern[1:]
    if secret_key_name_pattern and secret_key_name_pattern.startswith("*"):
        secret_key_name_pattern = ".*" + secret_key_name_pattern[1:]

    aws_access_key = boto3.Session().get_credentials().access_key

    print("AWS Secrets (%s)" % aws_access_key, end = "")
    if secret_name_pattern and secret_name_pattern != ".*":
        print(" / name contains: " + secret_name_pattern, end = "")
    if secret_key_name_pattern and secret_key_name_pattern != ".*":
        print(" / secret keys contains: " + secret_key_name_pattern, end = "")
    print("")

    c4 = boto3.client('secretsmanager')
    for secret in sorted(c4.list_secrets()["SecretList"], key=lambda key: key["Name"].lower()):
        secret_name = secret["Name"]
        if secret_name_pattern and not re.search(secret_name_pattern, secret_name, re.IGNORECASE):
            continue
        print(secret_name)
        if secret_key_name_pattern:
            secret_value = c4.get_secret_value(SecretId=secret_name)
            secret_value_json = json.loads(secret_value["SecretString"])
            for secret_key in sorted(secret_value_json.keys(), key=lambda key: key.lower()):
                if not re.search(secret_key_name_pattern, secret_key, re.IGNORECASE):
                    continue
                secret_value = secret_value_json[secret_key]
                if should_obfuscate_secret(secret_key) and not show:
                    secret_value = obfuscate(secret_value)
                print(f"- {secret_key}: {secret_value}")

if __name__ == "__main__":
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--name", type=str, required=False)
    #
    # How can we make --secret take an *option* argument,
    # so we can not have both '--secrets' and '--secret pattern'?
    #
    args_parser.add_argument("--secret", type=str, required=False)
    args_parser.add_argument("--secrets", action="store_true", required=False)
    args_parser.add_argument("--show", action="store_true", required=False)
    args = args_parser.parse_args()
    secret_key_name_pattern = args.secret
    if not secret_key_name_pattern and args.secrets:
        secret_key_name_pattern = ".*"
    print_aws_secrets(secret_name_pattern=args.name, secret_key_name_pattern=secret_key_name_pattern, show=args.show)
