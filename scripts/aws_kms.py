import argparse
import boto3
import json
from aws_utils import (obfuscate, should_obfuscate, validate_aws)


def get_kms_keys(customer: bool, access_key: str = None, secret_key: str = None, region: str = None):
    result_keys = []
    kms = boto3.client("kms", aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    for key in kms.list_keys()["Keys"]:
        key_id = key["KeyId"]
        key_description = kms.describe_key(KeyId=key_id)
        key_metadata = key_description["KeyMetadata"]
        key_manager = key_metadata["KeyManager"]
        if not customer or key_manager == "CUSTOMER":
            key_policy = kms.get_key_policy(KeyId=key_id, PolicyName="default")
            key_creation_date = key_metadata["CreationDate"]
            result_keys.append((key_id, key_policy, key_creation_date))
    return sorted(result_keys, key=lambda key: key)


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('--customer', action="store_true")
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args_parser.add_argument("--policy", action="store_true", required=False)
    args = args_parser.parse_args()

    print(f"AWS KMS Utility{' | customer-managed' if args.customer else ''}")

    access_key, secret_key, region = validate_aws(args.access_key, args.secret_key, args.region)

    keys = get_kms_keys(args.customer, access_key=access_key, secret_key=secret_key, region=region)
    for key_id, key_policy, key_created in keys:
        print(f"Key ID: {key_id} (created: {key_created.astimezone().strftime('%Y-%m-%d %H:%M:%S')})")
        if args.policy:
            print(json.dumps(json.loads(key_policy["Policy"]), indent=2))
            #print(json.dumps(json.loads(key_policy), indent=2))


if __name__ == "__main__":
    main()
