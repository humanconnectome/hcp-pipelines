#!/usr/bin/env python3

import os
from shared_values import (
    get_xnat_client,
    project,
    subject,
    classifier,
    extra,
    OUTPUT_RESOURCE_NAME,
    PIPELINE_NAME,
    CHECK_DATA_DIR,
    session,
    EXPECTED_FILES_LIST,
    print_system_info,
    RESOURCES_ROOT,
)
from check import is_processing_complete

client = get_xnat_client()
script_name = f"{PIPELINE_NAME}.XNAT_CHECK"
log_filename = f"{subject}_{classifier}.{script_name}.log"
log_filepath = CHECK_DATA_DIR / log_filename
success_filename = f"{subject}_{classifier}.{script_name}.success"
success_filepath = CHECK_DATA_DIR / success_filename
dest_dir = f"{session}/ProcessingInfo"

print_system_info()
check_cmd_ret_code = is_processing_complete(
    RESOURCES_ROOT,
    extra,
    session,
    OUTPUT_RESOURCE_NAME,
    EXPECTED_FILES_LIST,
    log_filepath,
)
print("Everything OK? ", check_cmd_ret_code)

if check_cmd_ret_code:
    print("Completion Check was successful")
    success_filepath.write_text("Completion Check was successful")
    client.upload_resource_filepath(
        OUTPUT_RESOURCE_NAME,
        success_filepath,
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
    OUTPUT_RESOURCE_NAME,
    str(log_filepath),
    resource_filepath=f"{dest_dir}/{log_filename}",
)
