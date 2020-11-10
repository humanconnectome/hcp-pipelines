#!/usr/bin/env python3

import subprocess
from xnat_file_client import XnatFileClient


serverlist = "{{ XNAT_PBS_JOBS_PUT_SERVER_LIST }}"
server = "{{ PUT_SERVER }}"
project = "{{ SUBJECT_PROJECT }}"
subject = "{{ SUBJECT_ID }}"
session = "{{ SUBJECT_SESSION }}"
reason = "{{ PIPELINE_NAME }}"
working_dir = "{{ WORKING_DIR }}"
resource = "{{ OUTPUT_RESOURCE_NAME }}"
credentials_file = "{{ XNAT_CREDENTIALS_FILE }}"

client = XnatFileClient(project, subject, session, serverlist, credentials_file)

print("Delete previous resource")
client.delete_resource(resource)

print("Making processing job log files readable so they can be pushed into database.")
subprocess.call(["chmod", "--recursive", "a+r", working_dir])

print("Putting new data into DB.")
client.upload_resource_filepath(resource, working_dir, reason, use_http=False)

print("Removing working_dir: ", working_dir)
subprocess.call(["rm", "-rf", working_dir])
