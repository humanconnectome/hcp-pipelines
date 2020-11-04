import glob
import os
import random
import shutil
import time
from .util import escape_path, keep_resting_state_scans, shell_run, qsub


def generate_timestamp(TIMESTAMP=None):
    if TIMESTAMP is None:
        return {"TIMESTAMP": str(int(time.time()))}


def split_subject_components(SUBJECT):
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


def get_project_acronym(SUBJECT_PROJECT):
    proj = SUBJECT_PROJECT
    if "HCA" in proj:
        proj_acronym = "HCA"
    elif "HCD" in proj:
        proj_acronym = "HCD"
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
    }


def set_credentials_from_file(XNAT_CREDENTIALS_FILE):
    with open(XNAT_CREDENTIALS_FILE, "r") as fd:
        cred = fd.read().strip()
    username, pwd = cred.split("\n")
    return {"USERNAME": username, "PASSWORD": pwd}


def choose_put_server(XNAT_PBS_JOBS_PUT_SERVER_LIST, PUT_SERVER=None):
    if PUT_SERVER is not None:
        print("PUT_SERVER has already been set. Skipping regeneration.")
        return

    server_list = XNAT_PBS_JOBS_PUT_SERVER_LIST.split(" ")
    chosen = random.choice(server_list)

    return {
        "PUT_SERVER": chosen,
    }


def set_study_folder(
    WORKING_DIR,
    SUBJECT_SESSION,
    SCRATCH_SPACE,
    WORKING_DIR_BASENAME,
    USE_SCRATCH_FOR_PROCESSING,
):
    if USE_SCRATCH_FOR_PROCESSING:
        WORKING_DIR = f"{SCRATCH_SPACE}/{WORKING_DIR_BASENAME}"
    STUDY_FOLDER = os.path.join(WORKING_DIR, SUBJECT_SESSION)
    STUDY_FOLDER_REPL = escape_path(STUDY_FOLDER)

    return {
        "STUDY_FOLDER": STUDY_FOLDER,
        "STUDY_FOLDER_REPL": STUDY_FOLDER_REPL,
    }


def make_directories(
    DRYRUN, WORKING_DIR, STUDY_FOLDER, CHECK_DATA_DIR, MARK_COMPLETION_DIR
):
    if not DRYRUN:
        print("Making ", WORKING_DIR)
        os.makedirs(WORKING_DIR, exist_ok=True)
        print("Making study folder: ", WORKING_DIR)
        os.makedirs(f"{STUDY_FOLDER}/processing", exist_ok=True)
        print("Making ", CHECK_DATA_DIR)
        os.makedirs(CHECK_DATA_DIR, exist_ok=True)
        print("Making ", MARK_COMPLETION_DIR)
        os.makedirs(MARK_COMPLETION_DIR, exist_ok=True)


def copy_free_surfer_assessor_script(
    DRYRUN, XNAT_PBS_JOBS, PIPELINE_NAME, WORKING_DIR, PRUNNER_CONFIG_DIR
):
    source = f"{XNAT_PBS_JOBS}/{PIPELINE_NAME}/{PIPELINE_NAME}.XNAT_CREATE_FREESURFER_ASSESSOR"
    dest = f"{WORKING_DIR}/{PIPELINE_NAME}.XNAT_CREATE_FREESURFER_ASSESSOR"
    if not DRYRUN:
        shutil.copy(source, dest)
        os.chmod(dest, 0o770)

    return {"FREESURFER_ASSESSOR_DEST_PATH": dest}


def launch_main_script(SUBMIT_TO_PBS_SCRIPT, DRYRUN, AUTOLAUNCH_AT_END):
    if DRYRUN:
        print(
            "Dry-Mode is active: Skipping the launch of the main script to prevent side-effects."
        )
    elif not AUTOLAUNCH_AT_END:
        print(
            "AUTOLAUNCH_AT_END has been set to False. Change that in common_vars section of variables.yaml to autolaunch."
        )
    else:
        print("Launching main Bash script...")
        shell_run(SUBMIT_TO_PBS_SCRIPT)


def available_bold_dirs(XNAT_PBS_JOBS_ARCHIVE_ROOT, SUBJECT_SESSION, SUBJECT_PROJECT):
    """
    List of full paths to any resource containing preprocessed functional data
    for the specified subject
    """

    archive_root = f"{XNAT_PBS_JOBS_ARCHIVE_ROOT}/{SUBJECT_PROJECT}/arc001"
    functional_preproc_dir = f"{archive_root}/{SUBJECT_SESSION}/RESOURCES/*fMRI*preproc"
    dir_list = sorted(glob.glob(functional_preproc_dir))
    available_bolds = [d[d.rindex("/") + 1 : d.index("_preproc")] for d in dir_list]

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


def set_bold_list_order(SUBJECT_PROJECT, SUBJECT_EXTRA):
    # possible values for BOLD_LIST_ORDER
    BLO_HCA = "hca"
    BLO_HCD_YOUNG = "hcd_5_to_7"
    BLO_HCD_OLDER = "hcd_8_and_up"

    if SUBJECT_PROJECT == "CCF_HCA_STG" or "CCF_HCA_TST":
        bold_list_order = BLO_HCA
    else:
        if SUBJECT_EXTRA == "YOUNGER":
            bold_list_order = BLO_HCD_YOUNG
        elif SUBJECT_EXTRA == "OLDER":
            bold_list_order = BLO_HCD_OLDER
        else:
            raise ValueError("The subject subgroup should be YOUNGER or OLDER.")

    return {"BOLD_LIST_ORDER": bold_list_order}


def set_qunex_scanlist(BOLD_LIST_ORDER, BOLD_LIST):
    qunex_scanlist = [scan for scan in BOLD_LIST_ORDER if scan[1] in BOLD_LIST]
    return {"QUNEX_SCALIST": qunex_scanlist}

def set_qunex_scanlist_dwi(SUBJECT_PROJECT, SUBJECT_EXTRA):
    if SUBJECT_PROJECT in ['CCF_HCA_STG','CCF_HCD_STG'] :
        qunex_scanlist = [
            ['01: DWI:dir98_AP','dMRI_dir98_AP'],
            ['02: DWI:dir98_AP','dMRI_dir98_PA'],
            ['03: DWI:dir99_AP','dMRI_dir99_AP'],
            ['04: DWI:dir99_AP','dMRI_dir99_PA']
        ]
    return {"QUNEX_SCANLIST": qunex_scanlist}

def structural_get_data_job_script(USE_PRESCAN_NORMALIZED, SINGULARITY_PARAMS):
    SINGULARITY_PARAMS["delay-seconds"] = 120
    del SINGULARITY_PARAMS["scan"]
    if USE_PRESCAN_NORMALIZED:
        SINGULARITY_PARAMS["use-prescan-normalized"] = None

    return {"SINGULARITY_PARAMS": SINGULARITY_PARAMS}


def structural_create_check_data_job_script(SINGULARITY_PARAMS):
    SINGULARITY_PARAMS["fieldmap"] = "NONE"
    return {"SINGULARITY_PARAMS": SINGULARITY_PARAMS}
