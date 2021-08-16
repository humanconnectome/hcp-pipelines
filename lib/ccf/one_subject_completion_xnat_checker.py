#!/usr/bin/env python3

import os
import re
import sys
from pathlib import Path


def is_processing_complete(
        RESOURCES_ROOT,
        scan,
        session,
        OUTPUT_RESOURCE_NAME,
        EXPECTED_FILES_LIST,
        log_file=None,
):
    if log_file is None:
        output = sys.stdout
    else:
        output = log_file.open("w")

    resource = RESOURCES_ROOT / OUTPUT_RESOURCE_NAME

    # Check if it exists
    if not resource.is_dir():
        print(f"resource: {resource} DOES NOT EXIST", file=output)
        print("Completion Check was unsuccessful", file=output)
        return False

    # check to see if all the expected files exist
    expected_files = filename_list(EXPECTED_FILES_LIST, dict(
        subjectid=(session),
        scan=(scan)
    ))

    success = do_all_files_exist(expected_files, resource / session, output)
    if success:
        print("Completion Check was successful", file=output)
    else:
        print("Completion Check was unsuccessful", file=output)

    if output != sys.stdout:
        output.close()

    return success


def do_all_files_exist(file_name_list, root_dir=None, output=sys.stdout):
    if root_dir is None:
        root_dir = Path("/")

    print("Checking for existence of files. Files that exist are prefaced with OKAY.")
    print("--------------------------------------------------------------------------------")
    all_files_exist = True
    for filename in file_name_list:
        file = root_dir / filename
        if file.exists():
            preface = "OKAY:  "
        else:
            preface = "ERROR: "
            all_files_exist = False
        print(preface, file.absolute(), file=output)

    return all_files_exist


def filename_list(expected_files_list, substitutions):
    """
    Create a list of partial filepaths based on the content of the expected_files_list.

    The content of the expected_files_path should be a list with one filepath per line.
    The parts of the filepath should be seperated with whitespace, not with the "/".
    Placeholders in the fileparts should be contained in curly brackets {}. The substitution
    parameter will be used to replace the placeholders.

    --------

    Suppose the file specified contains the following lines:

        MNINonLinear fsaverage {subjectid}.L.sphere.164k_fs_L.surf.gii # this is a comment
        MNINonLinear fsaverage {subjectid}.R.sphere.164k_fs_R.surf.gii
        # Full line comment
        MNINonLinear Results {scan} brainmask_fs.2.nii.gz
        MNINonLinear Results {scan} {scan}_Atlas.dtseries.nii

    and  substitutions = { "subjectid": "HCA6005242, "scan":"rfMRI_REST2_PA" }

    This would be the result:

        /mydir/MNINonLinear/fsaverage/HCA6005242.L.sphere.164k_fs_L.surf.gii
        /mydir/MNINonLinear/fsaverage/HCA6005242.R.sphere.164k_fs_L.surf.gii
        /mydir/MNINonLinear/Results/rfMRI_REST2_PA/brainmask_fs.2.nii.gz
        /mydir/MNINonLinear/Results/rfMRI_REST2_PA/rfMRI_REST2_PA_Atlas.dtseries.nii

    Notice that:

    * The comments are discarded
    * the correct path separator, '/', has been put where internal whitespace was
    * {subjectid} has been replaced with HCA6005242
    * {scan} has been replaced with rfMRI_REST2_PA
    """
    content = expected_files_list.read_text()

    # remove comments starting with pound sign ('#')
    content = re.sub("#.+", "", content)

    # loop through substitutions, replacing all "{key}" with "value"
    for k, v in substitutions.items():
        content = content.replace("{" + k + "}", v)

    # replace " " between filepath directories, with "/"
    expected_files = [
        os.sep.join(line.split())
        for line in content.splitlines()
        if line.strip()
    ]
    return expected_files
