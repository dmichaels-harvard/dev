#!/bin/bash
# ----------------------------------------------------------------------------------------------------------------------
# Encrypt or decrypt a file with a simple password, optionally in-place.
# The encrypt.sh and decrypt.sh scripts should be the same/sym-linked.
#
# usage: encrypt.sh file
#        derypt.sh file
#
# Adapted this from:
# https://superuser.com/questions/370388/simple-built-in-way-to-encrypt-and-decrypt-a-file-on-a-mac-via-command-line
# ----------------------------------------------------------------------------------------------------------------------

THIS_SCRIPT_NAME=`basename $0`

if [ ${THIS_SCRIPT_NAME} == "encrypt.sh" ]; then
    ENCRYPTING=1
elif [ ${THIS_SCRIPT_NAME} == "decrypt.sh" ]; then
    ENCRYPTING=
else
    echo "This script must be named encrypt.sh or decrypt.sh!"
    exit 9
fi

if [ $# -ne 1 ]; then
    if [ ${ENCRYPTING} ]; then
        echo "usage: ${THIS_SCRIPT_NAME} file-to-encrypt"
    else
        echo "usage: ${THIS_SCRIPT_NAME} file-to-decrypt"
    fi
    exit 1
fi

FILE=$1

if [ ! -f "${FILE}" ]; then
    echo "${THIS_SCRIPT_NAME}: File does not exist ($FILE)."
    exit 2
fi

if [ ${ENCRYPTING} ]; then
    ENCRYPTED_FILE=`mktemp`
    openssl aes-256-cbc -pbkdf2 -a -e -salt -in "${FILE}" -out "${ENCRYPTED_FILE}"
    STATUS=$?
    if [ ! ${STATUS} -eq 0 ]; then
        echo "Encryption error!"
        exit 3
    fi
    read -p "Replace file with the encrypted one in place? (yes|no) " yn
    case $yn in 
        yes )
            mv ${ENCRYPTED_FILE} ${FILE}
            ;;
        * )
            echo "Encrypted file is here: ${ENCRYPTED_FILE}"
            ;;
    esac
    exit 0
fi

if [ -z ${ENCRYPTING} ]; then
    DECRYPTED_FILE=`mktemp`
    openssl aes-256-cbc -pbkdf2 -a -d -salt -in "${FILE}" -out "${DECRYPTED_FILE}"
    STATUS=$?
    if [ ! ${STATUS} -eq 0 ]; then
        echo "Decryption error!"
        exit 3
    fi
    read -p "Replace file with the decrypted one in place? (yes|no) " yn
    case $yn in 
        yes )
            mv ${DECRYPTED_FILE} ${FILE}
            ;;
        * )
            echo "Decrypted file is here: ${DECRYPTED_FILE}"
            ;;
    esac
    exit 0
fi
