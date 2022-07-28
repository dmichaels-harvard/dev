#!/bin/bash
# --------------------------------------------------------------------------------------------------
# My personal simple common find tool.
# Case-insensitive and/or as-word versions are in: ff.sh, fw.sh, ffw.sh
#
# usage: f.sh search_string
#             [file_pattern]
#             [directory]
#             [--search search_string]
#             [--dir directory]
#             [--text]
#             [--python]
#             [--list]
#             [--num]
#             [--symlinks]
#             [--exclude directory_names_to_exclude...]
#             [--vi]
#             [--quiet]
#             [--dryrun]
#             [--verbose]
#             [--debug]
#
# search_string: search pattern to find within files.
# file_pattern:  find only within files with names matching this.
# directory:     find from given directory rather than default current (.) directory.
# --search:      same as search_string (above).
# --file:        same as file_pattern (above).
# --dir:         same as directory (above).
# --text:        turns on grep -I option which skips binary files.
# --python:      shorthand for file_pattern of '*.py'.
# --list:        turns on grep -l option to only list file names/paths matched.
# --num:         turns on grep -n option to include line numbers.
# --symlinks:    follow symlinks.
# --exclude:     list one or more directory names to skip in the search.
# --vi:          redirects output to temporary file and invokes the vim editor with that.
# --dryrun:      to just to see the find command that would be run.
# --verbose:     causes the full path of every file navigated to be printed. 
# --debug:       turns on any debugging output for troubleshooting.
# --------------------------------------------------------------------------------------------------

THIS_SCRIPT_NAME=`basename $0`

function usage() {
    echo "usage: ${THIS_SCRIPT_NAME}"
    echo "       search_string [file_pattern] [directory]"
    echo "       [--dir directory]"
    echo "       [--text]"
    echo "       [--python]"
    echo "       [--list]"
    echo "       [--num]"
    echo "       [--symlinks]"
    echo "       [--exclude directory_names_to_exclude...]"
    echo "       [--vi]"
    echo "       [--quiet]"
    echo "       [--dryrun]"
    echo "       [--verbose]"
    echo "       [--debug]"
    exit 1
}

GREP='grep'
DIRECTORY=.
TEXT_FILES_ONLY=
SEARCH_STRING=
FILE_PATTERN=
EXCLUDE_DIRS=
LIST_FILES_ONLY=
LINE_NUMBERS=
FIND_FOLLOW_SYMLINKS=
DRYRUN=
QUIET=
VERBOSE=
DEBUG=
VIM=

