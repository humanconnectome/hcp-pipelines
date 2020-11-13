#!/usr/bin/env python3

import os

from ccf.get_cinab_style_data import PipelinePrereqDownloader
from ccf.one_subject_completion_xnat_checker import OneSubjectCompletionXnatChecker
from .shared_values import (
    client,
    project,
    subject,
    classifier,
    extra,
    OUTPUT_RESOURCE_NAME,
    PIPELINE_NAME,
    XNAT_PBS_JOBS_ARCHIVE_ROOT,
    HCP_RUN_UTILS,
    XNAT_PBS_JOBS,
    CHECK_DATA_DIR,
    session, WORKING_DIR,
)

completion_checker = OneSubjectCompletionXnatChecker(
    project,
    extra,
    session,
    OUTPUT_RESOURCE_NAME,
    PIPELINE_NAME,
    HCP_RUN_UTILS,
    XNAT_PBS_JOBS,
    XNAT_PBS_JOBS_ARCHIVE_ROOT,
)

tmp_dir = f"{WORKING_DIR}/tmp"
os.makedirs(tmp_dir, exist_ok=True)
os.makedirs(f"{WORKING_DIR}/{session}", exist_ok=True)

prereq = PipelinePrereqDownloader(project, subject, classifier, extra, copy=False, log=False, output_dir=tmp_dir, XNAT_PBS_JOBS_ARCHIVE_ROOT=XNAT_PBS_JOBS_ARCHIVE_ROOT)
prereq.get_data_for_pipeline(PIPELINE_NAME, remove_non_subdirs=True)

#{% block post %}
print("Moving files")
os.system(f'find  {tmp_dir}/{session}/* -maxdepth 0 -type d ! -name "ProcessingInfo" -exec mv {"{}"} {WORKING_DIR}/{session} \;')

print("Removing tmp dir")
os.system(f"rm -r {tmp_dir}")
#{% endblock post %}
