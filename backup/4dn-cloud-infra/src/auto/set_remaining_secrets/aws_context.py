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

        aws = AwsContext(your_aws_credentials_directory_or_access_key_id_and_secret_access_key)
        with aws.establish_credentials() as credentials:
            do_something_with_boto3()
            # if desired reference credentials values ...
            access_key_id = credentials.access_key_id
            secret_access_key = credentials.secret_access_key
            default_region = credentials.default_region
            account_number = credentials.account_number
    """

    def __init__(self, aws_credentials_dir: str, aws_access_key_id: str = None, aws_secret_access_key: str = None, aws_default_region: str = None):
        """
        Constructor when stores the given AWS credentials directory, and AWS access key ID
        and secret access key and default region for use when establishing AWS credentials.
        The latter takes precedence.
        :param aws_credentials_dir: Path to AWS credentials directory.
        :param aws_access_key_id: AWS credentials access key ID.
        :param aws_secret_access_key: AWS credentials secret access key.
        :param aws_default_region: AWS credentials default region.
        """
        self._aws_credentials_dir = aws_credentials_dir
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_default_region = aws_default_region
        self._reset_boto3_default_session = True

    @contextlib.contextmanager
    def establish_credentials(self):
        """
        Context manager to establish AWS credentials without using environment,
        rather using the explicit AWS credentials directory or the explicit
        credentials values passed to the constructor of this object.

        Implementation note: to do this we temporarily (for the life of the context
        manager context) blow away the pertinent AWS credentials related environment
        variables, and set them appropriately based on given credentials information.

        :return: Yields named tuple with: access_key_id, secret_access_key, default_region, account_number, user_arn.
        """

        def unset_environ(environment_variables: list) -> list:
            saved_environ = {}
            for environment_variable in environment_variables:
                saved_environ[environment_variable] = os.environ.pop(environment_variable, None)
                if environment_variable.endswith("_FILE"):
                    os.environ[environment_variable] = "/dev/null"
            return saved_environ

        def restore_environ(saved_environ: list) -> None:
            for saved_environ_key, saved_environ_value in saved_environ.items():
                if saved_environ_value is not None:
                    os.environ[saved_environ_key] = saved_environ_value
                else:
                    os.environ.pop(saved_environ_key, None)

        saved_environ = unset_environ([ "AWS_ACCESS_KEY_ID",
                                        "AWS_SECRET_ACCESS_KEY",
                                        "AWS_SHARED_CREDENTIALS_FILE",
                                        "AWS_CONFIG_FILE",
                                        "AWS_DEFAULT_REGION" ])

        # This reset of the boto3.DEFAULT_SESSION is to workaround an odd problem with boto3
        # caching a default session, even for bad or non-existent credentials. This problem
        # was exhibited when importing (ultimately) modules from dcicutils (e.g. env_utils)
        # which (ultimately) globally creates a boto3 session with no credentials in effect.
        # Then our boto3 usage failed (here) with AWS credentials environment variables set.
        # Doing this just once (per AwsContext object creation) so as not to totally
        # undermine the (probably beneficial) caching that boto3 is trying to do.
        # Ref: https://stackoverflow.com/questions/36894947/boto3-uses-old-credentials
        if self._reset_boto3_default_session:
            boto3.DEFAULT_SESSION = None
            self._reset_boto3_default_session = False

        try:
            # TODO: Should we require all credentials, INCLUDING region, to come from EITHER
            # given arguments (i.e. command-line, ultimately) XOR from given AWS credentials
            # directory? I.e. so as not to split between them which may create some confusion.
            if self._aws_access_key_id and self._aws_secret_access_key:
                os.environ["AWS_ACCESS_KEY_ID"] = self._aws_access_key_id
                os.environ["AWS_SECRET_ACCESS_KEY"] = self._aws_secret_access_key
            else:
                aws_credentials_file = os.path.join(self._aws_credentials_dir, "credentials")
                if os.path.isfile(aws_credentials_file):
                    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = aws_credentials_file
                else:
                    raise Exception("No AWS credentials specified.")
            if self._aws_default_region:
                os.environ["AWS_DEFAULT_REGION"] = self._aws_default_region
            else:
                aws_config_file = os.path.join(self._aws_credentials_dir, "config")
                if os.path.isfile(aws_config_file):
                    os.environ["AWS_CONFIG_FILE"] = aws_config_file
            session = boto3.session.Session()
            credentials = session.get_credentials()
            access_key_id = credentials.access_key
            secret_access_key = credentials.secret_key
            default_region = session.region_name
            caller_identity = boto3.client("sts").get_caller_identity()
            account_number = caller_identity["Account"]
            user_arn = caller_identity["Arn"]
            yield namedtuple("aws", "access_key_id secret_access_key default_region account_number user_arn") \
                            (access_key_id=access_key_id,
                             secret_access_key=secret_access_key,
                             default_region=default_region,
                             account_number=account_number,
                             user_arn=user_arn)
        except Exception as e:
            # TODO
            print(f"EXCEPTION! {str(e)}")
        finally:
            restore_environ(saved_environ)
