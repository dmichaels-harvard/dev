# --------------------------------------------------------------------------------------------------
# Simple script to view AWS stack templates.
#
# usage: aws-stack-template stack-name
# --------------------------------------------------------------------------------------------------

import boto3
import os
import re


def obfuscate(value: str) -> str:
    return value[0:1] + "*******" if value is not None and len(value) > 0 else ""


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


def validate_aws_credentials(access_key: str = None, secret_key: str = None, region: str = None, display: bool = False) -> [str, str, str]:
    try:
        session = None
        if not access_key or not secret_key:
            session = boto3.Session()
            credentials = session.get_credentials()
            access_key = credentials.access_key if not access_key else access_key
            secret_key = credentials.secret_key if not secret_key else secret_key
        if not region:
            if not session:
                session = boto3.Session()
            region = session.region_name if not region else region
        if display:
            print("AWS Credentials: %s | %s | %s" % (access_key, obfuscate(secret_key), region))
        return access_key, secret_key, region
    except Exception as e:
        print("Cannot determine AWS credentials!")
        print(str(e))
        exit(1)
