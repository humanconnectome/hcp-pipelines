#!/usr/bin/env python3

import subprocess
import sys

from shared_values import (
    get_xnat_client,
    OUTPUT_RESOURCE_NAME,
    PIPELINE_NAME,
    WORKING_DIR,
    CLEAN_DATA_DIR,
    print_system_info,
    CLOBBER_RESOURCE,
    RESOURCES_ROOT,
)

reason = PIPELINE_NAME
resource = OUTPUT_RESOURCE_NAME
client = get_xnat_client()

print_system_info()

if client.resource_exists(resource):
    if CLOBBER_RESOURCE:
        print("Deleting existing resource from prior run.")
        client.delete_resource(resource, RESOURCES_ROOT)
    else:
        print(f"WARN: The resource {resource} already exists. To force overwrite set `CLOBBER_RESOURCE=True` in shared_values.py")
        print("Terminating early.")
        sys.exit(0)

print("Making processing job log files readable so they can be pushed into database.")
subprocess.call(["chmod", "--recursive", "a+r", str(CLEAN_DATA_DIR)])

print("Putting new data into DB.")
client.upload_resource_filepath(resource, str(CLEAN_DATA_DIR), reason, use_http=False)

#{% if DELETE_DATA_AFTER_PUT %}
print("Removing working_dir: ", str(WORKING_DIR))
subprocess.call(["rm", "-rf", str(WORKING_DIR)])

print("Removing clean_data_dir: ", str(CLEAN_DATA_DIR))
subprocess.call(["rm", "-rf", str(CLEAN_DATA_DIR)])
#{% endif %}
