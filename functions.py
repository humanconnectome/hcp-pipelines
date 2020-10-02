import glob
import os
import random
import time
from .util import escape_path, keep_resting_state_scans


def split_subject(_1):
    SUBJECT = _1
    components = SUBJECT.split(":")
    if len(components) != 4:
        raise ValueError(
            "Expecting a colon-delimited SUBJECT in the format AA:BB:CC:DD, instead got: ",
            SUBJECT,
        )

    proj, subject_id, classifier, extra = components
    return {
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


def chain_jobs_on_pbs():
    pass


def make_directories(WORKING_DIR):
    os.makedirs(WORKING_DIR, exist_ok=True)


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
    TESTMODE=None,
):
    SINGULARITY_VERSION = SINGULARITY_CONTAINER_VERSION
    OUTPUT_RESOURCE_NAME = f"{SUBJECT_EXTRA}_{OUTPUT_RESOURCE_SUFFIX}"

    # current seconds since 1970
    TIMESTAMP = str(int(time.time()))
    WORKING_DIR_PREFIX = f"{XNAT_PBS_JOBS_BUILD_DIR}/{SUBJECT_PROJECT}/{PIPELINE_NAME}.{SUBJECT_SESSION}_{SUBJECT_EXTRA}.{TIMESTAMP}"
    WORKING_DIR = f"{WORKING_DIR_PREFIX}.XNAT_PROCESS_DATA"
    CHECK_DATA_DIR = f"{WORKING_DIR_PREFIX}.XNAT_CHECK_DATA"
    MARK_COMPLETION_DIR = f"{WORKING_DIR_PREFIX}.XNAT_MARK_COMPLETE_RUNNING_STATUS"
    SCRIPTNAME = f"{SUBJECT_SESSION}_{SUBJECT_EXTRA}.{PIPELINE_NAME}"
    RUNPATH = f"{XNAT_PBS_JOBS}/{PIPELINE_NAME}/{PIPELINE_NAME}"
    GET_DATA_RUNPATH = f"{RUNPATH}.XNAT_GET"
    CHECK_DATA_RUNPATH = f"{RUNPATH}.XNAT_CHECK"
    MARK_RUNNING_STATUS_RUNPATH = f"{RUNPATH}.CHECK_DATA_RUNPATH"
    STARTTIME_FILE_NAME = f"{WORKING_DIR}/{SUBJECT_SESSION}/ProcessingInfo/{SUBJECT_SESSION}_{SUBJECT_EXTRA}.{PIPELINE_NAME}.starttime"
    XNAT_PBS_SETUP_SCRIPT_PATH = f"{XNAT_PBS_JOBS_CONTROL}/xnat_pbs_setup"

    if TESTMODE is not None:
        WORKING_DIR = "./temp/"
        CHECK_DATA_DIR = "./temp/"
        MARK_COMPLETION_DIR = "./temp/"
        SCRIPTNAME = "_script_"
        print("Testing Mode!!!")

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
    return {"USERNAME": "user", "PASSWORD": "pwd"}


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
    available_bolds = [
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
    ]
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


def set_qunex_boldlist(BOLD_LIST_ORDER, BOLD_LIST):
    print(BOLD_LIST_ORDER)
    print(BOLD_LIST)
    qunex_boldlist = [scan for scan in BOLD_LIST_ORDER if scan[1] in BOLD_LIST]
    return {"QUNEX_BOLDLIST": qunex_boldlist}

def set_bold_list_order(OBL_HCA, OBL_HCD_5TO7, OBL_HCD_8_AND_UP):
    order = OBL_HCD_5TO7
    return {
        "BOLD_LIST_ORDER": order
    }