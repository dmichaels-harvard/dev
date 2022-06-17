# --------------------------------------------------------------------------------------------------
# Simple script to view AWS stacks and related info.
# By default prints all stacks, and optionally all associated Outputs key/values.
#
# usage: aws-stacks [--name stack-name-pattern]
#                   {
#                   | [ --outputs [ output-key-pattern ] ]
#                   | [ --resources [ resource-name-pattern ] ]
#                   | [ --parameters [ parameter-name-pattern ] ]
#                   }
#                   [--verbose]
#
# If --name with a simple pattern is given then limit stacks to those
# whose stack names contains the specified simple pattern (case-insensitive).
#
# If --outputs is given then prints all outputs keys/values for each stack.
# If a simple pattern is given after this then limit outputs keys/values 
# to those whose key contains the specified simple pattern (case-insensitive).
#
# If --resources is given then prints all resources names/types for each stack.
# If a simple pattern is given after this then limit outputs names/types 
# to those whose name contains the specified simple pattern (case-insensitive).
#
# If --parameters is given then prints all parameters keys/values for each stack.
# If a simple pattern is given after this then limit outputs keys/types 
# to those whose key contains the specified simple pattern (case-insensitive).
#
# N.B. Only one of --output(s) or --resource(s) or --parameter(s) may be specified.
#
# If --verbose is given then include export name with the outputs keys/values.
# --------------------------------------------------------------------------------------------------

import argparse
import boto3
import re
from aws_utils import (obfuscate, validate_aws_credentials)


def print_aws_stacks(name: str,
                     outputs: str, resources: str, parameters: str,
                     access_key: str = None, secret_key: str = None, region: str = None,
                     verbose: bool = False):

    # https://www.learnaws.org/2021/02/24/boto3-resource-client/#:~:text=Clients%20vs%20Resources,when%20interacting%20with%20AWS%20services.
    # Resources are higher-level abstractions of AWS services compared to clients.
    # Resources are the recommended pattern to use boto3 as you don’t have to worry
    # about a lot of the underlying details when interacting with AWS services.
    c4 = boto3.resource('cloudformation', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    stacks = c4.stacks.all()
    for stack in stacks:
        stack_name = stack.name
        if name and not name.lower() in stack_name.lower():
            continue
        stack_updated = stack.last_updated_time
        if stack_updated:
            print("%-15s (updated: %s)" % (stack_name, stack_updated.astimezone().strftime("%Y-%m-%d %H:%M:%S")))
        else:
            stack_created = stack.creation_time
            if stack_created:
                print("%-15s (created: %s)" % (stack_name, stack_created.astimezone().strftime("%Y-%m-%d %H:%M:%S")))
            else:
                print("%-15s" % (stack_name))
        if outputs:
            stack_outputs = stack.outputs
            if stack_outputs:
                for stack_output in sorted(stack_outputs, key=lambda key: key["OutputKey"]):
                    stack_output_key = stack_output["OutputKey"]
                    if outputs and not re.search(outputs, stack_output_key, re.IGNORECASE):
                        continue
                    stack_output_value = stack_output["OutputValue"]
                    stack_output_export_name = stack_output.get("ExportName")
                    print(" - %s: %s" % (stack_output_key, stack_output_value))
                    if verbose and stack_output_export_name:
                        print("   %s (export name)" % (stack_output_export_name))
        elif resources:
            stack_resources = stack.resource_summaries.all()
            for stack_resource in sorted(stack_resources, key=lambda key: key.logical_resource_id.lower()):
                stack_resource_name = stack_resource.logical_resource_id
                stack_resource_type = stack_resource.resource_type
                if resources and not re.search(resources, stack_resource_name, re.IGNORECASE):
                    continue
                print("- %s: %s" % (stack_resource_name, stack_resource_type))
        elif parameters:
            stack_parameters = stack.parameters
            if stack_parameters:
                for stack_parameter in sorted(stack_parameters, key=lambda key: key["ParameterKey"]):
                    stack_parameter_key = stack_parameter["ParameterKey"]
                    if parameters and not re.search(parameters, stack_parameter_key, re.IGNORECASE):
                        continue
                    stack_parameter_value = stack_parameter["ParameterValue"]
                    print(" - %s: %s" % (stack_parameter_key, stack_parameter_value))


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--name", type=str, required=False)
    args_parser.add_argument('--outputs', type=str, const='.*', nargs='?')
    args_parser.add_argument('--resources', type=str, const='.*', nargs='?')
    args_parser.add_argument('--parameters', type=str, const='.*', nargs='?')
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args_parser.add_argument("--verbose", action="store_true", required=False)
    args = args_parser.parse_args()

    description = ""
    mutually_exclusive_options_count = 0
    if args.outputs:
        description = " Outputs"
        mutually_exclusive_options_count += 1
    if args.resources:
        description = " Resources"
        mutually_exclusive_options_count += 1
    if args.parameters:
        description = " Parameters"
        mutually_exclusive_options_count += 1
    if mutually_exclusive_options_count > 1:
        print("Must specify only one of: --outputs, --resources, --parameters")
        exit(1)

    print(f"AWS Stacks{description} Utility", end = "")
    if args.name:
        print(" | names containing: " + args.name, end = "")
    if args.outputs and args.outputs != ".*":
        print(" | output keys containing: " + args.outputs, end = "")
    if args.resources and args.resources != ".*":
        print(" | resource names containing: " + args.resources, end = "")
    if args.parameters and args.parameters != ".*":
        print(" | parameter names containing: " + args.parameters, end = "")
    print()

    access_key, secret_key, region = validate_aws_credentials(args.access_key, args.secret_key, args.region, True)

    print_aws_stacks(name=args.name,
                     outputs=args.outputs, resources=args.resources, parameters=args.parameters,
                     access_key=access_key, secret_key=secret_key, region=region,
                     verbose=args.verbose)


if __name__ == "__main__":
    main()
