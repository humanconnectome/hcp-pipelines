import os
import subprocess


def escape_path(text):
    return text.replace("\\", "\\\\").replace("/", "\\/").replace("&", "\\&")


def keep_resting_state_scans(scans):
    return [x for x in scans if not (x.startswith("t") or x.startswith("f"))]


def shell_run(cmd):
    return subprocess.check_output(cmd, shell=True, universal_newlines=True).strip()
    # result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    # print(result.returncode, result.stdout, result.stderr)
    # return None;


def is_unreadable(filename):
    return not os.access(filename, os.R_OK)
