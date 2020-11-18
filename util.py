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


def qsub(cmd, prior_job=None, afterok=True):
    if cmd is None:
        return prior_job

    if prior_job is None:
        full_cmd = f"qsub {cmd}"
    else:
        afterok = "afterok" if afterok else "afterany"
        full_cmd = f"qsub -W depend={afterok}:{prior_job} {cmd} "
    jobnumb = shell_run(full_cmd)
    return jobnumb
