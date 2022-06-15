#!/bin/bash
# --------------------------------------------------------------------------------------------------
# My very simple common find tool.
# Ignore-case and/or as-word versions are in: ff.sh, fw.sh, ffw.sh
#
# usage: f.sh search_string [file_pattern]
#             [--text]
#             [--list]
#             [--num]
#             [--dryrun]
#             [--quiet]
#             [--exclude directory_names_to_exclude...]
#
# The --text option turns on the grep -I option which skips binary files.
# The --list option turns on the grep -l option which only lists file names/paths matched.
# The --num option turns on the grep -n option which includes line numbers.
# The --exclude option can be used to list one or more directory names to skip in the search.
# The --dryrun option can be used to just to see the find command that would be run.
# --------------------------------------------------------------------------------------------------

THIS_SCRIPT_NAME=`basename $0`

function usage() {
    echo "usage: ${THIS_SCRIPT_NAME}"
    echo "       search_string [file_pattern]"
    echo "       [--text]"
    echo "       [--list]"
    echo "       [--num]"
    echo "       [--dryrun]"
    echo "       [--exclude directory_names_to_exclude...]"
    exit 1
}

GREP='grep'
TEXT_FILES_ONLY=
SEARCH_FOR=
FILE_PATTERN=
EXCLUDE_OPTION=
EXCLUDE_DIRS=
LIST_FILES_ONLY=
LINE_NUMBERS=
DRYRUN=
QUIET=
DEBUG=
VIM=

while [ $# -gt 0 ]; do
    if [ "$1" = "--help" -o "$1" = "-help" ]; then
        usage
    elif [ "$1" = "--dryrun" -o "$1" = "-dryrun" ]; then
        DRYRUN=1
        shift 1
    elif [ "$1" = "--quiet" -o "$1" = "-quiet" -o "$1" = "--q" -o "$1" = "-q" ]; then
        QUIET=1
        shift 1
    elif [ "$1" = "--vi" -o "$1" = "-vi" -o "$1" = "--vim" -o "$1" = "-vim" ]; then
        VIM=1
        QUIET=1
        shift 1
    elif [ "$1" = "--debug" -o "$1" = "-debug" ]; then
        DEBUG=1
        shift 1
    elif [ "$1" = "--grep" -o "$1" = "-grep" ]; then
        if [ $# -eq 1 ]; then
            usage
        fi
        GREP=$2
        shift 2
    elif [ "$1" = "--text" -o "$1" = "-text" -o "$1" = "--t" -o "$1" = "-t" ]; then
        TEXT_FILES_ONLY="-I"
        shift 1
    elif [ "$1" = "--list" -o "$1" = "-list" -o "$1" = "--l" -o "$1" = "-l" ]; then
        LIST_FILES_ONLY='-l'
        shift 1
    elif [ "$1" = "--num" -o "$1" = "--um" -o "$1" = "--n" -o "$1" = "-n" ]; then
        LINE_NUMBERS="-n"
        shift 1
    elif [ "$1" = "--py" -o "$1" = "-py" ]; then
        #
        # Just a shortcut for specifying "*.py" for the file pattern.
        #
        FILE_PATTERN="-name \"*.py\""
        shift 1
    elif [ "$1" = "--exclude" -o "$1" = "-exclude" -o "$1" = "--excludes" -o "$1" = "-excludes" -o "$1" = "--x"  -o "$1" = "-x" ]; then
        #
        # Get the directories to exclude from the find.
        #
        if [ $# -eq 1 ]; then
            usage
        fi
        shift 1
        while [ $# -gt 0 ]; do
            #
            # Special case allow --dryrun or --debug within --exclude list.
            #
            if [ "$1" = "--dryrun" -o "$1" = "-dryrun" ]; then
                DRYRUN=1
                shift 1
                continue
            elif [ "$1" = "--debug" -o "$1" = "-debug" ]; then
                DEBUG=1
                shift 1
                continue
            elif [[ "$1" == */ ]]; then
                #
                # Just in case they type directory name with trailing slash (can easily happen).
                #
                EXCLUDE_ARG=${1:0:$((${#1}-1))}
            else
                EXCLUDE_ARG=$1
            fi
            #
            # Odd syntax for this but seems to work.
            #
            EXCLUDE_DIRS="$EXCLUDE_DIRS -not -path '*/$EXCLUDE_ARG/*'"
            shift 1
        done
    else
        if [ -z "$SEARCH_FOR" ]; then
            SEARCH_FOR=$1
        elif [ -z "$FILE_PATTERN" ]; then
            FILE_PATTERN="-name \"$1\""
        else
            usage
        fi
        shift 1
    fi
done

if [ -z "$SEARCH_FOR"  ]; then
    usage
fi

COMMAND="find . -type f $EXCLUDE_DIRS $FILE_PATTERN -exec $GREP $LIST_FILES_ONLY $TEXT_FILES_ONLY $LINE_NUMBERS -H \"$SEARCH_FOR\" {} \;"
COMMAND=`echo $COMMAND | tr -s ' '`

if [ ! -z $DEBUG ]; then
    echo "SEARCH_FOR:[${SEARCH_FOR}]"
    echo "FILE_PATTERN:[${FILE_PATTERN}]"
    echo "EXCLUDE_DIRS:[${EXCLUDE_DIRS}]"
    echo "TEXT_FILES_ONLY:[${TEXT_FILES_ONLY}]"
    echo "DRYRUN:[${DRYRUN}]"
    echo "COMMAND:[${COMMAND}]"
    exit 1
fi

if [ ! -z $DRYRUN ]; then
    echo "DRYRUN: $COMMAND"
    exit 0
fi

if [ -z $QUIET ]; then
    echo "RUN: $COMMAND"
fi

if [ ! -z $VIM ]; then
    TMPFILE=/tmp/tmp-f.sh-$$
    eval $COMMAND > $TMPFILE 2>&1
    vi $TMPFILE
    exit 0
fi

eval $COMMAND

exit 0
