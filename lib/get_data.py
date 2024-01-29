#!/usr/bin/env python3
"""
get_data.py: Get (copy or link) a CinaB style directory tree of data
for a specified subject within a specified project.
"""
import typing
from pathlib import Path


def link_directory(source, destination, show_log=True):
    if not source.is_dir():
        raise OSError(f"ERROR: {source} is not a valid directory.")
    if destination.exists():
        if not destination.is_dir():
            raise OSError(f"ERROR: {destination} exists but is not a valid directory.")
    else:
        destination.mkdir(parents=True, exist_ok=True)

    visited = set()

    def recursively_link_files(source_dir, destination_dir):
        source_dir = source_dir.resolve().absolute()
        visited.add(str(source_dir))
        for source in source_dir.iterdir():
            destination = destination_dir / source.name
            if source.is_file():
                if not destination.exists():
                    if show_log:
                        print(
                            f"linking: {destination.absolute()} --> {source.absolute()}"
                        )
                    destination.symlink_to(source.absolute())
                else:
                    if show_log:
                        print(f"skipping: {destination.absolute()}")
            elif source.is_dir():
                if source.is_symlink():
                    resolved_path = str(source.resolve())
                    # keep track if already visited, to avoid infinite recursion from circular symlinks
                    if resolved_path in visited:
                        print("Skipping, because already visited: ", resolved_path)
                        continue
                if show_log:
                    print("dirname: " + str(destination.absolute()))
                if not destination.exists():
                    destination.mkdir()
                recursively_link_files(source, destination)

    recursively_link_files(source, destination)


class PipelineResources:
    """
    Get the data necessary to run the specific pipelines
    """

    def __init__(
        self,
        RESOURCES_ROOT,
        session,
        log,
        output_dir,
    ):
        self.SESSION = session
        self.RESOURCES_ROOT = RESOURCES_ROOT
        self.output_dir = Path(output_dir)
        self.show_log = log

    def list_resources(self, glob_pattern:str, str_contains_pattern:typing.Optional[str]=None)->typing.List[Path]:
        """
        List of files/folders matching the pattern(s)

        Args:
            glob_pattern: glob pattern to match
            str_contains_pattern: string that must be contained in the filename

        Returns:
            list of paths
        """
        files = sorted(self.RESOURCES_ROOT.glob(glob_pattern))

        if type(str_contains_pattern) is not str or str_contains_pattern.upper() == "ALL":
            return files
        else:
            return [
                x
                for x in files
                if str_contains_pattern in x.name
            ]

    def link_unprocessed_files(self, glob_pattern:str, contains_pattern:typing.Optional[str]=None)->None:
        """
        Create FS links to unprocessed data in CinaB style

        This function removes the "_unproc" from the end of the folder name, and then
        creates the link in "unprocessed" folder.

        Args:
            glob_pattern: glob pattern to match
            contains_pattern: string that must be contained in the filename
        """
        unprocessed_dir = self.output_dir / self.SESSION / "unprocessed"
        for source in self.list_resources(glob_pattern, contains_pattern):
            # Remove the "_unproc" suffix
            basename_with_no_suffix = source.name[:-7]

            destination = unprocessed_dir / basename_with_no_suffix
            link_directory(source, destination, self.show_log)

    def mirror_folders_in_output(self, glob_pattern:str, contains_pattern:typing.Optional[str]=None)->None:
        """
        Create FS links to mirror the folders from IntraDB to the output directory

        Args:
            glob_pattern: glob pattern to match
            contains_pattern: string that must be contained in the filename
        """
        destination = self.output_dir
        for source in self.list_resources(glob_pattern, contains_pattern):
            link_directory(source, destination, self.show_log)

    # get unprocessed data
    def get_structural_unproc_data(self):
        self.link_unprocessed_files("T[12]w_*unproc")

    def get_functional_unproc_data(self, extra=None):
        self.link_unprocessed_files("*fMRI*unproc", extra)

    def get_diffusion_unproc_data(self):
        self.link_unprocessed_files("Diffusion_unproc")

    def get_asl_unproc_data(self):
        self.link_unprocessed_files("mbPCASLhr_unproc")

    # get preprocessed data

    def get_structural_preproc_data(self):
        self.mirror_folders_in_output("Structural_preproc")

    def get_icafix_data(self):
        self.mirror_folders_in_output("MultiRunIcaFix_proc")

    def get_supplemental_structural_preproc_data(self):
        self.mirror_folders_in_output("Structural_preproc/supplemental")

    def get_hand_edit_data(self):
        self.mirror_folders_in_output("Structural_Hand_Edit")

    def get_functional_preproc_data(self, extra=None):
        self.mirror_folders_in_output("*fMRI*preproc", extra)

    def get_diffusion_preproc_data(self):
        self.mirror_folders_in_output("Diffusion_preproc")

    # get processed data
    def get_autoreclean_processed_data(self):
        self.mirror_folders_in_output("AutoReclean_proc")

    # get processed data
    def get_msmall_processed_data(self):
        self.mirror_folders_in_output("MsmAll_proc")

    def get_msmall_registration_data(self):
        self.mirror_folders_in_output("MSMAllReg")

    # get processed data
    def get_reapplyfix_processed_data(self):
        self.mirror_folders_in_output("ReapplyFix_proc")

    def get_fix_processed_data(self):
        self.mirror_folders_in_output("*FIX")

    def get_dedriftandresample_processed_data(self):
        self.mirror_folders_in_output("MSMAllDeDrift")

    def get_resting_state_stats_data(self):
        self.mirror_folders_in_output("*RSS")

    def get_postfix_data(self):
        self.mirror_folders_in_output("*PostFix")

    def get_bedpostx_data(self):
        self.mirror_folders_in_output("Diffusion_bedpostx")

    def get_tica_processed_data(self):
        self.mirror_folders_in_output("tICA_proc")

    def get_ptfcmm_processed_data(self):
        self.mirror_folders_in_output("PTFCMM_proc")

