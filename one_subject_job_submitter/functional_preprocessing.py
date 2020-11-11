#!/usr/bin/env python3

# import of built-in modules
import contextlib
import logging
import os
import stat
import subprocess

# import of third-party modules

# import of local modules
import ccf.one_subject_job_submitter as one_subject_job_submitter
import ccf.processing_stage as ccf_processing_stage
import utils.debug_utils as debug_utils

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2020, Connectome Coordination Facility"
__maintainer__ = "Junil Chang"

# create a module logger
module_logger = logging.getLogger(__name__)
# Note: This can be overidden by log file configuration
module_logger.setLevel(logging.WARNING)


class OneSubjectJobSubmitter(one_subject_job_submitter.OneSubjectJobSubmitter):
    def PIPELINE_NAME(self):
        return OneSubjectJobSubmitter.MY_PIPELINE_NAME()

    def create_get_data_job_script(self):
        """Create the script to be submitted to perform the get data job"""
        module_logger.debug(debug_utils.get_name())

        script_name = self.get_data_job_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        script = open(script_name, "w")
        self._write_bash_header(script)
        script.write("#PBS -l nodes=1:ppn=1,walltime=4:00:00,mem=4gb\n")
        script.write("#PBS -o " + WORKING_DIR + "\n")
        script.write("#PBS -e " + WORKING_DIR + "\n")
        script.write("\n")
        script.write("source " + XNAT_PBS_SETUP_SCRIPT_PATH + " intradb\n")
        script.write("module load " + SINGULARITY_CONTAINER_VERSION + "\n")
        script.write("\n")
        script.write("singularity exec -B " + XNAT_PBS_JOBS_ARCHIVE_ROOT + "," + SINGULARITY_BIND_PATH + " " + SINGULARITY_CONTAINER_XNAT_PATH + " " + GET_DATA_RUNPATH + " \\\n")
        script.write("  --project=" + SUBJECT_PROJECT + " \\\n")
        script.write("  --subject=" + SUBJECT_ID + " \\\n")
        script.write("  --classifier=" + SUBJECT_CLASSIFIER + " \\\n")
        if SUBJECT_EXTRA:
            script.write("  --scan=" + SUBJECT_EXTRA + " \\\n")
        script.write("  --working-dir=" + WORKING_DIR + " \\\n")
        script.write("\n")
        script.write("find " + WORKING_DIR + "/" + SUBJECT_SESSION + "/unprocessed/ -maxdepth 1 -mindepth 1 ")
        script.write("\( -type d -not -path " + WORKING_DIR + "/" + SUBJECT_SESSION + "/unprocessed/" + SUBJECT_EXTRA)
        script.write(" -path '" + WORKING_DIR + "/" + SUBJECT_SESSION + "/unprocessed/[rt]fMRI_*_[AP][PA]'")
        script.write(" -o -path '" + WORKING_DIR + "/" + SUBJECT_SESSION + "/unprocessed/T1w_*'")
        script.write(" -o -path '" + WORKING_DIR + "/" + SUBJECT_SESSION + "/unprocessed/T2w_*'")
        script.write(" -o -path '" + WORKING_DIR + "/" + SUBJECT_SESSION + "/unprocessed/Diffusion' \) -exec rm -rf '{}' \;\n")
        script.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def create_clean_data_script(self):
        module_logger.debug(debug_utils.get_name())

        script_name = self.clean_data_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        script = open(script_name, "w")
        self._write_bash_header(script)
        script.write("#PBS -l nodes=1:ppn=1,walltime=4:00:00,mem=4gb\n")
        script.write("#PBS -o " + WORKING_DIR + "\n")
        script.write("#PBS -e " + WORKING_DIR + "\n")
        script.write("\n")
        script.write("find " + WORKING_DIR + "/" + SUBJECT_SESSION + "/")
        script.write("subjects/" + SUBJECT_SESSION + "/hcp/")
        script.write(SUBJECT_SESSION + " \! -newer " + STARTTIME_FILE_NAME + " -delete")
        script.write("\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/")
        script.write("subjects/" + SUBJECT_SESSION + "/hcp/")
        script.write(SUBJECT_SESSION + "/* ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/processing ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/subjects/specs ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/info/hcpls ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/subjects/" + SUBJECT_SESSION + "/subject_hcp.txt ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo/processing\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/subjects/" + SUBJECT_SESSION + "/hcpls/hcpls2nii.log ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo/processing\n")
        script.write("find " + WORKING_DIR + "/" + SUBJECT_SESSION)
        script.write(" -maxdepth 1 -mindepth 1 \( -type d -not -path " + WORKING_DIR + "/" + SUBJECT_SESSION + "/T1w")
        script.write(" -a -not -path " + WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo")
        script.write(" -a -not -path " + WORKING_DIR + "/" + SUBJECT_SESSION + "/MNINonLinear")
        script.write(" -a -not -path " + WORKING_DIR + "/" + SUBJECT_SESSION + "/" + SUBJECT_EXTRA)
        script.write(" \) -exec rm -rf '{}' \;")
        script.write("\n")
        script.write('echo "Removing any XNAT catalog files still around."' + "\n")
        script.write("find " + WORKING_DIR + ' -name "*_catalog.xml" -delete')
        script.write("\n")
        script.write('echo "Remaining files:"' + "\n")
        script.write("find " + WORKING_DIR + "/" + SUBJECT_SESSION + "\n")
        script.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def create_process_data_job_script(self):
        module_logger.debug(debug_utils.get_name())

        script_name = self.process_data_job_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        with open(script_name, "w") as script:
            script.write("#PBS -l nodes=" + PBS_NODES + ":ppn=" + PBS_PPN + ":haswell,walltime=" + WALLTIME_LIMIT_HOURS + ":00:00,mem=" + MEM_LIMIT_GBS + "gb\n")
            script.write("#PBS -o " + WORKING_DIR + "\n")
            script.write("#PBS -e " + WORKING_DIR + "\n")
            script.write("\n")
            script.write("module load " + SINGULARITY_CONTAINER_VERSION + "\n")
            script.write("\n")
            script.write("singularity exec -B " + XNAT_PBS_JOBS_ARCHIVE_ROOT + "," + SINGULARITY_BIND_PATH + "," + GRADIENT_COEFFICIENT_PATH + ":/export/HCP/gradient_coefficient_files " + SINGULARITY_CONTAINER_PATH + " " + RUN_QUNEX_SCRIPT + " \\\n")
            script.write("  --parameterfolder=" + SINGULARITY_QUNEXPARAMETER_PATH + " \\\n")
            script.write("  --studyfolder=" + WORKING_DIR + "/" + SUBJECT_SESSION + " \\\n")
            script.write("  --subjects=" + SUBJECT_SESSION + " \\\n")
            script.write("  --scan=" + SUBJECT_EXTRA + " \\\n")
            script.write("  --overwrite=yes \\\n")
            script.write("  --hcppipelineprocess=FunctionalPreprocessing\n")
            os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def mark_running_status(self, stage):
        module_logger.debug(debug_utils.get_name())

        if stage > ccf_processing_stage.ProcessingStage.PREPARE_SCRIPTS:
            mark_cmd = XNAT_PBS_JOBS + "/" + PIPELINE_NAME + "/" + PIPELINE_NAME + ".XNAT_MARK_RUNNING_STATUS --user=" + USERNAME + " --password=" + PASSWORD + " --server=" + PUT_SERVER + " --project=" + SUBJECT_PROJECT + " --subject=" + SUBJECT_ID + " --classifier=" + SUBJECT_CLASSIFIER + " --scan=" + SUBJECT_EXTRA + " --resource=RunningStatus --queued"

            completed_mark_cmd_process = subprocess.run(mark_cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
            print(completed_mark_cmd_process.stdout)

            return
