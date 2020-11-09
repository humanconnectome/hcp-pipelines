#!/bin/bash
g_script_name=$(basename "${0}")

if [ -z "${XNAT_PBS_JOBS}" ] ; then
    echo "${g_script_name}: ABORTING: XNAT_PBS_JOBS environment variable must be set"
    exit 1
fi

if [ -z "${HCP_RUN_UTILS}" ]; then
	echo "${g_script_name}: ABORTING: HCP_RUN_UTILS environment variable must be set"
	exit 1
fi

source ${HCP_LIB_DIR}/shlib/request.shlib      # API requests
source ${HCP_LIB_DIR}/shlib/log.shlib          # Logging related functions
source ${HCP_LIB_DIR}/shlib/utils.shlib        # Utility functions
log_Msg "XNAT_PBS_JOBS: ${XNAT_PBS_JOBS}"
log_Msg "HCP_RUN_UTILS: ${HCP_RUN_UTILS}"

if [ -z "${XNAT_PBS_JOBS_XNAT_SERVER}" ] ; then
    echo "${g_script_name}: ABORTING: XNAT_PBS_JOBS_XNAT_SERVER environment variable must be set"
    exit 1
fi

if [ -z "${XNAT_PBS_JOBS_PIPELINE_ENGINE}" ] ; then
    echo "${g_script_name}: ABORTING: XNAT_PBS_JOBS_PIPELINE_ENGINE environment variable must be set"
    exit 1
fi

# echo a message with the script name as a prefix
inform()
{
    local msg=${1}
    echo "${g_script_name}: ${msg}"
}

get_options()
{
    local arguments=($@)

    # initialize global output variables
    unset g_user
    unset g_password
    unset g_protocol
    unset g_server
    unset g_project
    unset g_subject
    unset g_session
    unset g_resource
    unset g_force    # No prompt

    # parse arguments
    local num_args=${#arguments[@]}
    local argument
    local index=0

    while [ ${index} -lt ${num_args} ]; do
        argument=${arguments[index]}

        case ${argument} in
            --user=*)
                g_user=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --password=*)
                g_password=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --protocol=*)
                g_protocol=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --server=*)
                g_server=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --project=*)
                g_project=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --subject=*)
                g_subject=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --session=*)
                g_session=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --resource=*)
                g_resource=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --force)
                g_force="TRUE"
                index=$(( index + 1 ))
                ;;
            *)
                inform "ERROR: unrecognized option: ${argument}"
                inform ""
                exit 1
                ;;
        esac
    done

    local default_server="${XNAT_PBS_JOBS_XNAT_SERVER}"

    local error_count=0

    # check parameters
    if [ -z "${g_user}" ]; then
        inform "ERROR: user (--user=) required"
        error_count=$(( error_count + 1 ))
    else
        inform "g_user: ${g_user}"
    fi

    if [ -z "${g_password}" ]; then
        stty -echo
        printf "Password: "
        read g_password
        echo ""
        stty echo
    fi
    inform "g_password: Now you know I'm not going to show you that."

    if [ -z "${g_server}" ]; then
        g_server="${default_server}"
    fi

    if [ -z "${g_protocol}" ]; then
        if [ "${g_server}" = "${default_server}" ]; then
            g_protocol="https"
        else
            g_protocol="http"
        fi
    fi
    inform "g_protocol: ${g_protocol}"
    inform "g_server: ${g_server}"

    if [ -z "${g_project}" ]; then
        inform "ERROR: project (--project=) required"
        error_count=$(( error_count + 1 ))
    else
        inform "g_project: ${g_project}"
    fi

    if [ -z "${g_subject}" ]; then
        inform "ERROR: subject (--subject=) required"
        error_count=$(( error_count + 1 ))
    else
        inform "g_subject: ${g_subject}"
    fi

    if [ -z "${g_session}" ]; then
        inform "ERROR: session (--session=) required"
        error_count=$(( error_count + 1 ))
    else
        inform "g_session: ${g_session}"
    fi

    if [ -z "${g_resource}" ]; then
        inform "ERROR: resource (--resource=) required"
        error_count=$(( error_count + 1 ))
    else
        inform "g_resource: ${g_resource}"
    fi

    inform "g_force: ${g_force}"

    if [ ${error_count} -gt 0 ]; then
        exit 1
    fi
}

