import argparse
import io
import json
import glob
import os

from dcicutils.misc_utils import json_leaf_subst as expand_json
from aws_dirs_info import AwsDirsInfo

DEFAULT_AWS_DIR = "~/.aws_test"
DEFAULT_CUSTOM_DIR = "custom"

CUSTOM_DIR = DEFAULT_CUSTOM_DIR
AWS_DIR = DEFAULT_AWS_DIR

def obtain_account_number():
    return "123"
def obtain_deploying_iam_user():
    return "joe"

def main():

    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--env", type=str, required=True)
    args_parser.add_argument("--out", type=str, required=False)
    args = args_parser.parse_args()

    aws_dirs_info = AwsDirsInfo(AWS_DIR)
    aws_available_envs = aws_dirs_info.get_available_envs()
    if args.env not in aws_available_envs:
        print(f"No environment for this name exists: {args.env}")
        print("Available environments:")
        aws_available_envs = aws_dirs_info.get_available_envs()
        for aws_available_env in sorted(aws_available_envs):
            print(f"- {aws_available_env}")

    print(f"Setting up local custom config directory for environment: {args.env}")

    custom_dir = args.out if args.out else CUSTOM_DIR

    if os.path.exists(custom_dir):
        print(f"A 'custom' {'directory' if os.path.isdir(CUSTOM_DIR) else 'file'} already exists.")
        print("Exiting without doing anything")
        #exit(1)
    else:
        pass
        #os.symlink("x", CUSTOM_DIR)

    print(f"Making directory: {custom_dir}")

    #os.makedirs(custom_dir)

    ACCOUNT_NUMBER_TEMPLATE_VAR     = "__TEMPLATE_ACCOUNT_NUMBER__"
    DEPLOYING_IAM_USER_TEMPLATE_VAR = "__TEMPLATE_DEPLOYING_IAM_USER__"

    CONFIG_FILE_TEMPLATE = "config.json.template"
    CONFIG_FILE = "config.json"

    SECRETS_FILE_TEMPLATE = "secrets.json.template"
    SECRETS_FILE = "secrets.json"

    account_number = obtain_account_number()
    deploying_iam_user = obtain_deploying_iam_user()

    with io.open("config.json.template", "r") as config_file_template:
        config_file_template_json = json.load(config_file_template)

    expanded_config_file_json = expand_json(config_file_template_json, { ACCOUNT_NUMBER_TEMPLATE_VAR: account_number,
                                                      DEPLOYING_IAM_USER_TEMPLATE_VAR: deploying_iam_user })
    with io.open(CONFIG_FILE, "w") as config_file:
        json.dump(expanded_config_file_json, config_file, indent=2)
        config_file.write("\n")

    print(expanded_config_file_json)

if __name__ == "__main__":
    main()
