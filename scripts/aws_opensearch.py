# --------------------------------------------------------------------------------------------------
# Simple script to get AWS OpenSearch endpoint.
# usage: aws-opensearch --
# --------------------------------------------------------------------------------------------------

import argparse
import boto3
from aws_utils import (validate_aws)

def get_opensearch_endpoint(aws_credentials_name: str,
                            access_key: str = None, secret_key: str = None, region: str = None):
    opensearch_instance_name = f"es-{aws_credentials_name}"
    opensearch = boto3.client('opensearch')
    domain_names = opensearch.list_domain_names()["DomainNames"]
    domain_name = [domain_name for domain_name in domain_names if domain_name["DomainName"] == opensearch_instance_name]
    if domain_name is None or len(domain_name) != 1:
        return None
    domain_name = domain_name[0]["DomainName"]
    domain_description = opensearch.describe_domain(DomainName=domain_name)
    domain_status = domain_description["DomainStatus"]
    domain_endpoints = domain_status["Endpoints"]
    domain_endpoint_options = domain_status["DomainEndpointOptions"]
    domain_endpoint_vpc = domain_endpoints["vpc"]
    domain_endpoint_https = domain_endpoint_options["EnforceHTTPS"]
    if domain_endpoint_https:
        domain_endpoint = f"{domain_endpoint_vpc}:443"
    else:
        domain_endpoint = f"{domain_endpoint_vpc}:80"
    return domain_endpoint


def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("--name", type=str, required=True)
    args_parser.add_argument("--access-key", type=str, required=False)
    args_parser.add_argument("--secret-key", type=str, required=False)
    args_parser.add_argument("--region", type=str, required=False)
    args_parser.add_argument("--keys", action="store_true", required=False)
    args_parser.add_argument("--verbose", action="store_true", required=False)
    args = args_parser.parse_args()

    print(f"AWS OpenSearch Utility | {args.name}")

    access_key, secret_key, region = validate_aws(args.access_key, args.secret_key, args.region)

    endpoint = get_opensearch_endpoint(args.name, access_key, secret_key, region)
    print(endpoint)


if __name__ == "__main__":
    main()
