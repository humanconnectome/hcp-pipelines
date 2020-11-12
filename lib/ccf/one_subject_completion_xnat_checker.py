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

        with open(expected_list_file) as f:
            root_dir = "/".join([working_dir, self.SUBJECT_SESSION])
            l = file_utils.build_filename_list_from_file(
                f,
                root_dir,
                subjectid=self.SUBJECT_SESSION,
                scan=self.SUBJECT_EXTRA,
            )
            return l

    def my_prerequisite_dir_full_paths(self):
        raise NotImplementedError

    def my_resource(self):
        raise NotImplementedError

    def my_resource_time_stamp(self):
        return os.path.getmtime(self.my_resource())

    def does_processed_resource_exist(self):
        fullpath = self.my_resource()
        return os.path.isdir(fullpath)

    def latest_prereq_resource_time_stamp(self):
        latest_time_stamp = 0
        prerequisite_dir_paths = self.my_prerequisite_dir_full_paths()

        for full_path in prerequisite_dir_paths:
            this_time_stamp = os.path.getmtime(full_path)
            if this_time_stamp > latest_time_stamp:
                latest_time_stamp = this_time_stamp

        return latest_time_stamp

    def is_processing_complete(self, fieldmap, output=sys.stdout):
        # If the processed resource does not exist, then the processing is certainly not complete.
        if not self.does_processed_resource_exist():
            print(
                "resource: " + self.my_resource() + " DOES NOT EXIST",
                file=output,
            )
            return False

        # If processed resource is not newer than prerequisite resources, then the processing
        # is not complete.
        resource_time_stamp = self.my_resource_time_stamp()
        latest_prereq_time_stamp = self.latest_prereq_resource_time_stamp()

        if resource_time_stamp <= latest_prereq_time_stamp:
            print(
                "resource: "
                + self.my_resource()
                + " IS NOT NEWER THAN ALL PREREQUISITES",
                file=output,
            )
            return False

        resource_file_path = self.my_resource()
        # If processed resource exists and is newer than all the prerequisite resources, then check
        # to see if all the expected files exist
        expected_file_list = self.list_of_expected_files(resource_file_path, fieldmap)
        return file_utils.do_all_files_exist(expected_file_list, True, output, False)


class StructuralCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "StructuralPreprocessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/Structural_preproc"

    def my_prerequisite_dir_full_paths(self):
        return self.archive.structural_unproc()


class StructuralHandEditCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "StructuralPreprocessingHandEdit"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/Structural_preproc_handedit"

    def my_prerequisite_dir_full_paths(self):
        return self.archive.structural_preproc()


class FunctionalCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "FunctionalPreprocessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/" + archive.SUBJECT_EXTRA + "_preproc"

    def my_prerequisite_dir_full_paths(self):
        archive = self.archive
        return [(archive.subject_resources + "/Structural_preproc")]


class MultirunicafixCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "MultiRunIcaFixProcessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/MultiRunIcaFix_proc"

    def my_prerequisite_dir_full_paths(self):
        archive = self.archive
        return [(archive.subject_resources + "/Structural_preproc")]


class MsmAllCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "MsmAllProcessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/MsmAll_proc"

    def my_prerequisite_dir_full_paths(self):
        archive = self.archive
        return [(archive.subject_resources + "/Structural_preproc")]


class DiffusionCompletionChecker(OneSubjectCompletionXnatChecker):
    @property
    def processing_name(self):
        return "DiffusionPreprocessing"

    def my_resource(self):
        archive = self.archive
        return archive.subject_resources + "/Diffusion_preproc"

    def my_prerequisite_dir_full_paths(self):
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