utils_IsYes() {
    answer="$1"
    # lowercase the answer
    answer=$(echo $answer | tr '[:upper:]' '[:lower:]')
    if [ "$answer" = "y" ] || [ "$answer" = "yes" ]
    then
        return 0 # The answer is yes: True
    else
        return 1 # The answer is yes: False
    fi
}

utils_ShouldProceed() {
    echo -ne "Proceed? [n]: "
    read proceed

    if utils_IsYes $proceed
    then
        return 0 # Should proceed
    else
        return 1 # Should not proceed
    fi
}

main()
{
    get_options "$@"

    # Set up to run Python
    source ${HCP_RUN_UTILS}/ToolSetupScripts/epd-python_setup.sh

	HTTP_CODE=`curl https://${g_server} -o /dev/null -w "%{http_code}\n" -s`
	if [ "$HTTP_CODE" != "302" ] ; then
		numberofservers=($XNAT_PBS_JOBS_PUT_SERVER_LIST)
		shdw_server_list_i=0
		for shdw_server_list in ${XNAT_PBS_JOBS_PUT_SERVER_LIST}; do
			if [[ "${shdw_server_list}" == "${g_server}" ]]; then
				break
			fi
			shdw_server_list_i=$[$shdw_server_list_i + 1]
		done
		numberofservers_n=( ${numberofservers[@]:$shdw_server_list_i:${#numberofservers[@]}} ${numberofservers[@]:0:$shdw_server_list_i} )
		while_i=0
		while [ $while_i -le 60 ]; do
			log_Msg "searching for another shadow server"
			for shdw_server in ${numberofservers_n[@]}; do
				HTTP_CODE1=`curl https://${shdw_server} -o /dev/null -w "%{http_code}\n" -s`
				if [ "$HTTP_CODE1" == "302" ]; then
					g_server=${shdw_server}
					while_i=60
					log_Msg "switching to a New shadow Server: ${g_server}"
					break
				fi
			done
			while_i=$[$while_i + 1]
			if [ "$while_i" -lt 60 ]; then
				log_Msg "Sleeping for 1 minute to Check shadow servers again"
				sleep 1m
			elif [ "$while_i" -eq 60 ]; then
				log_Msg "all shadow servers are down"
				exit 3
			fi
		done
	fi

    # Get XNAT Session ID (a.k.a. the experiment ID, e.g ConnectomeDB_E1234)
    ##### get_session_id_cmd="python ${XNAT_PBS_JOBS_PIPELINE_ENGINE}/catalog/ToolsHCP/resources/scripts/sessionid.py --server=${XNAT_PBS_JOBS_XNAT_SERVER} --username=${g_user} --password=${g_password} --project=${g_project} --subject=${g_subject} --session=${g_session}"
    get_session_id_cmd="python ${XNAT_PBS_JOBS_PIPELINE_ENGINE}/catalog/ToolsHCP/resources/scripts/sessionid.py --server=${g_server} --username=${g_user} --password=${g_password} --project=${g_project} --subject=${g_subject} --session=${g_session}"
    #inform "get_session_id_cmd: ${get_session_id_cmd}"
    sessionID=$(${get_session_id_cmd})

	if [[ ${sessionID} == *Cannot\ get\ response\ from\ request* ]]; then
		inform "Cannot get session ID. Did you use the correct password?"
		exit
	fi
    inform "XNAT session ID: ${sessionID}"

    resource_url=""
    resource_url+="${g_protocol}:"
    resource_url+="//${g_server}"
    resource_url+="/REST/projects/${g_project}"
    resource_url+="/subjects/${g_subject}"
    resource_url+="/experiments/${sessionID}"
    resource_url+="/resources/${g_resource}"

    variable_values="?removeFiles=true"
    resource_uri="${resource_url}${variable_values}"

    inform "resource_uri: ${resource_uri}"

    if [ ! -z "${g_force}" ]; then
        delete_it="TRUE"
    elif utils_ShouldProceed ; then
        delete_it="TRUE"
    else
        unset delete_it
    fi

    if [ ! -z "${delete_it}" ]; then
        java -Xmx1024m -jar ${XNAT_PBS_JOBS_PIPELINE_ENGINE}/lib/XnatDataClient-1.7.6-SNAPSHOT-all.jar \
            -u ${g_user} -p ${g_password} -m DELETE \
            -r ${resource_uri}
    else
        inform "Did not attempt to delete resource: ${resource_url}"
    fi
}

# Invoke the main function to get things started
main "$@"
