import argparse
import boto3
from aws_utils import (obfuscate, should_obfuscate, validate_aws)


def get_kms_keys(customer: bool, access_key: str = None, secret_key: str = None, region: str = None):
    result_keys = []
    kms = boto3.client("kms", aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    for key in kms.list_keys()["Keys"]:
        key_id = key["KeyId"]
        key_description = kms.describe_key(KeyId=key_id)
        print(key_description)
        key_metadata = key_description["KeyMetadata"]
        key_manager = key_metadata["KeyManager"]
        if not customer or key_manager == "CUSTOMER":
            result_keys.append(key_id)
    return sorted(result_keys, key=lambda key: key)


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('--customer', action="store_true")
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args = args_parser.parse_args()

    print(f"AWS KMS Utility{' | customer-managed' if args.customer else ''}")

    access_key, secret_key, region = validate_aws(args.access_key, args.secret_key, args.region)

    keys = get_kms_keys(args.customer, access_key=access_key, secret_key=secret_key, region=region)
    for key in keys:
        print(key)


if __name__ == "__main__":
    main()
