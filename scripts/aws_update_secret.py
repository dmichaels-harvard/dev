# ----------------------------------------------------------------------------------------------------------------------
# Simple script to update/create/delete AWS secret.
# Displays any current values, and prompt (yes/no) before actually doing anything.
#
# usage: aws-update-secret --name secret-name --key secret-key-name [--value secret-key-value | --delete]
# ----------------------------------------------------------------------------------------------------------------------

import argparse
import boto3
import json
from aws_utils import (validate_aws_credentials)


def update_secret_value(secrets_manager, secret_name: str, secret_key_name: str, secret_key_value: str) -> bool:
    """
    Updates the AWS secret value for the given secret key name within the given secret name.
    If the given secret key value does not yet exist it will be created.
    If the given secret key value is None then the given secret key will be deleted.
    :param secrets_manager: AWS secrets manager ala boto3.
    :param secret_name: AWS secret name.
    :param secret_key_name: AWS secret key name to update.
    :param secret_key_value: AWS secret key value to update to. If None then the secret key will be deleted.
    :param prompt: Prompt for confirmation (from stdin) if True otherwise silent.
    :return: True if succeeded otherwise false.
    """
    try:
        # To update an individual secret key value we need to get the entire JSON
        # associated with the given secret name, update the specific element for
        # the given secret key name with the new given value, and write the updated
        # JSON back as the secret value for the given secret name.
        try:
            secret_value = secrets_manager.get_secret_value(SecretId=secret_name)
        except:
            print(f"AWS secret name does not exist: {secret_name}")
            return False

        secret_value_json = json.loads(secret_value["SecretString"])
        secret_key_value_current = secret_value_json.get(secret_key_name)

        action = None
        if secret_key_value is None:
            if secret_key_value_current is None:
                print(f"AWS secret {secret_name}.{secret_key_name} does not exist. Nothing to delete.")
                return False
            action = "delete"
        else:
            if secret_key_value_current is None:
                print(f"AWS secret {secret_name}.{secret_key_name} does not yet exist.")
                action = "create"
            else:
                print(f"Current value of AWS secret {secret_name}.{secret_key_name} is: {secret_key_value_current}")
                action = "update"
            print(f"New value of AWS secret {secret_name}.{secret_key_name} is: {secret_key_value}")

        yes_or_no = input(f"Are you sure you want to {action} AWS secret {secret_name}.{secret_key_name}? [yes/no] ").strip().lower()
        if yes_or_no == "yes":
            if secret_key_value is None:
                del secret_value_json[secret_key_name]
            else:
                secret_value_json[secret_key_name] = secret_key_value
            secrets_manager.update_secret(SecretId=secret_name, SecretString=json.dumps(secret_value_json))
            return True

    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
    return False


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--name", type=str, required=True)
    args_parser.add_argument('--key', type=str, required=True)
    args_parser.add_argument('--value', type=str, required=False)
    args_parser.add_argument('--delete', action="store_true", default=None, required=False)
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args_parser.add_argument("--no-confirm", dest="confirm", action="store_false", required=False)
    args = args_parser.parse_args()

    if (args.value is None and args.delete is None) or (args.value is not None and args.delete is not None):
        print("Must specify either --value or --delete and not both.")
        exit(1)

    if args.delete:
        print(f"AWS Secrets Delete Utility | {args.name}.{args.key}")
    else:
        print(f"AWS Secrets Update Utility | {args.name}.{args.key}")

    access_key, secret_key, region = validate_aws_credentials(args.access_key, args.secret_key, args.region, True)
    secrets_manager = boto3.client('secretsmanager', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)

    update_secret_value(secrets_manager, args.name, args.key, args.value)

if __name__ == "__main__":
    main()
