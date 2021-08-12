#!/usr/bin/env python3
"""
ccf.get_cinab_style_data.py: Get (copy or link) a CinaB style directory tree of data
for a specified subject within a specified project.
"""

import glob
import os
import subprocess
import sys
import ccf.archive as ccf_archive
import utils.debug_utils as debug_utils
import utils.file_utils as file_utils
import utils.os_utils as os_utils

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2019, Connectome Coordination Facility"
__maintainer__ = "Junil Chang"



def link_directory(get_from, put_to, show_log=True):
    os_utils.lndir(get_from, put_to, show_log, ignore_existing_dst_files=True)


class DataRetriever(object):
    def __init__(
        self,
        project,
        subject,
        classifier,
        scan,
        log,
        output_dir,
        ARCHIVE_ROOT,
    ):
        self.SUBJECT = subject
        session = f"{subject}_{classifier}"
        self.SESSION = session
        self.archive = ccf_archive.CcfArchive(project, session, ARCHIVE_ROOT)
        self.output_dir = output_dir
        self.show_log = log


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
        self._get_unprocessed_data(
            self.archive.structural_unproc(),
        )

    def get_functional_unproc_data(self, extra=None):
        self._get_unprocessed_data(
            self.archive.functional_unproc(extra),
        )

    def get_diffusion_unproc_data(self):
        self._get_unprocessed_data(
            self.archive.diffusion_unproc(),
        )

    def get_asl_unproc_data(self):
        self._get_unprocessed_data(
            self.archive.asl_unproc(),
        )

    def get_unproc_data(self):
        self.get_diffusion_unproc_data()
        self.get_functional_unproc_data()
        self.get_structural_unproc_data()

    # get preprocessed data

    def get_structural_preproc_data(self):
        self._get_preprocessed_data(
            self.archive.structural_preproc(),
        )

    def get_icafix_data(self):
        self._get_processed_data(
            self.archive.multirun_icafix(),
        )

    def get_supplemental_structural_preproc_data(self):
        self._get_preprocessed_data(
            self.archive.supplemental_structural_preproc(),
        )

    def get_hand_edit_data(self):
        self._get_preprocessed_data(self.archive.hand_edit())

    def get_functional_preproc_data(self, extra=None):
        self._get_preprocessed_data(
            self.archive.functional_preproc(extra),
        )

    def get_diffusion_preproc_data(self):
        self._get_preprocessed_data(
            self.archive.diffusion_preproc(),
        )

    def get_preproc_data(self):
        self.get_diffusion_preproc_data()
        self.get_functional_preproc_data()
        self.get_supplemental_structural_preproc_data()
        self.get_structural_preproc_data()

    # get processed data
    def get_msmall_processed_data(self):
        self._get_processed_data(
            self.archive.msmall_proc()
        )

    def get_msmall_registration_data(self):
        self._get_processed_data(
            self.archive.msmall_registration(),
        )

    def get_fix_processed_data(self):
        self._get_processed_data(
            self.archive.fix_processed(),
        )

    def get_dedriftandresample_processed_data(self):
        self._get_processed_data(
            self.archive.msmall_dedrift_and_resample(),
        )

    def get_resting_state_stats_data(self):
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
        log,
        output_dir,
        ARCHIVE_ROOT,
    ):
        self.data_retriever = DataRetriever(
            project,
            subject,
            classifier,
            scan,
            log,
            output_dir,
            ARCHIVE_ROOT,
        )

    def asl(self):
        print("Getting prereq data for the ASL pipeline.")
        r = self.data_retriever
        r.get_msmall_processed_data()
        r.get_structural_preproc_data()
        r.get_asl_unproc_data()

    def struct(self):
        print("Getting prereq data for the Structural pipeline.")
        r = self.data_retriever
        r.get_structural_unproc_data()

    def struct_hand_edit(self):
        print("Getting prereq data for the Structural HandEditting pipeline.")
        r = self.data_retriever
        r.get_supplemental_structural_preproc_data()
        r.get_hand_edit_data()
        r.get_structural_preproc_data()
        # r.get_structural_unproc_data()

    def diffusion(self):
        print("Getting prereq data for the Diffusion pipeline.")
        r = self.data_retriever
        r.get_supplemental_structural_preproc_data()
        r.get_structural_preproc_data()
        r.get_diffusion_unproc_data()

    def functional(self, extra=None):
        print("Getting prereq data for the Functional pipeline.")
        r = self.data_retriever
        r.get_supplemental_structural_preproc_data()
        r.get_structural_preproc_data()
        r.get_functional_unproc_data(extra)()

    def multirunicafix(self):
        print("Getting prereq data for the Multi-run ICA Fix pipeline.")
        r = self.data_retriever
        r.get_preproc_data()

    def msmall(self):
        print("Getting prereq data for the Msm-All pipeline.")
        r = self.data_retriever
        r.get_icafix_data()
        r.get_preproc_data()

    def task(self, extra=None):
        print("Getting prereq data for the Task fMRI pipeline.")
        r = self.data_retriever
        r.get_icafix_data()
        r.get_functional_preproc_data(extra)()
        r.get_structural_preproc_data()


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
        elif "task" in pipeline:
            self.task(extra)

        if remove_non_subdirs:
            # remove any non-subdirectory data at the output study directory level
            self.data_retriever.remove_non_subdirs()
