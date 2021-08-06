#!/usr/bin/env python3
"""
ccf.get_cinab_style_data.py: Get (copy or link) a CinaB style directory tree of data
for a specified subject within a specified project.
"""

import glob
import logging.config
import os
import subprocess
import sys
import ccf.archive as ccf_archive
import utils.debug_utils as debug_utils
import utils.file_utils as file_utils
import argparse
import utils.os_utils as os_utils

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2019, Connectome Coordination Facility"
__maintainer__ = "Junil Chang"

# create a module logger
module_logger = logging.getLogger(__name__)
module_logger.setLevel(
    logging.WARNING
)  # Note: This can be overridden by log file configuration
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(logging.Formatter("%(name)s: %(message)s"))
module_logger.addHandler(sh)


def copy_with_rsync(get_from, put_to, show_log=True):
    if show_log:
        rsync_cmd = "rsync -auLv "
    else:
        rsync_cmd = "rsync -auL "
    rsync_cmd += get_from + "/* " + put_to
    module_logger.debug(debug_utils.get_name() + " rsync_cmd: " + rsync_cmd)
    completed_rsync_process = subprocess.run(
        rsync_cmd,
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    module_logger.debug(
        debug_utils.get_name() + " stdout: " + completed_rsync_process.stdout
    )


def link_directory(get_from, put_to, show_log=True):
    module_logger.debug(
        debug_utils.get_name() + " linking " + put_to + " to " + get_from
    )
    os_utils.lndir(get_from, put_to, show_log, ignore_existing_dst_files=True)


class DataRetriever(object):
    def __init__(
        self,
        project,
        subject,
        classifier,
        scan,
        copy,
        log,
        output_dir,
        ARCHIVE_ROOT,
    ):
        self.SUBJECT = subject
        session = f"{subject}_{classifier}"
        self.SESSION = session
        self.archive = ccf_archive.CcfArchive(project, session, ARCHIVE_ROOT)
        self.output_dir = output_dir
        self.copy = copy
        self.show_log = log

    def run(self, *funcs):
        funcs = list(funcs)
        if self.copy:
            # when copying (via rsync), data should be retrieved in chronological order
            # (i.e. the order in which the pipelines are run)
            pass
        else:
            # when creating symbolic links, data should be
            # retrieved in reverse chronological order
            funcs.reverse()
        for fn in funcs:
            if not (fn is None):
            	fn()

    def remove_non_subdirs(self):
        cmd = [
            "find",
            self.output_dir,
            "-maxdepth",
            "1",
            "-not",
            "-type",
            "d",
            "-delete",
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, universal_newlines=True)

    def _from_to(self, source, destination):
        os.makedirs(destination, exist_ok=True)
        if self.copy:
            copy_with_rsync(source, destination, self.show_log)
        else:
            link_directory(source, destination, self.show_log)

    def _get_unprocessed_data(self, directories):
        for get_from in directories:
            module_logger.debug(debug_utils.get_name() + " get_from: " + get_from)

            base = os.path.basename(get_from)
            sub_dir = base[: base.rfind("_unproc")]
            put_to = (
                self.output_dir + "/" + self.SESSION + "/unprocessed/" + sub_dir
            )
            module_logger.debug(debug_utils.get_name() + "   put_to: " + put_to)

            self._from_to(get_from, put_to)

    def _get_preprocessed_data(self, directories):
        for directory in directories:
            get_from = directory
            module_logger.debug(debug_utils.get_name() + " get_from: " + get_from)

            put_to = self.output_dir
            module_logger.debug(debug_utils.get_name() + "   put_to: " + put_to)

            self._from_to(get_from, put_to)

    def _get_processed_data(self, directories):
        for directory in directories:
            get_from = directory
            module_logger.debug(debug_utils.get_name() + " get_from: " + get_from)

            put_to = self.output_dir
            module_logger.debug(debug_utils.get_name() + "   put_to: " + put_to)

            self._from_to(get_from, put_to)

    # get unprocessed data
    def get_structural_unproc_data(self):
        module_logger.debug(debug_utils.get_name())
        self._get_unprocessed_data(
            self.archive.structural_unproc(),
        )

    def get_functional_unproc_data(self, extra=None):
        module_logger.debug(debug_utils.get_name())
        self._get_unprocessed_data(
            self.archive.functional_unproc(extra),
        )

    def get_diffusion_unproc_data(self):
        module_logger.debug(debug_utils.get_name())
        self._get_unprocessed_data(
            self.archive.diffusion_unproc(),
        )

    def get_asl_unproc_data(self):
        module_logger.debug(debug_utils.get_name())
        self._get_unprocessed_data(
            self.archive.asl_unproc(),
        )

    def get_unproc_data(self):
        self.run(
            self.get_structural_unproc_data,
            self.get_functional_unproc_data,
            self.get_diffusion_unproc_data,
        )

    # get preprocessed data

    def get_structural_preproc_data(self):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(
            self.archive.structural_preproc(),
        )

    def get_icafix_data(self):
        module_logger.debug(debug_utils.get_name())
        self._get_processed_data(
            self.archive.multirun_icafix(),
        )

    def get_supplemental_structural_preproc_data(self):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(
            self.archive.supplemental_structural_preproc(),
        )

    def get_hand_edit_data(self):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(self.archive.hand_edit())

    def get_functional_preproc_data(self, extra=None):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(
            self.archive.functional_preproc(extra),
        )

    def get_diffusion_preproc_data(self):
        module_logger.debug(debug_utils.get_name())
        self._get_preprocessed_data(
            self.archive.diffusion_preproc(),
        )

    def get_preproc_data(self):
        self.run(
            self.get_structural_preproc_data,
            self.get_supplemental_structural_preproc_data,
            self.get_functional_preproc_data,
            self.get_diffusion_preproc_data,
        )

    # get processed data
    def get_msmall_processed_data(self):
        module_logger.debug(debug_utils.get_name())

        self._get_processed_data(
            self.archive.msmall_proc()
        )

    def get_msmall_registration_data(self):
        module_logger.debug(debug_utils.get_name())

        self._get_processed_data(
            self.archive.msmall_registration(),
        )

    def get_fix_processed_data(self):
        module_logger.debug(debug_utils.get_name())

        self._get_processed_data(
            self.archive.fix_processed(),
        )

    def get_dedriftandresample_processed_data(self):
        module_logger.debug(debug_utils.get_name())

        self._get_processed_data(
            self.archive.msmall_dedrift_and_resample(),
        )

    def get_resting_state_stats_data(self):
        module_logger.debug(debug_utils.get_name())

        self._get_processed_data(
            self.archive.rss_processed(),
        )

    def get_postfix_data(self):
        self._get_processed_data(
            self.archive.postfix_processed(),
        )

    def get_taskfmri_data(self):
        self._get_processed_data(
            self.archive.task_processed(),
        )

    def get_bedpostx_data(self):
        self._get_processed_data(
            self.archive.bedpostx_processed(),
        )

    # prerequisites data for specific pipelines

    def _copy_some_dedriftandresample_links(self):
        """
        Some files that already exist prior to running the DeDriftAndResample pipeline
        are opened for writing/modification by the pipeline script. If these files are
        left as symbolic links to files in the archive, they will not be able to be
        opened for writing. Each of these files needs to be copied instead of linked.
        """

        output_dir = self.output_dir
        session = self.SESSION
        subject_id = self.SUBJECT
        t1w_native_spec_file = (
            f"{output_dir}/{session}/T1w/Native/{subject_id}.native.wb.spec"
        )
        file_utils.make_link_into_copy(t1w_native_spec_file, verbose=True)

        native_spec_file = (
            f"{output_dir}/{session}/MNINonLinear/Native/{subject_id}.native.wb.spec"
        )
        file_utils.make_link_into_copy(native_spec_file, verbose=True)

    def _remove_some_dedriftandresample_ica_files(self):
        """
        Some files need to be re-created by the ReApplyFixPipeline.sh script which
        is invoked by the DeDriftAndResample pipeline. For the ReApplyFixPipeline
        to work correctly, those files need to be removed before processing begins.
        """
        path_expr = self.output_dir + "/" + self.SESSION
        path_expr += "/MNINonLinear/Results/*"

        dir_list = sorted(glob.glob(path_expr))

        for dir in dir_list:
            ica_dir_expr = dir + "/*.ica"
            ica_dir_list = sorted(glob.glob(ica_dir_expr))

            for ica_dir in ica_dir_list:
                atlas_dtseries_file = ica_dir + "/Atlas.dtseries.nii"
                file_utils.rm_file_if_exists(atlas_dtseries_file, verbose=True)

                atlas_file = ica_dir + "/Atlas.nii.gz"
                file_utils.rm_file_if_exists(atlas_file, verbose=True)

                filtered_func_data_file = ica_dir + "/filtered_func_data.nii.gz"
                file_utils.rm_file_if_exists(filtered_func_data_file, verbose=True)

                mc_dir = ica_dir + "/mc"
                file_utils.rm_dir_if_exists(mc_dir, verbose=True)

                atlas_preclean_dtseries_file = (
                    ica_dir + "/Atlas_hp_preclean.dtseries.nii"
                )
                file_utils.rm_file_if_exists(atlas_preclean_dtseries_file, verbose=True)

    def get_msm_group_average_drift_data(self, project_id):
        """
        Get the group average drift data stored in the specified project
        """
        get_from = self.archive.project_resources_dir_full_path(project_id)
        get_from += "/MSMAllDeDrift"
        put_to = self.output_dir

        self._from_to(get_from, put_to)

    def _copy_some_reapplyfix_links(self):
        """
        Some files that already exist prio to running the ReApplyFix pipeline are
        opened for writing/modification by the pipeline script. If these files are
        left as symbolic links to file in the archive, they will not be able to be
        opened for writing. Each of these files need to be copied instead of linked.
        """

        # find all paths that end with '.ica'
        paths = glob.iglob(self.output_dir + "/**/*.ica", recursive=True)
        for path in paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_to_copy = os.path.join(root, file)
                        file_utils.make_link_into_copy(file_to_copy, verbose=True)


class PipelinePrereqDownloader:
    """
    Get the data necessary to run the specific pipelines
    """

    def __init__(
        self,
        project,
        subject,
        classifier,
        scan,
        copy,
        log,
        output_dir,
        ARCHIVE_ROOT,
    ):
        self.data_retriever = DataRetriever(
            project,
            subject,
            classifier,
            scan,
            copy,
            log,
            output_dir,
            ARCHIVE_ROOT,
        )

    def asl(self):
        print("Getting prereq data for the ASL pipeline.")
        r = self.data_retriever
        r.run(
            r.get_asl_unproc_data,
            r.get_structural_preproc_data,
            r.get_msmall_processed_data,
        )

    def struct(self):
        print("Getting prereq data for the Structural pipeline.")
        r = self.data_retriever
        r.run(r.get_structural_unproc_data)

    def struct_hand_edit(self):
        print("Getting prereq data for the Structural HandEditting pipeline.")
        r = self.data_retriever
        r.run(
            # r.get_structural_unproc_data,
            r.get_structural_preproc_data,
            r.get_hand_edit_data,
            r.get_supplemental_structural_preproc_data,
        )

    def diffusion(self):
        print("Getting prereq data for the Diffusion pipeline.")
        r = self.data_retriever
        r.run(
            r.get_diffusion_unproc_data,
            r.get_structural_preproc_data,
            r.get_supplemental_structural_preproc_data,
        )

    def functional(self, extra=None):
        print("Getting prereq data for the Functional pipeline.")
        r = self.data_retriever
        r.run(
            r.get_functional_unproc_data(extra),
            r.get_structural_preproc_data,
            r.get_supplemental_structural_preproc_data,
        )

    def multirunicafix(self):
        print("Getting prereq data for the Multi-run ICA Fix pipeline.")
        r = self.data_retriever
        r.run(
            r.get_preproc_data,
        )

    def msmall(self):
        print("Getting prereq data for the Msm-All pipeline.")
        r = self.data_retriever
        r.run(
            r.get_preproc_data,
            r.get_icafix_data,
        )

    def dedriftandresample(self):
        print("Getting prereq data for the Dedrift & Resample pipeline.")
        r = self.data_retriever
        r.run(
            r.get_preproc_data,
            r.get_fix_processed_data,
            r.get_msmall_registration_data,
        )

        if not r.copy:
            r._copy_some_dedriftandresample_links()
        r._remove_some_dedriftandresample_ica_files()

        # Get the group average drift data
        # As of February 2017, the group average drift data has been moved from HCP_Staging to
        # HCP_1200
        r.get_msm_group_average_drift_data("HCP_1200")

    def task(self, extra=None):
        print("Getting prereq data for the Task fMRI pipeline.")
        r = self.data_retriever
        r.run(
            r.get_structural_preproc_data,
            r.get_functional_preproc_data(extra),
            r.get_icafix_data,
        )

    def reapplyfix(self):
        print("Getting prereq data for the ReapplyFix pipeline.")
        self.all_pipeline_data()
        self.data_retriever._copy_some_reapplyfix_links()

    def all_pipeline_data(self):
        print("Getting all pipeline data...")
        r = self.data_retriever
        r.run(
            r.get_unproc_data,
            r.get_preproc_data,
            r.get_fix_processed_data,
            r.get_msmall_registration_data,
            r.get_dedriftandresample_processed_data,
            r.get_resting_state_stats_data,
            r.get_postfix_data,
            r.get_taskfmri_data,
            r.get_bedpostx_data,
        )

    def get_data_for_pipeline(self, pipeline, extra=None, remove_non_subdirs=False):
        pipeline = pipeline.lower().replace("_", "").replace(" ", "")

        if "asl" in pipeline:
            self.asl()
        elif "handedit" in pipeline:
            self.struct_hand_edit()
        elif "struct" in pipeline:
            self.struct()
        elif "diff" in pipeline:
            self.diffusion()
        elif "func" in pipeline:
            self.functional(extra)
        elif "icafix" in pipeline:
            self.multirunicafix()
        elif "msmall" in pipeline:
            self.msmall()
        elif "dedrift" in pipeline:
            self.dedriftandresample()
        elif "reapplyfix" in pipeline:
            self.reapplyfix()
        elif "task" in pipeline:
            self.task(extra)

        if remove_non_subdirs:
            # remove any non-subdirectory data at the output study directory level
            self.data_retriever.remove_non_subdirs()


def main():
    # create a parser object for getting the command line arguments
    parser = argparse.ArgumentParser()

    # mandatory arguments
    parser.add_argument("-p", "--project", dest="project", required=True, type=str)
    parser.add_argument("-s", "--subject", dest="subject", required=True, type=str)
    parser.add_argument(
        "-d", "--study-dir", dest="output_study_dir", required=True, type=str
    )

    # optional arguments
    parser.add_argument(
        "-a", "--scan", dest="scan", required=False, type=str, default=None
    )
    parser.add_argument(
        "-c", "--copy", dest="copy", action="store_true", required=False, default=False
    )
    parser.add_argument(
        "-l", "--log", dest="log", action="store_true", required=False, default=False
    )
    parser.add_argument(
        "-r",
        "--remove-non-subdirs",
        dest="remove_non_subdirs",
        action="store_true",
        required=False,
        default=False,
    )

    parser.add_argument("-ph", "--phase", dest="phase", required=True, type=str)

    parser.add_argument(
        "-cl",
        "--classifier",
        dest="session_classifier",
        required=False,
        type=str,
        default="3T",
    )

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

    prereq = PipelinePrereqDownloader(
        args.project,
        args.subject,
        args.session_classifier,
        args.scan,
        args.copy,
        args.log,
        args.output_study_dir,
        os.getenv("ARCHIVE_ROOT"),
    )

    prereq.get_data_for_pipeline(args.phase, args.remove_non_subdirs)


if __name__ == "__main__":
    logging_config_file_name = file_utils.get_logging_config_file_name(
        __file__, use_env_variable=False
    )
    print("logging_config_file_name:", logging_config_file_name)

    logging.config.fileConfig(logging_config_file_name, disable_existing_loggers=False)
    main()
