from ccf.archive import CcfArchive
from xnat_file_client import XnatFileClient

OUTPUT_RESOURCE_NAME = "{{ OUTPUT_RESOURCE_NAME }}"
PIPELINE_NAME = "{{ PIPELINE_NAME }}"
HCP_RUN_UTILS = "{{ HCP_RUN_UTILS }}"
XNAT_PBS_JOBS = "{{ XNAT_PBS_JOBS }}"
XNAT_PBS_JOBS_ARCHIVE_ROOT = "{{ XNAT_PBS_JOBS_ARCHIVE_ROOT }}"
CHECK_DATA_DIR = "{{ CHECK_DATA_DIR }}"
WORKING_DIR = "{{ WORKING_DIR }}"
EXPECTED_FILES_LIST = "{{ EXPECTED_FILES_LIST }}"

serverlist = "{{ XNAT_PBS_JOBS_PUT_SERVER_LIST }}"
server = "{{ PUT_SERVER }}"
project = "{{ SUBJECT_PROJECT }}"
subject = "{{ SUBJECT_ID }}"
classifier = "{{ SUBJECT_CLASSIFIER }}"
extra = "{{ SUBJECT_EXTRA }}"
session = "{{ SUBJECT_SESSION }}"
credentials_file = "{{ XNAT_CREDENTIALS_FILE }}"
g_scan = "{% if SUBJECT_EXTRA %}_{{ SUBJECT_EXTRA }}{% endif %}"

client = XnatFileClient(project, subject, session, serverlist, credentials_file)
archive = CcfArchive(project, session, XNAT_PBS_JOBS_ARCHIVE_ROOT)
resources_root = archive.subject_resources
