import subprocess

# Import path modification
import sys
from pathlib import Path

sys.path.append("{{ PYTHON_IMPORT_DIR }}")

# Path modification (above) must occur before
# these imports below. Otherwise, you'll get a "ModuleNotFoundError".
from xnat_file_client import XnatFileClient

OUTPUT_RESOURCE_NAME = "{{ OUTPUT_RESOURCE_NAME }}"
PIPELINE_NAME = "{{ PIPELINE_NAME }}"
RESOURCES_ROOT = Path("{{ RESOURCES_ROOT }}")
CHECK_DATA_DIR = Path("{{ CHECK_DATA_DIR }}")
WORKING_DIR = Path("{{ WORKING_DIR }}")

project = "{{ PROJECT }}"
subject = "{{ SUBJECT }}"
classifier = "{{ CLASSIFIER }}"
extra = "{{ SCAN }}"
session = "{{ SESSION }}"
g_scan = "{{ _SCAN }}"


def print_system_info():
    platform = subprocess.check_output(["uname", "-a"]).decode()
    print(f" Platform:   {platform}")
