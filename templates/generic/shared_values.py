import subprocess

# Import path modification
import sys
sys.path.append('{{ PYTHON_IMPORT_DIR }}')

# Path modification (above) must occur before
# these imports below. Otherwise, you'll get a "ModuleNotFoundError".
from ccf.archive import CcfArchive
from xnat_file_client import XnatFileClient

OUTPUT_RESOURCE_NAME = "{{ OUTPUT_RESOURCE_NAME }}"
PIPELINE_NAME = "{{ PIPELINE_NAME }}"
ARCHIVE_ROOT = "{{ ARCHIVE_ROOT }}"
CHECK_DATA_DIR = "{{ CHECK_DATA_DIR }}"
WORKING_DIR = "{{ WORKING_DIR }}"
CLEAN_DATA_DIR = "{{ CLEAN_DATA_DIR }}"
EXPECTED_FILES_LIST = "{{ EXPECTED_FILES_LIST }}"

serverlist = "{{ PUT_SERVER_LIST }}"
server = "{{ PUT_SERVER }}"
project = "{{ PROJECT }}"
subject = "{{ SUBJECT }}"
classifier = "{{ CLASSIFIER }}"
extra = "{{ SCAN }}"
session = "{{ SESSION }}"
credentials_file = "{{ XNAT_CREDENTIALS_FILE }}"
g_scan = "{{ _SCAN }}"

client = XnatFileClient(project, subject, session, serverlist, credentials_file)
archive = CcfArchive(project, session, ARCHIVE_ROOT)
resources_root = archive.SESSION_RESOURCES


def print_system_info():
    platform = subprocess.check_output(["uname", "-a"]).decode()
    print(f" Platform:   {platform}")
