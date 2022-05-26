#!/bin/bash
# --------------------------------------------------------------------------------------------------
# My simple common find tool. This one is case-insensitive.
# usage: ff.sh search_string [file_pattern] [--dryrun] [--exclude directory_names_to_exclude...]
# --------------------------------------------------------------------------------------------------

~/bin/f.sh --grep 'fgrep -i' "$@"
