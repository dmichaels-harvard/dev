#!/bin/bash
# --------------------------------------------------------------------------------------------------
# My simple common find tool.
# usage: f.sh search_string [file_pattern] [--dryrun] [--exclude directory_names_to_exclude...]
# --------------------------------------------------------------------------------------------------

function usage() {
    echo "usage: f.sh search_string [file_pattern] [--exclude directory_names_to_exclude...]"
    exit 1
}

GREP='fgrep'
SEARCH_FOR=
FILE_PATTERN=
EXCLUDE_OPTION=
EXCLUDE_DIRS=
DRYRUN=
DEBUG=

while [ $# -gt 0 ]; do
    if [ "$1" = "--help" -o "$1" = "-help" ]; then
        usage
    elif [ "$1" = "--dryrun" -o "$1" = "-dryrun" ]; then
        DRYRUN=1
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
    elif [ "$1" = "--exclude" -o "$1" = "-exclude" -o "$1" = "--excludes" -o "$1" = "-excludes" -o "$1" = "-x" ]; then
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

COMMAND="find . -type f $EXCLUDE_DIRS $FILE_PATTERN -exec $GREP -H \"$SEARCH_FOR\" {} \;"

if [ ! -z $DEBUG ]; then
    echo "SEARCH_FOR:[${SEARCH_FOR}]"
    echo "FILE_PATTERN:[${FILE_PATTERN}]"
    echo "EXCLUDE_DIRS:[${EXCLUDE_DIRS}]"
    echo "DRYRUN:[${DRYRUN}]"
    echo "COMMAND:[${COMMAND}]"
    exit 1
fi

if [ ! -z $DRYRUN ]; then
    echo "DRYRUN: $COMMAND"
    exit 0
fi

echo "RUN: $COMMAND"
      eval $COMMAND

exit 0
