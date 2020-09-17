import os
import random


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
