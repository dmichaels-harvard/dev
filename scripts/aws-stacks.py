# --------------------------------------------------------------------------------------------------
# Simple script to view AWS stacks and related info.
# By default prints all stacks, and optionally all associated Outputs key/values.
#
# usage: aws-stacks [--stack stack-name-pattern] [--output output-key-pattern ] [--outputs] [--exports]
#
# If --outputs is given then prints all outputs key/values for each stack.
#
# If --output with a simple pattern is given then limit outputs key/values
# to those whose key contains the specified simple pattern (case-insensitive).
#
# If --stack with a simple pattern is given then limit stacks to those
# whose stack name contins the specified simple pattern (case-insensitive).
#
# If --exports is given then include export name with the outputs keys/values.
# --------------------------------------------------------------------------------------------------

import boto3
import argparse

args_parser = argparse.ArgumentParser()
args_parser.add_argument("--stack", type=str, required=False)
args_parser.add_argument("--output", type=str, required=False)
args_parser.add_argument("--outputs", action="store_true", required=False)
args_parser.add_argument("--exports", action="store_true", required=False)
args = args_parser.parse_args()

def print_aws_stacks():

    print("AWS Stacks", end = "")
    if args.stack:
        print(" / stack name containing: " + args.stack, end = "")
    if args.output:
        print(" / output keys containing: " + args.output, end = "")
    print()

    c4 = boto3.client('cloudformation')
    for stack in c4.describe_stacks()["Stacks"]:
        stack_name = stack["StackName"]
        if args.stack and not args.stack.lower() in stack_name.lower():
            continue
        stack_updated = stack["LastUpdatedTime"]
        print("%-15s (updated: %s)" % (stack_name, stack_updated.astimezone().strftime("%Y:%m:%d %H:%M:%S")))
        if args.output or args.outputs:
            for stack_output in sorted(stack["Outputs"], key=lambda key: key["OutputKey"]):
                stack_output_key = stack_output["OutputKey"]
                if args.output and not args.output.lower() in stack_output_key.lower():
                    continue
                stack_output_value = stack_output["OutputValue"]
                stack_output_export_name = stack_output.get("ExportName")
                print(" - %s:" % (stack_output_key))
                print("   %s" % (stack_output_value))
                if args.exports and stack_output_export_name:
                    print("   %s (export name)" % (stack_output_export_name))

print_aws_stacks()





#c4 = boto3.resource('cloudformation')
#stacks = c4.meta.client.list_stacks()
#for stack in stacks:
#    print(stack)
#print("All AWS Stacks:")
# This way oes not give 'ExportName' properties of Outputs.
#for stack in c4.stacks.all():
#    print("%-15s %s" % (stack.name, stack.last_updated_time.astimezone().strftime("%Y:%m:%d %H:%M:%S")))
#    if len(stack.outputs) > 0:
#        print("Outputs (%d):" % len(stack.outputs))
#        print(stack.outputs)
#        for stack_output in sorted(stack.outputs, key=lambda key: key["OutputKey"]):
#            print(" - %s: %s" % (stack_output["OutputKey"], stack_output["OutputValue"]))
