import argparse
import io
import json
import glob
import os
import subprocess
from enum import Enum

from dcicutils.misc_utils import json_leaf_subst as expand_json
from dcicutils.cloudformation_utils import camelize
from .aws_env_info import AwsEnvInfo

AWS_DIR                = "~/.aws_test"
CUSTOM_DIR             = "customxxx"
CUSTOM_AWS_DIR         = "aws_creds"
TEST_CREDS_SCRIPT_FILE = "test_creds.sh"
CONFIG_FILE            = "config.json"
SECRETS_FILE           = "secrets.json"
CONFIG_TEMPLATE_FILE   = "templates/config.json.template"
SECRETS_TEMPLATE_FILE  = "templates/secrets.json.template"
THIS_SCRIPT_DIR        = os.path.dirname(__file__)

class TemplateVars(Enum):
    ACCOUNT_NUMBER     = "__TEMPLATE_ACCOUNT_NUMBER__"
    DEPLOYING_IAM_USER = "__TEMPLATE_DEPLOYING_IAM_USER__"
    IDENTITY           = "__TEMPLATE_IDENTITY__"
    ENCODED_ENV_NAME   = "__TEMPLATE_ENCODED_ENV_NAME__"
    S3_BUCKET_ORG      = "__TEMPLATE_VALUE_S3_BUCKET_ORG__"
    AUTH0_CLIENT       = "__TEMPLATE_VALUE_AUTH0_CLIENT__"
    AUTH0_SECRET       = "__TEMPLATE_VALUE_AUTH0_SECRET__"
    RE_CAPTCHA_KEY     = "__TEMPLATE_VALUE_RE_CAPTCHA_KEY__"
    RE_CAPTCHA_SECRET  = "__TEMPLATE_VALUE_RE_CAPTCHA_SECRET__"

def get_fallback_account_number(aws_dir):
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

def get_fallback_deploying_iam_user():
    """
    Obtains/returns the deploying_iam_user value
    simply from the USER environment variable.
    """
    return os.environ.get("USER")

def get_fallback_identity(aws_env):
    """
    Obtains/returns the identity by simple concantentation of strings
    the same way the 4dn-cloud-infra code does it.
    TODO: Get this directly via 4dn-cloud-infra code.
    """
    return "C4Datastore" + camelize(aws_env) + "ApplicationConfiguration"

def confirm_with_user(message: str):
    input_answer = input(message + " ").strip().lower()
    if input_answer == "yes":
        return True
    return False

def exit_without_doing_anything(message: str = "", status: int = 1):
    if message:
        print(message)
    print("Exiting without doing anything.")
    exit(status)

