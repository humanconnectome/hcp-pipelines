import glob
import logging
import sys
import os
import random
import time
from datetime import datetime
from pathlib import Path

from .lib.get_data import PipelineResources
from .util import escape_path, keep_resting_state_scans, shell_run, is_unreadable


def check_required_files_are_available(
    QUNEX_CONTAINER,
    XNAT_CREDENTIALS_FILE,
    EXPECTED_FILES_LIST,
    GRADIENT_COEFFICIENT_PATH,
    PYTHON_IMPORT_DIR,
    #FREESURFER_LICENSE_PATH,
    DRYRUN,
):
    if DRYRUN:
        logging.warning(
            "Dry-Mode is active: Skipping the checking of required files."
        )
        return
    if is_unreadable(QUNEX_CONTAINER):
        raise Exception("QUNEX_CONTAINER is not accessible. Value = ", QUNEX_CONTAINER)
    if is_unreadable(XNAT_CREDENTIALS_FILE):
        raise Exception("XNAT_CREDENTIALS_FILE is not accessible. Value = ", XNAT_CREDENTIALS_FILE)
    if is_unreadable(EXPECTED_FILES_LIST):
        raise Exception("EXPECTED_FILES_LIST is not accessible. Value = ", EXPECTED_FILES_LIST)
    if is_unreadable(GRADIENT_COEFFICIENT_PATH):
       raise Exception("GRADIENT_COEFFICIENT_PATH is not accessible. Value = ", GRADIENT_COEFFICIENT_PATH)
    if is_unreadable(PYTHON_IMPORT_DIR):
        raise Exception("PYTHON_IMPORT_DIR is not accessible. Value = ", PYTHON_IMPORT_DIR)
    #if is_unreadable(FREESURFER_LICENSE_PATH):
        #raise Exception("FREESURFER_LICENSE_PATH is not accessible. Value = ", FREESURFER_LICENSE_PATH)


def generate_timestamp():
    return {"TIMESTAMP": str(int(time.time()))}


def split_subject_components(_1):
    components = _1.split(":")
    if len(components) != 4:
        raise ValueError(
            "Expecting the first CLI Argument to be in the format AA:BB:CC:DD, instead got: ",
            _1,
        )

    proj, subject_id, classifier, scan = components

    if scan == "all":
        scan = ""
    _scan = "_" + scan if scan else ""

    # find the unique project identifier e.g., HCA, HCD, MDD, ECP, BWH, BANDA
    if proj.startswith("CCF_"):
        pid = proj[4:proj.find("_", 4)]
    elif proj.startswith("AABC_"):
        pid = "HCA"
    else:
        pid = "UNKNOWN"

    return {
        "PROJECT_ID": pid,
        "PROJECT": proj,
        "SUBJECT": subject_id,
        "CLASSIFIER": classifier,
        "SCAN": scan,
        "_SCAN": _scan,
        "SESSION": f"{subject_id}_{classifier}",
    }


def get_tasks(SCAN, RESOURCES_ROOT):
    mutations = {}
    tfMRI_SCAN = f"tfMRI_{SCAN}"
    mutations["TASK_SUMMARY_NAME"] = f"{tfMRI_SCAN}/{tfMRI_SCAN}"

    dir_list = sorted(Path(RESOURCES_ROOT).glob(f"{tfMRI_SCAN}_*_preproc"))
    available_bolds = [x.name[:-8] for x in dir_list]
    mutations["LEVEL1_TASKS"] = "@".join(available_bolds)
    mutations["QUNEX_SCANLIST"] = elongate_bold_list_order(available_bolds)

    # if there are two level1, then do a level2 analysis
    if "@" in mutations["LEVEL1_TASKS"]:
        mutations["LEVEL2_TASKS"] = tfMRI_SCAN

    return mutations


def choose_put_server(PUT_SERVER_LIST):
    server_list = PUT_SERVER_LIST.split(" ")
    chosen = random.choice(server_list)

    return {
        "PUT_SERVER": chosen,
    }


def set_study_folder(
    WORKING_DIR,
    SESSION,
    SCRATCH_SPACE,
    WORKING_DIR_BASENAME,
    USE_SCRATCH_FOR_PROCESSING,
):
    if USE_SCRATCH_FOR_PROCESSING:
        WORKING_DIR_SCRATCH = f"{SCRATCH_SPACE}/{WORKING_DIR_BASENAME}"
    else:
        WORKING_DIR_SCRATCH = WORKING_DIR
    STUDY_FOLDER_SCRATCH = os.path.join(WORKING_DIR_SCRATCH, SESSION)
    STUDY_FOLDER = os.path.join(WORKING_DIR, SESSION)
    STUDY_FOLDER_REPL = escape_path(STUDY_FOLDER)

    return {
        "STUDY_FOLDER": STUDY_FOLDER,
        "STUDY_FOLDER_SCRATCH": STUDY_FOLDER_SCRATCH,
        "STUDY_FOLDER_REPL": STUDY_FOLDER_REPL,
        "WORKING_DIR_SCRATCH": WORKING_DIR_SCRATCH,
    }


