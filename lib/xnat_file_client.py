import os
import random
from requests_toolbelt import MultipartEncoder
import requests
import subprocess
import time


def make_zip_from_dir(dirpath):
    zipped_file = os.path.basename(dirpath) + ".zip"
    cmd = ["zip", "--recurse-paths", "--test", zipped_file, "."]
    status = subprocess.call(cmd, cwd=dirpath)
    if status == 0:
        return os.path.join(dirpath, zipped_file)
    else:
        raise Exception("Unable to create zip using shell command.", cmd)


def ping(server):
    _server = server if server.startswith("http") else f"https://{server}"
    try:
        r = requests.get(_server)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        # if shadow server is down, HAProxy abruptly terminates connection
        # causing error rather than just bad status_code
        return False


def get_server(serverlist):
    serverlist = serverlist.split()
    for i in range(60):
        print("searching for another shadow server")
        random.shuffle(serverlist)
        for shadow_server in serverlist:
            if ping(shadow_server):
                print(f"switching to a New shadow Server: {shadow_server}")
                return shadow_server
            else:
                print(f"Server ({shadow_server}) is down, trying next server")
        print("Sleeping for 1 minute to Check shadow servers again")
        time.sleep(60)

    raise Exception("all shadow servers are down")


def reference_path(filepath):
    return os.path.realpath(filepath)


class XnatFileClient:
    def __init__(
        self,
        project,
        subject,
        session,
        serverlist,
        credentials_file=None,
        protocol="https",
        username=None,
        password=None,
    ):
        if credentials_file:
            with open(credentials_file, "r") as fd:
                cred = fd.read().strip()
            username, password = cred.split("\n")
        elif username is None or password is None:
            raise Exception(
                "Either `credentials_file` needs to be specified or both `username` and `password`."
            )
        self.auth = (username, password)

        server = get_server(serverlist)
        self.server = server
        self.protocol = protocol
        self.project = project
        self.subject = subject
        self.session = session
        api_base = f"{protocol}://{server}/REST/projects/{project}/subjects/{subject}/experiments"
        sessionId = self.__get_session_id(api_base, session)
        self.sessionId = sessionId
        self.api_base = f"{api_base}/{sessionId}"

    def __put(self, url, filepath=None):
        print(url, filepath)
        if filepath:
            m = MultipartEncoder(
                fields={"file": (os.path.basename(filepath), open(filepath, "rb"))}
            )
            return requests.put(
                url, auth=self.auth, data=m, headers={"Content-Type": m.content_type}
            )
        else:
            return requests.put(url, auth=self.auth)

    def __post(self, url):
        print("POST:", url)
        return requests.post(url, auth=self.auth)

    def __delete(self, url):
        print("DELETE:", url)
        return requests.delete(url, auth=self.auth)

    def __get_session_id(self, request_url, session):
        response = requests.get(request_url, auth=self.auth)
        if response.status_code != 200:
            raise Exception("Server response is not OK.", request_url, response.content)

        sessions_list = response.json()["ResultSet"]["Result"]

        for item in sessions_list:
            if item["label"] == session:
                return item["ID"]

    def upload_resource_filepath(
        self,
        resource,
        filepath,
        reason="Unspecified",
        use_http=True,
        resource_filepath=None,
    ):
        if resource_filepath is None:
            resource_filepath = ""

        resource_url = f"{self.api_base}/resources/{resource}/files/{resource_filepath}"
        resource_url += f"?overwrite=true&replace=true&event_reason={reason}"

        filepath = os.path.abspath(filepath)
        if use_http:
            # if filepath is a directory, send as single zipped file
            if os.path.isdir(filepath):
                resource_url += "&extract=true"
                tmp_zip_file = make_zip_from_dir(filepath)
                r = self.__put(resource_url, tmp_zip_file)
                os.remove(tmp_zip_file)
            else:
                # otherwise send file directly
                r = self.__put(resource_url, filepath)
        else:
            # if file is local to XNAT server, send file path as reference
            resource_url += "&reference=" + reference_path(filepath)
            r = self.__put(resource_url)
        return r

    def remove_resource_filepath(self, resource, resource_filepath):
        resource_url = f"{self.api_base}/resources/{resource}/files/{resource_filepath}"
        return self.__delete(resource_url)

    def delete_resource(self, resource):
        resource_url = f"{self.api_base}/resources/{resource}?removeFiles=true"
        return self.__delete(resource_url)

    def refresh_catalog(self, project, subject, session, resource):
        resource_url = f"{self.protocol}://{self.server}/data/services/refresh/catalog" \
                       f"?resource=/archive/projects/{project}/subjects/{subject}/experiments/{session}/resources/{resource}" \
                        "&options=delete,append,populateStats"
        return self.__post(resource_url)
