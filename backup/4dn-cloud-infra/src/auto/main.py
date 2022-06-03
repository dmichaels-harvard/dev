import argparse
import io
import json
import glob
import os
import subprocess

from dcicutils.misc_utils import json_leaf_subst as expand_json
from dcicutils.cloudformation_utils import camelize
from aws_dirs_info import AwsDirsInfo

DEFAULT_AWS_DIR                = "~/.aws_test"
DEFAULT_CUSTOM_DIR             = "customxxx"
DEFAULT_TEST_CREDS_SCRIPT_FILE = "test_creds.sh"

CUSTOM_DIR             = DEFAULT_CUSTOM_DIR
AWS_DIR                = DEFAULT_AWS_DIR
TEST_CREDS_SCRIPT_FILE = DEFAULT_TEST_CREDS_SCRIPT_FILE

def obtain_account_number(aws_dir):
    """
    Obtains/returns the account_number value by executing the test_creds.sh
    file in the chosen (use_test_creds) AWS environment and grabbing the value
    of the ACCOUNT_NUMBER environment value which is likely to be set there.
    :param aws_dir: The AWS envronment directory path.
    """
    ACCOUNT_NUMBER_ENV_VAR = "ACCOUNT_NUMBER"
    try:
        test_creds_script_file = os.path.join(aws_dir, TEST_CREDS_SCRIPT_FILE)
        command = f"source {test_creds_script_file } ; echo ${ACCOUNT_NUMBER_ENV_VAR}"
        return str(subprocess.check_output(command, shell=True).decode("utf-8")).strip()
    except Exception as e:
        return None

def obtain_deploying_iam_user():
    """
    Obtains/returns the deploying_iam_user value
    simply by using the 'whoami' system command.
    """
    try:
        command = f"whoami"
        return str(subprocess.check_output(command, shell=True).decode("utf-8")).strip()
    except Exception as e:
        return None

def obtain_identity(aws_env):
    """
    Obtains/returns the identity by simple concantentation of strings
    the same way the 4dn-cloud-infra code does it.
    TODO: Get this directly via 4dn-cloud-infra code.
    """
    return "C4Datastore" + camelize(aws_env) + "ApplicationConfiguration"

def main():

    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--env", type=str, required=False)
    args_parser.add_argument("--out", type=str, required=False)
    args_parser.add_argument("--account", type=str, required=False)
    args_parser.add_argument("--username", type=str, required=False)
    args_parser.add_argument("--identity", type=str, required=False)
    args_parser.add_argument("--verbose", action="store_true", required=False)
    args_parser.add_argument("--debug", action="store_true", required=False)
    args = args_parser.parse_args()

    aws_dirs_info = AwsDirsInfo(AWS_DIR)
    aws_available_envs = aws_dirs_info.get_available_envs()
    aws_current_env = aws_dirs_info.get_current_env()

    aws_env = args.env
    custom_dir = args.out
    account_number = args.account
    deploying_iam_user = args.username
    identity = args.identity

    if not aws_env:
        if not aws_current_env:
            print("No --env specified. And not current environment in place.")
            print("Exiting without doing anything")
            exit(1)
        else:
            aws_env = aws_current_env
            print(f"No --env specified. Assuming current environment: {aws_current_env}")

    if aws_env not in aws_available_envs:
        print(f"No environment for this name exists: {aws_env}")
        print("Available environments:")
        aws_available_envs = aws_dirs_info.get_available_envs()
        for aws_available_env in sorted(aws_available_envs):
            print(f"- {aws_available_env}")

    aws_dir = aws_dirs_info.get_dir(aws_env)

    print(f"Setting up local custom config directory for environment: {aws_env}")

    if not custom_dir:
        custom_dir = CUSTOM_DIR

    if os.path.exists(custom_dir):
        print(f"A 'custom' {'directory' if os.path.isdir(CUSTOM_DIR) else 'file'} already exists.")
        print("Exiting without doing anything")
        exit(1)
    else:
        pass
        #os.symlink("x", CUSTOM_DIR)

    print(f"Creating custom directory: {custom_dir}")
    os.makedirs(custom_dir)

    ACCOUNT_NUMBER_TEMPLATE_VAR     = "__TEMPLATE_ACCOUNT_NUMBER__"
    DEPLOYING_IAM_USER_TEMPLATE_VAR = "__TEMPLATE_DEPLOYING_IAM_USER__"
    IDENTITY_TEMPLATE_VAR = "__TEMPLATE_IDENTITY__"

    CONFIG_FILE_TEMPLATE = "config.json.template"
    CONFIG_FILE = "config.json"

    SECRETS_FILE_TEMPLATE = "secrets.json.template"
    SECRETS_FILE = "secrets.json"

    if not account_number:
        account_number = obtain_account_number(aws_dir)
        if not account_number:
            print("Cannot determine account number. Use the --account option.")
            print("Exiting without doing anything.")
            exit(2)
    print(f"Using account number: {account_number}")

    if not deploying_iam_user:
        deploying_iam_user = obtain_deploying_iam_user()
        if not deploying_iam_user:
            print(f"Cannot determine deploying IAM username. Use the --username option.")
            print("Exiting without doing anything.")
            exit(3)
    print(f"Using deploying IAM username: {deploying_iam_user}")

    if not identity:
        identity = obtain_identity(aws_env)
        if not identity:
            print(f"Cannot determine deploying IAM username. Use the --username option.")
            print("Exiting without doing anything.")
            exit(3)
    print(f"Using identity: {identity}")

    input_answer = input("Does this look okay? ").strip().lower()
    print(input_answer)
    if input_answer != "yes":
        print("Exiting without doing anything.")
        exit(4)

    print("Continuing ...")

    with io.open("config.json.template", "r") as config_file_template:
        config_file_template_json = json.load(config_file_template)
    expanded_config_file_json = expand_json(config_file_template_json,
    {
        ACCOUNT_NUMBER_TEMPLATE_VAR: account_number,
        DEPLOYING_IAM_USER_TEMPLATE_VAR: deploying_iam_user,
        IDENTITY_TEMPLATE_VAR: identity
    })
    config_file_path = os.path.join(custom_dir, CONFIG_FILE)
    print(f"Creating config file: {config_file_path}")
    with io.open(config_file_path, "w") as config_file:
        json.dump(expanded_config_file_json, config_file, indent=2)
        config_file.write("\n")

    print(expanded_config_file_json)

if __name__ == "__main__":
    main()
