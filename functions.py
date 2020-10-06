import glob
import os
import random
import time
from .util import escape_path, keep_resting_state_scans, shell_run, qsub


def split_subject(_1):
    # the first positional argument is the subject string
    subject = _1
    components = subject.split(":")
    if len(components) != 4:
        raise ValueError(
            "Expecting a colon-delimited SUBJECT in the format AA:BB:CC:DD, instead got: ",
            subject,
        )

    proj, subject_id, classifier, extra = components

    if "HCA" in proj:
        proj_acronym = "HCA"
    elif "HCD" in proj:
        proj_acronym = "HCA"
    elif "MDD" in proj:
        proj_acronym = "MDD"
    elif "BWH" in proj:
        proj_acronym = "BWH"
    else:
        raise ValueError(
            "Unexpected project value. Expecting HCA, HCD, MDD, or BWH. Got: ", proj
        )

    return {
        "SUBJECT_PROJECT_ACRONYM": proj_acronym,
        "SUBJECT_PROJECT": proj,
        "SUBJECT_ID": subject_id,
        "SUBJECT_CLASSIFIER": classifier,
        "SUBJECT_EXTRA": extra,
        "SUBJECT_SESSION": f"{subject_id}_{classifier}",
    }


def choose_node(XNAT_PBS_JOBS_PUT_SERVER_LIST):
    server_list = XNAT_PBS_JOBS_PUT_SERVER_LIST.split(" ")
    return {
        "PUT_SERVER": random.choice(server_list),
    }


def chain_jobs_on_pbs(DRYRUN):
    if DRYRUN:
        print("Not actually loading on PBS, since in dryrun mode.")
    pass


def make_directories(DRYRUN, WORKING_DIR, CHECK_DATA_DIR, MARK_COMPLETION_DIR):
    if not DRYRUN:
        os.makedirs(WORKING_DIR, exist_ok=True)
        os.makedirs(CHECK_DATA_DIR, exist_ok=True)
        os.makedirs(MARK_COMPLETION_DIR, exist_ok=True)


def clean_output_resource(DRYRUN, clean_output_resource=False):
    # from lib.utils.delete_resource.py
    # delete_resource.delete_resource(
    #     self.username,
    #     self.password,
    #     self.server,
    #     self.subject.project,
    #     self.subject.subjectid,
    #     self.session,
    #     self.output_resource_name,
    # )

    if DRYRUN or not clean_output_resource:
        return

    # TODO: on line 361-370 of one_subject_job_submitter.py


def mark_running_status(
    PIPELINE_NAME,
    DRYRUN,
    MARK_RUNNING_STATUS_RUNPATH,
    USERNAME,
    PASSWORD,
    PUT_SERVER,
    SUBJECT_PROJECT,
    SUBJECT_ID,
    SUBJECT_CLASSIFIER,
    SUBJECT_EXTRA,
):
    if not DRYRUN:
        cmd = (
            f"{MARK_RUNNING_STATUS_RUNPATH} "
            f"--user={USERNAME} "
            f"--password={PASSWORD} "
            f"--server={PUT_SERVER} "
            f"--project={SUBJECT_PROJECT} "
            f"--subject={SUBJECT_ID} "
            f"--classifier={SUBJECT_CLASSIFIER} "
            f"--resource=RunningStatus --queued"
        )
        if "functional" in PIPELINE_NAME.lower():
            cmd += " --scan=" + SUBJECT_EXTRA

        completed_mark_cmd_process = shell_run(cmd)
        print(completed_mark_cmd_process)


