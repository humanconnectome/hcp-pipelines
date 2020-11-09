#!/usr/bin/env python3
"""
ccf.get_cinab_style_data.py: Get (copy or link) a CinaB style directory tree of data
for a specified subject within a specified project.
"""

# import of built-in modules
import abc
import glob
import logging
import logging.config
import os
import subprocess
import sys

# import of third-party modules

# import of local modules
import ccf.archive as ccf_archive
import ccf.subject as ccf_subject
import utils.debug_utils as debug_utils
import utils.file_utils as file_utils
import utils.my_argparse as my_argparse
import utils.os_utils as os_utils

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2019, Connectome Coordination Facility"
__maintainer__ = "Junil Chang"

# create a module logger
module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.WARNING)  # Note: This can be overridden by log file configuration
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(logging.Formatter('%(name)s: %(message)s'))
module_logger.addHandler(sh)



class DataRetriever(object):

    def __init__(self, archive):
        self._archive = archive

        # indication of whether data should be copied
        # False ==> symbolic links will be created
        # True  ==> files will be copied
        self._copy = False

        # indication of whether logging of files copied
        # or linked should be shown
        self._show_log = False

    @property
    def archive(self):
        return self._archive

    @property
    def copy(self):
        return self._copy

    @copy.setter
    def copy(self, value):
        if not isinstance(value, bool):
            raise TypeError("copy must be set to a boolean value")
        self._copy = value

    @property
    def show_log(self):
        return self._show_log

    @show_log.setter
    def show_log(self, value):
        if not isinstance(value, bool):
            raise TypeError("show_log must be set to a boolean value")
        self._show_log = value

    def _from_to(self, get_from, put_to):
        os.makedirs(put_to, exist_ok=True)
        if self.copy:
            if self.show_log:
                rsync_cmd = 'rsync -auLv '
            else:
                rsync_cmd = 'rsync -auL '

            rsync_cmd += get_from + os.sep + '*' + ' ' + put_to
            module_logger.debug(debug_utils.get_name() + " rsync_cmd: " + rsync_cmd)

            completed_rsync_process = subprocess.run(
                rsync_cmd, shell=True, check=True, stdout=subprocess.PIPE,
                universal_newlines=True)
            module_logger.debug(debug_utils.get_name() + " stdout: " + completed_rsync_process.stdout)

        else:
            module_logger.debug(debug_utils.get_name() + " linking " + put_to + " to " + get_from)
            os_utils.lndir(get_from, put_to, self.show_log, ignore_existing_dst_files=True)

    # get unprocessed data

    def _get_unprocessed_data(self, directories, subject_info, output_dir):
        for directory in directories:
            get_from = directory
            module_logger.debug(debug_utils.get_name() + " get_from: " + get_from)

            last_sep_loc = get_from.rfind(os.sep)
            unproc_loc = get_from.rfind("_" + 'unproc')
            sub_dir = get_from[last_sep_loc + 1:unproc_loc]
            put_to = output_dir + os.sep + subject_info.subject_id + "_" + subject_info.classifier + os.sep + 'unprocessed' + os.sep + sub_dir
			
            module_logger.debug(debug_utils.get_name() + "   put_to: " + put_to)

            self._from_to(get_from, put_to)

    def get_structural_unproc_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())
        self._get_unprocessed_data(
            self.archive.available_structural_unproc_dir_full_paths(subject_info),
            subject_info,
            output_dir)

    def get_functional_unproc_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())
        self._get_unprocessed_data(
            self.archive.available_functional_unproc_dir_full_paths(subject_info),
            subject_info,
            output_dir)

    def get_diffusion_unproc_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())
        self._get_unprocessed_data(
            self.archive.available_diffusion_unproc_dir_full_paths(subject_info),
            subject_info,
            output_dir)

    def get_unproc_data(self, subject_info, output_dir):
        self.get_structural_unproc_data(subject_info, output_dir)
        self.get_functional_unproc_data(subject_info, output_dir)
        self.get_diffusion_unproc_data(subject_info, output_dir)

    # get preprocessed data

    def _get_preprocessed_data(self, directories, output_dir):
        for directory in directories:
            get_from = directory
            module_logger.debug(debug_utils.get_name() + " get_from: " + get_from)

            put_to = output_dir
            module_logger.debug(debug_utils.get_name() + "   put_to: " + put_to)

            self._from_to(get_from, put_to)

    def get_structural_preproc_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(
            self.archive.available_structural_preproc_dir_full_paths(subject_info),
            output_dir)

    def get_icafix_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())
        self._get_processed_data(
            self.archive.available_multirun_icafix_dir_full_paths(subject_info),
            output_dir)

    def get_supplemental_structural_preproc_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(
            self.archive.available_supplemental_structural_preproc_dir_full_paths(subject_info),
            output_dir)

    def get_hand_edit_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(
            self.archive.available_hand_edit_full_paths(subject_info),
            output_dir)

    def get_functional_preproc_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(
            self.archive.available_functional_preproc_dir_full_paths(subject_info),
            output_dir)

    def get_diffusion_preproc_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(
            self.archive.available_diffusion_preproc_dir_full_paths(subject_info),
            output_dir)

    def get_preproc_data(self, subject_info, output_dir):

        if self.copy:
            # when copying (via rsync), data should be retrieved in chronological order
            # (i.e. the order in which the pipelines are run)
            self.get_structural_preproc_data(subject_info, output_dir)
            self.get_supplemental_structural_preproc_data(subject_info, output_dir)
            self.get_functional_preproc_data(subject_info, output_dir)
            self.get_diffusion_preproc_data(subject_info, output_dir)

        else:
            # when creating symbolic links, data should be retrieved in reverse
            # chronological order
            self.get_diffusion_preproc_data(subject_info, output_dir)
            self.get_functional_preproc_data(subject_info, output_dir)
            self.get_supplemental_structural_preproc_data(subject_info, output_dir)
            self.get_structural_preproc_data(subject_info, output_dir)

    # get processed data

    def _get_processed_data(self, directories, output_dir):
        for directory in directories:
            get_from = directory
            module_logger.debug(debug_utils.get_name() + " get_from: " + get_from)

            put_to = output_dir
            module_logger.debug(debug_utils.get_name() + "   put_to: " + put_to)

            self._from_to(get_from, put_to)

    def get_msmall_registration_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())

        self._get_processed_data(
            self.archive.available_msmall_registration_dir_full_paths(subject_info),
            output_dir)

    def get_fix_processed_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())

        self._get_processed_data(
            self.archive.available_fix_processed_dir_full_paths(subject_info),
            output_dir)

    def get_dedriftandresample_processed_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())

        self._get_processed_data(
            self.archive.available_msmall_dedrift_and_resample_dir_full_paths(subject_info),
            output_dir)

    def get_resting_state_stats_data(self, subject_info, output_dir):
        module_logger.debug(debug_utils.get_name())

        self._get_processed_data(
            self.archive.available_rss_processed_dir_full_paths(subject_info),
            output_dir)

    def get_postfix_data(self, subject_info, output_dir):
        self._get_processed_data(
            self.archive.available_postfix_processed_dir_full_paths(subject_info),
            output_dir)

    def get_taskfmri_data(self, subject_info, output_dir):
        self._get_processed_data(
            self.archive.available_task_processed_dir_full_paths(subject_info),
            output_dir)

    def get_bedpostx_data(self, subject_info, output_dir):
        self._get_processed_data(
            self.archive.available_bedpostx_processed_dir_full_paths(subject_info),
            output_dir)

    # prerequisites data for specific pipelines

    def get_struct_preproc_prereqs(self, subject_info, output_dir):
        """
        Get the data necessary to run the Structural Preprocessing pipeline
        """
        if self.copy:
            # when copying (via rsync), data should be retrieved in chronological order
            # (i.e. the order in which the pipelines are run)
            self.get_unproc_data(subject_info, output_dir)

        else:
            # when creating symbolic links, data should be retrieved in reverse
            # chronological order
            self.get_unproc_data(subject_info, output_dir)

    def get_struct_preproc_hand_edit_prereqs(self, subject_info, output_dir):
        """
        Get the data necessary to run the Functional Preprocessing pipelines
        """
        if self.copy:
            # when copying (via rsync), data should be retrieved in chronological order
            # (i.e. the order in which the pipelines are run)
            self.get_unproc_data(subject_info, output_dir)
            self.get_structural_preproc_data(subject_info, output_dir)
            self.get_hand_edit_data(subject_info, output_dir)
            self.get_supplemental_structural_preproc_data(subject_info, output_dir)
        else:
            # chronological order
            self.get_supplemental_structural_preproc_data(subject_info, output_dir)
            self.get_hand_edit_data(subject_info, output_dir)
            self.get_structural_preproc_data(subject_info, output_dir)
            self.get_unproc_data(subject_info, output_dir)

    def get_diffusion_preproc_prereqs(self, subject_info, output_dir):
        """
        Get the data necessary to run the Diffusion Preprocessing pipeline
        """
        if self.copy:
            # when copying (via rsync), data should be retrieved in chronological order
            # (i.e. the order in which the pipelines are run)
            self.get_unproc_data(subject_info, output_dir)
            self.get_structural_preproc_data(subject_info, output_dir)
            self.get_supplemental_structural_preproc_data(subject_info, output_dir)
        else:
            # when creating symbolic links, data should be retrieved in reverse
            # chronological order
            self.get_supplemental_structural_preproc_data(subject_info, output_dir)
            self.get_structural_preproc_data(subject_info, output_dir)
            self.get_unproc_data(subject_info, output_dir)

    def get_functional_preproc_prereqs(self, subject_info, output_dir):
        """
        Get the data necessary to run the Functional Preprocessing pipelines
        """
        if self.copy:
            # when copying (via rsync), data should be retrieved in chronological order
            # (i.e. the order in which the pipelines are run)
            self.get_unproc_data(subject_info, output_dir)
            self.get_structural_preproc_data(subject_info, output_dir)
            self.get_supplemental_structural_preproc_data(subject_info, output_dir)
        else:
            # when creating symbolic links, data should be retrieved in reverse
            # chronological order
            self.get_supplemental_structural_preproc_data(subject_info, output_dir)
            self.get_structural_preproc_data(subject_info, output_dir)
            self.get_unproc_data(subject_info, output_dir)

    def get_multirunicafix_prereqs(self, subject_info, output_dir):
        """
        Get the data necessary to run the MultiRunICAFIX pipeline
        """
        if self.copy:
            # when copying (via rsync), data should be retrieved in chronological order
            # (i.e. the order in which the pipelines are run)
            self.get_unproc_data(subject_info, output_dir)
            self.get_preproc_data(subject_info, output_dir)

        else:
            # when creating symbolic links, data should be retrieved in reverse
            # chronological order
            self.get_preproc_data(subject_info, output_dir)
            self.get_unproc_data(subject_info, output_dir)


    def get_msmall_prereqs(self, subject_info, output_dir):
        """
        Get the data necessary to run the MsmAll pipeline
        """
        if self.copy:
            # when copying (via rsync), data should be retrieved in chronological order
            # (i.e. the order in which the pipelines are run)
            self.get_unproc_data(subject_info, output_dir)
            self.get_preproc_data(subject_info, output_dir)
            self.get_icafix_data(subject_info, output_dir)

        else:
            # when creating symbolic links, data should be retrieved in reverse
            # chronological order
            self.get_icafix_data(subject_info, output_dir)
            self.get_preproc_data(subject_info, output_dir)
            self.get_unproc_data(subject_info, output_dir)

    def _copy_some_dedriftandresample_links(self, subject_info, output_dir):
        """
        Some files that already exist prior to running the DeDriftAndResample pipeline
        are opened for writing/modification by the pipeline script. If these files are
        left as symbolic links to files in the archive, they will not be able to be
        opened for writing. Each of these files needs to be copied instead of linked.
        """

        t1w_native_spec_file = output_dir + os.sep + subject_info.subject_id + "_" + subject_info.classifier
        t1w_native_spec_file += os.sep + 'T1w' + os.sep + 'Native'
        t1w_native_spec_file += os.sep + subject_info.subject_id + '.native.wb.spec'
        file_utils.make_link_into_copy(t1w_native_spec_file, verbose=True)

        native_spec_file = output_dir + os.sep + subject_info.subject_id + "_" + subject_info.classifier
        native_spec_file += os.sep + 'MNINonLinear' + os.sep + 'Native'
        native_spec_file += os.sep + subject_info.subject_id + '.native.wb.spec'
        file_utils.make_link_into_copy(native_spec_file, verbose=True)

    def _remove_some_dedriftandresample_ica_files(self, subject_info, output_dir):
        """
        Some files need to be re-created by the ReApplyFixPipeline.sh script which
        is invoked by the DeDriftAndResample pipeline. For the ReApplyFixPipeline
        to work correctly, those files need to be removed before processing begins.
        """
        path_expr = output_dir + os.sep + subject_info.subject_id + "_" + subject_info.classifier
        path_expr += os.sep + 'MNINonLinear' + os.sep + 'Results'
        path_expr += os.sep + '*'

        dir_list = sorted(glob.glob(path_expr))

        for dir in dir_list:
            ica_dir_expr = dir + os.sep + '*.ica'
            ica_dir_list = sorted(glob.glob(ica_dir_expr))

            for ica_dir in ica_dir_list:
                atlas_dtseries_file = ica_dir + os.sep + 'Atlas.dtseries.nii'
                file_utils.rm_file_if_exists(atlas_dtseries_file, verbose=True)

                atlas_file = ica_dir + os.sep + 'Atlas.nii.gz'
                file_utils.rm_file_if_exists(atlas_file, verbose=True)

                filtered_func_data_file = ica_dir + os.sep + 'filtered_func_data.nii.gz'
                file_utils.rm_file_if_exists(filtered_func_data_file, verbose=True)

                mc_dir = ica_dir + os.sep + 'mc'
                file_utils.rm_dir_if_exists(mc_dir, verbose=True)

                atlas_preclean_dtseries_file = ica_dir + os.sep + 'Atlas_hp_preclean.dtseries.nii'
                file_utils.rm_file_if_exists(atlas_preclean_dtseries_file, verbose=True)

    def get_dedriftandresample_prereqs(self, subject_info, output_dir):
        """
        Get the subject specific data necessary to run the DeDriftAndResample pipeline
        """

        if self.copy:
            # when copying (via rsync), data should be retreived in chronological order
            # (i.e. the order in which the pipelines are run)
            self.get_preproc_data(subject_info, output_dir)
            self.get_fix_processed_data(subject_info, output_dir)
            self.get_msmall_registration_data(subject_info, output_dir)

        else:
            # when creating symbolic links, data should be retrieved in reverse
            # chronological order
            self.get_msmall_registration_data(subject_info, output_dir)
            self.get_fix_processed_data(subject_info, output_dir)
            self.get_preproc_data(subject_info, output_dir)

            self._copy_some_dedriftandresample_links(subject_info, output_dir)

        self._remove_some_dedriftandresample_ica_files(subject_info, output_dir)

    def get_msm_group_average_drift_data(self, project_id, output_dir):
        """
        Get the group average drift data stored in the specified project
        """
        get_from = self.archive.project_resources_dir_full_path(project_id)
        get_from += os.sep + 'MSMAllDeDrift'
        put_to = output_dir

        self._from_to(get_from, put_to)

    def _copy_some_reapplyfix_links(self, subject_info, output_dir):
        """
        Some files that already exist prio to running the ReApplyFix pipeline are
        opened for writing/modification by the pipeline script. If these files are
        left as symbolic links to file in the archive, they will not be able to be
        opened for writing. Each of these files need to be copied instead of linked.
        """

        # find all paths that end with '.ica'
        paths = glob.iglob(output_dir + os.sep + '**' + os.sep + '*.ica', recursive=True)
        for path in paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_to_copy = os.path.join(root, file)
                        file_utils.make_link_into_copy(file_to_copy, verbose=True)

    def get_reapplyfix_prereqs(self, subject_info, output_dir):
        """
        Get the subject specific data necessary to run the ReApplyFix pipeline
        """
        self.get_all_pipeline_data(subject_info, output_dir)
        self._copy_some_reapplyfix_links(subject_info, output_dir)

    # all pipeline data

    def get_all_pipeline_data(self, subject_info, output_dir):
        """
        Get all the subject specific data recognized.
        Note, this is based on the recognized processing. It does not simply
        get all data from all resources. There is a specific set of recognized
        resource directories that are searched for and used. This means that
        adding new resources to a session doesn't automatically cause those
        resources to be copied/linked to the output_dir. (That gives us the
        freedom to have resources that are not specifically dealing with
        pipeline processing.) However, it also means that this method needs
        to be updated when new pipelines are added to the processing stream.
        """

        if self.copy:
            # when copying (via rsync), data should be retrieved in chronological order
            # (i.e. the order in which the pipelines are run)
            self.get_unproc_data(subject_info, output_dir)
            self.get_preproc_data(subject_info, output_dir)
            self.get_fix_processed_data(subject_info, output_dir)
            self.get_msmall_registration_data(subject_info, output_dir)
            self.get_dedriftandresample_processed_data(subject_info, output_dir)
            self.get_resting_state_stats_data(subject_info, output_dir)
            self.get_postfix_data(subject_info, output_dir)
            self.get_taskfmri_data(subject_info, output_dir)
            self.get_bedpostx_data(subject_info, output_dir)

        else:
            # when creating symbolic links, data should be retrieved in reverse
            # chronological order
            self.get_bedpostx_data(subject_info, output_dir)
            self.get_taskfmri_data(subject_info, output_dir)
            self.get_postfix_data(subject_info, output_dir)
            self.get_resting_state_stats_data(subject_info, output_dir)
            self.get_dedriftandresample_processed_data(subject_info, output_dir)
            self.get_msmall_registration_data(subject_info, output_dir)
            self.get_fix_processed_data(subject_info, output_dir)
            self.get_preproc_data(subject_info, output_dir)
            self.get_unproc_data(subject_info, output_dir)

    def remove_non_subdirs(self, directory):
        cmd = 'find ' + directory + ' -maxdepth 1 -not -type d -delete'
        completed_process = subprocess.run(
            cmd, shell=True, check=True, stdout=subprocess.PIPE,
            universal_newlines=True)
        return

