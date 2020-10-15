#!/usr/bin/env python3

"""
ccf/one_subject_job_submitter.py: Abstract base class for an object
that submits jobs for a pipeline for one subject.
"""

# import of built-in modules
import abc
import contextlib
import logging
import os
import shutil
import stat
import subprocess
import time

# import of third-party modules

# import of local modules
import ccf.processing_stage as ccf_processing_stage
import utils.debug_utils as debug_utils
import utils.delete_resource as delete_resource
import utils.file_utils as file_utils
import utils.os_utils as os_utils
import utils.str_utils as str_utils
import ccf.subject as ccf_subject

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2020, The Connectome Coordination Facility (CCF)"
__maintainer__ = "Junil Chang"

# create a module logger
module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.WARNING)  # Note: This can be overidden by log file configuration


class OneSubjectJobSubmitter(abc.ABC):
    """
    This class is an abstract base class for classes that are used to submit jobs
    for one pipeline for one subject.
    """

    def processing_stage_from_string(self, str_value):
        return ccf_processing_stage.ProcessingStage.from_string(str_value)

    def PIPELINE_NAME(self):
        raise NotImplementedError()

    def get_data_program_path(self):
        """Path to the program that can get the appropriate data for this processing"""
        return self.xnat_pbs_jobs_home + "/" + PIPELINE_NAME + "/" + PIPELINE_NAME + ".XNAT_GET"

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
        script.write("  --working-dir=" + WORKING_DIR + "\n")
        script.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def create_put_data_script(self):
        module_logger.debug(debug_utils.get_name())

        script_name = self.put_data_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        script = open(script_name, "w")
        script.write("#PBS -l nodes=1:ppn=1,walltime=4:00:00,mem=12gb\n")
        script.write("#PBS -o " + XNAT_PBS_JOBS_LOG_DIR + "\n")
        script.write("#PBS -e " + XNAT_PBS_JOBS_LOG_DIR + "\n")
        script.write("\n")
        script.write("source " + XNAT_PBS_SETUP_SCRIPT_PATH + " intradb\n")
        script.write("module load " + SINGULARITY_CONTAINER_VERSION + "\n")
        script.write("\n")
        script.write("mv " + WORKING_DIR + "/*" + PIPELINE_NAME + "* " + WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo\n")
        script.write("\n")
        script.write("singularity exec -B " + XNAT_PBS_JOBS_ARCHIVE_ROOT + "," + SINGULARITY_BIND_PATH + " " + SINGULARITY_CONTAINER_XNAT_PATH + " " + self.xnat_pbs_jobs_home + "/WorkingDirPut/XNAT_working_dir_put.sh \\\n")
        script.write("  --leave-subject-id-level \\\n")
        script.write('  --user="' + USERNAME + '" \\' + "\n")
        script.write('  --password="' + PASSWORD + '" \\' + "\n")
        script.write('  --server="' + PUT_SERVER + '" \\' + "\n")
        script.write('  --project="' + SUBJECT_PROJECT + '" \\' + "\n")
        script.write('  --subject="' + SUBJECT_ID + '" \\' + "\n")
        script.write('  --session="' + SUBJECT_SESSION + '" \\' + "\n")
        script.write('  --working-dir="' + WORKING_DIR + '" \\' + "\n")
        if SUBJECT_EXTRA:
            script.write('  --scan="' + SUBJECT_EXTRA + '" \\' + "\n")
            script.write('  --resource-suffix="' + self.output_resource_suffix + '" \\' + "\n")
        else:
            script.write('  --resource-suffix="' + self.output_resource_name + '" \\' + "\n")
        script.write('  --reason="' + PIPELINE_NAME + '"' + "\n")
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
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/" + SUBJECT_SESSION + "/MNINonLinear ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/" + SUBJECT_SESSION + "/T*w ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/subjects/specs ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/processing ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/info/hcpls ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/subjects/" + SUBJECT_SESSION + "/subject_hcp.txt ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo/processing\n")
        script.write("mv " + WORKING_DIR + "/" + SUBJECT_SESSION + "/subjects/" + SUBJECT_SESSION + "/hcpls/hcpls2nii.log ")
        script.write(WORKING_DIR + "/" + SUBJECT_SESSION + "/ProcessingInfo/processing\n")
        script.write("find " + WORKING_DIR + "/" + SUBJECT_SESSION)
        script.write(' -not -path "' + WORKING_DIR + "/" + SUBJECT_SESSION + "/" + 'T*w/*"')
        script.write(' -not -path "' + WORKING_DIR + "/" + SUBJECT_SESSION + "/" + 'ProcessingInfo/*"')
        script.write(' -not -path "' + WORKING_DIR + "/" + SUBJECT_SESSION + "/" + 'MNINonLinear/*"')
        script.write(" -delete")
        script.write("\n")
        script.write('echo "Removing any XNAT catalog files still around."' + "\n")
        script.write("find " + WORKING_DIR + ' -name "*_catalog.xml" -delete')
        script.write("\n")
        script.write('echo "Remaining files:"' + "\n")
        script.write("find " + WORKING_DIR + "/" + SUBJECT_SESSION + "\n")
        script.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def create_check_data_job_script(self):
        """
        Create the script to be submitted as a job to perform the check data functionality.
        """
        module_logger.debug(debug_utils.get_name())

        script_name = self.check_data_job_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        script = open(script_name, "w")
        self._write_bash_header(script)
        script.write("#PBS -l nodes=1:ppn=1,walltime=4:00:00,mem=4gb\n")
        script.write("#PBS -o " + XNAT_PBS_JOBS_LOG_DIR + "\n")
        script.write("#PBS -e " + XNAT_PBS_JOBS_LOG_DIR + "\n")
        script.write("\n")
        script.write("source " + XNAT_PBS_SETUP_SCRIPT_PATH + " intradb\n")
        script.write("module load " + SINGULARITY_CONTAINER_VERSION + "\n")
        script.write("\n")
        script.write("singularity exec -B " + XNAT_PBS_JOBS_ARCHIVE_ROOT + "," + SINGULARITY_BIND_PATH + " " + SINGULARITY_CONTAINER_XNAT_PATH + " " + self.check_data_program_path + " \\\n")
        script.write('  --user="' + USERNAME + '" \\' + "\n")
        script.write('  --password="' + PASSWORD + '" \\' + "\n")
        script.write('  --server="' + PUT_SERVER + '" \\' + "\n")
        script.write("  --project=" + SUBJECT_PROJECT + " \\\n")
        script.write("  --subject=" + SUBJECT_ID + " \\\n")
        script.write("  --classifier=" + SUBJECT_CLASSIFIER + " \\\n")
        if SUBJECT_EXTRA:
            script.write("  --scan=" + SUBJECT_EXTRA + " \\\n")
        elif PIPELINE_NAME == "StructuralPreprocessing":
            subject_info = ccf_subject.SubjectInfo(SUBJECT_PROJECT, SUBJECT_ID, SUBJECT_CLASSIFIER)
            fieldmap_type_line = "  --fieldmap=NONE"
            script.write(fieldmap_type_line + " \\\n")
        script.write("  --working-dir=" + self.check_data_directory_name + "\n")
        script.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def create_mark_no_longer_running_script(self):
        module_logger.debug(debug_utils.get_name())

        script_name = self.mark_no_longer_running_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        script = open(script_name, "w")
        self._write_bash_header(script)
        script.write("#PBS -l nodes=1:ppn=1,walltime=4:00:00,mem=4gb\n")
        script.write("#PBS -o " + XNAT_PBS_JOBS_LOG_DIR + "\n")
        script.write("#PBS -e " + XNAT_PBS_JOBS_LOG_DIR + "\n")
        script.write("\n")
        script.write("source " + XNAT_PBS_SETUP_SCRIPT_PATH + " intradb\n")
        script.write("module load " + SINGULARITY_CONTAINER_VERSION + "\n")
        script.write("\n")
        script.write("singularity exec -B " + XNAT_PBS_JOBS_ARCHIVE_ROOT + "," + SINGULARITY_BIND_PATH + " " + SINGULARITY_CONTAINER_XNAT_PATH + " " + self.mark_running_status_program_path + " \\\n")
        script.write('  --user="' + USERNAME + '" \\' + "\n")
        script.write('  --password="' + PASSWORD + '" \\' + "\n")
        script.write('  --server="' + PUT_SERVER + '" \\' + "\n")
        script.write('  --project="' + SUBJECT_PROJECT + '" \\' + "\n")
        script.write('  --subject="' + SUBJECT_ID + '" \\' + "\n")
        script.write('  --classifier="' + SUBJECT_CLASSIFIER + '" \\' + "\n")
        if SUBJECT_EXTRA:
            script.write('  --scan="' + SUBJECT_EXTRA + '" \\' + "\n")
        script.write('  --resource="' + "RunningStatus" + '" \\' + "\n")
        script.write("  --done\n")
        script.write("\n")
        script.write("rm -rf " + self.mark_completion_directory_name)
        script.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def submit_get_data_jobs(self, stage, prior_job=None):
        module_logger.debug(debug_utils.get_name())

        if stage >= ccf_processing_stage.ProcessingStage.GET_DATA:
            if prior_job:
                get_data_submit_cmd = "qsub -W depend=afterok:" + prior_job + " " + self.get_data_job_script_name
            else:
                get_data_submit_cmd = "qsub " + self.get_data_job_script_name

            completed_submit_process = subprocess.run(get_data_submit_cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
            get_data_job_no = str_utils.remove_ending_new_lines(completed_submit_process.stdout)
            return get_data_job_no, [get_data_job_no]

        else:
            module_logger.info("Get data job not submitted")
            return None, None

    def submit_process_data_jobs(self, stage, prior_job=None):
        module_logger.debug(debug_utils.get_name())

        if stage >= ccf_processing_stage.ProcessingStage.PROCESS_DATA:
            if prior_job:
                work_submit_cmd = "qsub -W depend=afterok:" + prior_job + " " + self.process_data_job_script_name
            else:
                work_submit_cmd = "qsub " + self.process_data_job_script_name

            completed_submit_process = subprocess.run(work_submit_cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
            work_job_no = str_utils.remove_ending_new_lines(completed_submit_process.stdout)
            return work_job_no, [work_job_no]

        else:
            module_logger.info("Process data job not submitted")
            return None, None

    def submit_clean_data_jobs(self, stage, prior_job=None):
        module_logger.debug(debug_utils.get_name())

        if stage >= ccf_processing_stage.ProcessingStage.CLEAN_DATA:
            if prior_job:
                clean_submit_cmd = "qsub -W depend=afterok:" + prior_job + " " + self.clean_data_script_name
            else:
                clean_submit_cmd = "qsub " + self.clean_data_script_name

            completed_submit_process = subprocess.run(clean_submit_cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
            clean_job_no = str_utils.remove_ending_new_lines(completed_submit_process.stdout)
            return clean_job_no, [clean_job_no]

        else:
            module_logger.info("Clean data job not submitted")
            return None, None

    def submit_put_data_jobs(self, stage, prior_job=None):
        module_logger.debug(debug_utils.get_name())

        if stage >= ccf_processing_stage.ProcessingStage.PUT_DATA:
            if prior_job:
                put_submit_cmd = "qsub -W depend=afterok:" + prior_job + " " + self.put_data_script_name
            else:
                put_submit_cmd = "qsub " + self.put_data_script_name

            completed_submit_process = subprocess.run(put_submit_cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
            put_job_no = str_utils.remove_ending_new_lines(completed_submit_process.stdout)
            return put_job_no, [put_job_no]

        else:
            module_logger.info("Put data job not submitted")
            return None, None

    def submit_check_jobs(self, stage, prior_job=None):
        module_logger.debug(debug_utils.get_name())

        if stage >= ccf_processing_stage.ProcessingStage.CHECK_DATA:
            if prior_job:
                check_submit_cmd = "qsub -W depend=afterok:" + prior_job + " " + self.check_data_job_script_name
            else:
                check_submit_cmd = "qsub " + self.check_data_job_script_name

            completed_submit_process = subprocess.run(check_submit_cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True)
            check_job_no = str_utils.remove_ending_new_lines(completed_submit_process.stdout)
            return check_job_no, [check_job_no]

        else:
            module_logger.info("Check data job not submitted")
            return None, None

    def submit_no_longer_running_jobs(self, stage, prior_job=None):
        module_logger.debug(debug_utils.get_name())

        if prior_job:
            cmd = "qsub -W depend=afterany:" + prior_job + " " + self.mark_no_longer_running_script_name
        else:
            cmd = "qsub " + self.mark_no_longer_running_script_name

        job_no = str_utils.remove_ending_new_lines(subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, universal_newlines=True).stdout)
        return job_no, [job_no]

    def create_scripts(self, stage):
        module_logger.debug(debug_utils.get_name())

        if stage >= ccf_processing_stage.ProcessingStage.PREPARE_SCRIPTS:
            self.create_get_data_job_script()
            self.create_process_data_job_script()
            self.create_clean_data_script()
            self.create_put_data_script()
            self.create_check_data_job_script()
            self.create_mark_no_longer_running_script()

        else:
            module_logger.info("Scripts not created")

    def do_job_submissions(self, processing_stage):
        submitted_jobs_list = []
        prior = None

        # create scripts
        self.create_scripts(stage=processing_stage)

        # create running status marker file to indicate that jobs are queued
        self.mark_running_status(stage=processing_stage)

        # Submit job(s) to get the data
        last_get_data_job_no, all_get_data_job_nos = self.submit_get_data_jobs(stage=processing_stage, prior_job=prior)
        if all_get_data_job_nos:
            submitted_jobs_list.append((ccf_processing_stage.ProcessingStage.GET_DATA.name, all_get_data_job_nos))
        if last_get_data_job_no:
            prior = last_get_data_job_no

        # Submit job(s) to process the data
        last_process_job_no, all_process_data_job_nos = self.submit_process_data_jobs(stage=processing_stage, prior_job=prior)
        if all_process_data_job_nos:
            submitted_jobs_list.append((ccf_processing_stage.ProcessingStage.PROCESS_DATA.name, all_process_data_job_nos))
        if last_process_job_no:
            prior = last_process_job_no

        # Submit job(s) to clean the data
        last_clean_job_no, all_clean_data_job_nos = self.submit_clean_data_jobs(stage=processing_stage, prior_job=prior)
        if all_process_data_job_nos:
            submitted_jobs_list.append((ccf_processing_stage.ProcessingStage.CLEAN_DATA.name, all_clean_data_job_nos))
        if last_clean_job_no:
            prior = last_clean_job_no

        # Submit job(s) to put the resulting data in the DB
        last_put_job_no, all_put_job_nos = self.submit_put_data_jobs(stage=processing_stage, prior_job=prior)
        if all_put_job_nos:
            submitted_jobs_list.append((ccf_processing_stage.ProcessingStage.PUT_DATA.name, all_put_job_nos))
        if last_put_job_no:
            prior = last_put_job_no

        # Submit job(s) to perform completeness check
        last_check_job_no, all_check_job_nos = self.submit_check_jobs(stage=processing_stage, prior_job=prior)
        if all_check_job_nos:
            submitted_jobs_list.append((ccf_processing_stage.ProcessingStage.CHECK_DATA.name, all_check_job_nos))
        if last_check_job_no:
            prior = last_check_job_no

        # Submit job(s) to change running status marker file
        last_running_status_job_no, all_running_status_job_nos = self.submit_no_longer_running_jobs(stage=processing_stage, prior_job=prior)
        if all_running_status_job_nos:
            submitted_jobs_list.append(("Complete Running Status", all_running_status_job_nos))
        if last_running_status_job_no:
            prior = last_running_status_job_no

        return submitted_jobs_list

    def submit_jobs(self, processing_stage=ccf_processing_stage.ProcessingStage.CHECK_DATA):
        module_logger.debug(debug_utils.get_name() + ": processing_stage: " + str(processing_stage))

        module_logger.info("-----")

        module_logger.info("Submitting " + PIPELINE_NAME + " jobs for")
        module_logger.info("  Project: " + SUBJECT_PROJECT)
        module_logger.info("  Subject: " + SUBJECT_ID)
        module_logger.info("  Session: " + SUBJECT_SESSION)
        module_logger.info("	Stage: " + str(processing_stage))

        # make sure working directories do not have the same name based on
        # the same start time by sleeping a few seconds
        time.sleep(5)

        # build the working directory name
        os.makedirs(name=WORKING_DIR)
        os.makedirs(name=self.check_data_directory_name)
        os.makedirs(name=self.mark_completion_directory_name)

        module_logger.info("Output Resource Name: " + self.output_resource_name)

        # clean output resource if requested
        if self.clean_output_resource_first:
            module_logger.info("Deleting resource: " + self.output_resource_name + " for:")
            module_logger.info("  project: " + SUBJECT_PROJECT)
            module_logger.info("  subject: " + SUBJECT_ID)
            module_logger.info("  session: " + SUBJECT_SESSION)

            delete_resource.delete_resource(USERNAME, PASSWORD, PUT_SERVER, SUBJECT_PROJECT, SUBJECT_ID, SUBJECT_SESSION, self.output_resource_name)

        return self.do_job_submissions(processing_stage)
