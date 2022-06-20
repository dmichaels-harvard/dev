import boto3
from collections import namedtuple
import contextlib
import os

class AwsContext:
    """
    Class to setup the context for AWS credentials which do NOT rely on environment AT ALL.
    I.e. neither on the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables,
    nor on the ~/.aws credentials and config files (nor on the AWS_SHARED_CREDENTIALS_FILE
    and AWS_CONFIG_FILE environment variables).

    A specific path to the ~/.aws credentials directory MUST be specified, which will
    setup the context to refer to the credentials and config file(s) there; OR, specific
    AWS access key ID and associated secret access key (and default region) values MUST
    to be specified; the latter taking precedence over the former. Usage like this:

        aws = AwsContext(your_custom_aws_directory)
        with aws.establish_credentials() as credentials:
            do_something_with_boto3()
            # if desired reference credentials values ...
            access_key_id = credentials.access_key_id
            secret_access_key = credentials.secret_access_key
            default_region = credentials.default_region
            account_number = credentials.account_number
    """

    def __init__(self, custom_aws_creds_dir: str, access_key: str = None, secret_key: str = None, region: str = None):
        self._custom_aws_creds_dir = custom_aws_creds_dir
        self._aws_access_key_id = access_key
        self._aws_secret_access_key = secret_key
        self._aws_default_region = region

    @contextlib.contextmanager
    def establish_credentials(self):
        """
        Context manager to establish AWS credentials without using environment,
        rather using the explicit AWS credentials directory or the explicit
        credentials values passed to the constructor of this object.

        Implementation note: to do this we temporarily (for the life of the context
        manager context) blow away the pertinent AWS credentials related environment variables.

        :return: Yields named tuple with: access_key_id, secret_access_key, default_region, account_number.
        """

        def save_and_unset_environment_variables(environment_variables: list) -> list:
            saved_environment_variables = {}
            for environment_variable in environment_variables:
                saved_environment_variables[environment_variable] = os.environ.pop(environment_variable, None)
                if environment_variable.endswith("_FILE"):
                    os.environ[environment_variable] = "/dev/null"
            return saved_environment_variables

        def restore_environment_variables(saved_environment_variables: list) -> None:
            for saved_environment_variable, saved_environment_variable_value in saved_environment_variables.items():
                if saved_environment_variable_value is not None:
                    os.environ[saved_environment_variable] = saved_environment_variable_value
                else:
                    os.environ.pop(saved_environment_variable, None)

        saved_environment_variables = save_and_unset_environment_variables([ "AWS_ACCESS_KEY_ID",
                                                                             "AWS_SECRET_ACCESS_KEY",
                                                                             "AWS_SHARED_CREDENTIALS_FILE",
                                                                             "AWS_CONFIG_FILE",
                                                                             "AWS_DEFAULT_REGION" ])

        # This reset of the boto3.DEFAULT_SESSION is to workaround an odd problem with boto3
        # caching a default session, even bad or non-existent credentials. This problem was
        # exhibited when importing (ultimately) modules from dcicutils (e.g. env_utils)
        # which (ultimately) globally creates a boto3 session with no credentials in effect.
        # Ref: https://stackoverflow.com/questions/36894947/boto3-uses-old-credentials
        boto3.DEFAULT_SESSION = None

        try:
            if self._aws_access_key_id and self._aws_secret_access_key:
                os.environ["AWS_ACCESS_KEY_ID"] = self._aws_access_key_id
                os.environ["AWS_SECRET_ACCESS_KEY"] = self._aws_secret_access_key
            else:
                custom_aws_creds_credentials_file = os.path.join(self._custom_aws_creds_dir, "credentials")
                if os.path.isfile(custom_aws_creds_credentials_file):
                    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = custom_aws_creds_credentials_file
                else:
                    raise Exception("No AWS credentials specified.")
            if self._aws_default_region:
                os.environ["AWS_DEFAULT_REGION"] = self._aws_default_region
            else:
                custom_aws_creds_config_file = os.path.join(self._custom_aws_creds_dir, "config")
                if os.path.isfile(custom_aws_creds_config_file):
                    os.environ["AWS_CONFIG_FILE"] = custom_aws_creds_config_file
            session = boto3.session.Session()
            credentials = session.get_credentials()
            access_key_id = credentials.access_key
            secret_access_key = credentials.secret_key
            default_region = session.region_name
            account_number = boto3.client("sts").get_caller_identity()["Account"]
            yield namedtuple("aws", "access_key_id secret_access_key default_region account_number") \
                            (access_key_id=access_key_id,
                             secret_access_key=secret_access_key,
                             default_region=default_region,
                             account_number=account_number)
        except Exception as e:
            # TODO
            print(f"EXCEPTION! {str(e)}")
        finally:
            restore_environment_variables(saved_environment_variables)
