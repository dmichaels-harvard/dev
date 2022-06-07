# IN PROGRESS / dmichaels / 2022-06-04
#
# Miscellaneous utilities.
#
# Testing notes:
# - External resources accesed by this module:
#   - filesystem via:
#     - glob.glob
#     - io.open
#     - os.listdir
#     - os.path.basename
#     - os.path.isdir
#     - os.path.join
#     - os.readlink
#   - shell via:
#     - subprocess.check_output (to execute test_cred.sh)

import binascii # TODO: add to pyproject.toml dependencies?
import io
import json
import os
import pbkdf2 # TODO: add to pyproject.toml dependencies?
import secrets 
import string 
import subprocess

from   dcicutils.misc_utils import json_leaf_subst as expand_json_template
from   .defs import Files


def expand_json_template_file(template_file: str, output_file: str, template_substitutions: dict):
    """
    Expands the JSON template file specified by the given :param:`template_file`
    with the substitutions in the given :param:`template_substitutions`
    dictionary and writes to the given :param:`output_file`.
    :param template_file: The input JSON template file path name.
    :param output_file: The output file path name.
    :param template_substitutions: The dictionary of substitution keys/values.
    """
    with io.open(template_file, "r") as template_f:
        template_file_json = json.load(template_f)
    expanded_template_json = expand_json_template(template_file_json, template_substitutions)
    with io.open(output_file, "w") as output_f:
        json.dump(expanded_template_json, output_f, indent=2)
        output_f.write("\n")

def generate_s3_encrypt_key() -> str:
    """ Generate a cryptographically secure encryption key suitable for AWS S3 encryption.
        References:
        https://cryptobook.nakov.com/symmetric-key-ciphers/aes-encrypt-decrypt-examples#password-to-key-derivation
        https://docs.python.org/3/library/secrets.html#recipes-and-best-practices
        :returns: A cryptographically secure encryption key.
    """
    def generate_password() -> str:
        #
        # Will suggests using a password from some (4) random words.
        #
        password = ""
        if os.path.isfile(Files.SYSTEM_WORDS_DICTIONARY_FILE):
            try:
                with open(system_words_file) as system_words_f:
                    words = [word.strip() for word in system_words_f]
                    password = "".join(secrets.choice(words) for i in range(4))
            except Exception as e:
                pass
        #
        # As fallback, and in any case, tack on a random token.
        #
        return password + secrets.token_hex(16)
    password = generate_password()
    password_salt = os.urandom(16)
    s3_encrypt_key = pbkdf2.PBKDF2(password, password_salt).read(16)
    s3_encrypt_key = binascii.hexlify(s3_encrypt_key).decode("utf-8")
    return s3_encrypt_key

    # Second try:
    # return secrets.token_hex(16)

    # First try:
    # Replicating exactly the method used in scripts/create_s3_encrypt_key but
    # should we rather modify that script and call out to it? And if we do do
    # it here then may need to also replicate the openssl version checking.
    # s3_encrypt_key_command = "openssl enc -aes-128-cbc -k `ps -ax | md5` -P -pbkdf2 -a"
    # s3_encrypt_key_command_output = subprocess.check_output(s3_encrypt_key_command, shell=True).decode("utf-8").strip()
    # return re.compile("key=(.*)\n").search(s3_encrypt_key_command_output).group(1)

def read_env_variable_from_subshell(shell_script_file: str, env_variable_name: str) -> str:
    """
    Obtains/returns the value of the given envrionment variable name by executing
    the given shell script file in a sub-shell.
    :param shell_script_file: The shell script file to execute.
    :param env_variable_name: The environment variable name.
    :returns: The value of the given environment variable name from the executed given shell script.
    """
    try:
        if not os.path.isfile(shell_script_file):
            return None
        command = f"source {shell_script_file} ; echo ${env_variable_name}"
        command_output = str(subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT).decode("utf-8")).strip()
        return command_output
    except Exception as e:
        print(e)
        return None

def obfuscate(value: str) -> str:
    """
    Obfuscates and returns the given string value.
    :param value: The value to obfuscate.
    :returns: The obfuscated value or empty string if not a string or empty.
    """
    return value[0] + "********" if isinstance(value, str) else ""

def confirm_with_user(message: str):
    """
    Prompts the user with the given message and asks for yes or no.
    Returns True if "yes" (exactly, trimmed, case-insensitive) otherwise False.
    :param message: Message to print for the user prompt.
    """
    return input(message + " (yes|no) ").strip().lower() == "yes"

def exit_with_no_action(message: str = "", status: int = 0):
    """
    Prints the given message (if any) and exits with the given status.
    :param message: Message to print before exit.
    :param status: The exit status code.
    """
    if message:
        print(message)
    print("Exiting without doing anything.")
    exit(status)

def print_directory_tree(directory: str):
    """
    Prints the given directory as a tree structure. Taken/adapted from:
    https://stackoverflow.com/questions/9727673/list-directory-tree-structure-in-python
    :param directory: The directory name whose tree structure to print. 
    """
    def tree_generator(directory: str, prefix: str = ""):
        space = "    " ; branch = "│   " ; tee = "├── " ; last = "└── "
        contents = [os.path.join(directory, item) for item in sorted(os.listdir(directory))]
        pointers = [tee] * (len(contents) - 1) + [last]
        for pointer, path in zip(pointers, contents):
            symlink = "@ ─> " + os.readlink(path) if os.path.islink(path) else ""
            yield prefix + pointer + os.path.basename(path) + symlink
            if os.path.isdir(path):
                extension = branch if pointer == tee else space 
                yield from tree_generator(path, prefix=prefix+extension)
    print("└─ " + directory)
    for line in tree_generator(directory, prefix="   "): print(line)
