#!{{ PYTHON }}
import argparse
import os
import subprocess
from shared_values import get_xnat_client, RESOURCES_ROOT, project, subject, session


client = get_xnat_client()
g_resource = "RunningStatus"


directory = (
    f"{{BUILD_DIR}}/{{PROJECT}}/{{ PIPELINE_NAME }}.{{SESSION}}{{_SCAN}}_RUNNING_STATUS"
)
file = f"{{ PIPELINE_NAME }}.{{SESSION}}{{_SCAN}}.RUNNING"
existing_file = RESOURCES_ROOT / "RunningStatus" / file
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

        ### The step above sometimes doesn't successfully update the catalog
        client.refresh_catalog(project, subject, session, g_resource)
    else:
        if os.path.exists(existing_file):
            client.remove_resource_filepath(g_resource, file)
