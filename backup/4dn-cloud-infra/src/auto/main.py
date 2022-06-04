# Script to setup the 'custom' directory for 4dn-cloud-infra
# IN PROGRESS (dmichaels)

import argparse
from   enum import Enum
import glob
import io
import json
import os
import re
import stat
import subprocess

from  dcicutils.misc_utils import json_leaf_subst as expand_json_template
from  dcicutils.cloudformation_utils import camelize
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

def get_fallback_identity(env_name: str):
    """
    Obtains/returns the identity by simple concantentation of strings
    the same way the 4dn-cloud-infra code does it.
    TODO: Get this directly via 4dn-cloud-infra code.
    """
    return "C4Datastore" + camelize(env_name) + "ApplicationConfiguration"

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
    s3_encrypt_key_command_output = subprocess.check_output(s3_encrypt_key_command, shell=True).decode("utf-8")
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
            symlink = "@ -> " + os.readlink(path) if os.path.islink(path) else ""
            yield prefix + pointer + os.path.basename(path) + symlink # + modified_time
            if os.path.isdir(path):
                extension = branch if pointer == tee else space 
                yield from tree_generator(path, prefix=prefix+extension)
    print(directory)
    for line in tree_generator(directory): print(line)

def main():

    argp = argparse.ArgumentParser()
    argp.add_argument("--env",             dest='env_name', type=str, required=True)
    argp.add_argument("--out",             dest='custom_dir_name', type=str, default=CUSTOM_DIR, required=False)
    argp.add_argument("--account",         dest='account_number', type=str, required=False)
    argp.add_argument("--username",        dest='deploying_iam_user', type=str, required=False)
    argp.add_argument("--identity",        dest='identity', type=str, required=False)
    argp.add_argument("--s3org",           dest='s3_bucket_org', type=str, required=True)
    argp.add_argument("--auth0client",     dest='auth0_client', type=str, required=False)
    argp.add_argument("--auth0secret",     dest='auth0_secret', type=str, required=False)
    argp.add_argument("--recaptchakey",    dest='re_captcha_key', type=str, required=False)
    argp.add_argument("--recaptchasecret", dest='re_captcha_secret', type=str, required=False)
    argp.add_argument("--debug",           dest='debug', action="store_true", required=False)
    argp.add_argument("--yes",             dest='yes', action="store_true", required=False)
    args = argp.parse_args()

    if args.debug:
        print(f"Current directory: {os.getcwd()}")
        print(f"Current username: {os.environ['USER']}")

    # Get basic environment info.

    env_info       = AwsEnvInfo(AWS_DIR)
    current_env    = env_info.get_current_env()
    available_envs = env_info.get_available_envs()

    # Make sure the AWS environment name given is good.
    # Required but just in case not set anyways, check current
    # environment, if set, and ask them if they want to use that.
    # But don't do this if --yes option given.

    if not args.env_name and args.yes:
        if not current_env:
            exit_without_doing_anything("No environment specified. Use the --env option to specify this.")
        else:
            args.env_name = current_env
            print(f"No environment specified. Use the --env option to specify this.")
            print(f"Though it looks like your current environment is: {current_env}")
            if not confirm_with_user(f"Do you want to use this ({current_env})?"):
                exit_without_doing_anything()

    # Make sure the environment specified
    # actually exists as a ~/.aws_test.ENV_NAME directory.

    if args.env_name not in available_envs:
        print(f"No environment for this name exists: {args.env_name}")
        if available_envs:
            print("Available environments:")
            for aws_available_env in sorted(available_envs):
                print(f"- {aws_available_env} ({env_info.get_dir(aws_available_env)})")
            exit_without_doing_anything("Choose on of the above environment using the --env option.")
        else:
            exit_without_doing_anything \
               (f"No environments found at all.\nYou need to have at least one {env_info.get_base_dir()}.{{ENV_NAME}} directory setup.") 

    aws_dir = env_info.get_dir(args.env_name)
    print(f"Setting up local custom config directory for environment: {args.env_name}")
    print(f"Your AWS credentials directory: {aws_dir}")

    # Create the custom directory; but make sue it doesn't already exist.

    custom_dir = os.path.abspath(args.custom_dir_name)
    if not custom_dir:
        exit_without_doing_anything("You must specify a custom output directory using the --out option.")
    if os.path.exists(custom_dir):
        exit_without_doing_anything(f"A custom {'directory' if os.path.isdir(custom_dir) else 'file'} already exists: {custom_dir}")

    print(f"Using custom directory: {custom_dir}")

    # Check all the inputs.

    if not args.account_number:
        env_dir = env_info.get_dir(args.env_name)
        args.account_number = get_fallback_account_number(env_dir)
        if not args.account_number:
            exit_without_doing_anything("Cannot determine account number. Use the --account option.")
    print(f"Using account number: {args.account_number}")

    if not args.deploying_iam_user:
        args.deploying_iam_user = get_fallback_deploying_iam_user()
        if not args.deploying_iam_user:
            exit_without_doing_anything(f"Cannot determine deploying IAM username. Use the --username option.")
    print(f"Using deploying IAM username: {args.deploying_iam_user}")

    if not args.identity:
        args.identity = get_fallback_identity(args.env_name)
        if not args.identity:
            exit_without_doing_anything(f"Cannot determine deploying IAM username. Use the --username option.")
    print(f"Using identity: {args.identity}")

    if not args.s3_bucket_org:
        exit_without_doing_anything(f"You must specify an S3 bucket organization name. Use the --s3org option.")
    print(f"Using S3 bucket organization name: {args.s3_bucket_org}")

    if not args.auth0_client:
        print("You must specify a Auth0 client ID using the --auth0client option.")
        args.auth0_client = input("Or enter your Auth0 client ID: ").strip()
        if not args.auth0_client:
            exit_without_doing_anything(f"You must specify an Auth0 client. Use the --auth0client option.")
    print(f"Using Auth0 client: {args.auth0_client}")

    if not args.auth0_secret:
        print("You must specify a Auth0 secret using the --auth0secret option.")
        args.auth0_secret = input("Or enter your Auth0 secret ID: ").strip()
        if not args.auth0_secret:
            exit_without_doing_anything(f"You must specify an Auth0 secret. Use the --auth0secret option.")
    print(f"Using Auth0 secret: {args.auth0_secret}")

    if args.re_captcha_key:
        print(f"Using reCaptchaKey: {args.re_captcha_key}")
    if args.re_captcha_secret:
        print(f"Using reCaptchaSecret: {args.re_captcha_secret}")

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
        ConfigTemplateVars.ACCOUNT_NUMBER.value:     args.account_number,
        ConfigTemplateVars.DEPLOYING_IAM_USER.value: args.deploying_iam_user,
        ConfigTemplateVars.IDENTITY.value:           args.identity,
        ConfigTemplateVars.S3_BUCKET_ORG.value:      args.s3_bucket_org,
        ConfigTemplateVars.ENCODED_ENV_NAME.value:   args.env_name
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
        SecretsTemplateVars.AUTH0_CLIENT.value:      args.auth0_client,
        SecretsTemplateVars.AUTH0_SECRET.value:      args.auth0_secret,
        SecretsTemplateVars.RE_CAPTCHA_KEY.value:    args.re_captcha_key,
        SecretsTemplateVars.RE_CAPTCHA_SECRET.value: args.re_captcha_secret
    }):
        print(f"Error writing: {secrets_file} (from: {secrets_template_file})")

    # Create the symlink from custom/aws_creds to ~/.aws_test.ENV_NAME.

    custom_aws_dir = os.path.abspath(os.path.join(custom_dir, CUSTOM_AWS_DIR))
    print(f"Creating symlink: {custom_aws_dir} -> {aws_dir} ")
    os.symlink(aws_dir, custom_aws_dir)

    # Create the S3 encrypt key file (with mode 400).

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
        os.chmod(s3_encrypt_key_file, stat.S_IRUSR)

    # Done. Summarize.

    print("Here is your new custom config directory:")
    print_directory_tree(custom_dir)


if __name__ == "__main__":
    main()
