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
import utils.str_utils as str_utils

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2017, The Human Connectome Project"
__maintainer__ = "Timothy B. Brown"

# create a module logger
module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.WARNING)  # Note: This can be overridden by log file configuration


class OneSubjectJobSubmitter(one_subject_job_submitter.OneSubjectJobSubmitter):
    def PIPELINE_NAME(self):
        return "ReApplyFix"

    def create_work_script(self):
        module_logger.debug(debug_utils.get_name())

        script_name = self.work_script_name

        with contextlib.suppress(FileNotFoundError):
            os.remove(script_name)

        with open(script_name, "w") as script:
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
            script.write("  --scan=" + SUBJECT_EXTRA + " \\\n")
            script.write("  --working-dir=" + WORKING_DIR + " \\\n")
            if self.reg_name != "MSMSulc":
                script.write("  --reg-name=" + self.reg_name + " \\\n")
            script.write("  --setup-script=" + self.xnat_pbs_jobs_home + "/" + PIPELINE_NAME + "/" + self.setup_script + "\n")

        os.chmod(script_name, stat.S_IRWXU | stat.S_IRWXG)

    def output_resource_name(self):
        module_logger.debug(debug_utils.get_name())
        return SUBJECT_EXTRA + "_" + self.output_resource_suffix