def main():
    # create a parser object for getting the command line arguments
    parser = my_argparse.MyArgumentParser()

    # mandatory arguments
    parser.add_argument('-p', '--project', dest='project', required=True, type=str)
    parser.add_argument('-s', '--subject', dest='subject', required=True, type=str)
    parser.add_argument('-d', '--study-dir', dest='output_study_dir', required=True, type=str)

    # optional arguments
    parser.add_argument('-a', '--scan', dest='scan', required=False, type=str, default=None)
    parser.add_argument('-c', '--copy', dest='copy', action='store_true',
                        required=False, default=False)
    parser.add_argument('-l', '--log', dest='log', action='store_true',
                        required=False, default=False)
    parser.add_argument('-r', '--remove-non-subdirs', dest='remove_non_subdirs', action='store_true',
                        required=False, default=False)

    phase_choices = [
        "STRUCT_PREPROC_PREREQS", "struct_preproc_prereqs",
		"STRUCT_PREPROC_HAND_EDIT_PREREQS", "struct_preproc_hand_edit_prereqs",
        "DIFF_PREPROC_PREREQS", "diff_preproc_prereqs",
        "FUNC_PREPROC_PREREQS", "func_preproc_prereqs",
        "MULTIRUNICAFIX_PREREQS", "multirunicafix_prereqs",
        "MSMALL_PREREQS", "msmall_prereqs",
        "DEDRIFTANDRESAMPLE_PREREQS", "dedriftandresample_prereqs",
        "REAPPLYFIX_PREREQS", "reapplyfix_prereqs"
    ]

    default_phase_choice = phase_choices[0]

    parser.add_argument(
        '-ph', '--phase', dest='phase', required=False,
        choices=phase_choices,
        default=default_phase_choice)

    parser.add_argument(
        '-cl', '--classifier', dest='session_classifier', required=False, type=str,
        default='3T')

    # parse the command line arguments
    args = parser.parse_args()

    # convert phase argument to uppercase
    args.phase = args.phase.upper()

    # show arguments
    module_logger.info("Arguments:")
    module_logger.info("            Project: " + args.project)
    module_logger.info("            Subject: " + args.subject)
    module_logger.info(" Session Classifier: " + args.session_classifier)
    module_logger.info("         Output Dir: " + args.output_study_dir)
    module_logger.info("              Phase: " + args.phase)
    if args.copy:
        module_logger.info("               Copy: " + str(args.copy))
    if args.log:
        module_logger.info("                Log: " + str(args.log))
    if args.remove_non_subdirs:
        module_logger.info(" Remove Non-Subdirs: " + str(args.remove_non_subdirs))

    subject_info = ccf_subject.SubjectInfo(args.project, args.subject, args.session_classifier,
                                           args.scan)
    archive = ccf_archive.CcfArchive()

    data_retriever = DataRetriever(archive)
    data_retriever.copy = args.copy
    data_retriever.show_log = args.log

    # retrieve data based on phase requested
    if args.phase == "STRUCT_PREPROC_PREREQS":
        data_retriever.get_struct_preproc_prereqs(subject_info, args.output_study_dir)

    elif args.phase == "STRUCT_PREPROC_HAND_EDIT_PREREQS":
        data_retriever.get_struct_preproc_hand_edit_prereqs(subject_info, args.output_study_dir)

    elif args.phase == "DIFF_PREPROC_PREREQS":
        data_retriever.get_diffusion_preproc_prereqs(subject_info, args.output_study_dir)

    elif args.phase == "FUNC_PREPROC_PREREQS":
        data_retriever.get_functional_preproc_prereqs(subject_info, args.output_study_dir)

    elif args.phase == "MULTIRUNICAFIX_PREREQS":
        data_retriever.get_multirunicafix_prereqs(subject_info, args.output_study_dir)

    elif args.phase == "MSMALL_PREREQS":
        data_retriever.get_msmall_prereqs(subject_info, args.output_study_dir)

    elif args.phase == "DEDRIFTANDRESAMPLE_PREREQS":
        data_retriever.get_dedriftandresample_prereqs(subject_info, args.output_study_dir)
        # Get the group average drift data
        # As of February 2017, the group average drift data has been moved from HCP_Staging to
        # HCP_1200
        data_retriever.get_msm_group_average_drift_data("HCP_1200", args.output_study_dir)

    elif args.phase == "REAPPLYFIX_PREREQS":
        data_retriever.get_reapplyfix_prereqs(subject_info, args.output_study_dir)

    if args.remove_non_subdirs:
        # remove any non-subdirectory data at the output study directory level
        data_retriever.remove_non_subdirs(args.output_study_dir)

if __name__ == '__main__':
    logging_config_file_name = file_utils.get_logging_config_file_name(__file__, use_env_variable=False)
    print("logging_config_file_name:", logging_config_file_name)

    logging.config.fileConfig(
        logging_config_file_name,
        disable_existing_loggers=False)
    main()

