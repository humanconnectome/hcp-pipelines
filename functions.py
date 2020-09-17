import os


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


def choose_node(_2):
    pass


def chain_jobs_on_pbs():
    pass


def make_directories(WORKING_DIR):
    os.makedirs(WORKING_DIR, exist_ok=True)
