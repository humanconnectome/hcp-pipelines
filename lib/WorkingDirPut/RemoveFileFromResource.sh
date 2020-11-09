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

if [ -z "${XNAT_PBS_JOBS_PIPELINE_ENGINE}" ] ; then
	log_Err_Abort "XNAT_PBS_JOBS_PIPELINE_ENGINE environment variable must be set"
fi

if [ -z "${XNAT_PBS_JOBS_XNAT_SERVER}" ] ; then
	log_Err_Abort "XNAT_PBS_JOBS_XNAT_SERVER environment variable must be set"
fi

usage()
{
		cat <<EOF

Removes a file from a resource

Example invocation when file is available on the server

  ./RemoveFileFromResource.sh
	--user=tbbrown
	--password=<some_password>
	--project=PipelineTest
	--subject=100307
	--session=100307_3T
	--resource=Structural_preproc
	--file-path-within-resource=T1w/wmparc.nii.gz	  # Should not start with a slash "/"

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
	unset g_file_path_within_resource # should not start with a slash

	# default values

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
			--file-path-within-resource=*)
				g_file_path_within_resource=${argument/*=/""}
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

	if [ -z "${g_file_path_within_resource}" ]; then
		log_Err "file path within resource (--file-path-within-resource=) required"
		error_count=$(( error_count + 1 ))
	else
		log_Msg "g_file_path_within_resource: ${g_file_path_within_resource}"
	fi

	if [ ${error_count} -gt 0 ]; then
		usage
		exit 1
	fi
}

main()
{
	get_options "$@"

	get_session_id_script="${XNAT_PBS_JOBS_PIPELINE_ENGINE}/catalog/ToolsHCP/resources/scripts/sessionid.py"

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

	resource_url=""
	resource_url+="${g_protocol}:"
	resource_url+="//${g_server}"
	resource_url+="/REST/projects/${g_project}"
	resource_url+="/subjects/${g_subject}"
	resource_url+="/experiments/${sessionID}"
	resource_url+="/resources/${g_resource}"
	resource_url+="/files"
	resource_url+="/${g_file_path_within_resource}"

	resource_uri="${resource_url}"
	log_Msg "resource_uri: ${resource_uri}"

	log_Msg "Using curl to DELETE the file: ${g_file} into the resource: ${resource_uri}"
	api_delete $resource_uri
}

# Invoke the main function to get things started
main "$@"
