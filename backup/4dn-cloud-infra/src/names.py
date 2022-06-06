from .constants import APPLICATION_CONFIGURATION_SECRET_NAME_SUFFIX, COMMON_STACK_PREFIX, COMMON_STACK_PREFIX_CAMEL_CASE, DATASTORE_STACK_TITLE_TOKEN
from dcicutils.cloudformation_utils import camelize
from dcicutils.misc_utils import remove_prefix

# Factored out of C4Name for common usage to for get_global_application_configuration_secret_name,
# above, so we can get the GAC name (from the init-custom-dir script) without importing
# anything from 4dn-cloud-infra, which is quite problematic with no config setup yet.
#
def get_logical_id(resource, context="", string_to_trim=None, logical_id_prefix=None):
    print('ffffffffffffffffffffff')
    print(f"resource={resource}")
    print(f"context={context}")
    print(f"string_to_trim={string_to_trim}")
    print(f"logical_id_prefix={logical_id_prefix}")
    """ Build the Cloud Formation 'Logical Id' for a resource.
        Takes string s and returns s with uniform resource prefix added.
        Can also be used to construct Name tags for resources. """
    # Don't add the prefix redundantly.
    resource_name = str(resource)
    if string_to_trim and resource_name.startswith(string_to_trim):
        if context:
            context = f"In {context}: "
        else:
            context = ""
        maybe_resource_name = remove_prefix(string_to_trim, resource_name, required=False)
        if maybe_resource_name:  # make sure we didn't remove the whole string
            resource_name = maybe_resource_name
    if logical_id_prefix:
        res = logical_id_prefix + resource_name
    else:
        res = resource_name
    return res

def get_suggest_stack_name():
    pass

def get_global_application_configuration_secret_name(env_name: str) -> str:
    def logical_id(resource: str, context = "") -> str:
        #
        # This is supposed to replicate C4Name.logical_id in part.py
        # at least WRT the case of CDatastore.application_configuration_secret.
        #
        # When called as CName.logical_id "normally" in part.py we get passed
        #
        # - resource="CgapSupertestApplicationConfiguration"
        # - context=""
        #
        # And the CName self looks like:
        #
        # - name: "c4-datastore-cgap-supertest"
        # - raw_name: None
        # - logical_id_prefix: "C4DatastoreCgapSupertest"
        # - string_to_trim: "CgapSupertest"
        # - stack_name: "c4-datastore-cgap-supertest-stack"
        #
        # Only self.string_to_trim and self.logical_id_prefix are used in the logic.
        # It strips string_to_trim off of the given resource name and prefixes
        # logical_id_prefix to that result -> "C4DatastoreCgapSupertestApplicationConfiguration"
        #
        # Question is where did all these come from.
        # Well it gets call from part.py/StackNameMixin.suggest_stack_name("datastore")
        # which creates C4Name via ctor like this:
        #
        # - C4Name(name=f'{COMMON_STACK_PREFIX}{name_token}{qualifier_suffix}',
        #          title_token=(f'{COMMON_STACK_PREFIX_CAMEL_CASE}{title_token}{qualifier_camel}' if title_token else None),
        #          string_to_trim=qualifier_camel)
        #
        #   - where name_token is from cls(StackNameMixin).STACK_NAME_TOKEN which is "datastore"
        #     which got that value because the cls is (somehow) a C4Datastore (which isa C4Part
        #     which isa StackNameMixin)
        #   - where qualifier_suffix is f"-{qualifier}" where qualifier is from
        #     cls/StackNameMixin.suggest_sharing_qualifier() which gives "cgap-supertest" and
        #     which gets that from StackNameMixin._SHARING_QUALIFIERS['env'] which got its value from base.py/ENV_NAME
        #     which is "cgap-supertest" which came from ConfigManger.get_config_setting("ENCODED_BS_ENV")
        #   - where title_token is "Datastore" which is from cls.stack_title_token() which gets
        #     it from cls/StackNameMixin.STACK_TITLE_TOKEN (or camelize(cls/StackNameMixin.STACK_NAME_TOKEN) if not set),
        #     which, because cls isa C4Datastore, and STACK_TITLE_TOKEN is hardcoded there (in C4Datastore) to "Datastore";
        #     and where also STACK_TITLE_NAME is "datastore".
        #   - where qualifier_camel is camelize(qualifier), from above.
        #   - where COMMON_STACK_PREFIX is "c4-" from base.py
        #   - where COMMON_STACK_PREFIX_CAMEL_CASE is "C4" from base.py
        #
        # - And the C4Name ctor sets its self.logical_id_prefix to: title_token or camelize(name) 
        #  
        # Note we don't, in C4Name.logical_id(), even use C4Name.name, only string_to_trim and logical_id_prefix.
        # However, in the C4Name ctor if title_token is not set (which it is in our case) we set it (title_token) to the given name
        #
        # So back to C4Name.logical_id() ...
        # - C4Name.logical_id_prefix comes ultimately from C4Datastore.STACK_TITLE_TOKEN, i.e. "Datastore"
        # - C4Name.string_to_trim comes ultimately from camelized env-name, e.g. CgapSupertest
        #
        # So to get CName.logical_id("CgapSupertestApplicationConfiguration") where that arg is from
        # the call, i.e. logical_id(camelize(env_name) + APPLICATION_CONFIGURATION_SECRET_NAME_SUFFIX) ...
        #
        # So do we want a new function in this new (names.py) module called logical_id ...
        # def logical_id(resource_name, string_to_trim, logical_id_prefix)
        # so we can call from here like:
        #
        # logical_id(resource=camelize(env_name) + APPLICATION_CONFIGURATION_SECRET_NAME_SUFFIX,
        #            string_to_trim=camelize(env_name),
        #            logical_id_prefix=C4Datastore.STACK_TITLE_TOKEN)
        #
        return camelize(COMMON_STACK_PREFIX) + camelize('datastore') + resource

    #return logical_id(camelize(env_name) + APPLICATION_CONFIGURATION_SECRET_NAME_SUFFIX)
    resource_name = camelize(env_name) + APPLICATION_CONFIGURATION_SECRET_NAME_SUFFIX
    string_to_trim = camelize(env_name)
    #
    # But need to factor out this "logic" ... which is from suggest part.py/suggest_stack_name
    # To do this we need to factor out from suggest_stack_name just the part that passes this
    # string to the C4Name ctor: title_token=(f'{COMMON_STACK_PREFIX_CAMEL_CASE}{title_token}{qualifier_camel}' if title_token else None)
    # This is getting a bit wonky, and would really serve to further obfuscate the existing code ...
    #
    # This "works" (and with my "real" custom directory moved to custom-save).
    #
    title_token = f"{COMMON_STACK_PREFIX_CAMEL_CASE}{DATASTORE_STACK_TITLE_TOKEN}{camelize(env_name)}"
    logical_id_prefix = title_token
    return get_logical_id(resource=resource_name, string_to_trim=string_to_trim, logical_id_prefix=logical_id_prefix)
    #return get_logical_id(resource=camelize(env_name) + APPLICATION_CONFIGURATION_SECRET_NAME_SUFFIX, string_to_trim=camelize(env_name), logical_id_prefix=DATASTORE_STACK_TITLE_TOKEN)