def submit_jobs(
    DRYRUN,
    GET_DATA_JOB_SCRIPT_NAME=None,
    PROCESS_DATA_JOB_SCRIPT_NAME=None,
    CLEAN_DATA_SCRIPT_NAME=None,
    PUT_DATA_SCRIPT_NAME=None,
    CHECK_DATA_JOB_SCRIPT_NAME=None,
    MARK_NO_LONGER_RUNNING_SCRIPT_NAME=None,
    FREE_SURFER_SCRIPT_NAME=None,
):
    # short-circuit on dryrun mode
    if DRYRUN:
        return

    # all of the scripts in the order in which
    # they should be chained together
    script_list = [
        GET_DATA_JOB_SCRIPT_NAME,
        PROCESS_DATA_JOB_SCRIPT_NAME,
        CLEAN_DATA_SCRIPT_NAME,
        PUT_DATA_SCRIPT_NAME,
        CHECK_DATA_JOB_SCRIPT_NAME,
    ]

    prior_job = None
    for script in script_list:
        # chain the jobs
        # but break on first missing script
        if script:
            prior_job = qsub(script, prior_job)
        else:
            break

    # this script always goes last
    qsub(MARK_NO_LONGER_RUNNING_SCRIPT_NAME, prior_job, afterok=False)


def set_common_variables(
    SINGULARITY_CONTAINER_VERSION,
    XNAT_PBS_JOBS,
    XNAT_PBS_JOBS_BUILD_DIR,
    SUBJECT_PROJECT,
    SUBJECT_EXTRA,
    SUBJECT_SESSION,
    PIPELINE_NAME,
    OUTPUT_RESOURCE_SUFFIX,
    XNAT_PBS_JOBS_CONTROL,
):
    SINGULARITY_VERSION = SINGULARITY_CONTAINER_VERSION
    OUTPUT_RESOURCE_NAME = f"{SUBJECT_EXTRA}_{OUTPUT_RESOURCE_SUFFIX}"

    TIMESTAMP = str(int(time.time()))
    WORKING_DIR_PREFIX = f"{XNAT_PBS_JOBS_BUILD_DIR}/{SUBJECT_PROJECT}/{PIPELINE_NAME}.{SUBJECT_SESSION}_{SUBJECT_EXTRA}.{TIMESTAMP}"
    WORKING_DIR = f"{WORKING_DIR_PREFIX}.XNAT_PROCESS_DATA"
    CHECK_DATA_DIR = f"{WORKING_DIR_PREFIX}.XNAT_CHECK_DATA"
    MARK_COMPLETION_DIR = f"{WORKING_DIR_PREFIX}.XNAT_MARK_COMPLETE_RUNNING_STATUS"
    SCRIPTNAME = f"{SUBJECT_SESSION}_{SUBJECT_EXTRA}.{PIPELINE_NAME}"
    RUNPATH = f"{XNAT_PBS_JOBS}/{PIPELINE_NAME}/{PIPELINE_NAME}"
    GET_DATA_RUNPATH = f"{RUNPATH}.XNAT_GET"
    CHECK_DATA_RUNPATH = f"{RUNPATH}.XNAT_CHECK"
    MARK_RUNNING_STATUS_RUNPATH = f"{RUNPATH}.XNAT_MARK_RUNNING_STATUS"
    STARTTIME_FILE_NAME = f"{WORKING_DIR}/{SUBJECT_SESSION}/ProcessingInfo/{SUBJECT_SESSION}_{SUBJECT_EXTRA}.{PIPELINE_NAME}.starttime"
    XNAT_PBS_SETUP_SCRIPT_PATH = f"{XNAT_PBS_JOBS_CONTROL}/xnat_pbs_setup"

    return {
        "OUTPUT_RESOURCE_NAME": OUTPUT_RESOURCE_NAME,
        "SINGULARITY_VERSION": SINGULARITY_VERSION,
        "TIMESTAMP": TIMESTAMP,
        "WORKING_DIR_PREFIX": WORKING_DIR_PREFIX,
        "WORKING_DIR": WORKING_DIR,
        "CHECK_DATA_DIR": CHECK_DATA_DIR,
        "MARK_COMPLETION_DIR": MARK_COMPLETION_DIR,
        "SCRIPTNAME": SCRIPTNAME,
        "RUNPATH": RUNPATH,
        "GET_DATA_RUNPATH": GET_DATA_RUNPATH,
        "CHECK_DATA_RUNPATH": CHECK_DATA_RUNPATH,
        "MARK_RUNNING_STATUS_RUNPATH": MARK_RUNNING_STATUS_RUNPATH,
        "STARTTIME_FILE_NAME": STARTTIME_FILE_NAME,
        "XNAT_PBS_SETUP_SCRIPT_PATH": XNAT_PBS_SETUP_SCRIPT_PATH,
    }


