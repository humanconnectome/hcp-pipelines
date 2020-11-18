#!/usr/bin/env python3

import os
from ccf.one_subject_completion_xnat_checker import OneSubjectCompletionXnatChecker
from shared_values import (
    client,
    project,
    subject,
    classifier,
    extra,
    OUTPUT_RESOURCE_NAME,
    PIPELINE_NAME,
    ARCHIVE_ROOT,
    CHECK_DATA_DIR,
    session,
    EXPECTED_FILES_LIST,
    print_system_info,
)


completion_checker = OneSubjectCompletionXnatChecker(
    project,
    extra,
    session,
    OUTPUT_RESOURCE_NAME,
    PIPELINE_NAME,
    ARCHIVE_ROOT,
    EXPECTED_FILES_LIST,
)

g_working_dir = CHECK_DATA_DIR
script_name = f"{PIPELINE_NAME}.XNAT_CHECK"
log_filename = f"{subject}.{classifier}.{script_name}.log"
success_filename = f"{subject}.{classifier}.{script_name}.success"
dest_dir = f"{session}/ProcessingInfo/"

print_system_info()
check_cmd_ret_code = completion_checker.is_processing_complete(log_filename)
print("Everything OK? ", check_cmd_ret_code)

if check_cmd_ret_code:
    print("Completion Check was successful")
    print("Completion Check was successful", file=success_filename)
    client.upload_resource_filepath(
        OUTPUT_RESOURCE_NAME,
        success_filename,
        resource_filepath=f"{dest_dir}/{success_filename}",
    )
else:
    print("Completion Check was unsuccessful")
    if os.path.exists(success_filename):
        os.remove(success_filename)

    client.remove_resource_filepath(
        OUTPUT_RESOURCE_NAME, f"{dest_dir}/{success_filename}"
    )

client.upload_resource_filepath(
    OUTPUT_RESOURCE_NAME, log_filename, resource_filepath=f"{dest_dir}/{log_filename}"
)
