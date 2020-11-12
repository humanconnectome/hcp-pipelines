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

hcp_run_utils = os_utils.getenv_required("HCP_RUN_UTILS")
xnat_pbs_jobs = os_utils.getenv_required("XNAT_PBS_JOBS")


class OneSubjectCompletionXnatChecker(abc.ABC):
    """
    Abstract base class for classes that are used to check the completion
    of pipeline processing for one subject
    """

    def __init__(self, project, subject, classifier, scan):
        self.SUBJECT_PROJECT = project
        self.SUBJECT_ID = subject
        self.SUBJECT_CLASSIFIER = classifier
        self.SUBJECT_EXTRA = scan
        self.SUBJECT_SESSION = f"{subject}_{classifier}"
        self.archive = ccf_archive.CcfArchive(project, subject, classifier, scan)

    @property
    def processing_name(self):
        """Name of processing type to check (e.g. StructuralPreprocessing, FunctionalPreprocessing, etc.)"""
        raise NotImplementedError

    def prereq_dirs(self):
        raise NotImplementedError

    def my_resource(self):
        raise NotImplementedError

    def list_of_expected_files(self, working_dir, fieldmap):
        # define all possible locations
        common = (
            f"{self.processing_name}/ExpectedOutputFiles-FieldMap-{fieldmap}.CCF.txt"
        )
        alts = [
            "/pipeline_tools/pipelines/expected_files/DiffusionPreprocessing.txt",
            f"{hcp_run_utils}/{common}",
            f"{xnat_pbs_jobs}/{common}",
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

    def is_processing_complete(self, fieldmap, output=sys.stdout):
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
            expected_file_list = self.list_of_expected_files(resource, fieldmap)
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


class StructuralCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "StructuralPreprocessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/Structural_preproc"

    def prereq_dirs(self):
        return self.archive.structural_unproc()


class StructuralHandEditCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "StructuralPreprocessingHandEdit"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/Structural_preproc_handedit"

    def prereq_dirs(self):
        return self.archive.structural_preproc()


class FunctionalCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "FunctionalPreprocessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/" + archive.SUBJECT_EXTRA + "_preproc"

    def prereq_dirs(self):
        archive = self.archive
        return [(archive.subject_resources + "/Structural_preproc")]


class MultirunicafixCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "MultiRunIcaFixProcessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/MultiRunIcaFix_proc"

    def prereq_dirs(self):
        archive = self.archive
        return [(archive.subject_resources + "/Structural_preproc")]


class MsmAllCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "MsmAllProcessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/MsmAll_proc"

    def prereq_dirs(self):
        archive = self.archive
        return [(archive.subject_resources + "/Structural_preproc")]


class DiffusionCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "DiffusionPreprocessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/Diffusion_preproc"

    def prereq_dirs(self):
        archive = self.archive
        return [(archive.subject_resources + "/Structural_preproc")]


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
    # if PIPELINE_NAME == "DiffusionPreprocessing":
    if False:
        fieldmap = "NONE"
    else:
        fieldmap = "SpinEcho"
    completion_checker = FunctionalCompletionChecker(
        project,
        subject,
        classifier,
        scan,
    )

    if args.output:
        processing_output = open(
            args.output,
            "w",
        )
    else:
        processing_output = sys.stdout

    if completion_checker.is_processing_complete(
        fieldmap=fieldmap, verbose=True, output=processing_output, short_circuit=False
    ):
        print("Exiting with 0 code - Completion Check Successful")
        exit(0)
    else:
        print("Existing wih 1 code - Completion Check Unsuccessful")
        exit(1)
