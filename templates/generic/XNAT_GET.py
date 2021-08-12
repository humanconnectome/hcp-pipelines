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
from ccf.get_cinab_style_data import PipelinePrereqDownloader

print_system_info()
tmp_dir = f"{WORKING_DIR}/tmp"
os.makedirs(tmp_dir, exist_ok=True)
os.makedirs(f"{WORKING_DIR}/{session}", exist_ok=True)

prereq = PipelinePrereqDownloader(
    project,
    subject,
    classifier,
    extra,
    log=False,
    output_dir=tmp_dir,
    ARCHIVE_ROOT=ARCHIVE_ROOT,
)
prereq.get_data_for_pipeline(PIPELINE_NAME, extra)

# {% block post %}
print("Remove metadata")
os.system(
    f'find  {tmp_dir} -maxdepth 1 -not -type d -delete'
)


print("Moving files")
os.system(
    f'find  {tmp_dir}/{session}/* -maxdepth 0 -type d ! -name "ProcessingInfo" -exec mv {"{}"} {WORKING_DIR}/{session} \;'
)

print("Removing tmp dir")
os.system(f"rm -r {tmp_dir}")
# {% endblock post %}
