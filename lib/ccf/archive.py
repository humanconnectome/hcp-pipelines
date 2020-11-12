#!/usr/bin/env python3

"""
ccf/archive.py: Provides direct access to a CCF project archive.
"""

# import of built-in modules
import glob
from glob import glob
import os


ARCHIVE_ROOT = os.getenv("XNAT_PBS_JOBS_ARCHIVE_ROOT")
BUILD_DIR = os.getenv("XNAT_PBS_JOBS_BUILD_DIR")


class CcfArchive(object):
    """
    This class provides access to a CCF project data archive.

    This access goes 'behind the scenes' and uses the actual underlying file
    system and assumes a particular organization of directories, resources, and
    file naming conventions. Because of this, a change in XNAT implementation
    or a change in conventions could cause this code to no longer be correct.
    """

    def __init__(self, project, subject, classifier, scan):
        self.SUBJECT_PROJECT = project
        self.SUBJECT_ID = subject
        self.SUBJECT_CLASSIFIER = classifier
        self.SUBJECT_EXTRA = scan
        self.SUBJECT_SESSION = subject + "_" + classifier + ""
        self.subject_resources = (
            ARCHIVE_ROOT
            + "/"
            + self.SUBJECT_PROJECT
            + "/arc001/"
            + self.SUBJECT_SESSION
            + "/RESOURCES"
        )

    # scan name property checking methods

    @staticmethod
    def project_resources_dir_full_path(project_id):
        """
        The full path to the project-level resources directory
        for the specified project
        """
        return ARCHIVE_ROOT + "/" + project_id + "/resources"

    # Unprocessed data paths and names

    def available_structural_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessed structural scans
        for the specified subject
        """
        return ls(self.subject_resources + "/T[12]w_*unproc")

    def available_structural_unproc_names(self):
        """
        List of names (not full paths) of structural unprocessed scans
        """
        dir_list = self.available_structural_unproc_dir_full_paths()
        name_list = scan_names_from_paths(dir_list)
        return name_list

    def available_t1w_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessed T1w scans
        for the specified subject
        """
        return ls(self.subject_resources + "/T1w_*unproc")

    def available_t1w_unproc_names(self):
        """
        List of names (not full paths) of T1w unprocessed scans
        """
        dir_list = self.available_t1w_unproc_dir_full_paths()
        name_list = scan_names_from_paths(dir_list)
        return name_list

    def available_t2w_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessed T2w scans
        for the specified subject
        """
        return ls(self.subject_resources + "/T2w_*unproc")

    def available_t2w_unproc_names(self):
        """
        List of names (not full paths) of T2w unprocessed scans
        """
        dir_list = self.available_t2w_unproc_dir_full_paths()
        name_list = scan_names_from_paths(dir_list)
        return name_list

    def available_functional_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessed functional scans
        for the specified subject
        """
        return ls(self.subject_resources + "/*fMRI*unproc")

    def available_functional_unproc_names(self):
        """
        List of names (not full paths) of functional scans

        If the full paths available are:

        /HCP/hcpdb/archive/HCP_Staging_7T/arc001/102311_7T/RESOURCES/rfMRI_REST1_PA_unproc
        /HCP/hcpdb/archive/HCP_Staging_7T/arc001/102311_7T/RESOURCES/rfMRI_REST2_AP_unproc
        /HCP/hcpdb/archive/HCP_Staging_7T/arc001/102311_7T/RESOURCES/tfMRI_RETCCW_AP_unproc

        then the scan names available are:

        rfMRI_REST1_PA
        rfMRI_REST2_AP
        tfMRI_RETCCW_AP
        """
        dir_list = self.available_functional_unproc_dir_full_paths()
        name_list = scan_names_from_paths(dir_list)
        return name_list

    def available_diffusion_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessing diffusion scans
        for the specified subject
        """
        return ls(self.subject_resources + "/Diffusion_unproc")

    def available_diffusion_unproc_names(self):
        """
        List of names (not full paths) of diffusion scan resources
        """
        dir_list = self.available_diffusion_unproc_dir_full_paths()
        name_list = scan_names_from_paths(dir_list)
        return name_list

    # preprocessed data paths and names

    def available_running_status_dir_full_paths(self):
        """
        List of full paths to the running status directories
        """
        return ls(self.subject_resources + "/RunningStatus")

    def available_hand_edit_full_paths(self):
        """
        List of full paths to any resource containing preprocessed functional data
        for the specified subject
        """
        return self.available_hand_edit_dir_full_paths()

    def available_structural_preproc_hand_edit_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        return ls(self.subject_resources + "/Structural_preproc_handedit")

    def available_structural_preproc_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        return ls(self.subject_resources + "/Structural_preproc")

    def available_supplemental_structural_preproc_dir_full_paths(self):
        """
        List of full paths to any resource containing supplemental preprocessed structural
        data for the specified subject
        """
        return ls(self.subject_resources + "/Structural_preproc/supplemental")

    def available_hand_edit_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        return ls(self.subject_resources + "/Structural_Hand_Edit")

    def available_diffusion_preproc_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed diffusion data
        for the specified subject
        """
        return ls(self.subject_resources + "/Diffusion_preproc")

    def available_functional_preproc_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed functional data
        for the specified subject
        """
        return ls(self.subject_resources + "/*fMRI*preproc")

    def available_functional_preproc_names(self):
        """
        List of names (not full paths) of functional scans that have been preprocessed
        """
        dir_list = self.available_functional_preproc_dir_full_paths()
        name_list = scan_names_from_paths(dir_list)
        return name_list

    # processed data paths and names

    def available_msmall_registration_dir_full_paths(self):
        """
        List of full paths to any resource containing msmall registration results
        data for the specified subject
        """
        return ls(self.subject_resources + "/MSMAllReg")

    def available_multirun_icafix_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed diffusion data
        for the specified subject
        """
        return ls(self.subject_resources + "/MultiRunIcaFix_proc")

    def available_fix_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing FIX processed results data
        for the specified subject
        """
        return ls(self.subject_resources + "/*FIX")

    def available_msmall_dedrift_and_resample_dir_full_paths(self):
        """
        List of full paths to any resource containing msmall dedrift and resample results
        data for the specified subject
        """
        return ls(self.subject_resources + "/MSMAllDeDrift")

    def available_rss_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing RestingStateStats processed results data
        for the specified subject
        """
        return ls(self.subject_resources + "/*RSS")

    def available_postfix_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing PostFix processed results data
        for the specified subject
        """
        return ls(self.subject_resources + "/*PostFix")

    def available_task_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing Task Analysis processed results data
        for the specified subject
        """
        dir_list = ls(self.subject_resources + "/tfMRI*")
        return sorted([d for d in dir_list if os.path.basename(d).count("_") <= 1])

    def available_bedpostx_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing bedpostx processed results data
        for the specified subject
        """
        return ls(self.subject_resources + "/Diffusion_bedpostx")

    def available_reapplyfix_names(self, reg_name=None):
        if not reg_name:
            reg_name = ""
        dir_list = ls(self.subject_resources + "/*ReApplyFix" + reg_name)
        return scan_names_from_paths(dir_list)


def ls(path_expression):
    items = glob.glob(path_expression)
    return sorted(items)


def _get_scan_name_from_path(path):
    basename = os.path.basename(path)
    last_position = basename.rfind("_")
    scan_name = basename[:last_position]
    return scan_name


def scan_names_from_paths(dir_list):
    return [_get_scan_name_from_path(d) for d in dir_list]


def is_resting_state_scan_name(scan_name):
    """
    Return an indication of whether the specified name is for a
    resting state scan
    """
    return scan_name.startswith("rfMRI")


def is_task_scan_name(scan_name):
    """
    Return an indication of whethe the specified name is for a
    task scan
    """
    return scan_name.startswith("tfMRI")
