import os
import random
import time


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


def choose_node(_2, XNAT_PBS_JOBS_PUT_SERVER_LIST):
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
    }


def structural_create_check_data_job_script(SINGULARITY_PARAMS):
    SINGULARITY_PARAMS["fieldmap"] = "NONE"
    return {"SINGULARITY_PARAMS": SINGULARITY_PARAMS}
