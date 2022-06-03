# Script to setup the 'custom' directory for 4dn-cloud-infra
# IN PROGRESS (dmichaels)

import argparse
from   enum import Enum
import re
import io
import json
import glob
import os
import subprocess

from dcicutils.misc_utils import json_leaf_subst as expand_json_template
from dcicutils.cloudformation_utils import camelize
from .aws_env_info import AwsEnvInfo

AWS_DIR                = "~/.aws_test"
TEST_CREDS_SCRIPT_FILE = "test_creds.sh"
CUSTOM_DIR             = "custom"
CUSTOM_AWS_DIR         = "aws_creds"
CONFIG_FILE            = "config.json"
SECRETS_FILE           = "secrets.json"
CONFIG_TEMPLATE_FILE   = "templates/config.json.template"
SECRETS_TEMPLATE_FILE  = "templates/secrets.json.template"
S3_ENCRYPT_KEY_FILE    = "s3_encrypt_key.txt-TEST"
THIS_SCRIPT_DIR        = os.path.dirname(__file__)

class ConfigTemplateVars(Enum):
    ACCOUNT_NUMBER     = "__TEMPLATE_ACCOUNT_NUMBER__"
    DEPLOYING_IAM_USER = "__TEMPLATE_DEPLOYING_IAM_USER__"
    IDENTITY           = "__TEMPLATE_IDENTITY__"
    ENCODED_ENV_NAME   = "__TEMPLATE_ENCODED_ENV_NAME__"
    S3_BUCKET_ORG      = "__TEMPLATE_VALUE_S3_BUCKET_ORG__"

class SecretsTemplateVars(Enum):
    AUTH0_CLIENT       = "__TEMPLATE_VALUE_AUTH0_CLIENT__"
    AUTH0_SECRET       = "__TEMPLATE_VALUE_AUTH0_SECRET__"
    RE_CAPTCHA_KEY     = "__TEMPLATE_VALUE_RE_CAPTCHA_KEY__"
    RE_CAPTCHA_SECRET  = "__TEMPLATE_VALUE_RE_CAPTCHA_SECRET__"

def get_fallback_account_number(aws_dir: str):
    """
    Obtains/returns the account_number value by executing the test_creds.sh
    file in the chosen (use_test_creds) AWS environment and grabbing the value
    of the ACCOUNT_NUMBER environment value which is likely to be set there.
    :param aws_dir: The AWS envronment directory path.
    """
    try:
        test_creds_script_file = os.path.join(aws_dir, TEST_CREDS_SCRIPT_FILE)
        command = f"source {test_creds_script_file} ; echo $ACCOUNT_NUMBER"
        return str(subprocess.check_output(command, shell=True).decode("utf-8")).strip()
    except Exception as e:
        return None

def get_fallback_deploying_iam_user():
    """
    Obtains/returns the deploying_iam_user value
    simply from the USER environment variable.
    """
    return os.environ.get("USER")

def get_fallback_identity(aws_env: str):
    """
    Obtains/returns the identity by simple concantentation of strings
    the same way the 4dn-cloud-infra code does it.
    TODO: Get this directly via 4dn-cloud-infra code.
    """
    return "C4Datastore" + camelize(aws_env) + "ApplicationConfiguration"

def expand_json_template_file(template_file: str, output_file: str, template_substitutions: dict):
    if not os.path.isfile(template_file):
        return False
    try:
        with io.open(template_file, "r") as template_f:
            template_file_json = json.load(template_f)
        expanded_template_json = expand_json_template(template_file_json, template_substitutions)
        with io.open(output_file, "w") as output_f:
            json.dump(expanded_template_json, output_f, indent=2)
            output_f.write("\n")
        return True
    except Exception as e:
        return False

def generate_s3_encrypt_key():
    """
    Returns a value suitable for an S3 encrypt key.
    TODO: Replicating the method used in scripts/create_s3_encrypt_key but should
          we modifed that script and call out to it? ANd if we do do it here then
          probably should also replicate the openssl version checking.
    """
    s3_encrypt_key_command = "openssl enc -aes-128-cbc -k `ps -ax | md5` -P -pbkdf2 -a"
    s3_encrypt_key_command_output = subprocess.check_output(s3_encrypt_key_command, shell=True).decode("utf-8").strip()
    return re.compile("key=(.*)\n").search(s3_encrypt_key_command_output).group(1)

def confirm_with_user(message: str):
    input_answer = input(message + " (yes|no) ").strip().lower()
    if input_answer == "yes":
        return True
    return False

def exit_without_doing_anything(message: str = "", status: int = 1):
    if message:
        print(message)
    print("Exiting without doing anything.")
    exit(status)

