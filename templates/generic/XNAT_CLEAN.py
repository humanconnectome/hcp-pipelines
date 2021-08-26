import sys
from pathlib import Path

from shared_values import WORKING_DIR, CLEAN_DATA_DIR, session
from virtual_fs import VirtualFileSystem

fs = VirtualFileSystem()

print("Copy the processing output.")
processing_output = WORKING_DIR / session / "sessions" / session / "hcp" / session
if not processing_output.exists():
    sys.exit(f"ERROR: `processing_output` folder does not exist. {processing_output}")
fs.copy(
    processing_output,
    CLEAN_DATA_DIR
)

print("Remove old files, keep files newer than start_time_file.")
start_time_file = Path("{{ STARTTIME_FILE_NAME }}")
start_time = start_time_file.stat().st_mtime
fs.remove(lambda src, dest: src.stat().st_mtime < start_time)

print("Remove comlogs. Copies available at ProcessingInfo/processing/logs")
comlogs = CLEAN_DATA_DIR / session / "logs/comlogs"
fs.remove(lambda src, dest: comlogs in dest.parents)

print("Copy processing info/logs.")
ProcessingInfo = CLEAN_DATA_DIR / session / "ProcessingInfo"
fs.copy(
    WORKING_DIR / session / "ProcessingInfo",
    CLEAN_DATA_DIR / session
)
fs.copy(
    WORKING_DIR / session / "processing",
    ProcessingInfo
)
fs.copy(
    WORKING_DIR / session / "sessions/specs",
    ProcessingInfo
)
fs.copy(
    WORKING_DIR / session / "info/hcpls",
    ProcessingInfo
)
fs.copy(
    WORKING_DIR / session / "sessions" / session / "session_hcp.txt",
    ProcessingInfo / "processing"
)
fs.copy(
    WORKING_DIR / session / "sessions" / session / "hcpls/hcpls2nii.log",
    ProcessingInfo / "processing"
)

print("Remove XNAT catalogs if any.")
fs.remove(lambda src, dest: dest.name.endswith("_catalog.xml"))

print("Making changes to FileSystem")
fs.sync()