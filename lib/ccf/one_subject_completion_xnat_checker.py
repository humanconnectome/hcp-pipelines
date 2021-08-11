#!/usr/bin/env python3

"""
Abstract Base Class for One Subject Completion Checker Classes
"""
import os
import sys
from utils import file_utils
import ccf.archive as ccf_archive


class OneSubjectCompletionXnatChecker:
    def __init__(
        self,
        project,
        scan,
        session,
        OUTPUT_RESOURCE_NAME,
        PIPELINE_NAME,
        ARCHIVE_ROOT,
        EXPECTED_FILES_LIST,
    ):
        self.EXPECTED_FILES_LIST = EXPECTED_FILES_LIST
        self.SCAN = scan
        self.SESSION = session
        self.OUTPUT_RESOURCE_NAME = OUTPUT_RESOURCE_NAME
        self.PIPELINE_NAME = PIPELINE_NAME
        self.archive = ccf_archive.CcfArchive(project, session, ARCHIVE_ROOT)

    def prereq_dirs(self):
        if self.PIPELINE_NAME == "StructuralPreprocessing":
            return self.archive.structural_unproc()
        else:
            return self.archive.structural_preproc()

    def my_resource(self):
        return self.archive.SESSION_RESOURCES / self.OUTPUT_RESOURCE_NAME

    def list_of_expected_files(self, working_dir):
        if not os.path.isfile(self.EXPECTED_FILES_LIST):
            raise Exception(
                "The list of expected files was not found in the specified location:",
                self.EXPECTED_FILES_LIST,
            )

        with open(self.EXPECTED_FILES_LIST) as fd:
            root_dir = os.path.join(working_dir, self.SESSION)
            l = file_utils.build_filename_list_from_file(
                fd,
                root_dir,
                subjectid=self.SESSION,
                scan=self.SCAN,
            )
            return l

    def is_processing_complete(self, output=None):
        if output is None:
            output = sys.stdout
        else:
            output = open(output, "w")

        resource = self.my_resource()

        # Check if it exists
        if not os.path.isdir(resource):
            print(f"resource: {resource} DOES NOT EXIST", file=output)
            print("Completion Check was unsuccessful", file=output)
            return False

        prereq_timestamps = map(os.path.getmtime, self.prereq_dirs())
        max_prereq_timestamp = max(prereq_timestamps, default=0)
        resource_timestamp = os.path.getmtime(resource)

        # Make sure the resource is newer (larger timestamp) than the newest prereq file
        if resource_timestamp > max_prereq_timestamp:
            # resource is newer than all the prerequisite resources
            # check to see if all the expected files exist
            expected_file_list = self.list_of_expected_files(resource)
            success = do_all_files_exist(expected_file_list, output)
            if success:
                print("Completion Check was successful", file=output)
            else:
                print("Completion Check was unsuccessful", file=output)
            return success
        else:
            print(
                f"resource: {resource} IS NOT NEWER THAN ALL PREREQUISITES", file=output
            )
            print("Completion Check was unsuccessful", file=output)
            return False


def do_all_files_exist(file_name_list, output=sys.stdout):
    all_files_exist = True

    for file_name in file_name_list:
        print("Checking for existence of: " + file_name, file=output)
        if not os.path.exists(file_name):
            print("FILE DOES NOT EXIST: " + file_name, file=output)
            all_files_exist = False

    return all_files_exist
