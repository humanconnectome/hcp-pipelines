import logging
import os
import subprocess
import shlex


def escape_path(text):
    return text.replace("\\", "\\\\").replace("/", "\\/").replace("&", "\\&")


def keep_resting_state_scans(scans):
    return [x for x in scans if not (x.startswith("t") or x.startswith("f"))]


def shell_run(cmd):
    """
    Run a shell command and log stdout and stderr.

    Source: https://stackoverflow.com/a/21953948/11953415
    """
    logger = logging.getLogger("shell_run")
    logger.info('running subprocess: %s', cmd)
    command_line_args = shlex.split(cmd)
    try:
        command_line_process = subprocess.Popen(
            command_line_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = command_line_process.communicate()
        logger.info("stdout:\n--------------------\n%s", stdout.decode())
    except (OSError, subprocess.CalledProcessError) as exception:
        logger.critical('Exception occured: ' + str(exception))
        logger.warning('Subprocess failed.')
        return False
    else:
        # no exception was raised
        logger.info('Subprocess finished.')

    return True


def is_unreadable(filename):
    return not os.access(filename, os.R_OK)