def structural_create_check_data_job_script(SINGULARITY_PARAMS):
    SINGULARITY_PARAMS["fieldmap"] = "NONE"
    return {"SINGULARITY_PARAMS": SINGULARITY_PARAMS}


def set_credentials():
    with open(".secret", "r") as fd:
        cred = fd.read().strip()
    username, pwd = cred.split("\n")
    return {"USERNAME": username, "PASSWORD": pwd}


def available_bold_dirs(XNAT_PBS_JOBS_ARCHIVE_ROOT, SUBJECT_SESSION, SUBJECT_PROJECT):
    """
    List of full paths to any resource containing preprocessed functional data
    for the specified subject
    """

    archive_root = f"{XNAT_PBS_JOBS_ARCHIVE_ROOT}/{SUBJECT_PROJECT}/arc001"
    functional_preproc_dir = f"{archive_root}/{SUBJECT_SESSION}/RESOURCES/*fMRI*preproc"
    dir_list = sorted(glob.glob(functional_preproc_dir))
    available_bolds = [d[d.rindex("/") : d.index("_preproc")] for d in dir_list]

    def fmrisort(x):
        priority = [
            "rfMRI_REST1_AP",
            "rfMRI_REST1_PA",
            "rfMRI_REST1a_PA",
            "rfMRI_REST1a_AP",
            "rfMRI_REST1b_PA",
            "rfMRI_REST1b_AP",
            "tfMRI_GUESSING_PA",
            "tfMRI_GUESSING_AP",
            "tfMRI_VISMOTOR_PA",
            "tfMRI_CARIT_PA",
            "tfMRI_CARIT_AP",
            "tfMRI_EMOTION_PA",
            "tfMRI_FACENAME_PA",
            "rfMRI_REST2_AP",
            "rfMRI_REST2_PA",
            "rfMRI_REST2a_AP",
            "rfMRI_REST2a_PA",
            "rfMRI_REST2b_AP",
            "rfMRI_REST2b_PA",
        ]
        return priority.index(x)

    available_bolds = sorted(available_bolds, key=fmrisort)
    return {"BOLD_LIST": available_bolds}


def set_msm_all_bolds(BOLD_LIST):
    resting_bolds = keep_resting_state_scans(BOLD_LIST)
    MSM_ALL_BOLDS = ",".join(resting_bolds)

    return {"MSM_ALL_BOLDS": MSM_ALL_BOLDS}


def set_study_folder(WORKING_DIR, SUBJECT_SESSION):
    STUDY_FOLDER = os.path.join(WORKING_DIR, SUBJECT_SESSION)
    STUDY_FOLDER_REPL = escape_path(STUDY_FOLDER)

    return {
        "STUDY_FOLDER": STUDY_FOLDER,
        "STUDY_FOLDER_REPL": STUDY_FOLDER_REPL,
    }


def set_bold_list_order(SUBJECT_PROJECT, SUBJECT_EXTRA):
    # possible values for BOLD_LIST_ORDER
    BLO_HCA = "hca"
    BLO_HCD_YOUNG = "hcd_5_to_7"
    BLO_HCD_OLDER = "hcd_8_and_up"

    if SUBJECT_PROJECT == "CCF_HCA_STG":
        bold_list_order = BLO_HCA
    else:
        if SUBJECT_EXTRA == "YOUNGER":
            bold_list_order = BLO_HCD_YOUNG
        elif SUBJECT_EXTRA == "OLDER":
            bold_list_order = BLO_HCD_OLDER
        else:
            raise ValueError("The subject subgroup should be YOUNGER or OLDER.")

    return {"BOLD_LIST_ORDER": bold_list_order}


def set_qunex_boldlist(BOLD_LIST_ORDER, BOLD_LIST):
    qunex_boldlist = [scan for scan in BOLD_LIST_ORDER if scan[1] in BOLD_LIST]
    return {"QUNEX_BOLDLIST": qunex_boldlist}
