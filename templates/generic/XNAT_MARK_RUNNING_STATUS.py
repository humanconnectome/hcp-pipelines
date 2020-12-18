#!/usr/bin/env python3
import argparse
import os
import subprocess
from shared_values import client


g_resource = "RunningStatus"


directory = f"{{BUILD_DIR}}/{{PROJECT}}/{{ PIPELINE_NAME }}.{{SUBJECT}}_{{CLASSIFIER}}{{_SCAN}}_RUNNING_STATUS"
file = f"{{ PIPELINE_NAME }}.{{SUBJECT}}_{{CLASSIFIER}}{{_SCAN}}.RUNNING"
existing_file = f"{{ARCHIVE_ROOT}}/{{ PROJECT }}/arc001/{{SESSION}}/RESOURCES/RunningStatus/{file}"
path = f"{directory}/{file}"

parser = argparse.ArgumentParser("Set up a running status file")
parser.add_argument("--status", choices=["queued", "done"], default="done")

if __name__ == "__main__":
    args = parser.parse_args()
    reason = args.status

    if reason == "queued":
        os.makedirs(directory, exist_ok=True)
        with open(path, "w") as fd:
            fd.write(f"Reason: {reason}")
        client.upload_resource_filepath(g_resource, directory, reason)
        subprocess.call(["rm", "-rf", directory])
    else:
        if os.path.exists(existing_file):
            client.remove_resource_filepath(g_resource, file)
