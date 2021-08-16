#!/usr/bin/env python3

import subprocess
from shared_values import (
    get_xnat_client,
    OUTPUT_RESOURCE_NAME,
    PIPELINE_NAME,
    WORKING_DIR,
    CLEAN_DATA_DIR,
    print_system_info,
)

reason = PIPELINE_NAME
resource = OUTPUT_RESOURCE_NAME
client = get_xnat_client()


print_system_info()

print("Delete previous resource")
client.delete_resource(resource)

print("Making processing job log files readable so they can be pushed into database.")
subprocess.call(["chmod", "--recursive", "a+r", CLEAN_DATA_DIR])

print("Putting new data into DB.")
client.upload_resource_filepath(resource, CLEAN_DATA_DIR, reason, use_http=False)

print("Removing working_dir: ", WORKING_DIR)
subprocess.call(["rm", "-rf", WORKING_DIR])

print("Removing clean_data_dir: ", CLEAN_DATA_DIR)
subprocess.call(["rm", "-rf", CLEAN_DATA_DIR])
