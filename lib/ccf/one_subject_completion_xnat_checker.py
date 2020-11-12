#!/usr/bin/env python3

"""
Abstract Base Class for One Subject Completion Checker Classes
"""
import abc
import argparse
import os
import sys
from utils import os_utils, file_utils
import ccf.archive as ccf_archive


class OneSubjectCompletionXnatChecker:
    def __init__(
        self,
        project,
        subject,
        classifier,
        scan,
        OUTPUT_RESOURCE_NAME,
        PIPELINE_NAME,
        HCP_RUN_UTILS,
        XNAT_PBS_JOBS,
    ):
        self.HCP_RUN_UTILS = HCP_RUN_UTILS
        self.XNAT_PBS_JOBS = XNAT_PBS_JOBS
        self.SUBJECT_EXTRA = scan
        self.SUBJECT_SESSION = f"{subject}_{classifier}"
        self.OUTPUT_RESOURCE_NAME = OUTPUT_RESOURCE_NAME
        self.PIPELINE_NAME = PIPELINE_NAME
        self.archive = ccf_archive.CcfArchive(project, subject, classifier, scan)

    def prereq_dirs(self):
        if self.PIPELINE_NAME == "StructuralPreprocessing":
            return self.archive.structural_unproc()
        else:
            return self.archive.structural_preproc()

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/" + self.OUTPUT_RESOURCE_NAME

    def list_of_expected_files(self, working_dir):
        if self.PIPELINE_NAME == "DiffusionPreprocessing":
            fieldmap = "NONE"
        else:
            fieldmap = "SpinEcho"

        # define all possible locations
        common = f"{self.PIPELINE_NAME}/ExpectedOutputFiles-FieldMap-{fieldmap}.CCF.txt"
        alts = [
            "/pipeline_tools/pipelines/expected_files/DiffusionPreprocessing.txt",
            f"{self.HCP_RUN_UTILS}/{common}",
            f"{self.XNAT_PBS_JOBS}/{common}",
        ]

        # look in all locations and find first file that exists
        expected_list_file = None
        for filename in alts:
            if os.path.isfile(filename):
                expected_list_file = filename
        if expected_list_file is None:
            raise Exception(
                "Couldn't find an expected file in all the locations:", alts
            )

        with open(expected_list_file) as fd:
            root_dir = os.path.join(working_dir, self.SUBJECT_SESSION)
            l = file_utils.build_filename_list_from_file(
                fd,
                root_dir,
                subjectid=self.SUBJECT_SESSION,
                scan=self.SUBJECT_EXTRA,
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
            return False

        prereq_timestamps = map(os.path.getmtime, self.prereq_dirs())
        max_prereq_timestamp = max(prereq_timestamps, default=0)
        resource_timestamp = os.path.getmtime(resource)

        # Make sure the resource is newer (larger timestamp) than the newest prereq file
        if resource_timestamp > max_prereq_timestamp:
            # resource is newer than all the prerequisite resources
            # check to see if all the expected files exist
            expected_file_list = self.list_of_expected_files(resource)
            return do_all_files_exist(expected_file_list, output)
        else:
            print(
                f"resource: {resource} IS NOT NEWER THAN ALL PREREQUISITES", file=output
            )
            return False


def do_all_files_exist(file_name_list, output=sys.stdout):
    all_files_exist = True

    for file_name in file_name_list:
        print("Checking for existence of: " + file_name, file=output)
        if not os.path.exists(file_name):
            print("FILE DOES NOT EXIST: " + file_name, file=output)
            all_files_exist = False

    return all_files_exist


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Program to check for completion of Functional Preprocessing."
    )

    # mandatory arguments
    parser.add_argument(
        "--project",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--subject",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--classifier",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--scan",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=str,
    )

    # parse the command line arguments
    args = parser.parse_args()

    # check the specified subject and scan for functional preprocessing completion
    project = args.project
    subject = args.subject
    classifier = args.classifier
    scan = args.scan
    completion_checker = OneSubjectCompletionXnatChecker(
        project,
        subject,
        classifier,
        scan,
    )

    if completion_checker.is_processing_complete(args.output):
        print("Exiting with 0 code - Completion Check Successful")
        exit(0)
    else:
        print("Existing wih 1 code - Completion Check Unsuccessful")
        exit(1)
