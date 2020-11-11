#!/usr/bin/env python3

"""
Abstract Base Class for One Subject Completion Checker Classes
"""
import abc
import os
import sys
from utils import os_utils, file_utils


class OneSubjectCompletionXnatChecker(abc.ABC):
    """
    Abstract base class for classes that are used to check the completion
    of pipeline processing for one subject
    """

    @property
    def processing_name(self):
        """Name of processing type to check (e.g. StructuralPreprocessing, FunctionalPreprocessing, etc.)"""
        raise NotImplementedError

    def expected_output_files_template_filename(self, fieldmap):
        """Name of the file containing a list of templates for expected output files"""
        return "ExpectedOutputFiles-FieldMap-" + fieldmap + ".CCF.txt"

    def list_of_expected_files(self, working_dir, fieldmap, subject_info):

        hcp_run_utils = os_utils.getenv_required("HCP_RUN_UTILS")
        if os.path.isfile(
            hcp_run_utils
            + os.sep
            + self.processing_name
            + os.sep
            + self.expected_output_files_template_filename(fieldmap)
        ):
            f = open(
                hcp_run_utils
                + os.sep
                + self.processing_name
                + os.sep
                + self.expected_output_files_template_filename(fieldmap)
            )
        else:
            xnat_pbs_jobs = os_utils.getenv_required("XNAT_PBS_JOBS")
            f = open(
                xnat_pbs_jobs
                + os.sep
                + self.processing_name
                + os.sep
                + self.expected_output_files_template_filename(fieldmap)
            )

        root_dir = os.sep.join(
            [working_dir, subject_info.subject_id + "_" + subject_info.classifier]
        )
        l = file_utils.build_filename_list_from_file(
            f,
            root_dir,
            subjectid=subject_info.subject_id + "_" + subject_info.classifier,
            scan=subject_info.extra,
        )
        return l

    def do_all_files_exist(
        self, file_name_list, verbose=False, output=sys.stdout, short_circuit=True
    ):
        return file_utils.do_all_files_exist(
            file_name_list, verbose, output, short_circuit
        )

    def my_prerequisite_dir_full_paths(self, archive, subject_info):
        pass

    def my_resource_time_stamp(self, archive, subject_info):
        return os.path.getmtime(self.my_resource(archive, subject_info))

    def does_processed_resource_exist(self, archive, subject_info):
        fullpath = self.my_resource(archive, subject_info)
        return os.path.isdir(fullpath)

    def latest_prereq_resource_time_stamp(self, archive, subject_info):
        latest_time_stamp = 0
        prerequisite_dir_paths = self.my_prerequisite_dir_full_paths(
            archive, subject_info
        )

        for full_path in prerequisite_dir_paths:
            this_time_stamp = os.path.getmtime(full_path)
            if this_time_stamp > latest_time_stamp:
                latest_time_stamp = this_time_stamp

        return latest_time_stamp

    def is_processing_marked_complete(self, archive, subject_info):

        # If the processed resource does not exist, then the process is certainly not marked
        # as complete. The file that marks completeness would be in that resource.
        if not self.does_processed_resource_exist(archive, subject_info):
            return False

        resource_path = (
            self.my_resource(archive, subject_info)
            + os.sep
            + subject_info.subject_id
            + "_"
            + subject_info.classifier
            + os.sep
            + "ProcessingInfo"
        )

        subject_pipeline_name = subject_info.subject_id + "_" + subject_info.classifier
        subject_pipeline_name_check = (
            subject_info.subject_id + "." + subject_info.classifier
        )
        if subject_info.extra.lower() != "all" and subject_info.extra != "":
            subject_pipeline_name += "_" + subject_info.extra
            subject_pipeline_name_check += "." + subject_info.extra
        subject_pipeline_name += "." + self.PIPELINE_NAME
        subject_pipeline_name_check += "." + self.PIPELINE_NAME

        completion_marker_file_path = (
            resource_path + os.sep + subject_pipeline_name_check + ".XNAT_CHECK.success"
        )
        starttime_marker_file_path = (
            resource_path + os.sep + subject_pipeline_name + ".starttime"
        )

        # If the completion marker file does not exist, the the processing is certainly not marked
        # as complete.
        marker_file_exists = os.path.exists(completion_marker_file_path)
        if not marker_file_exists:
            return False

        # If the completion marker file is older than the starttime marker file, then any mark
        # of completeness is invalid.
        if not os.path.exists(starttime_marker_file_path):
            return False

        if os.path.getmtime(completion_marker_file_path) < os.path.getmtime(
            starttime_marker_file_path
        ):
            return False

        # If the completion marker file does exist, then look at the contents for further
        # confirmation.

        f = open(completion_marker_file_path, "r")
        lines = f.readlines()

        if lines[-1].strip() != "Completion Check was successful":
            return False

        return True

    def is_processing_complete(
        self,
        archive,
        fieldmap,
        subject_info,
        verbose=False,
        output=sys.stdout,
        short_circuit=True,
    ):
        # If the processed resource does not exist, then the processing is certainly not complete.
        if not self.does_processed_resource_exist(archive, subject_info):
            if verbose:
                print(
                    "resource: "
                    + self.my_resource(archive, subject_info)
                    + " DOES NOT EXIST",
                    file=output,
                )
            return False

        # If processed resource is not newer than prerequisite resources, then the processing
        # is not complete.
        resource_time_stamp = self.my_resource_time_stamp(archive, subject_info)
        latest_prereq_time_stamp = self.latest_prereq_resource_time_stamp(
            archive, subject_info
        )

        if resource_time_stamp <= latest_prereq_time_stamp:
            if verbose:
                print(
                    "resource: "
                    + self.my_resource(archive, subject_info)
                    + " IS NOT NEWER THAN ALL PREREQUISITES",
                    file=output,
                )
            return False

        resource_file_path = self.my_resource(archive, subject_info)
        # If processed resource exists and is newer than all the prerequisite resources, then check
        # to see if all the expected files exist
        expected_file_list = self.list_of_expected_files(
            resource_file_path, fieldmap, subject_info
        )
        return self.do_all_files_exist(
            expected_file_list, verbose, output, short_circuit
        )


