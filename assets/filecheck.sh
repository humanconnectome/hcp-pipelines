#!/bin/bash

exists(){
    local file="$1"
    if [ -e "$file" ]; then
        echo "OKAY:  $file"
    else
        echo "ERROR: $file"
        ((missing_files++))
    fi
}

check_all_expected_files_exist(){
    # Replacements in order do the following:
    # * strip comments (#)
    # * remove empty lines
    # * replace {scan} with variable
    # * replace {subjectid} with variable
    # * replace spaces (" ") with path seperator ("/")
    sed -e 's/#.*//' \
        -e '/^\s*$/d' \
        -e 's/{scan}/${SCAN}/g' \
        -e 's/{subjectid}/${SESSION}/g' \
        -e 's# #/#g' \
        $EXPECTED_FILE_LIST \
        | while read line; do

       # eval is being used to allow advanced glob patterns
       eval "exists $line"
    done
}

script_dir=$(dirname "$0")
PIPELINE_NAME="$1"
SESSION="$2"
SCAN="$3"
EXPECTED_FILE_LIST="${script_dir}/expected_files/${PIPELINE_NAME}.txt"
missing_files=0
check_all_expected_files_exist
export missing_files

if [ $missing_files -ne 0 ] ; then
    echo "File Check was unsuccessful."
    exit 1
else
    echo "All expected files are present."
    exit 0
fi