# These are from C4Name ...
# ----------------------------------------------------------------------------------------------------------------------
#   def logical_id(self, resource, context=""):
#       """ Build the Cloud Formation 'Logical Id' for a resource.
#           Takes string s and returns s with uniform resource prefix added.
#           Can also be used to construct Name tags for resources. """
#       # Don't add the prefix redundantly.
#       resource_name = str(resource)
#       if resource_name.startswith(self.string_to_trim):
#           if context:
#               context = f"In {context}: "
#           else:
#               context = ""
#           maybe_resource_name = remove_prefix(self.string_to_trim, resource_name, required=False)
#           if maybe_resource_name:  # make sure we didn't remove the whole string
#               resource_name = maybe_resource_name
#       res = self.logical_id_prefix + resource_name
#       # print(f"{context}{self}.logical_id({resource!r}) => {res}")
#       return res
# ----------------------------------------------------------------------------------------------------------------------
#   @classmethod
#   def suggest_stack_name(cls, name=None):
#       title_token = cls.stack_title_token()
#       qualifier = cls.suggest_sharing_qualifier()
#       qualifier_suffix = f"-{qualifier}"
#       qualifier_camel = camelize(qualifier)
#       name_token = cls.STACK_NAME_TOKEN
#       return C4Name(name=f'{COMMON_STACK_PREFIX}{name_token}{qualifier_suffix}',
#                     title_token=(f'{COMMON_STACK_PREFIX_CAMEL_CASE}{title_token}{qualifier_camel}'
#                                  if title_token else None),
#                     string_to_trim=qualifier_camel)
# ----------------------------------------------------------------------------------------------------------------------
#
# And this is what we can replace the above with:
# ----------------------------------------------------------------------------------------------------------------------
#   from .names import get_logical_id
#   def logical_id(self, resource, context=""):
#       return get_logical_id(resource, context, string_to_trim=self.string_to_trim, logical_id_prefix=self.logical_id_prefix)
#
# ----------------------------------------------------------------------------------------------------------------------
#   def suggest_stack_name(cls, name=None):
