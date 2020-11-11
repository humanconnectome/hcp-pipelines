#!/usr/bin/env python3

# import of built-in modules
import contextlib
import logging
import os
import stat

# import of third-party modules

# import of local modules
import ccf.one_subject_job_submitter as one_subject_job_submitter
import utils.debug_utils as debug_utils

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2017, Connectome Coordination Facility"
__maintainer__ = "Timothy B. Brown"

# create a module logger
module_logger = logging.getLogger(__name__)
# Note: This can be overidden by log file configuration
module_logger.setLevel(logging.WARNING)


class OneSubjectJobSubmitter(one_subject_job_submitter.OneSubjectJobSubmitter):
    def PIPELINE_NAME(self):
        return "DeDriftAndResample"

    def create_work_script(self):
        module_logger.debug(debug_utils.get_name())

        script_name = self.work_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        script = open(script_name, "w")

        script.write("#PBS -l nodes=" + PBS_NODES + ":ppn=" + PBS_PPN + ",walltime=" + WALLTIME_LIMIT_HOURS + ":00:00,vmem=" + MEM_LIMIT_GBS + "gb\n")
        script.write("#PBS -o " + WORKING_DIR + "\n")
        script.write("#PBS -e " + WORKING_DIR + "\n")
        script.write("\n")
        script.write(self.xnat_pbs_jobs_home + "/" + PIPELINE_NAME + "/" + PIPELINE_NAME + ".XNAT.sh \\\n")
        script.write("  --user=" + USERNAME + " \\\n")
        script.write("  --password=" + PASSWORD + " \\\n")
        script.write("  --server=" + PUT_SERVER + " \\\n")
        script.write("  --project=" + SUBJECT_PROJECT + " \\\n")
        script.write("  --subject=" + SUBJECT_ID + " \\\n")
        script.write("  --session=" + SUBJECT_SESSION + " \\\n")

        script.write("  --working-dir=" + WORKING_DIR + "\\\n")
        script.write("  --setup-script=" + self.xnat_pbs_jobs_home + "/" + PIPELINE_NAME + "/" + self.setup_script + "\n")

        script.close()
        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def create_clean_data_script(self):
        module_logger.debug(debug_utils.get_name())

        # first create the "standard" version of the clean data script
        super().create_clean_data_script()

        # Add a statement to it to get rid of a bit more
        script_name = self.clean_data_script_name

        with open(script_name, "a") as script:
            script.write('echo "Removing subdirectories for other subjects ')
            script.write('and groups"' + "\n")
            script.write("find " + WORKING_DIR + " -maxdepth 1 -type d -not -newer " + STARTTIME_FILE_NAME + " -exec rm -rf {} \;")
            script.write("\n")
            script.write('echo "Remaining files:"' + "\n")
            script.write("find " + WORKING_DIR + "/" + SUBJECT_ID + "\n")

    def output_resource_name(self):
        module_logger.debug(debug_utils.get_name())
        return self.output_resource_suffix