def make_directories(
    DRYRUN, WORKING_DIR, CLEAN_DATA_DIR, STUDY_FOLDER, CHECK_DATA_DIR, MARK_COMPLETION_DIR
):
    if not DRYRUN:
        logging.debug("Making %s", WORKING_DIR)
        os.makedirs(WORKING_DIR, exist_ok=True)
        logging.debug("Making %s", CLEAN_DATA_DIR)
        os.makedirs(CLEAN_DATA_DIR, exist_ok=True)
        logging.debug("Making study folder: %s", f"{STUDY_FOLDER}/processing")
        os.makedirs(f"{STUDY_FOLDER}/processing", exist_ok=True)
        logging.debug("Making %s", CHECK_DATA_DIR)
        os.makedirs(CHECK_DATA_DIR, exist_ok=True)
        #logging.debug("Making ", MARK_COMPLETION_DIR)
        #os.makedirs(MARK_COMPLETION_DIR, exist_ok=True)


def launch_main_script(SUBMIT_TO_PBS_SCRIPT, DRYRUN, AUTOLAUNCH_AT_END):
    if DRYRUN:
        logging.warning(
            "Dry-Mode is active: Skipping the launch of the main script to prevent side-effects."
        )
    elif not AUTOLAUNCH_AT_END:
        logging.warning(
            "AUTOLAUNCH_AT_END has been set to False. Change that in common_vars section of variables.yaml to autolaunch."
        )
    else:
        launch_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        logging.info("Launching main Bash script... at %s", launch_time)
        shell_run(f"{SUBMIT_TO_PBS_SCRIPT} --normal-start")


def available_bold_dirs(RESOURCES_ROOT, PROJECT):
    """
    List of full paths to any resource containing preprocessed functional data
    for the specified subject
    """
    dir_list = sorted(Path(RESOURCES_ROOT).glob("[rt]fMRI*preproc"))
    available_bolds = [x.name[:-8] for x in dir_list]

    def fmrisort(x):
        if "CCF_HC" in PROJECT or "AABC_STG" in PROJECT:
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
                "rfMRI_REST2b_PA"
            ]
        elif "CCF_BANDA" in PROJECT:
            priority = [
                "rfMRI_REST1_AP",
                "rfMRI_REST1_PA",
                "rfMRI_REST2_AP",
                "rfMRI_REST2_PA",
                "tfMRI_GAMBLING_AP",
                "tfMRI_GAMBLING_PA",
                "tfMRI_FACEMATCHING_AP",
                "tfMRI_FACEMATCHING_PA",
                "tfMRI_CONFLICT1_AP",
                "tfMRI_CONFLICT1_PA",
                "tfMRI_CONFLICT2_AP",
                "tfMRI_CONFLICT2_PA"
            ]
        elif "CCF_MDD" in PROJECT:
            priority = [
                "rfMRI_REST1_AP",
                "rfMRI_REST1_PA",
                "tfMRI_CARIT_PA",
                "tfMRI_FACEMATCHING_AP",
                "tfMRI_FACEMATCHING_PA",
                "rfMRI_REST2_AP",
                "rfMRI_REST2_PA"
            ]
        elif "CCF_BWH" in PROJECT:
            priority = [
                "rfMRI_REST1_AP",
                "rfMRI_REST1_PA",
                "rfMRI_REST2_AP",
                "rfMRI_REST2_PA"
            ]
        elif "CCF_ECP" in PROJECT:
            priority = [
                "rfMRI_REST1_PE1",
                "rfMRI_REST1_PE2",
                "tfMRI_SOC_PE1",
                "tfMRI_SOC_PE2",
                "tfMRI_LANG_PE1",
                "tfMRI_LANG_PE2",
                "tfMRI_SEM_PE1",
                "tfMRI_SEM_PE2",
                "rfMRI_REST2_PE1",
                "rfMRI_REST2_PE2",
                "rfMRI_REST3_PE1",
                "rfMRI_REST3_PE2",
                "tfMRI_EMOT_PE1",
                "tfMRI_EMOT_PE2",
                "rfMRI_REST4_PE1",
                "rfMRI_REST4_PE2"
            ]
        elif "CCF_ANXPE" in PROJECT:
            priority = [
                "rfMRI_REST1_AP",
                "rfMRI_REST1_PA",
                "rfMRI_REST2_AP",
                "rfMRI_REST2_PA",
                "tfMRI_FACES_AP",
                "tfMRI_FACES_PA",
                "tfMRI_GAMBLING_AP",
                "tfMRI_GAMBLING_PA",
                "tfMRI_CONFLICT1_AP",
                "tfMRI_CONFLICT1_PA",
                "tfMRI_CONFLICT2_AP",
                "tfMRI_CONFLICT2_PA"
            ]
        elif "CCF_CBA" in PROJECT:
            priority = [
                "rfMRI_REST1_AP",
                "rfMRI_REST1_PA",
                "rfMRI_REST2_AP",
                "rfMRI_REST2_PA",
                "tfMRI_WM_AP",
                "tfMRI_WM_PA",
                "rfMRI_REST3_AP",
                "rfMRI_REST3_PA",
                "rfMRI_REST4_AP",
                "rfMRI_REST4_PA",
                "tfMRI_LANGUAGE1_AP",
                "tfMRI_LANGUAGE2_PA",
                "tfMRI_MOTOR_AP",
                "tfMRI_MOTOR_PA"
            ]
        else:
            sys.exit("ERROR (available_bolds_dir):  Unexpected project value (" + PROJECT + ")")

        return priority.index(x)

    available_bolds = sorted(available_bolds, key=fmrisort)
    return {"BOLD_LIST": available_bolds}


