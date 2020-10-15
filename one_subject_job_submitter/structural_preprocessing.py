#!/usr/bin/env python3

# import of built-in modules
import contextlib
import glob
import logging
import os
import shutil
import stat
import subprocess
import sys
import random

# import of third-party modules

# import of local modules
import ccf.one_subject_job_submitter as one_subject_job_submitter
import ccf.processing_stage as ccf_processing_stage
import ccf.subject as ccf_subject
import utils.debug_utils as debug_utils
import utils.os_utils as os_utils
import utils.str_utils as str_utils
import utils.user_utils as user_utils
import ccf.archive as ccf_archive

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2020, Connectome Coordination Facility"
__maintainer__ = "Junil Chang"

# create a module logger
module_logger = logging.getLogger(__name__)
# Note: This can be overidden by log file configuration
module_logger.setLevel(logging.WARNING)


class OneSubjectJobSubmitter(one_subject_job_submitter.OneSubjectJobSubmitter):

    _SEVEN_MM_TEMPLATE_PROJECTS = os_utils.getenv_required("SEVEN_MM_TEMPLATE_PROJECTS")
    _CONNECTOME_SKYRA_SCANNER_PROJECTS = os_utils.getenv_required("CONNECTOME_SKYRA_SCANNER_PROJECTS")
    _PRISMA_3T_PROJECTS = os_utils.getenv_required("PRISMA_3T_PROJECTS")
    _SCRATCH_PROCESSING_DIR = os_utils.getenv_required("SCRATCH_PROCESSING_DIR")
    _SUPPRESS_FREESURFER_ASSESSOR_JOB = True

    def PIPELINE_NAME(self):
        return OneSubjectJobSubmitter.MY_PIPELINE_NAME()

    def T1W_TEMPLATE_NAME(self):
        return "MNI152_T1_" + self._template_size_str() + ".nii.gz"

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
        if self.use_prescan_normalized:
            script.write("  --use-prescan-normalized \\\n")
        script.write("  --delay-seconds=120\n")
        script.write("\n")
        script.write("rm -rf " + WORKING_DIR + "/" + SUBJECT_SESSION + "/unprocessed/T1w_MPR_vNav_4e_RMS\n")
        script.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def create_process_data_job_script(self):

        project_build_dir = self.build_home + "/" + SUBJECT_PROJECT
        pipeline_processing_dir = WORKING_DIR.replace(project_build_dir + "/", "")
        scratch_processing_dir = self._SCRATCH_PROCESSING_DIR + "/" + SUBJECT_PROJECT
        if not os.path.exists(scratch_processing_dir):
            os.mkdir(scratch_processing_dir)

        module_logger.debug(debug_utils.get_name())

        script_name = self.process_data_job_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        # studyfolder_line   = '  --studyfolder=' + WORKING_DIR + '/' + SUBJECT_ID + '_' + SUBJECT_CLASSIFIER
        studyfolder_line = "  --studyfolder=" + scratch_processing_dir + "/" + pipeline_processing_dir + "/" + SUBJECT_SESSION
        with open(script_name, "w") as script:
            script.write("#PBS -l nodes=" + PBS_NODES + ":ppn=" + PBS_PPN + ":haswell,walltime=" + WALLTIME_LIMIT_HOURS + ":00:00,mem=" + MEM_LIMIT_GBS + "gb\n")
            script.write("#PBS -o " + WORKING_DIR + "\n")
            script.write("#PBS -e " + WORKING_DIR + "\n")
            script.write("\n")
            script.write("module load " + SINGULARITY_CONTAINER_VERSION + "\n")
            script.write("\n")
            script.write('# TEMPORARILY MOVE PROCESSING DIRECTORY TO SCRATCH SPACE DUE TO "Cannot allocate memory" ERRORS IN BUILD SPACE' + "\n")
            script.write("mv " + WORKING_DIR + " " + scratch_processing_dir + "\n")
            script.write("\n")
            script.write("singularity exec -B " + XNAT_PBS_JOBS_ARCHIVE_ROOT + "," + SINGULARITY_BIND_PATH + "," + GRADIENT_COEFFICIENT_PATH + ":/export/HCP/gradient_coefficient_files " + SINGULARITY_CONTAINER_PATH + " " + RUN_QUNEX_SCRIPT + " \\\n")
            script.write("  --parameterfolder=" + SINGULARITY_QUNEXPARAMETER_PATH + " \\\n")
            script.write(studyfolder_line + " \\\n")
            script.write("  --subjects=" + SUBJECT_SESSION + " \\\n")
            script.write("  --overwrite=yes \\\n")
            script.write("  --hcppipelineprocess=StructuralPreprocessing\n")
            script.write("\n")
            script.write("# MOVE PROCESSING BACK\n")
            script.write("mv " + scratch_processing_dir + "/" + pipeline_processing_dir + " " + project_build_dir + "\n")
            script.write("\n")
            os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def create_freesurfer_assessor_script(self):
        module_logger.debug(debug_utils.get_name())

        # copy the .XNAT_CREATE_FREESURFER_ASSESSOR script to the working directory

        freesurfer_assessor_dest_path = WORKING_DIR + "/" + PIPELINE_NAME + ".XNAT_CREATE_FREESURFER_ASSESSOR"

        shutil.copy(self.xnat_pbs_jobs_home + "/" + PIPELINE_NAME + "/" + PIPELINE_NAME + ".XNAT_CREATE_FREESURFER_ASSESSOR", freesurfer_assessor_dest_path)
        os.chmod(freesurfer_assessor_dest_path, stat.S_IRWXU | stat.S_IRWXG)

        # write the freesurfer assessor submission script (that calls the .XNAT_CREATE_FREESURFER_ASSESSOR script)

        script_name = self.freesurfer_assessor_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        script = open(script_name, "w")

        self._write_bash_header(script)
        script.write("#PBS -l nodes=1:ppn=1,walltime=4:00:00,mem=4gb\n")
        script.write("#PBS -o " + WORKING_DIR + "\n")
        script.write("#PBS -e " + WORKING_DIR + "\n")
        script.write("\n")
        script.write("source " + XNAT_PBS_SETUP_SCRIPT_PATH + " intradb\n")
        script.write("\n")

        script.write(freesurfer_assessor_dest_path + " \\\n")
        script.write("  --user=" + USERNAME + " \\\n")
        script.write("  --password=" + PASSWORD + " \\\n")
        script.write("  --server=" + PUT_SERVER + " \\\n")
        script.write("  --project=" + SUBJECT_PROJECT + " \\\n")
        script.write("  --subject=" + SUBJECT_ID + " \\\n")
        script.write("  --session=" + SUBJECT_SESSION + " \\\n")
        script.write("  --session-classifier=" + SUBJECT_CLASSIFIER + " \\\n")
        script.write("  --working-dir=" + WORKING_DIR + "\n")

        script.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def create_scripts(self, stage):
        module_logger.debug(debug_utils.get_name())
        super().create_scripts(stage)

        if OneSubjectJobSubmitter._SUPPRESS_FREESURFER_ASSESSOR_JOB:
            return

        if stage >= ccf_processing_stage.ProcessingStage.PREPARE_SCRIPTS:
            self.create_freesurfer_assessor_script()

    def submit_process_data_jobs(self, stage, prior_job=None):
        module_logger.debug(debug_utils.get_name())

        # go ahead and submit the standard process data job and then
        # submit an additional freesurfer assessor job

        standard_process_data_jobno, all_process_data_jobs = super().submit_process_data_jobs(stage, prior_job)

        if OneSubjectJobSubmitter._SUPPRESS_FREESURFER_ASSESSOR_JOB:
            module_logger.info("freesufer assessor job not submitted because freesurfer assessor creation has been suppressed")
            return standard_process_data_jobno, all_process_data_jobs

        if stage >= ccf_processing_stage.ProcessingStage.PROCESS_DATA:
            if standard_process_data_jobno:
                fs_submit_cmd = "qsub -W depend=afterok:" + standard_process_data_jobno + " " + self.freesurfer_assessor_script_name
            else:
                fs_submit_cmd = "qsub " + self.freesurfer_assessor_script_name

            completed_submit_process = subprocess.run(fs_submit_cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
            fs_job_no = str_utils.remove_ending_new_lines(completed_submit_process.stdout)
            all_process_data_jobs.append(fs_job_no)
            return fs_job_no, all_process_data_jobs

        else:
            module_logger.info("freesurfer assessor job not submitted because of requested processing stage")
            return standard_process_data_jobno, all_process_data_jobs

    def mark_running_status(self, stage):
        module_logger.debug(debug_utils.get_name())

        if stage > ccf_processing_stage.ProcessingStage.PREPARE_SCRIPTS:
            mark_cmd = XNAT_PBS_JOBS + "/" + PIPELINE_NAME + "/" + PIPELINE_NAME + ".XNAT_MARK_RUNNING_STATUS --user=" + USERNAME + " --password=" + PASSWORD + " --server=" + PUT_SERVER + " --project=" + SUBJECT_PROJECT + " --subject=" + SUBJECT_ID + " --classifier=" + SUBJECT_CLASSIFIER + " --resource=RunningStatus --queued"

            completed_mark_cmd_process = subprocess.run(mark_cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
            print(completed_mark_cmd_process.stdout)

            return
