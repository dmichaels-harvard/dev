# --------------------------------------------------------------------------------------------------
# Simple script to view AWS stack templates.
#
# usage: aws-stack-template stack-name
# --------------------------------------------------------------------------------------------------

import boto3
import os


def validate_aws_credentials(access_key: str = None, secret_key: str = None, region: str = None) -> [str, str, str]:
    try:
        if not access_key:
            access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        if not secret_key:
            secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        if not region:
            region = os.environ.get("AWS_DEFAULT_REGION")
        if not access_key or not secret_key:
            session = boto3.Session()
            credentials = session.get_credentials()
            access_key = credentials.access_key if not access_key else access_key
            secret_key = credentials.secret_key if not secret_key else secret_key
        if not region:
            session = boto3.Session()
            region = session.region_name if not region else region
        return access_key, secret_key, region
    except Exception as e:
        print("Cannot determine AWS credentials!")
        print(str(e))
        exit(1)


def obfuscate(value: str) -> str:
    return value[0:1] + "*******" if value is not None and len(value) > 0 else ""
