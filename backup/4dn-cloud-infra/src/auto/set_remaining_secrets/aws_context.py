import boto3
import contextlib
import os

class AwsContext:
    def __init__(self, custom_aws_creds_dir: str, access_key: str = None, secret_key: str = None, region: str = None):
        # This reset of the boto3.DEFAULT_SESSION is to workaround an odd problem with boto3
        # caching a default session even bad or non-existent credentials. It was manifest due
        # to importing (ultimately) modules from dcicutils (e.g. env_utils) which globally
        # create a boto3 session when no credentials are in effect.
        boto3.DEFAULT_SESSION = None
        self._custom_aws_creds_dir = custom_aws_creds_dir
        self._aws_access_key_id = access_key
        self._aws_secret_access_key = secret_key
        self._aws_default_region = region
        self.access_key_id = None
        self.secret_access_key = None
        self.default_region = None
        self.account_number = None
        pass

    @contextlib.contextmanager
    def establish_credentials(self):
        # Credentials for this process need to come from custom/aws_creds directory,
        # or be directly passed in. We don't want to come from environment.
        try:
            save_AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
            save_AWS_SECRET_ACCESS_KEY= os.environ.get("AWS_SECRET_ACCESS_KEY")
            save_AWS_SHARED_CREDENTIALS_FILE = os.environ.get("AWS_SHARED_CREDENTIALS_FILE")
            save_AWS_CONFIG_FILE = os.environ.get("AWS_CONFIG_FILE")
            save_AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION")

            os.environ.pop("AWS_ACCESS_KEY_ID", None)
            os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            os.environ.pop("AWS_SHARED_CREDENTIALS_FILE", "/dev/null")
            os.environ.pop("AWS_CONFIG_FILE", None)
            os.environ.pop("AWS_DEFAULT_REGION", None)

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
            self.access_key_id = credentials.access_key
            self.secret_access_key = credentials.secret_key
            self.default_region = session.region_name
            self.account_number = boto3.client("sts").get_caller_identity()["Account"]
            yield
        except Exception as e:
            print(f"EXCEPTION! {str(e)}")
        finally:
            if save_AWS_ACCESS_KEY_ID:
                os.environ["AWS_ACCESS_KEY_ID"] = save_AWS_ACCESS_KEY_ID
            else:
                os.environ.pop("AWS_ACCESS_KEY_ID", None)
            if save_AWS_SECRET_ACCESS_KEY:
                os.environ["AWS_SECRET_ACCESS_KEY"] = save_AWS_SECRET_ACCESS_KEY
            else:
                os.environ.pop("AWS_ACCESS_KEY_ID", None)
            if save_AWS_SHARED_CREDENTIALS_FILE:
                os.environ["AWS_SHARED_CREDENTIALS_FILE"] = save_AWS_SHARED_CREDENTIALS_FILE
            else:
                os.environ.pop("AWS_SHARED_CREDENTIALS_FILE", None)
            if save_AWS_CONFIG_FILE:
                os.environ["AWS_CONFIG_FILE"] = save_AWS_CONFIG_FILE
            else:
                os.environ.pop("AWS_CONFIG_FILE", None)
            if save_AWS_DEFAULT_REGION:
                os.environ["AWS_DEFAULT_REGION"] = save_AWS_DEFAULT_REGION
            else:
                os.environ.pop("AWS_DEFAULT_REGION", None)
            self.access_key_id = None
            self.secret_access_key = None
            self.default_region = None
            self.account_number = None
