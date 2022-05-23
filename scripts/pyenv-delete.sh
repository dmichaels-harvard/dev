#!/bin/bash
# --------------------------------------------------------------------------------------------------
# Deletes a pyenv virtualenv ENTIRELY!
#
# Usage: pyenv-delete.sh your-virtualenv-name
# Will not let you delete if the specified virtualenv is currently active.
# Prompts before actually deleting the ~/.pyenv virtualenv symlink/directory.
# Perhaps there is a pyenv way of doing this but have not been able to find it.
#
# NEVERMIND!
# Hadn't been able to find a pyenv way of doing this but then I did ...
# Simply: pyenv virtualenv-delete your-virtualenv-name
# So no need for this script!
# --------------------------------------------------------------------------------------------------

if [ $# -ne 1 ]; then
    echo "usage: pyenv-delete virtualenv-name"
    exit 1
fi

ENV_TO_DELETE=$1
PYENV_DIR=${PYENV_ROOT:-~/.pyenv}

# Make sure we are not trying to delete a currently active virtualenv.
# FYI when a pyenv virtualenv is active in a shell we see something like:
#
# PYENV_VERSION=myenv
# PYENV_VIRTUAL_ENV=/Users/dmichaels/.pyenv/versions/3.8.12/envs/myenv
# PYENV_VIRTUALENV_INIT=1
#
# And the directories to cleanup (delete!) are like:
#
# ~/.pyenv/versions/myenv             (symlink)
# ~/.pyenv/versions/3.8.12/envs/myenv (directory)
#
# We do case-insensitive string compare here (must be better way)
# because pyenv does seem to be case insensitive ...
#
if [ ! -z "${PYENV_VERSION}" -a "`echo ${PYENV_VERSION} | tr '[:upper:]' '[:lower:]'`" == "`echo ${ENV_TO_DELETE} | tr '[:upper:]' '[:lower:]'`" ]; then
    echo "This is your current pyenv virtualenv: ${PYENV_VERSION}"
    echo "You cannot delete it with deactivating!"
    echo "Deactivate it first using: pyenv deactivate"
    exit 2
fi

# For each directory in ~/.pyenv/versions/ which is NOT a symlink,
# look for the specified virtualenv to delete (ENV_TO_DELETE0.

ENV_DIR_TO_DELETE=
ENV_SYMLINK_TO_DELETE=

for version_dir in `ls ${PYENV_DIR}/versions`; do
    if [ -L ${PYENV_DIR}/versions/${version_dir} ]; then
        if [ ${version_dir} == ${ENV_TO_DELETE} ]; then
            if [ ! -z ${ENV_SYMLINK_TO_DELETE} ]; then
                echo "Something is wrong. Duplicate directory found: ${ENV_SYMLINK_TO_DELETE}"
                echo "Exiting without doing anything."
                echo "See this script for more info: $0"
                exit 3
            fi
            ENV_SYMLINK_TO_DELETE=${PYENV_DIR}/versions/${version_dir}
        fi
    else
        virtualenv_dir=${PYENV_DIR}/versions/${version_dir}/envs/${ENV_TO_DELETE}
        if [ -d ${virtualenv_dir} ]; then
            if [ ! -z ${ENV_DIR_TO_DELETE} ]; then
                echo "Something is wrong. Duplicate directory found: ${ENV_DIR_TO_DELETE}"
                echo "Exiting without doing anything."
                echo "See this script for more info: $0"
                exit 4
            fi
            ENV_DIR_TO_DELETE=${virtualenv_dir}
        fi
    fi
done

if [ -z "${ENV_DIR_TO_DELETE}" -o -z "${ENV_SYMLINK_TO_DELETE}" ]; then
    echo "Cannot find pyenv virtualenv: ${ENV_TO_DELETE}"
    echo "Exiting without doing anything."
    exit 5
fi

echo "Deleting pyenv virtualenv: ${ENV_TO_DELETE}"
echo "Ready to delete directory: ${ENV_DIR_TO_DELETE}"
echo "Ready to delete symlink:   ${ENV_SYMLINK_TO_DELETE}"

read -p "Do you want to proceed? (yes|no) " yn
case $yn in 
	yes ) echo -n "OK deleting ... "
          rm -rf ${ENV_DIR_TO_DELETE} ${ENV_SYMLINK_TO_DELETE}
          RM_STATUS=$#
          echo "Done."
          exit ${RM_STATUS}
          ;;
	no  ) echo "Exiting without doing anything."
          exit 5
          ;;
	*   ) echo "Exiting without doing anything."
          exit 6
          ;;
esac
