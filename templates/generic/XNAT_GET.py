#!/usr/bin/env python3

import os
from shared_values import (
    project,
    subject,
    classifier,
    extra,
    PIPELINE_NAME,
    ARCHIVE_ROOT,
    session,
    WORKING_DIR,
    print_system_info,
)
from ccf.get_cinab_style_data import PipelineResources

print_system_info()
tmp_dir = f"{WORKING_DIR}/tmp"
os.makedirs(tmp_dir, exist_ok=True)
os.makedirs(f"{WORKING_DIR}/{session}", exist_ok=True)

resources = PipelineResources(
    project,
    subject,
    classifier,
    log=False,
    output_dir=tmp_dir,
    ARCHIVE_ROOT=ARCHIVE_ROOT,
)

print('Getting Data...')
# {% block get_data %}
# {% endblock get_data %}

# {% block post %}
print("Removing metadata")
os.system(
    f'find  {tmp_dir} -maxdepth 1 -not -type d -delete'
)


print("Moving files")
os.system(
    f'find  {tmp_dir}/{session}/* -maxdepth 0 -type d ! -name "ProcessingInfo" -exec mv {"{}"} {WORKING_DIR}/{session} \;'
)

print("Moving root directories to location qunex expects it")
destination = f'{WORKING_DIR}/{session}/sessions/{session}/hcp/{session}/'
os.makedirs(destination, exist_ok=True)
os.system(
    "mv %s/{MNINonLinear,T1w,T2w} %s" % (f"{WORKING_DIR}/{session}", destination)
)

print("Removing tmp dir")
os.system(f"rm -r {tmp_dir}")
# {% endblock post %}
