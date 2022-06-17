# --------------------------------------------------------------------------------------------------
# Simple script to view AWS stack templates.
#
# usage: aws-stack-template stack-name
# --------------------------------------------------------------------------------------------------

import argparse
import boto3
import json
import sys
import yaml
from collections import OrderedDict
from aws_utils import (obfuscate, validate_aws_credentials)


def print_aws_stack_template(stack_name: str, access_key: str = None, secret_key: str = None, region: str = None):

    c4 = boto3.client('cloudformation', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    stack_template = c4.get_template(StackName=stack_name)
    stack_template_body = stack_template["TemplateBody"]
    if isinstance(stack_template_body, OrderedDict):
        #
        # For some reason for our AWS stack c4-foursight-cgap-supertest-stack
        # in particular, we get back an OrderedDict, which we print as JSON;
        # having trouble converting to YAML.
        #
        stack_template_json = json.dumps(stack_template_body, default=str, indent=2)
        print(stack_template_json)
    else:
        #
        # For other AWS stacks like c4-datastore-cgap-supertest-stack,
        # we get a simple string containing the YAML for the template.
        #
        print(stack_template_body)


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--name", type=str, required=True)
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args = args_parser.parse_args()

    print(f"AWS Stack Template Utility | {args.name}")

    access_key, secret_key, region = validate_aws_credentials(args.access_key, args.secret_key, args.region, True)

    print_aws_stack_template(args.name, access_key, secret_key, region)


if __name__ == "__main__":
    main()
