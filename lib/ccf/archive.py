#!/usr/bin/env python3

"""
ccf/archive.py: Provides direct access to a CCF project archive.
"""

# import of built-in modules
import glob
import os

UNPROC_SUFFIX = "unproc"
PREPROC_SUFFIX = "preproc"
FUNCTIONAL_SCAN_MARKER = "fMRI"
RESTING_STATE_SCAN_MARKER = "rfMRI"
TASK_SCAN_MARKER = "tfMRI"
FIX_PROCESSED_SUFFIX = "FIX"
RSS_PROCESSED_SUFFIX = "RSS"
POSTFIX_PROCESSED_SUFFIX = "PostFix"
REAPPLY_FIX_SUFFIX = "ReApplyFix"

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
        self.SUBJECT_SESSION = f"{subject}_{classifier}"

    def session_dir_full_path(self):
        """
        The full path to the conventional session directory for a subject
        in this project archive
        """
        session_dir = f"{ARCHIVE_ROOT}/{self.SUBJECT_PROJECT}/arc001"
        session_dir += "/" + self.SUBJECT_SESSION
        return session_dir

    def subject_resources_dir_full_path(self):
        """
        The full path to the conventional subject-level resources
        directory for a subject in this project archive
        """
        return self.session_dir_full_path() + "/" + "RESOURCES"

    def project_resources_dir_full_path(self, project_id):
        """
        The full path to the project-level resources directory
        for the specified project
        """
        return f"{ARCHIVE_ROOT}/{project_id}/resources"

    # scan name property checking methods

    def is_resting_state_scan_name(self, scan_name):
        """
        Return an indication of whether the specified name is for a
        resting state scan
        """
        return scan_name.startswith(RESTING_STATE_SCAN_MARKER)

    def is_task_scan_name(self, scan_name):
        """
        Return an indication of whethe the specified name is for a
        task scan
        """
        return scan_name.startswith(TASK_SCAN_MARKER)

    # Unprocessed data paths and names

    def available_structural_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessed structural scans
        for the specified subject
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "T[12]w" + "_" + "*" + UNPROC_SUFFIX
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_structural_unproc_names(self):
        """
        List of names (not full paths) of structural unprocessed scans
        """
        dir_list = self.available_structural_unproc_dir_full_paths()
        name_list = self._get_scan_names_from_full_paths(dir_list)
        return name_list

    def available_t1w_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessed T1w scans
        for the specified subject
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "T1w" + "_" + "*" + UNPROC_SUFFIX
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_t1w_unproc_names(self):
        """
        List of names (not full paths) of T1w unprocessed scans
        """
        dir_list = self.available_t1w_unproc_dir_full_paths()
        name_list = self._get_scan_names_from_full_paths(dir_list)
        return name_list

    def available_t2w_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessed T2w scans
        for the specified subject
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "T2w" + "_" + "*" + UNPROC_SUFFIX
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_t2w_unproc_names(self):
        """
        List of names (not full paths) of T2w unprocessed scans
        """
        dir_list = self.available_t2w_unproc_dir_full_paths()
        name_list = self._get_scan_names_from_full_paths(dir_list)
        return name_list

    def available_functional_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessed functional scans
        for the specified subject
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "*" + FUNCTIONAL_SCAN_MARKER + "*" + UNPROC_SUFFIX
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

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
        name_list = self._get_scan_names_from_full_paths(dir_list)
        return name_list

    def diffusion_unproc_dir_full_path(self):
        """
        Full path to the unprocessed diffusion data resource directory
        """
        path = self.subject_resources_dir_full_path()
        path += "/" + "Diffusion" + "_" + UNPROC_SUFFIX
        return path

    def available_diffusion_unproc_dir_full_paths(self):
        """
        List of full paths to any resources containing unprocessing diffusion scans
        for the specified subject
        """
        dir_list = glob.glob(self.diffusion_unproc_dir_full_path())
        return sorted(dir_list)

    def available_diffusion_unproc_names(self):
        """
        List of names (not full paths) of diffusion scan resources
        """
        dir_list = self.available_diffusion_unproc_dir_full_paths()
        name_list = self._get_scan_names_from_full_paths(dir_list)
        return name_list

    def running_status_dir_full_path(self):
        """
        Full path to the running status resource directory
        """
        path = self.subject_resources_dir_full_path()
        path += "/" + "RunningStatus"
        return path

    def available_running_status_dir_full_paths(self):
        """
        List of full paths to the running status directories
        """
        dir_list = glob.glob(self.running_status_dir_full_path())
        return sorted(dir_list)

    # preprocessed data paths and names

    def structural_preproc_dir_full_path(self):
        """
        Full path to structural preproc resource directory
        """
        path_expr = self.subject_resources_dir_full_path() + "/"
        path_expr += self.structural_preproc_dir_name()
        return path_expr

    def structural_preproc_dir_name(self):
        name = "Structural" + "_" + PREPROC_SUFFIX
        return name

    def available_hand_edit_full_paths(self):
        """
        List of full paths to any resource containing preprocessed functional data
        for the specified subject
        """
        path_expr = self.hand_edit_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_structural_preproc_hand_edit_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        path_expr = self.structural_preproc_hand_edit_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_structural_preproc_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        path_expr = self.structural_preproc_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def supplemental_structural_preproc_dir_full_path(self):
        """
        Full path to supplemental structural preproc resource directory
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "Structural" + "_" + PREPROC_SUFFIX
        path_expr += "/" + "supplemental"
        return path_expr

    def available_supplemental_structural_preproc_dir_full_paths(self):
        """
        List of full paths to any resource containing supplemental preprocessed structural
        data for the specified subject
        """
        path_expr = self.supplemental_structural_preproc_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def hand_edit_dir_full_path(self):
        """
        Full path to structural preproc resource directory
        """
        path_expr = self.subject_resources_dir_full_path() + "/"
        path_expr += self.hand_edit_dir_name()
        return path_expr

    def structural_preproc_hand_edit_dir_full_path(self):
        """
        Full path to structural preproc resource directory
        """
        path_expr = self.subject_resources_dir_full_path() + "/"
        path_expr += self.structural_preproc_hand_edit_dir_name()
        return path_expr

    def hand_edit_dir_name(self):
        name = "Structural_Hand_Edit"
        return name

    def structural_preproc_hand_edit_dir_name(self):
        name = "Structural" + "_" + PREPROC_SUFFIX + "_handedit"
        return name

    def available_hand_edit_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        path_expr = self.hand_edit_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_structural_preproc_hand_edit_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed structural data
        for the specified subject
        """
        path_expr = self.structural_preproc_hand_edit_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def diffusion_preproc_dir_full_path(self):
        """
        Full path to diffusion preproc resource directory
        """
        path_expr = self.subject_resources_dir_full_path() + "/"
        path_expr += self.diffusion_preproc_dir_name()
        return path_expr

    def diffusion_preproc_dir_name(self):
        name = "Diffusion" + "_" + PREPROC_SUFFIX
        return name

    def available_diffusion_preproc_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed diffusion data
        for the specified subject
        """
        path_expr = self.diffusion_preproc_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_functional_preproc_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed functional data
        for the specified subject
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "*" + FUNCTIONAL_SCAN_MARKER + "*" + PREPROC_SUFFIX
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_functional_preproc_names(self):
        """
        List of names (not full paths) of functional scans that have been preprocessed
        """
        dir_list = self.available_functional_preproc_dir_full_paths()
        name_list = self._get_scan_names_from_full_paths(dir_list)
        return name_list

    def functional_preproc_dir_full_path(self):
        """
        Full path to functional preprocessed resource for the specified subject
        (including the specified scan in the self.SUBJECT_EXTRA field)
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + self.functional_preproc_dir_name()
        return path_expr

    def functional_preproc_dir_name(self):
        """
        Name of functional preprocessed resource for the specified subject
        (including the specified scan in the self.SUBJECT_EXTRA field)
        """
        name = self.SUBJECT_EXTRA + "_" + PREPROC_SUFFIX
        return name

    # processed data paths and names

    def msmall_registration_dir_full_path(self):
        """
        Full path to MSM All registration resource directory
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "MSMAllReg"
        return path_expr

    def available_msmall_registration_dir_full_paths(self):
        """
        List of full paths to any resource containing msmall registration results
        data for the specified subject
        """
        path_expr = self.msmall_registration_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def msm_all_dir_full_path(self):
        """
        Full path to diffusion preproc resource directory
        """
        path_expr = self.subject_resources_dir_full_path() + "/"
        path_expr += self.msm_all_dir_name()
        return path_expr

    def msm_all_dir_name(self):
        name = "MsmAll_proc"
        return name

    # def available_msm_all_dir_full_paths(self):
    # 	"""
    # 	List of full paths to any resource containing preprocessed diffusion data
    # 	for the specified subject
    # 	"""
    # 	# path_expr = self.msm_all_dir_full_path()
    # 	# dir_list = glob.glob(path_expr)
    # 	# return sorted(dir_list)
    # 	path_expr = self.subject_resources_dir_full_path()
    # 	path_expr += "/" + '*' + MSMALL_PROCESSED_SUFFIX
    # 	dir_list = glob.glob(path_expr)
    # 	return sorted(dir_list)

    def multirun_icafix_dir_full_path(self):
        """
        Full path to diffusion preproc resource directory
        """
        path_expr = self.subject_resources_dir_full_path() + "/"
        path_expr += self.multirun_icafix_dir_name()
        return path_expr

    def multirun_icafix_dir_name(self):
        # name = 'MultiRunICAFIX' + "_" + FIX_PROCESSED_SUFFIX
        # name = 'MultiRunICAFIX'
        name = "MultiRunIcaFix_proc"
        return name

    def available_multirun_icafix_dir_full_paths(self):
        """
        List of full paths to any resource containing preprocessed diffusion data
        for the specified subject
        """
        # path_expr = self.multirun_icafix_dir_full_path()
        # dir_list = glob.glob(path_expr)
        # return sorted(dir_list)
        path_expr = self.multirun_icafix_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_fix_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing FIX processed results data
        for the specified subject
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "*" + FIX_PROCESSED_SUFFIX
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def dedrift_and_resample_dir_full_path(self):
        """
        Full path to MSM All DeDrift and Resample resource directory
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "MSMAllDeDrift"
        return path_expr

    def available_msmall_dedrift_and_resample_dir_full_paths(self):
        """
        List of full paths to any resource containing msmall dedrift and resample results
        data for the specified subject
        """
        path_expr = self.dedrift_and_resample_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_rss_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing RestingStateStats processed results data
        for the specified subject
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "*" + RSS_PROCESSED_SUFFIX
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_postfix_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing PostFix processed results data
        for the specified subject
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "*" + POSTFIX_PROCESSED_SUFFIX
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_task_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing Task Analysis processed results data
        for the specified subject
        """
        dir_list = []

        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + TASK_SCAN_MARKER + "*"
        first_dir_list = glob.glob(path_expr)

        for directory in first_dir_list:
            lastsepindex = directory.rfind("/")
            basename = directory[lastsepindex + 1 :]
            index = basename.find("_")
            rindex = basename.rfind("_")
            if index == rindex:
                dir_list.append(directory)

        return sorted(dir_list)

    def bedpostx_dir_full_path(self):
        """
        Full path to bedpostx processed resource directory
        """
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "Diffusion_bedpostx"
        return path_expr

    def available_bedpostx_processed_dir_full_paths(self):
        """
        List of full paths to any resource containing bedpostx processed results data
        for the specified subject
        """
        path_expr = self.bedpostx_dir_full_path()
        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def reapplyfix_dir_full_path(self, scan_name, reg_name=None):
        path_expr = self.subject_resources_dir_full_path() + "/" + scan_name
        path_expr += "_" + REAPPLY_FIX_SUFFIX
        if reg_name:
            path_expr += reg_name

        return path_expr

    def available_reapplyfix_dir_full_paths(self, reg_name=None):
        path_expr = self.subject_resources_dir_full_path()
        path_expr += "/" + "*" + REAPPLY_FIX_SUFFIX
        if reg_name:
            path_expr += reg_name

        dir_list = glob.glob(path_expr)
        return sorted(dir_list)

    def available_reapplyfix_names(self, reg_name=None):
        dir_list = self.available_reapplyfix_dir_full_paths(reg_name)
        name_list = []
        for directory in dir_list:
            name_list.append(self._get_scan_name_from_path(directory))
        return name_list

    # Internal utility methods

    def _get_scan_names_from_full_paths(self, dir_list):
        name_list = []
        for directory in dir_list:
            name_list.append(self._get_scan_name_from_path(directory))
        return name_list

    def _get_scan_name_from_path(self, path):
        short_path = os.path.basename(path)
        last_char = short_path.rfind("_")
        name = short_path[:last_char]
        return name