def main():

    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--env", type=str, required=True)
    args_parser.add_argument("--out", type=str, default=CUSTOM_DIR, required=False)
    args_parser.add_argument("--account", type=str, required=False)
    args_parser.add_argument("--username", type=str, required=False)
    args_parser.add_argument("--identity", type=str, required=False)
    args_parser.add_argument("--s3org", type=str, required=True)
    args_parser.add_argument("--auth0client", type=str, required=False)
    args_parser.add_argument("--auth0secret", type=str, required=False)
    args_parser.add_argument("--recaptchakey", type=str, required=False)
    args_parser.add_argument("--recaptchasecret", type=str, required=False)
    args_parser.add_argument("--verbose", action="store_true", required=False)
    args_parser.add_argument("--debug", action="store_true", required=False)
    args_parser.add_argument("--silent", action="store_true", required=False)
    args_parser.add_argument("--yes", action="store_true", required=False)
    args = args_parser.parse_args()

    aws_env = args.env
    custom_dir = args.out
    account_number = args.account
    deploying_iam_user = args.username
    identity = args.identity
    s3_bucket_org = args.s3org
    auth0_client = args.auth0client
    auth0_secret = args.auth0secret
    re_captcha_key = args.recaptchakey
    re_captcha_secret = args.recaptchasecret

    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    print(f"Current username: {os.environ['USER']}")

    aws_env_info = AwsEnvInfo(AWS_DIR)
    aws_current_env = aws_env_info.get_current_env()

    # Make sure the AWS environment name given is good.
    # Required but just in case not set anyways, check current
    # environment, if set, and ask them if they want to use that.
    #
    if not aws_env:
        if not aws_current_env:
            exit_without_doing_anything("No environment specified. Use the --env option to specify this.")
        else:
            aws_env = aws_current_env
            print(f"No environment specified. Use the --env option to specify this.")
            print(f"Though it looks like your current environment is: {aws_current_env}")
            if not confirm_with_user(f"Do you want to use this ({aws_current_env})?"):
                exit_without_doing_anything()

    # Make sure the environment specified
    # actually exists as a ~/.aws_test.ENV_NAME directory.
    #
    aws_available_envs = aws_env_info.get_available_envs()
    if aws_env not in aws_available_envs:
        print(f"No environment for this name exists: {aws_env}")
        if aws_available_envs:
            print("Available environments:")
            for aws_available_env in sorted(aws_available_envs):
                print(f"- {aws_available_env} ({aws_env_info.get_dir(aws_available_env)})")
            exit_without_doing_anything("Choose on of the above environment using the --env option.")
        else:
            exit_without_doing_anything \
               (f"No environments found at all.\nYou need to have at least one {aws_env_info.get_base_dir()}.{{ENV_NAME}} directory setup.") 

    aws_dir = aws_env_info.get_dir(aws_env)
    print(f"Setting up local custom config directory for environment: {aws_env}")
    print(f"Your AWS credentials directory: {aws_dir}")

    # Create the custom directory; but make sue it doesn't already exist.
    #
    if not custom_dir:
        exit_without_doing_anything("You must specify a custom output directory using the --out option.")
    if os.path.exists(custom_dir):
        exit_without_doing_anything(f"A custom {'directory' if os.path.isdir(custom_dir) else 'file'} ({custom_dir}) already exists.")

    print(f"Using custom directory: {custom_dir} ({os.path.abspath(custom_dir)})")

    # Check all the inputs.

    if not account_number:
        account_number = get_fallback_account_number(aws_env_info.get_dir(aws_env))
        if not account_number:
            exit_without_doing_anything("Cannot determine account number. Use the --account option.")
    print(f"Using account number: {account_number}")

    if not deploying_iam_user:
        deploying_iam_user = get_fallback_deploying_iam_user()
        if not deploying_iam_user:
            exit_without_doing_anything(f"Cannot determine deploying IAM username. Use the --username option.")
    print(f"Using deploying IAM username: {deploying_iam_user}")

    if not identity:
        identity = get_fallback_identity(aws_env)
        if not identity:
            exit_without_doing_anything(f"Cannot determine deploying IAM username. Use the --username option.")
    print(f"Using identity: {identity}")

    if not s3_bucket_org:
        exit_without_doing_anything(f"You must specify an S3 bucket organization name. Use the --s3org option.")
    print(f"Using S3 bucket organization name: {s3_bucket_org}")

    if not auth0_client:
        print("You must specify a Auth0 client ID using the --auth0client option.")
        response = input("Or enter your Auth0 client ID: ").strip()
        if not response:
            exit_without_doing_anything(f"You must specify an Auth0 client. Use the --auth0client option.")
        auth0_client = response
    print(f"Using Auth0 client: {auth0_client}")

    if not auth0_secret:
        print("You must specify a Auth0 secret using the --auth0secret option.")
        response = input("Or enter your Auth0 secret ID: ").strip()
        if not response:
            exit_without_doing_anything(f"You must specify an Auth0 secret. Use the --auth0secret option.")
        auth0_secret = response
    print(f"Using Auth0 secret: {auth0_secret}")

    # Confirm with the user the everything looks okay.

    if not confirm_with_user("Does the above look okay?"):
        exit_without_doing_anything()

    # Confirmed. First create the custom directory itself. 

    print(f"Creating directory: {os.path.abspath(custom_dir)}")
    os.makedirs(custom_dir)

    # Create the config.json file from the template and the inputs.
    # First we expand the template variables in the config.json file.

    config_template_file_path = os.path.join(THIS_SCRIPT_DIR, CONFIG_TEMPLATE_FILE)
    if args.debug:
        print(f"Config template file: {config_template_file_path}")
    if not os.path.isfile(config_template_file_path):
        exit_without_doing_anything(f"ERROR: SHOULD NOT HAPPEN: Cannot find config.json template file: {config_template_file_path}")

    with io.open(config_template_file_path , "r") as config_template_file:
        config_template_file_json = json.load(config_template_file)

    expanded_config_file_json = expand_json(config_template_file_json,
    {
        TemplateVars.ACCOUNT_NUMBER.value:     account_number,
        TemplateVars.DEPLOYING_IAM_USER.value: deploying_iam_user,
        TemplateVars.IDENTITY.value:           identity,
        TemplateVars.S3_BUCKET_ORG.value:      s3_bucket_org,
        TemplateVars.ENCODED_ENV_NAME.value:   aws_env
    })

    # Write the template-expanded config.json file.

    config_file_path = os.path.join(custom_dir, CONFIG_FILE)
    print(f"Creating config file: {os.path.abspath(config_file_path)}")
    with io.open(config_file_path, "w") as config_file:
        json.dump(expanded_config_file_json, config_file, indent=2)
        config_file.write("\n")

    # Create the secrets.json file from the template and the inputs.
    # First we expand the template variables in the secrets.json file.

    secrets_template_file_path = os.path.join(THIS_SCRIPT_DIR, SECRETS_TEMPLATE_FILE)
    if args.debug:
        print(f"Secrets template file: {secrets_template_file_path}")
    if not os.path.isfile(secrets_template_file_path):
        exit_without_doing_anything(f"ERROR: SHOULD NOT HAPPEN: Cannot find secrets.json template file: {secrets_template_file_path}")

    with io.open(secrets_template_file_path , "r") as secrets_template_file:
        secrets_template_file_json = json.load(secrets_template_file)

    expanded_secrets_file_json = expand_json(secrets_template_file_json,
    {
        TemplateVars.AUTH0_CLIENT.value:      auth0_client,
        TemplateVars.AUTH0_SECRET.value:      auth0_secret,
        TemplateVars.RE_CAPTCHA_KEY.value:    re_captcha_key,
        TemplateVars.RE_CAPTCHA_SECRET.value: re_captcha_secret
    })

    # Write the template-expanded secrets.json file.

    secrets_file_path = os.path.join(custom_dir, SECRETS_FILE)
    print(f"Creating secrets file: {os.path.abspath(secrets_file_path)}")
    with io.open(secrets_file_path, "w") as secrets_file:
        json.dump(expanded_secrets_file_json, secrets_file, indent=2)
        secrets_file.write("\n")

    # Create the symlink from custom/aws_creds to ~/.aws_test.ENV_NAME

    custom_aws_dir = os.path.abspath(os.path.join(custom_dir, CUSTOM_AWS_DIR))
    print(f"Creating symlink: {custom_aws_dir} -> {aws_dir} ")
    os.symlink(aws_dir, custom_aws_dir)


if __name__ == "__main__":
    main()
