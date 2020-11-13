#!/usr/bin/env python3

import subprocess
from .shared_values import client, OUTPUT_RESOURCE_NAME, PIPELINE_NAME, WORKING_DIR

reason = PIPELINE_NAME
resource = OUTPUT_RESOURCE_NAME


print("Delete previous resource")
client.delete_resource(resource)

print("Making processing job log files readable so they can be pushed into database.")
subprocess.call(["chmod", "--recursive", "a+r", WORKING_DIR])

print("Putting new data into DB.")
client.upload_resource_filepath(resource, WORKING_DIR, reason, use_http=False)

print("Removing working_dir: ", WORKING_DIR)
subprocess.call(["rm", "-rf", WORKING_DIR])
