#!/usr/bin/env python3

import os
from ccf.get_cinab_style_data import PipelinePrereqDownloader
from shared_values import (
    project,
    subject,
    classifier,
    extra,
    PIPELINE_NAME,
    ARCHIVE_ROOT,
    session,
    WORKING_DIR,
)

tmp_dir = f"{WORKING_DIR}/tmp"
os.makedirs(tmp_dir, exist_ok=True)
os.makedirs(f"{WORKING_DIR}/{session}", exist_ok=True)

prereq = PipelinePrereqDownloader(
    project,
    subject,
    classifier,
    extra,
    copy=False,
    log=False,
    output_dir=tmp_dir,
    ARCHIVE_ROOT=ARCHIVE_ROOT,
)
prereq.get_data_for_pipeline(PIPELINE_NAME, remove_non_subdirs=True)

# {% block post %}
print("Moving files")
os.system(
    f'find  {tmp_dir}/{session}/* -maxdepth 0 -type d ! -name "ProcessingInfo" -exec mv {"{}"} {WORKING_DIR}/{session} \;'
)

print("Removing tmp dir")
os.system(f"rm -r {tmp_dir}")
# {% endblock post %}
