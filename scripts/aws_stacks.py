# --------------------------------------------------------------------------------------------------
# Simple script to view AWS stacks and related info.
# By default prints all stacks, and optionally all associated Outputs key/values.
# TODO: Use regex for pattern rather than just simple contains.
# TODO: Move the args stuff inside main.
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
import json
import re


def print_aws_stacks(name: str, outputs: str, resources: str, parameters: str, verbose: bool):

    c4 = boto3.client('cloudformation')
    for stack in c4.describe_stacks()["Stacks"]:
        stack_name = stack["StackName"]
        if name and not name.lower() in stack_name.lower():
            continue
        stack_updated = stack["LastUpdatedTime"]
        print("%-15s (updated: %s)" % (stack_name, stack_updated.astimezone().strftime("%Y-%m-%d %H:%M:%S")))
        if outputs:
            for stack_output in sorted(stack["Outputs"], key=lambda key: key["OutputKey"]):
                stack_output_key = stack_output["OutputKey"]
                if outputs and not re.search(outputs, stack_output_key, re.IGNORECASE):
                    continue
                stack_output_value = stack_output["OutputValue"]
                stack_output_export_name = stack_output.get("ExportName")
                print(" - %s: %s" % (stack_output_key, stack_output_value))
                if verbose and stack_output_export_name:
                    print("   %s (export name)" % (stack_output_export_name))
        elif resources:
            for stack_resource in sorted(c4.describe_stack_resources(StackName=stack_name)["StackResources"], key=lambda key: key["LogicalResourceId"].lower()):
                stack_resource_name = stack_resource["LogicalResourceId"]
                stack_resource_type = stack_resource["ResourceType"]
                if resources and not re.search(resources, stack_resource_name, re.IGNORECASE):
                    continue
                print("- %s: %s" % (stack_resource_name, stack_resource_type))
        elif parameters:
            stack_parameters = stack.get("Parameters")
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
    args_parser.add_argument("--verbose", action="store_true", required=False)
    args = args_parser.parse_args()

    description = ""
    mutually_exclusive_options_count = 0
    if args.outputs:
        description = " with Outputs"
        mutually_exclusive_options_count += 1
    if args.resources:
        description = " with Resources"
        mutually_exclusive_options_count += 1
    if args.parameters:
        description = " with Parameters"
        mutually_exclusive_options_count += 1
    if mutually_exclusive_options_count > 1:
        print("Must specify only one of: --outputs, --resources, --parameters")
        exit(1)

    print(f"AWS Stacks{description}", end = "")
    if args.name:
        print(" / names containing: " + args.name, end = "")
    if args.outputs and args.outputs != ".*":
        print(" / output keys containing: " + args.outputs, end = "")
    if args.resources and args.resources != ".*":
        print(" / resource names containing: " + args.resources, end = "")
    if args.parameters and args.parameters != ".*":
        print(" / parameter names containing: " + args.parameters, end = "")
    print()

    print_aws_stacks(args.name, args.outputs, args.resources, args.parameters, args.verbose)


if __name__ == "__main__":
    main()