while [ $# -gt 0 ]; do
    if [ "$1" = "--help" -o "$1" = "-help" ]; then
        usage
    elif [ "$1" = "--search" -o "$1" = "-search" ]; then
        if [ $# -eq 1 ]; then
            usage
        fi
        SEARCH_STRING=$2
        shift 2
    elif [ "$1" = "--files" -o "$1" = "-files" -o "$1" = "--file" -o "$1" = "-file" -o "$1" = "--f" -o "$1" = "-f" ]; then
        if [ $# -eq 1 ]; then
            usage
        fi
        FILE_PATTERN="-name \"$2\""
        shift 2
    elif [ "$1" = "--directory" -o "$1" = "-directory" -o "$1" = "--dir" -o "$1" = "-dir" -o "$1" = "--d" -o "$1" = "-d" ]; then
        if [ $# -eq 1 ]; then
            usage
        fi
        DIRECTORY=$2
        shift 2
    elif [ "$1" = "--dryrun" -o "$1" = "-dryrun" -o "$1" = "--dry" -o "$1" = "-dry" ]; then
        DRYRUN=1
        shift 1
    elif [ "$1" = "--quiet" -o "$1" = "-quiet" -o "$1" = "--q" -o "$1" = "-q" ]; then
        QUIET=1
        shift 1
    elif [ "$1" = "--vim" -o "$1" = "-vim" -o "$1" = "--vi" -o "$1" = "-vi" ]; then
        VIM=1
        QUIET=1
        shift 1
    elif [ "$1" = "--verbose" -o "$1" = "-verbose" ]; then
        VERBOSE='-print'
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
    elif [ "$1" = "--num" -o "$1" = "-num" -o "$1" = "--n" -o "$1" = "-n" ]; then
        LINE_NUMBERS="-n"
        shift 1
    elif [ "$1" = "--symlinks" -o "$1" = "-symlinks" -o "$1" = "--symlink" -o "$1" = "-symlink" -o "$1" = "--s" -o "$1" = "-s" ]; then
        FIND_FOLLOW_SYMLINKS="-L"
        shift 1
    elif [ "$1" = "--python" -o "$1" = "-python" -o "$1" = "--py" -o "$1" = "-py" ]; then
        #
        # Just a shortcut for specifying "*.py" for the file pattern.
        #
        FILE_PATTERN="-name \"*.py\""
        shift 1
    elif [ "$1" = "--excludes" -o "$1" = "-excludes" -o "$1" = "--exclude" -o "$1" = "-exclude" -o "$1" = "--x"  -o "$1" = "-x" ]; then
        #
        # Get the directories to exclude from the find.
        #
        if [ $# -eq 1 ]; then
            usage
        fi
        shift 1
        while [ $# -gt 0 ]; do
            #
            # If we get any known options while doing this, i.e. while
            # collecting directories to exclude, then break out of this.
            #
            if [ "$1" = "--help" -o "$1" = "-help" \
              -o "$1" = "--search" -o "$1" = "-search" \
              -o "$1" = "--directory" -o "$1" = "-directory" -o "$1" = "--dir" -o "$1" = "-dir" -o "$1" = "--d" -o "$1" = "-d" \
              -o "$1" = "--file" -o "$1" = "-file" -o "$1" = "--file" -o "$1" = "-file" -o "$1" = "--f" -o "$1" = "-f" \
              -o "$1" = "--dryrun" -o "$1" = "-dryrun" -o "$1" = "--dry" -o "$1" = "-dry" \
              -o "$1" = "--quiet" -o "$1" = "-quiet" -o "$1" = "--q" -o "$1" = "-q" \
              -o "$1" = "--vim" -o "$1" = "-vim" -o "$1" = "--vi" -o "$1" = "-vi" -o "$1" = "--v" -o "$1" = "-v" \
              -o "$1" = "--debug" -o "$1" = "-debug" \
              -o "$1" = "--grep" -o "$1" = "-grep" \
              -o "$1" = "--text" -o "$1" = "-text" -o "$1" = "--t" -o "$1" = "-t" \
              -o "$1" = "--list" -o "$1" = "-list" -o "$1" = "--l" -o "$1" = "-l" \
              -o "$1" = "--num" -o "$1" = "-num" -o "$1" = "--n" -o "$1" = "-n" \
              -o "$1" = "--symlinks" -o "$1" = "-symlinks" -o "$1" = "--symlink" -o "$1" = "-symlink" -o "$1" = "--s" -o "$1" = "-s" \
              -o "$1" = "--python" -o "$1" = "-python" -o "$1" = "--py" -o "$1" = "-py" \
              -o "$1" = "--excludes" -o "$1" = "-excludes" -o "$1" = "--exclude" -o "$1" = "-exclude" -o "$1" = "--x"  -o "$1" = "-x" ]; then
                break
            elif [[ "$1" == */ ]]; then
                #
                # Just in case they type directory name with trailing slash (can easily happen).
                #
                EXCLUDE_ARG=${1:0:$((${#1}-1))}
            else
                EXCLUDE_ARG=$1
            fi
            #
            # Odd syntax for this directory exclusion thing, but seems to work.
            #
            EXCLUDE_DIRS="$EXCLUDE_DIRS -not -path '*/$EXCLUDE_ARG/*'"
            shift 1
        done
    else
        if [ -z "$SEARCH_STRING" ]; then
            SEARCH_STRING=$1
        elif [ -z "$FILE_PATTERN" ]; then
            FILE_PATTERN="-name \"$1\""
        elif [ -z "$DIRECTORY" -o "$DIRECTORY" = "." ]; then
            DIRECTORY=$1
        else
            usage
        fi
        shift 1
    fi
done

if [ -z "$SEARCH_STRING"  ]; then
    usage
fi

COMMAND="find $FIND_FOLLOW_SYMLINKS $DIRECTORY $VERBOSE -type f $EXCLUDE_DIRS $FILE_PATTERN -exec $GREP $LIST_FILES_ONLY $TEXT_FILES_ONLY $LINE_NUMBERS -H \"$SEARCH_STRING\" {} \;"
COMMAND=`echo $COMMAND | tr -s ' '`

if [ ! -z $DEBUG ]; then
    echo "SEARCH_STRING:[${SEARCH_STRING}]"
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
    rm $TMPFILE
    exit 0
fi

eval $COMMAND

exit 0
