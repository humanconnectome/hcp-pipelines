import subprocess

from util import escape_path, keep_resting_state_scans


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
