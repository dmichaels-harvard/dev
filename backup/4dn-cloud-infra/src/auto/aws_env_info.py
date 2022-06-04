import os
import glob

# Testing notes ...
# External resources accesed by this module:
# - File System via:
#   - glob.glob
#   - os.path.basename
#   - os.path.expanduser
#   - os.path.isdir
#   - os.path.islink
#   - os.readlink

class AwsEnvInfo:
    """
    Class to gather/dispense info about the ~/.aws_test directories
    ala use_test_creds, i.e. what AWS credentials enviroment is currently
    active (based on what ~/.aws_test is symlinked to), and the list
    of available environments (based on what ~/.aws_test.{ENV_NAME}
    directories actually exist).

    Looks for set of directories of the form ~/.aws_test.{ENV_NAME} where ENV_NAME can
    be anything; and the directory ~/.aws_test can by symlinked to any or none of them.

    The get_current_env() method returns the ENV_NAME for the one currently symlinked
    to, if any. The get_available_envs() method returns a list of available
    ENV_NAMEs each of the ~/.aws_test.{ENV_NAME} directories which actually exist.

    May construct with a base directory name other than ~/.aws_test if desired.
    """

    # TOD)
    # We're probably going to change this default directory name ~/.aws_test
    # to something like ~/.aws_cgap or something; when we do we can change
    # this, and/or of course can pass this into the AwsEnvInfo constructor.
    #
    __DEFAULT_AWS_DIR = "~/.aws_test"

    def __init__(self, aws_dir = __DEFAULT_AWS_DIR):
        if not aws_dir:
            aws_dir = AwsEnvInfo.__DEFAULT_AWS_DIR
        self.__aws_base_dir = os.path.basename(aws_dir)
        self.__aws_dir = os.path.expanduser(aws_dir)

    def __get_dirs(self):
        dirs = []
        for dir in glob.glob(self.__aws_dir + ".*"):
            if os.path.isdir(dir):
                dirs.append(dir)
        return dirs

    def __get_env_name_from_path(self, path: str):
        if path:
            basename = os.path.basename(path)
            if basename.startswith(self.__aws_base_dir + "."):
                return basename[len(self.__aws_base_dir) + 1:]

    def get_base_dir(self):
        return self.__aws_dir

    def get_available_envs(self):
        """
        Returns a list of available AWS environments based on what
        directories are present of the form ~/.aws_test.{ENV_NAME}.
        Returns empty list of none found.
        """
        return [ self.__get_env_name_from_path(path) for path in self.__get_dirs() ]

    def get_current_env(self):
        """
        Returns the AWS environment name as represented by the ENV_NAME portion
        of the symlink target of the ~/.aws_test directory itself.
        Returns None if not set.
        """
        symlink_target = os.readlink(self.__aws_dir) if os.path.islink(self.__aws_dir) else None
        return self.__get_env_name_from_path(symlink_target)

    def get_dir(self, env_name):
        """
        Returns a full directory path name of the form ~/.aws_test.{ENV_NAME}
        for the given :param:`env_name`.
        :param env_name: The AWS environment name.
        """
        if env_name:
            return self.__aws_dir + "." + env_name


if __name__ == "__main__":
    aws_dirs_info = AwsEnvInfo()
    aws_current_env = aws_dirs_info.get_current_env()
    if aws_current_env:
        print(f"Your current AWS (use_test_creds) environment is: {aws_current_env}")
    else:
        print(f"You currently have no (use_test_creds) AWS environment set.")
    aws_available_envs = aws_dirs_info.get_available_envs()
    if aws_available_envs:
        print("Available AWS (use_test_creds) environments:")
        for aws_available_env in sorted(aws_available_envs):
            print(f"- {aws_available_env}")
