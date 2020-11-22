import subprocess
import os
from pathlib import Path

from util import escape_path, keep_resting_state_scans, is_unreadable


def original_sed_command(text):
    cmd = "sed -e 's/[\\/&]/\\\\&/g'"
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, text=True, input=text, shell=True
    )
    return result.stdout


def test_escape_path():
    query = r"/one\two/three&four/"
    actual = escape_path(query)
    expected = original_sed_command(query)
    # expected = "\\/one\\\\two\\/three\\&four\\/"

    assert actual == expected


def test_resting_state():
    original = ["rfMRI_REST", "tfMRI_EMOTION", "fMRI_CARIT"]
    expected = ["rfMRI_REST"]
    assert keep_resting_state_scans(original) == expected


def test_is_readable():
    testname = "__temporary_file__"
    p = Path(testname)
    assert is_unreadable(testname) == True
    p.touch()
    assert is_unreadable(testname) == False
    p.chmod(0o333)
    assert is_unreadable(testname) == True
    p.chmod(0o777)
    assert is_unreadable(testname) == False
    p.unlink()
    assert is_unreadable(testname) == True


def test_is_readable_dir():
    testname = "__temporary_dir__"
    assert is_unreadable(testname) == True
    os.makedirs(testname, exist_ok=True)
    p = Path(testname)
    assert is_unreadable(testname) == False
    p.chmod(0o333)
    assert is_unreadable(testname) == True
    p.rmdir()