def print_directory_tree(directory: str):
    """
    Prints the given directory as a tree. Taken/adapted from:
    https://stackoverflow.com/questions/9727673/list-directory-tree-structure-in-python
    """
    def tree_generator(directory, prefix: str = ''):
        space = '    ' ; branch = '│   ' ; tee = '├── ' ; last = '└── '
        contents = [os.path.join(directory, item) for item in os.listdir(directory)]
        pointers = [tee] * (len(contents) - 1) + [last]
        for pointer, path in zip(pointers, contents):
            if os.path.islink(path): symlink = "@ -> " + os.readlink(path)
            else: symlink = ""
            yield prefix + pointer + os.path.basename(path) + symlink # + modified_time
            if os.path.isdir(path):
                extension = branch if pointer == tee else space 
                yield from tree_generator(path, prefix=prefix+extension)
    print(directory)
    for line in tree_generator(directory): print(line)

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
    args_parser.add_argument("--debug", action="store_true", required=False)
    args_parser.add_argument("--yes", action="store_true", required=False)
    args = args_parser.parse_args()

    aws_env = args.env
    custom_dir = os.path.abspath(args.out)
    account_number = args.account
    deploying_iam_user = args.username
    identity = args.identity
    s3_bucket_org = args.s3org
    auth0_client = args.auth0client
    auth0_secret = args.auth0secret
    re_captcha_key = args.recaptchakey
    re_captcha_secret = args.recaptchasecret

    if args.debug:
        print(f"Current directory: {os.getcwd()}")
        print(f"Current username: {os.environ['USER']}")

    aws_env_info = AwsEnvInfo(AWS_DIR)
    aws_current_env = aws_env_info.get_current_env()

    # Make sure the AWS environment name given is good.
    # Required but just in case not set anyways, check current
    # environment, if set, and ask them if they want to use that.
    # But don't do this if --yes option given.

    if not aws_env and args.yes:
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

    if not custom_dir:
        exit_without_doing_anything("You must specify a custom output directory using the --out option.")
    if os.path.exists(custom_dir):
        exit_without_doing_anything(f"A custom {'directory' if os.path.isdir(custom_dir) else 'file'} already exists: {custom_dir}")

    print(f"Using custom directory: {custom_dir}")

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
        auth0_client = input("Or enter your Auth0 client ID: ").strip()
        if not auth0_client:
            exit_without_doing_anything(f"You must specify an Auth0 client. Use the --auth0client option.")
    print(f"Using Auth0 client: {auth0_client}")

    if not auth0_secret:
        print("You must specify a Auth0 secret using the --auth0secret option.")
        auth0_secret = input("Or enter your Auth0 secret ID: ").strip()
        if not auth0_secret:
            exit_without_doing_anything(f"You must specify an Auth0 secret. Use the --auth0secret option.")
    print(f"Using Auth0 secret: {auth0_secret}")

    if re_captcha_key:
        print(f"Using reCaptchaKey: {re_captcha_key}")
    if re_captcha_secret:
        print(f"Using reCaptchaSecret: {re_captcha_secret}")

    # Confirm with the user the everything looks okay.

    if not args.yes and not confirm_with_user("Confirm the above. Continue with setup?"):
        exit_without_doing_anything()

    # Confirmed. First create the custom directory itself. 
    # TODO: Catch exceptions et cetera

    print(f"Creating directory: {os.path.abspath(custom_dir)}")
    os.makedirs(custom_dir)

    # Create the config.json file from the template and the inputs.
    # First we expand the template variables in the config.json file.
    # TODO: template file relative to this script directory?

    config_template_file = os.path.join(THIS_SCRIPT_DIR, CONFIG_TEMPLATE_FILE)
    config_file = os.path.abspath(os.path.join(custom_dir, CONFIG_FILE))

    if args.debug:
        print(f"Config template file: {config_template_file}")

    print(f"Creating config file: {os.path.abspath(config_file)}")

    if not expand_json_template_file(config_template_file, config_file,
    {
        ConfigTemplateVars.ACCOUNT_NUMBER.value:     account_number,
        ConfigTemplateVars.DEPLOYING_IAM_USER.value: deploying_iam_user,
        ConfigTemplateVars.IDENTITY.value:           identity,
        ConfigTemplateVars.S3_BUCKET_ORG.value:      s3_bucket_org,
        ConfigTemplateVars.ENCODED_ENV_NAME.value:   aws_env
    }): print(f"Error writing: {config_file} (from: {config_template_file})")

    # Create the secrets.json file from the template and the inputs.
    # First we expand the template variables in the secrets.json file.
    # TODO: template file relative to this script directory?

    secrets_template_file = os.path.join(THIS_SCRIPT_DIR, SECRETS_TEMPLATE_FILE)
    secrets_file = os.path.abspath(os.path.join(custom_dir, SECRETS_FILE))

    if args.debug:
        print(f"Secrets template file: {secrets_template_file}")

    print(f"Creating secrets file: {secrets_file}")

    if not expand_json_template_file(secrets_template_file, secrets_file,
    {
        SecretsTemplateVars.AUTH0_CLIENT.value:      auth0_client,
        SecretsTemplateVars.AUTH0_SECRET.value:      auth0_secret,
        SecretsTemplateVars.RE_CAPTCHA_KEY.value:    re_captcha_key,
        SecretsTemplateVars.RE_CAPTCHA_SECRET.value: re_captcha_secret
    }):
        print(f"Error writing: {secrets_file} (from: {secrets_template_file})")

    # Create the symlink from custom/aws_creds to: ~/.aws_test.ENV_NAME

    custom_aws_dir = os.path.abspath(os.path.join(custom_dir, CUSTOM_AWS_DIR))
    print(f"Creating symlink: {custom_aws_dir} -> {aws_dir} ")
    os.symlink(aws_dir, custom_aws_dir)

    # Create the S3 encrypt key file.

    s3_encrypt_key = generate_s3_encrypt_key()
    s3_encrypt_key_file = os.path.abspath(os.path.join(custom_aws_dir, S3_ENCRYPT_KEY_FILE))
    if os.path.exists(s3_encrypt_key_file):
        print(f"S3 encrypt file already exists: {s3_encrypt_key_file}")
        print("Not overwriting this!")
    else:
        print(f"Creating S3 encrypt file: {s3_encrypt_key_file}")
        with io.open(s3_encrypt_key_file, "w") as s3_encrypt_key_f:
            s3_encrypt_key_f.write(s3_encrypt_key)
            s3_encrypt_key_f.write("\n")

    # Done. Summarize.

    print("Here is your new custom config directory:")
    print_directory_tree(custom_dir)


if __name__ == "__main__":
    main()
