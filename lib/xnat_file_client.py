import os
import random
from requests_toolbelt import MultipartEncoder
import requests
import subprocess
import time
import sys


def make_zip_from_dir(dirpath):
    zipped_file = os.path.basename(dirpath) + ".zip"
    cmd = ["zip", "--recurse-paths", "--test", zipped_file, "."]
    status = subprocess.call(cmd, cwd=dirpath)
    if status == 0:
        return os.path.join(dirpath, zipped_file)
    else:
        raise Exception("Unable to create zip using shell command.", cmd)


def ping(server):
    try:
        r = requests.get(server)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        # if shadow server is down, HAProxy abruptly terminates connection
        # causing error rather than just bad status_code
        return False


def get_server(serverlist):
    serverlist = serverlist.split()
    for i in range(60):
        print("searching for shadow server")
        random.shuffle(serverlist)
        for shadow_server in serverlist:
            if not shadow_server.startswith("http"):
                raise Exception("Server must specify protocol (http or https) and optionally the port. e.g., http://shadow1.wustl.edu:8080 . You tried: ", shadow_server)
            elif ping(shadow_server):
                print(f"switching to a shadow Server: {shadow_server}")
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
        self.project = project
        self.subject = subject
        self.session = session
        api_base = f"{server}/REST/projects/{project}/subjects/{subject}/experiments"
        sessionId = self.__get_session_id(api_base, session)
        self.sessionId = sessionId
        self.api_base = f"{api_base}/{sessionId}"

    def _put(self, url, filepath=None):
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

    def _post(self, url):
        print("POST:", url)
        return requests.post(url, auth=self.auth)

    def _delete(self, url):
        print("DELETE:", url)
        return requests.delete(url, auth=self.auth)

    def _get(self, url):
        print("GET:", url)
        return requests.get(url, auth=self.auth)

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
                r = self._put(resource_url, tmp_zip_file)
                os.remove(tmp_zip_file)
            else:
                # otherwise send file directly
                r = self._put(resource_url, filepath)
        else:
            # if file is local to XNAT server, send file path as reference
            resource_url += "&reference=" + reference_path(filepath)
            r = self._put(resource_url)
        return r

    def remove_resource_filepath(self, resource, resource_filepath):
        resource_url = f"{self.api_base}/resources/{resource}/files/{resource_filepath}"
        return self._delete(resource_url)

    def delete_resource(self, resource, RESOURCES_ROOT, attempts=3):
        resource_url = f"{self.api_base}/resources/{resource}?removeFiles=true"
        resource_path = str(RESOURCES_ROOT / resource)

        for i in range(attempts):
            print(f'Delete attempt #{i + 1}')
            response = self._delete(resource_url)

            # check every 10 seconds that cummulative filesize is shrinking (ie, deletion in progress)
            old_size, new_size = sys.maxsize, get_size(resource_path)
            while old_size > new_size:
                if new_size == 0:
                    print("Successfully deleted.")
                    return response

                time.sleep(10)
                old_size, new_size = new_size, get_size(resource_path)
                print("Current size: ", new_size)
        else:
            print("ERROR: Deletion failed three times. Quitting.")
            sys.exit(1)

    def refresh_catalog(self, project, subject, session, resource):
        resource_url = f"{self.server}/data/services/refresh/catalog" \
                       f"?resource=/archive/projects/{project}/subjects/{subject}/experiments/{session}/resources/{resource}" \
                        "&options=delete,append,populateStats"
        return self._post(resource_url)

    def resource_exists(self, resource):
        resource_url = f"{self.api_base}/resources/{resource}"
        r = self._get(resource_url)
        return r.status_code == 200


def get_size(p):
    if not os.path.exists(p):
        return 0
    try:
        size = subprocess.check_output(["du", "-s", p]).decode()
        size = int(size[:size.find("\t")])
        return size
    except:
        return -1
