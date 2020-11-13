#!/usr/bin/env python3

"""
ccf/archive.py: Provides direct access to a CCF project archive.
"""

# import of built-in modules
import glob
from glob import glob
import os


class _ArchiveScanNames:
    def __init__(self, archive):
        self.archive = archive

    def structural_unproc(self):
        return scan_names_from_paths(self.archive.structural_unproc())

    def t1w_unproc(self):
        return scan_names_from_paths(self.archive.t1w_unproc())

    def t2w_unproc(self):
        return scan_names_from_paths(self.archive.t2w_unproc())

    def functional_unproc(self):
        return scan_names_from_paths(self.archive.functional_unproc())

    def diffusion_unproc(self):
        return scan_names_from_paths(self.archive.diffusion_unproc())

    def functional_preproc(self):
        return scan_names_from_paths(self.archive.functional_preproc())

    def reapplyfix(self):
        return scan_names_from_paths(self.archive.reapplyfix())


class CcfArchive(object):
    """
    This class provides access to a CCF project data archive.

    This access goes 'behind the scenes' and uses the actual underlying file
    system and assumes a particular organization of directories, resources, and
    file naming conventions. Because of this, a change in XNAT implementation
    or a change in conventions could cause this code to no longer be correct.
    """

    def __init__(self, project, session, XNAT_PBS_JOBS_ARCHIVE_ROOT):
        self.ARCHIVE_ROOT = XNAT_PBS_JOBS_ARCHIVE_ROOT
        self.subject_resources = (
            f"{XNAT_PBS_JOBS_ARCHIVE_ROOT}/{project}/arc001/{session}/RESOURCES"
        )
        self.scans = _ArchiveScanNames(self)

    # Unprocessed data paths and names

    def reapplyfix(self):
        return ls(self.subject_resources + "/*ReApplyFix")

    def structural_unproc(self):
        """
        List of full paths to any resources containing unprocessed structural scans
        for the specified subject
        """
        return ls(self.subject_resources + "/T[12]w_*unproc")

    def t1w_unproc(self):
        """
        List of full paths to any resources containing unprocessed T1w scans
        for the specified subject
        """
        return ls(self.subject_resources + "/T1w_*unproc")

    def t2w_unproc(self):
        """
        List of full paths to any resources containing unprocessed T2w scans
        for the specified subject
        """
        return ls(self.subject_resources + "/T2w_*unproc")

    def functional_unproc(self):
        """
        List of full paths to any resources containing unprocessed functional scans
        for the specified subject
        """
        return ls(self.subject_resources + "/*fMRI*unproc")

    def diffusion_unproc(self):
        """
        List of full paths to any resources containing unprocessing diffusion scans
        for the specified subject
        """
        return ls(self.subject_resources + "/Diffusion_unproc")

    # preprocessed data paths and names

    def running_status(self):
        """
        List of full paths to the running status directories
        """
        return ls(self.subject_resources + "/RunningStatus")

    def structural_preproc_hand_edit(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        return ls(self.subject_resources + "/Structural_preproc_handedit")

    def structural_preproc(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        return ls(self.subject_resources + "/Structural_preproc")

    def supplemental_structural_preproc(self):
        """
        List of full paths to any resource containing supplemental preprocessed structural
        data for the specified subject
        """
        return ls(self.subject_resources + "/Structural_preproc/supplemental")

    def hand_edit(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        return ls(self.subject_resources + "/Structural_Hand_Edit")

    def diffusion_preproc(self):
        """
        List of full paths to any resource containing preprocessed diffusion data
        for the specified subject
        """
        return ls(self.subject_resources + "/Diffusion_preproc")

    def functional_preproc(self):
        """
        List of full paths to any resource containing preprocessed functional data
        for the specified subject
        """
        return ls(self.subject_resources + "/*fMRI*preproc")

    # processed data paths and names

    def msmall_registration(self):
        """
        List of full paths to any resource containing msmall registration results
        data for the specified subject
        """
        return ls(self.subject_resources + "/MSMAllReg")

    def multirun_icafix(self):
        """
        List of full paths to any resource containing preprocessed diffusion data
        for the specified subject
        """
        return ls(self.subject_resources + "/MultiRunIcaFix_proc")

    def fix_processed(self):
        """
        List of full paths to any resource containing FIX processed results data
        for the specified subject
        """
        return ls(self.subject_resources + "/*FIX")

    def msmall_dedrift_and_resample(self):
        """
        List of full paths to any resource containing msmall dedrift and resample results
        data for the specified subject
        """
        return ls(self.subject_resources + "/MSMAllDeDrift")

    def rss_processed(self):
        """
        List of full paths to any resource containing RestingStateStats processed results data
        for the specified subject
        """
        return ls(self.subject_resources + "/*RSS")

    def postfix_processed(self):
        """
        List of full paths to any resource containing PostFix processed results data
        for the specified subject
        """
        return ls(self.subject_resources + "/*PostFix")

    def task_processed(self):
        """
        List of full paths to any resource containing Task Analysis processed results data
        for the specified subject
        """
        dir_list = ls(self.subject_resources + "/tfMRI*")
        return sorted([d for d in dir_list if os.path.basename(d).count("_") <= 1])

    def bedpostx_processed(self):
        """
        List of full paths to any resource containing bedpostx processed results data
        for the specified subject
        """
        return ls(self.subject_resources + "/Diffusion_bedpostx")

    def project_resources_dir_full_path(self, project_id):
        """
        The full path to the project-level resources directory
        for the specified project
        """
        return self.ARCHIVE_ROOT + "/" + project_id + "/resources"


def ls(path_expression):
    items = glob.glob(path_expression)
    return sorted(items)


def _get_scan_name_from_path(path):
    basename = os.path.basename(path)
    last_position = basename.rfind("_")
    scan_name = basename[:last_position]
    return scan_name


def scan_names_from_paths(dir_list):
    """List of names (not full paths) of scans

    If the full paths available are:

    /HCP/hcpdb/archive/HCP_Staging_7T/arc001/102311_7T/RESOURCES/rfMRI_REST1_PA_unproc
    /HCP/hcpdb/archive/HCP_Staging_7T/arc001/102311_7T/RESOURCES/rfMRI_REST2_AP_unproc
    /HCP/hcpdb/archive/HCP_Staging_7T/arc001/102311_7T/RESOURCES/tfMRI_RETCCW_AP_unproc

    then the scan names available are:

    rfMRI_REST1_PA
    rfMRI_REST2_AP
    tfMRI_RETCCW_AP
    """
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
