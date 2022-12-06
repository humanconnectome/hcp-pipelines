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

    def get_unprocessed_data(self, glob, extra=None):
        unprocessed_dir = self.output_dir / self.SESSION / "unprocessed"
        for source in self.list_resources(glob, extra):
            # Remove the "_unproc" suffix
            basename_with_no_suffix = source.name[:-7]

            destination = unprocessed_dir / basename_with_no_suffix
            link_directory(source, destination, self.show_log)

    def get_preprocessed_data(self, glob, extra=None):
        # currently has same implementation
        # so just make it an alias
        return self.get_processed_data(glob, extra)

    def get_processed_data(self, glob, extra=None):
        destination = self.output_dir
        for source in self.list_resources(glob, extra):
            link_directory(source, destination, self.show_log)

    # get unprocessed data
    def get_structural_unproc_data(self):
        self.get_unprocessed_data("T[12]w_*unproc")

    def get_functional_unproc_data(self, extra=None):
        self.get_unprocessed_data("*fMRI*unproc", extra)

    def get_diffusion_unproc_data(self):
        self.get_unprocessed_data("Diffusion_unproc")

    def get_asl_unproc_data(self):
        self.get_unprocessed_data("mbPCASLhr_unproc")

    # get preprocessed data

    def get_structural_preproc_data(self):
        self.get_preprocessed_data("Structural_preproc")

    def get_icafix_data(self):
        self.get_processed_data("MultiRunIcaFix_proc")

    def get_supplemental_structural_preproc_data(self):
        self.get_preprocessed_data("Structural_preproc/supplemental")

    def get_hand_edit_data(self):
        self.get_preprocessed_data("Structural_Hand_Edit")

    def get_functional_preproc_data(self, extra=None):
        self.get_preprocessed_data("*fMRI*preproc", extra)

    def get_diffusion_preproc_data(self):
        self.get_preprocessed_data("Diffusion_preproc")

    # get processed data
    def get_msmall_processed_data(self):
        self.get_processed_data("MsmAll_proc")

    def get_msmall_registration_data(self):
        self.get_processed_data("MSMAllReg")

    def get_fix_processed_data(self):
        self.get_processed_data("*FIX")

    def get_dedriftandresample_processed_data(self):
        self.get_processed_data("MSMAllDeDrift")

    def get_resting_state_stats_data(self):
        self.get_processed_data("*RSS")

    def get_postfix_data(self):
        self.get_processed_data("*PostFix")

    def get_bedpostx_data(self):
        self.get_processed_data("Diffusion_bedpostx")
