def escape_path(text):
    return text.replace("\\", "\\\\").replace("/", "\\/").replace("&", "\\&")


def keep_resting_state_scans(scans):
    return [x for x in scans if not (x.startswith("t") or x.startswith("f"))]
