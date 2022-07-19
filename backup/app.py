from chalice import Chalice
from dcicutils.secrets_utils import (
    assume_identity,
    assumed_identity,
    apply_identity as secrets_apply_identity,
    get_identity_secrets,
    get_secrets,
)
import os

# Minimal app.py; used to verify foursight-core packaging scripts
app = Chalice(app_name='foursight_core')

GAC_SECRET_NAME = 'C4DatastoreCgapSupertestApplicationConfiguration'
RDS_SECRET_NAME = 'C4DatastoreCgapSupertestRDSSecret'

IDENTITY_NAME = GAC_SECRET_NAME
IDENTITY_ENV_NAME = 'IDENTITY'

def apply_identity_name():
    os.environ[IDENTITY_ENV_NAME] = IDENTITY_NAME

def apply_identity():
    apply_identity_name()
    rename_keys = {
        "ENCODED_AUTH0_CLIENT":      "CLIENT_ID",
        "ENCODED_AUTH0_SECRET":      "CLIENT_SECRET",
        "ENCODED_S3_ENCRYPT_KEY_ID": "S3_ENCRYPT_KEY_ID",
        "ENCODED_ES_SERVER":         "ES_HOST",
    }
    secrets_apply_identity(identity_kind=IDENTITY_ENV_NAME, rename_keys=rename_keys)

def apply_rds_secrets():
    rds_secrets = get_secrets(RDS_SECRET_NAME)
    os.environ["RDS_NAME"] = rds_secrets.get("dbInstanceIdentifier")

def apply_environ():
    apply_identity()
    apply_rds_secrets()

@app.route('/')
def index():
    return {'minimal-foo': 'foursight_core-hoo'}

@app.route('/env')
def route_env():
    return dict(os.environ)

@app.route('/secrets')
def route_secrets():
    try:
        apply_identity_name()
        identity = get_identity_secrets(identity_kind=IDENTITY_ENV_NAME)
        return identity
    except Exception as e:
        return {'exception': str(e)}

@app.route('/secrets-two')
def route_env():
    print('foo')
    try:
        apply_identity_name()
        with assumed_identity(identity_kind=IDENTITY_ENV_NAME):
            return dict(os.environ)
    except Exception as e:
        print('goo')
        return {'exception': str(e)}

@app.route('/apply-identity')
def route_apply_identity():
    try:
    #   apply_identity_name()
    #   rename_keys = {
    #       "ENCODED_AUTH0_CLIENT":      "CLIENT_ID",
    #       "ENCODED_AUTH0_SECRET":      "CLIENT_SECRET",
    #       "ENCODED_S3_ENCRYPT_KEY_ID": "S3_ENCRYPT_KEY_ID",
    #       "ENCODED_ES_SERVER":         "ES_HOST",
    #   }
    #   secrets_apply_identity(identity_kind=IDENTITY_ENV_NAME, rename_keys=rename_keys)
    #   rds_secrets = get_secrets(RDS_SECRET_NAME)
    #   os.environ["RDS_NAME"] = rds_secrets.get("dbInstanceIdentifier")
        apply_environ()
        return dict(os.environ)
    except Exception as e:
        return {'exception': str(e)}

@app.route('/rds-secrets')
def route_rds_secrets():
    try:
        rds_secrets = get_secrets(RDS_SECRET_NAME)
        return dict(rds_secrets)
    except Exception as e:
        return {'exception': str(e)}
