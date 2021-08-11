#!/usr/bin/env python3

"""
ccf/archive.py: Provides direct access to a CCF project archive.
"""

# import of built-in modules
import glob
import os
from pathlib import Path


class CcfArchive(object):
    """
    This class provides access to a CCF project data archive.

    This access goes 'behind the scenes' and uses the actual underlying file
    system and assumes a particular organization of directories, resources, and
    file naming conventions. Because of this, a change in XNAT implementation
    or a change in conventions could cause this code to no longer be correct.
    """

    def __init__(self, project, session, ARCHIVE_ROOT):
        self.ARCHIVE_ROOT = Path(ARCHIVE_ROOT)
        self.SESSION_RESOURCES = self.ARCHIVE_ROOT / project / "arc001" / session / "RESOURCES"

    def get_resource_path(self, path_expression, extra=None):
        files = sorted(self.SESSION_RESOURCES.glob(path_expression))

        if type(extra) is not str or extra.upper() == 'ALL':
            return files
        else:
            scans = extra.split("@")
            return [x for individual_scan in scans for x in files if x.name.startswith(individual_scan)]

    # Unprocessed data paths and names

    def reapplyfix(self):
        return self.get_resource_path("*ReApplyFix")

    def structural_unproc(self):
        return self.get_resource_path("T[12]w_*unproc")

    def t1w_unproc(self):
        return self.get_resource_path("T1w_*unproc")

    def t2w_unproc(self):
        return self.get_resource_path("T2w_*unproc")

    def functional_unproc(self, extra=None):
        return self.get_resource_path("*fMRI*unproc", extra)

    def diffusion_unproc(self):
        return self.get_resource_path("Diffusion_unproc")

    def asl_unproc(self):
        return self.get_resource_path("mbPCASLhr_unproc")

    # preprocessed data paths and names

    def running_status(self):
        return self.get_resource_path("RunningStatus")

    def structural_preproc_hand_edit(self):
        return self.get_resource_path("Structural_preproc_handedit")

    def structural_preproc(self):
        return self.get_resource_path("Structural_preproc")

    def supplemental_structural_preproc(self):
        return self.get_resource_path("Structural_preproc/supplemental")

    def hand_edit(self):
        return self.get_resource_path("Structural_Hand_Edit")

    def diffusion_preproc(self):
        return self.get_resource_path("Diffusion_preproc")

    def functional_preproc(self, extra=None):
        return self.get_resource_path("*fMRI*preproc", extra)

    # processed data paths and names

    def msmall_registration(self):
        return self.get_resource_path("MSMAllReg")

    def msmall_proc(self):
        return self.get_resource_path("MsmAll_proc")

    def multirun_icafix(self):
        return self.get_resource_path("MultiRunIcaFix_proc")

    def fix_processed(self):
        return self.get_resource_path("*FIX")

    def msmall_dedrift_and_resample(self):
        return self.get_resource_path("MSMAllDeDrift")

    def rss_processed(self):
        return self.get_resource_path("*RSS")

    def postfix_processed(self):
        return self.get_resource_path("*PostFix")

    def task_processed(self):
        dir_list = self.get_resource_path("tfMRI*")
        return [d for d in dir_list if d.name.count("_") <= 1]

    def bedpostx_processed(self):
        return self.get_resource_path("Diffusion_bedpostx")

    def project_resources_dir_full_path(self, project_id):
        return self.ARCHIVE_ROOT / project_id / "resources"