def set_msm_all_bolds(BOLD_LIST):
    resting_bolds = keep_resting_state_scans(BOLD_LIST)
    MSM_ALL_BOLDS = ",".join(resting_bolds)

    return {"MSM_ALL_BOLDS": MSM_ALL_BOLDS}

def set_all_bolds(BOLD_LIST):
    # Just to get a comma separated list of all bolds
    all_bolds = BOLD_LIST
    ALL_BOLDS = ",".join(all_bolds)

    return {"ALL_BOLDS": ALL_BOLDS}


def set_bold_list_order(PROJECT, SCAN):
    # possible values for BOLD_LIST_ORDER
    BLO_HCA = "hca"
    BLO_BANDA = "banda"
    BLO_MDD = "mdd"
    BLO_BWH = "bwh"
    BLO_ECP = "ecp"
    BLO_HCD_YOUNG = "hcd_5_to_7"
    BLO_HCD_OLDER = "hcd_8_and_up"
    BLO_ANXPE = "anxpe"
    BLO_CBA = "cba"

    if PROJECT == "CCF_HCA_STG" or PROJECT == "CCF_HCA_TST" or PROJECT == "AABC_STG":
        bold_list_order = BLO_HCA
    elif PROJECT == "CCF_BANDA_STG":
        bold_list_order = BLO_BANDA
    elif PROJECT == "CCF_MDD_STG":
        bold_list_order = BLO_MDD
    elif PROJECT == "CCF_BWH_STG":
        bold_list_order = BLO_BWH
    elif PROJECT == "CCF_ECP_STG":
        bold_list_order = BLO_ECP
    elif PROJECT == "CCF_HCD_STG" or PROJECT == "CCF_HCD_TST":
        if SCAN == "YOUNGER":
            bold_list_order = BLO_HCD_YOUNG
        elif SCAN == "OLDER":
            bold_list_order = BLO_HCD_OLDER
        else:
            raise ValueError("The subject subgroup should be YOUNGER or OLDER.")
    elif PROJECT == "CCF_ANXPE_STG":
        bold_list_order = BLO_ANXPE
    elif PROJECT == "CCF_CBA_STG":
        bold_list_order = BLO_CBA
    else:
        raise ValueError("The BOLD LIST ORDER for this project has not yet been defined")

    return {"BOLD_LIST_ORDER_NAME": bold_list_order}

def elongate_bold_list_order(bold_list_order):
    # convert from a list of [..., 'tfMRI_GUESSING_AP', 'tfMRI_CARIT_PA', ...] into
    # [ ..., ['04: bold4:GUESSING', 'tfMRI_GUESSING_AP'], ['05: bold5:CARIT', 'tfMRI_CARIT_PA'], ..]
    elongated = []
    for i, original in enumerate(bold_list_order, start=1):
        _type, name, _direction = original.split("_")
        elongated.append(["{i:02d}: bold{i}:{name}".format(i=i, name=name), original])
    return elongated

def set_qunex_scanlist_bold(BOLD_LIST_ORDER, BOLD_LIST):
    BOLD_LIST_ORDER = elongate_bold_list_order(BOLD_LIST_ORDER)
    qunex_scanlist = [scan for scan in BOLD_LIST_ORDER if scan[1] in BOLD_LIST]
    return {"QUNEX_SCANLIST": qunex_scanlist}

def multirunicafix_process_overrides(PROJECT):
    if "BANDA" in PROJECT:
        # BANDA often exceeds the 48GB memory limit.  It needs to be set higher.
        overrides = dict(MEM_LIMIT_GBS = 60)
    else:
        overrides = {}

    return overrides
