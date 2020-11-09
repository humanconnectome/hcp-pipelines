import requests
import argparse
import sys
import json
import inspect

def get_json_response_list_of_lists(username, password, request_url, keys):
    response_list = list()

    response = requests.get(request_url, auth=(username, password))
    if (response.status_code != 200):
        print(inspect.stack()[0][3] + ": Cannot get response from request: " + request_url)
        sys.exit(1)

    if not 'application/json' in response.headers['content-type']:
        print(inspect.stack()[0][3] + ": Unexpected response content-type: " + response.headers['content-type'] + " from " + request_url)
        sys.exit(1)

    json_response = json.loads(response.text)
    json_result_set = json_response['ResultSet']
    json_record_count = int(json_result_set['totalRecords'])
    json_result = json_result_set['Result']
    xrange=range
    for i in xrange(0, json_record_count):
        item_list = list()
        for key in keys:
            item_list.append(str(json_result[i][key]))
        response_list.append(item_list)

    return response_list
    

def main():

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

    session_and_session_id_list = list()
    request_url = "http://" + args.server + "/data/projects/" + args.project + "/subjects/" + args.subject + "/experiments"
    session_and_session_id_list = get_json_response_list_of_lists(args.username, args.password, request_url, ['label', 'ID'])
    
    for session_and_session_id in session_and_session_id_list:
        if args.session == session_and_session_id[0]:
            print('%s' % session_and_session_id[1])

if __name__ == '__main__':
    main()
