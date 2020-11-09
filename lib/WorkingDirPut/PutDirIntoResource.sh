#!/bin/bash
set -e
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

if [ -z "${XNAT_PBS_JOBS_PIPELINE_ENGINE}" ] ; then
    log_Err_Abort "XNAT_PBS_JOBS_PIPELINE_ENGINE environment variable must be set"
fi

if [ -z "${XNAT_PBS_JOBS_XNAT_SERVER}" ] ; then
    log_Err_Abort "XNAT_PBS_JOBS_XNAT_SERVER environment variable must be set"
fi

usage()
{
    cat <<EOF

${g_script_name} - Put a directory of files into an XNAT DB session level resource
                   (overwrites any data currently in the resource)

Usage: ${g_script_name} <options>

Options: [ ] = optional, < > = user-supplied value

 [--help]                  : show this usage information and exit

  --user=<user>            : XNAT DB user ID

  --password=<password>    : XNAT DB password

 [--protocol={http,https}] : protocol used as part of REST call URL to put data in resource
                             If server used is ${XNAT_PBS_JOBS_XNAT_SERVER}, then
                             this value defaults to https. Otherwise, this value defaults
                             to http.

 [--server=XNAT DB server] : XNAT DB Server to which to put the data
                             Defaults to ${XNAT_PBS_JOBS_XNAT_SERVER}

  --project=<project-id>   : XNAT DB project to which to put the data

  --subject=<subject-id>   : XNAT DB subject to which to put the data

  --session=<session-id>   : XNAT DB session to which to put the data (e.g. 100307_3T)

  --resource=<resource-id> : XNAT DB session level resource in which to put the data

 [--reason=<reason>]       : Reason - pipeline run or other description of why
                             the data is being placed in the resource

                             If the reason is not specified, then a "reason" of
                             "Unspecified" is used.

  --dir=<directory>        : Directory containing data to be placed in the
                             XNAT DB resource.

                             If --use-http is NOT specified, then this should be
                             the path to the directory of data as it is accessed
                             from the system running the XNAT SERVER (i.e. the
                             path to the directory as seen from the XNAT SERVER).

                             If --use-http is specified, then this should be the
                             path to the directory of data as it is accessed from
                             the system on which this command is running (i.e.
                             the local path).

 [--force]                 : If --force is NOT specified, then the user is prompted
                             to confirm that the data should truly be uploaded
                             before the data is put in the XNAT DB.

                             If --force is specified, no prior prompting is done
                             before data is put/uploaded to the XNAT DB.

 [--use-http]              : If --use-http is NOT specified, then it is assumed that
                             the specified directory (--dir=) is an accessible path
                             on the system running the XNAT SERVER to which the data
                             is being sent.

                             If --use-http is specified, then there is no assumption
                             that the specified directory (--dir=) is an accessible
                             path on the system running the XNAT SERVER to which the
                             data is being sent. Instead the directory must be
                             an accessible path on the system on which this command
                             is being run. The directory's contents are zipped up
                             and the resulting zip file is sent to the XNAT SERVER
                             with a request to extract it into the specified resource.

EOF
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
    unset g_reason
    unset g_dir
    unset g_force
    unset g_use_http
	unset g_java_mem

    # default values
    g_use_http="FALSE"
    g_reason="Unspecified"
    g_force="FALSE"
	g_java_mem="1024"

    # parse arguments
    local num_args=${#arguments[@]}
    local argument
    local index=0

    while [ ${index} -lt ${num_args} ]; do
        argument=${arguments[index]}

        case ${argument} in
            --help)
                usage
                exit 1
                ;;
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
			--mem=*)
				g_java_mem=${argument/*=/""}
				index=$(( index + 1 ))
				;;
            --reason=*)
                g_reason=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --dir=*)
                g_dir=${argument/*=/""}
                index=$(( index + 1 ))
                ;;
            --force)
                g_force="TRUE"
                index=$(( index + 1 ))
                ;;
            --use-http)
                g_use_http="TRUE"
                index=$(( index + 1 ))
                ;;
            *)
                usage
                log_Err_Abort "unrecognized option: ${argument}"
                ;;
        esac
    done

    local default_server="${XNAT_PBS_JOBS_XNAT_SERVER}"

    local error_count=0

    # check parameters
    if [ -z "${g_user}" ]; then
        log_Err "user (--user=) required"
        error_count=$(( error_count + 1 ))
    else
        log_Msg "g_user: ${g_user}"
    fi

    if [ -z "${g_password}" ]; then
        log_Err "password (--password=) required"
        error_count=$(( error_count + 1 ))
    else
        log_Msg "g_password: *******"
    fi

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

    if [ "${g_protocol}" != "https" -a "${g_protocol}" != "http" ]; then
        log_Err "Unrecognized protocol: ${g_protocol}"
        error_count=$(( error_count + 1 ))
    fi

    log_Msg "g_protocol: ${g_protocol}"
    log_Msg "g_server: ${g_server}"

    if [ -z "${g_project}" ]; then
        log_Err "project (--project=) required"
        error_count=$(( error_count + 1 ))
    else
        log_Msg "g_project: ${g_project}"
    fi

    if [ -z "${g_subject}" ]; then
        log_Err "subject (--subject=) required"
        error_count=$(( error_count + 1 ))
    else
        log_Msg "g_subject: ${g_subject}"
    fi

    if [ -z "${g_session}" ]; then
        log_Err "session (--session=) required"
        error_count=$(( error_count + 1 ))
    else
        log_Msg "g_session: ${g_session}"
    fi

    if [ -z "${g_resource}" ]; then
        log_Err "resource (--resource=) required"
        error_count=$(( error_count + 1 ))
    else
        log_Msg "g_resource: ${g_resource}"
    fi

    if [ -z "${g_dir}" ]; then
        log_Err "dir (--dir=) required"
        error_count=$(( error_count + 1 ))
    else
        log_Msg "g_dir: ${g_dir}"
    fi

    if [ -z "${g_reason}" ]; then
        log_Err "reason (--reason=) required"
        error_count=$(( error_count + 1 ))
    else
        log_Msg "g_reason: ${g_reason}"
    fi

	log_Msg "g_java_mem: ${g_java_mem}"
    log_Msg "g_force: ${g_force}"
    log_Msg "g_use_http: ${g_use_http}"

    if [ ${error_count} -gt 0 ]; then
        usage
        exit 1
    fi
}

utils_IsYes()
{
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

    data_client_jar="${XNAT_PBS_JOBS_PIPELINE_ENGINE}/lib/XnatDataClient-1.7.6-SNAPSHOT-all.jar"
    get_session_id_script="${XNAT_PBS_JOBS_PIPELINE_ENGINE}/catalog/ToolsHCP/resources/scripts/sessionid.py"

    # Set up to run Python
    source_script ${HCP_RUN_UTILS}/ToolSetupScripts/epd-python_setup.sh

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
    get_session_id_cmd="python ${get_session_id_script}"
    get_session_id_cmd+=" --server=${g_server}"
    get_session_id_cmd+=" --username=${g_user}"
    get_session_id_cmd+=" --password=${g_password}"
    get_session_id_cmd+=" --project=${g_project}"
    get_session_id_cmd+=" --subject=${g_subject}"
    get_session_id_cmd+=" --session=${g_session}"
    # Since this command contains a password, it should only be logged in debugging mode.
    #log_Msg "get_session_id_cmd: ${get_session_id_cmd}"
    sessionID=$(${get_session_id_cmd})
    log_Msg "XNAT session ID: ${sessionID}"

    if [ "${g_use_http}" = "TRUE" ]; then
        # Zip up the specified directory and send it over http to be extracted on the server
        resource_url=""
        resource_url="${g_protocol}:"
        resource_url+="//${g_server}"
        resource_url+="/REST/projects/${g_project}"
        resource_url+="/subjects/${g_subject}"
        resource_url+="/experiments/${sessionID}"
        resource_url+="/resources/${g_resource}"
        resource_url+="/files"
        resource_url+="/"

        variable_values=""
        variable_values+="?overwrite=true"
        variable_values+="&replace=true"
        variable_values+="&event_reason=${g_reason}"
        variable_values+="&extract=true"

        resource_uri="${resource_url}${variable_values}"
        log_Msg "resource_uri: ${resource_uri}"

        if [ "${g_force}" = "TRUE" ]; then
            put_it="TRUE"
        elif utils_ShouldProceed ; then
            put_it="TRUE"
        else
            put_it="FALSE"
        fi

        if [ "${put_it}" = "TRUE" ]; then
            zipped_file=$(basename ${g_dir}).zip
            pushd ${g_dir}
            zip_cmd="zip --recurse-paths --test ${zipped_file} ."
            log_Msg "zip_cmd: ${zip_cmd}"
            ${zip_cmd}

            java_cmd=""
            java_cmd+="java -Xmx${g_java_mem}m -jar ${data_client_jar}"
            java_cmd+=" -u ${g_user}"
            java_cmd+=" -p ${g_password}"
            java_cmd+=" -m PUT"
            java_cmd+=" -r ${resource_uri}"
            java_cmd+=" -l ${zipped_file}"

            log_Msg "Using java -Xmx${g_java_mem}m -jar ${data_client_jar} to PUT the file: ${zipped_file} into the resource: ${resource_uri}"
            ${java_cmd}

            rm ${zipped_file}
            popd

        else
            log_Msg "Did not attempt to put to resource: ${resource_uri}"

        fi

    else
        # The specified directory is available on the server, so upload it "by reference"
	workfolder=$(basename ${g_dir})
        resource_url=""
        resource_url+="${g_protocol}:"
        resource_url+="//${g_server}"
        resource_url+="/REST/projects/${g_project}"
        resource_url+="/subjects/${g_subject}"
        resource_url+="/experiments/${sessionID}"
        resource_url+="/resources/${g_resource}"
        resource_url+="/files"

        variable_values=""
        variable_values+="?overwrite=true"
        variable_values+="&replace=true"
        variable_values+="&event_reason=${g_reason}"
	if [ -z "${XNAT_PBS_JOBS_SHADOWS_SUBDIR}" ]; then
        	variable_values+="&reference=${XNAT_PBS_JOBS_SHADOWS_ROOT}/chpc/BUILD/${USER}/${g_project}/${workfolder}"
	else
        	variable_values+="&reference=${XNAT_PBS_JOBS_SHADOWS_ROOT}/chpc/BUILD/${USER}/${XNAT_PBS_JOBS_SHADOWS_SUBDIR}/${g_project}/${workfolder}"
	fi

        resource_uri="${resource_url}${variable_values}"
        log_Msg "resource_uri: ${resource_uri}"

        if [ "${g_force}" = "TRUE" ]; then
            put_it="TRUE"
        elif utils_ShouldProceed ; then
            put_it="TRUE"
        else
            put_it="FALSE"
        fi

        if [ "${put_it}" = "TRUE" ]; then
            java_cmd=""
            java_cmd+="java -Xmx${g_java_mem}m -jar ${data_client_jar}"
            java_cmd+=" -u ${g_user}"
            java_cmd+=" -p ${g_password}"
            java_cmd+=" -m PUT"
            java_cmd+=" -r ${resource_uri}"

            log_Msg "Using java -Xmx${g_java_mem}m -jar ${data_client_jar} to PUT the resource: ${resource_uri}"
            ${java_cmd}

        else
            log_Msg "Did not attempt to put to resource: ${resource_uri}"

        fi

    fi
}

# Invoke the main function to get things started
main "$@"
