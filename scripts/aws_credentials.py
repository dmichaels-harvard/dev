# Simple utility to print current and environmental AWS related credentials/info.

import boto3
import json
import os
import sys

show = False

for arg in sys.argv:
    if arg == "--show" or arg == "-show":
        show = True

def value(value: str, sensitive: bool, show: bool, match_value: str = None) -> str:
    if not value:
        return '-'
    display_value = value
    if sensitive and not show:
        display_value = len(value) * "*"
    if match_value and value != match_value:
        display_value = value + " (mismatch)"
    return display_value

# Get active AWS credentials/info.

try:
    session = boto3.session.Session()
    credentials = None if not session else session.get_credentials()
except Exception as e:
    print(f"ERROR: {str(e)}")
    session = None
    credentials = None

region_name = "" if not session else session.region_name
access_key_id = "" if not credentials else credentials.access_key
secret_access_key = "" if not credentials else credentials.secret_key
session_token = "" if not credentials else credentials.token
try:
    caller_identity = boto3.client("sts").get_caller_identity()
except Exception as e:
    print(f"ERROR: {str(e)}")
    caller_identity = None
user_arn = "" if not caller_identity else caller_identity["Arn"]
account_number = "" if not caller_identity else caller_identity["Account"]

# Get environmentally set AWS credentials/info.

env_credentials_file = os.environ.get("AWS_SHARED_CREDENTIALS_FILE")
env_config_file = os.environ.get("AWS_CONFIG_FILE")
env_default_region = os.environ.get("AWS_DEFAULT_REGION")
env_region = os.environ.get("AWS_REGION")
env_region_name = env_region if env_region else env_default_region
env_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
env_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
env_session_token = os.environ.get("AWS_SESSION_TOKEN")
env_account_number = os.environ.get("ACCOUNT_NUMBER")

print()
print(f"Current active AWS credentials:")
print(f"- AWS Access Key ID:           {value(access_key_id, False, show, env_access_key_id)}")
print(f"- AWS Secret Access Key:       {value(secret_access_key, True, show, env_secret_access_key)}")
print(f"- AWS Region:                  {value(region_name, False, show, env_region_name)}")
if session_token or env_session_token:
    print(f"- AWS Session Token:           {value(session_token, False, show, env_session_token)}")
print(f"- AWS Account Number:          {value(account_number, False, show, env_account_number)}")
print(f"- AWS User ARN:                {value(user_arn, False, show)}")

print()
print(f"Current AWS related credentials environment variables:")
print(f"- AWS_ACCESS_KEY_ID:           {value(env_access_key_id, False, show, access_key_id)}")
print(f"- AWS_SECRET_ACCESS_KEY_ID:    {value(env_secret_access_key, True, show, secret_access_key)}")
if env_region:
    print(f"- AWS_REGION:                  {value(env_region_name, False, show, region_name)}")
else:
    print(f"- AWS_DEFAULT_REGION:          {value(env_region_name, False, show, region_name)}")
if session_token or env_session_token:
    print(f"- AWS_SESSION_TOKEN:           {value(env_session_token, True, show, session_token)}")
print(f"- AWS_SHARED_CREDENTIALS_FILE: {value(env_credentials_file, False, show)}")
print(f"- AWS_CONFIG_FILE:             {value(env_config_file, False, show)}")
print(f"- ACCOUNT_NUMBER:              {value(env_account_number, False, show, account_number)}")
print()