class StructuralCompletionChecker(OneSubjectCompletionXnatChecker):
    def __init__(self):
        super().__init__()

    @property
    def processing_name(self):
        return "StructuralPreprocessing"

    @property
    def PIPELINE_NAME(self):
        return "StructuralPreprocessing"

    def my_resource(self, archive, subject_info):
        return archive.structural_preproc_dir_full_path(subject_info)

    def my_prerequisite_dir_full_paths(self, archive, subject_info):
        return archive.available_structural_unproc_dir_full_paths(subject_info)


class StructuralHandEditCompletionChecker(OneSubjectCompletionXnatChecker):
    def __init__(self):
        super().__init__()

    @property
    def processing_name(self):
        return "StructuralPreprocessingHandEdit"

    @property
    def structural_preproc_processing_name(self):
        return "StructuralPreprocessing"

    @property
    def PIPELINE_NAME(self):
        return "StructuralPreprocessingHandEdit"

    def my_resource(self, archive, subject_info):

        return archive.structural_preproc_hand_edit_dir_full_path(subject_info)

    def my_prerequisite_dir_full_paths(self, archive, subject_info):
        return archive.available_structural_preproc_dir_full_paths(subject_info)


class FunctionalCompletionChecker(OneSubjectCompletionXnatChecker):
    def __init__(self):
        super().__init__()

    @property
    def processing_name(self):
        return "FunctionalPreprocessing"

    @property
    def PIPELINE_NAME(self):
        return "FunctionalPreprocessing"

    def my_resource(self, archive, subject_info):
        return archive.functional_preproc_dir_full_path(subject_info)

    def my_prerequisite_dir_full_paths(self, archive, subject_info):
        dirs = []
        dirs.append(archive.structural_preproc_dir_full_path(subject_info))
        return dirs


class MultirunicafixCompletionChecker(OneSubjectCompletionXnatChecker):
    def __init__(self):
        super().__init__()

    @property
    def processing_name(self):
        return "MultiRunIcaFixProcessing"

    @property
    def PIPELINE_NAME(self):
        return "MultiRunIcaFixProcessing"

    def my_resource(self, archive, subject_info):
        return archive.multirun_icafix_dir_full_path(subject_info)

    def my_prerequisite_dir_full_paths(self, archive, subject_info):
        dirs = []
        dirs.append(archive.structural_preproc_dir_full_path(subject_info))
        return dirs


class MsmAllCompletionChecker(OneSubjectCompletionXnatChecker):
    def __init__(self):
        super().__init__()

    @property
    def processing_name(self):
        return "MsmAllProcessing"

    @property
    def PIPELINE_NAME(self):
        return "MsmAllProcessing"

    def my_resource(self, archive, subject_info):
        return archive.msm_all_dir_full_path(subject_info)

    def my_prerequisite_dir_full_paths(self, archive, subject_info):
        dirs = []
        dirs.append(archive.structural_preproc_dir_full_path(subject_info))
        return dirs


class DiffusionCompletionChecker(OneSubjectCompletionXnatChecker):
    def __init__(self):
        super().__init__()

    @property
    def processing_name(self):
        return "DiffusionPreprocessing"

    @property
    def PIPELINE_NAME(self):
        return "DiffusionPreprocessing"

    def my_resource(self, archive, subject_info):
        return archive.diffusion_preproc_dir_full_path(subject_info)

    def my_prerequisite_dir_full_paths(self, archive, subject_info):
        dirs = []
        dirs.append(archive.structural_preproc_dir_full_path(subject_info))
        return dirs
