import requests
import argparse

def generate_url(server, project, subject):
    request_url = "http://" + server + "/data/projects/" + project + "/subjects/" + subject + "/experiments"
    return request_url
    

def get_sessions(username, password, request_url):
    response = requests.get(request_url, auth=(username, password))
    if (response.status_code != 200) or 'application/json' not in response.headers['content-type']:
        raise Exception("Server response is not OK.", request_url, response.content)

    json_result = response.json()['ResultSet']['Result']
    return json_result

def find_session_id(server, subject, project, username, password, target_session):
    request_url = generate_url(server, project, subject)
    sessions = get_sessions(username, password, request_url)

    if type(sessions) is not list:
        raise Exception( "I thought sessions was a list, turns out it's probably a dict. I can't test because server is down. Please append .values() to sessions")

    for item in sessions:
        session, sessionid = item['label'], str(item['ID'])
        if target_session == session:
            return str(sessionid)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to get session id")
    parser.add_argument("-s", "--server", dest="server", default="db.humanconnectome.org", type=str,
                        help="database server system, defaults to db.humanconnectome.org")
    parser.add_argument("-u", "--username", dest="username", required=True, type=str)
    parser.add_argument("-pw", "--password", dest="password", required=True, type=str)
    parser.add_argument("-pr", "--project", dest="project", required=True, type=str,
                        help="project in which to find session")
    parser.add_argument("-su", "--subject", dest="subject", required=True, type=str)
    parser.add_argument("-se", "--session", dest="session", required=True, type=str)
    args = parser.parse_args()

    sessionid = find_session_id(args.server, args.subject, args.project, args.username, args.password, args.session)
    print(sessionid)
