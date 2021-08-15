import subprocess

# Import path modification
import sys
from pathlib import Path

sys.path.append('{{ PYTHON_IMPORT_DIR }}')

# Path modification (above) must occur before
# these imports below. Otherwise, you'll get a "ModuleNotFoundError".
from xnat_file_client import XnatFileClient

OUTPUT_RESOURCE_NAME = "{{ OUTPUT_RESOURCE_NAME }}"
PIPELINE_NAME = "{{ PIPELINE_NAME }}"
RESOURCES_ROOT = Path("{{ RESOURCES_ROOT }}")
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

def get_xnat_client():
    return XnatFileClient(project, subject, session, serverlist, credentials_file)

def print_system_info():
    platform = subprocess.check_output(["uname", "-a"]).decode()
    print(f" Platform:   {platform}")
