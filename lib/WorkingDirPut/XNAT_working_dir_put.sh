#!/bin/bash

#~ND~FORMAT~MARKDOWN~
#~ND~START~
#
# # XNAT_working_dir_put.sh
#
# ## Copyright Notice
#
# Copyright (C) 2015-2017 The Human Connectome Project and its
#						 successor The Connectome Coordination Facility
#
# * Washington University in St. Louis
# * University of Minnesota
# * Oxford University
#
# ## Author(s)
#
# * Timothy B. Brown, Neuroinformatics Research Group,
#   Washington University in St. Louis
#
# ## Description
#
# This script pushes data from a working directory into a resource in
# the (${XNAT_PBS_JOBS_XNAT_SERVER}) XNAT database.
#
#~ND~END~

# If any commands exit with a non-zero value, this script exits
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

source ${HCP_RUN_UTILS}/shlib/log.shlib  # Logging related functions
log_Msg "XNAT_PBS_JOBS: ${XNAT_PBS_JOBS}"
log_Msg "HCP_RUN_UTILS: ${HCP_RUN_UTILS}"

if [ -z "${XNAT_PBS_JOBS_XNAT_SERVER}" ] ; then
	log_Err_Abort "XNAT_PBS_JOBS_XNAT_SERVER environment variable must be set"
fi

# Show script usage information
usage()
{
	cat <<EOF

${g_script_name} - Push data from a working directory into a resource in an
				   XNAT database. 

				   Overwrites any data currently in the resource.

				   Masks any use of the specified password (--password=) found 
				   in files in the working directory (--working-dir=). Only 
				   instances of the password found in files at the main
				   level (the working directory) are masked, not all uses of 
				   the password anywhere in all the sub-directories of the 
				   working directory. The masking operation may have the 
				   side-effect of changing the permissions on the files that
				   have had the password masked out of them.				   

Usage: ${g_script_name} <options>

Options: [ ] = optional, < > = user-supplied-value

 [--help]					: show this usage information and exit

  --user=<username>		  : XNAT DB username

  --password=<password>	  : XNAT DB password

  --server=<server>		  : XNAT server (e.g. ${XNAT_PBS_JOBS_XNAT_SERVER})

  --project=<project>		: XNAT project (e.g. HCP_500)

  --subject=<subject>		: XNAT subject ID within project (e.g. 100307)

  --session=<session>		: XNAT session ID within project (e.g. 100307_3T)

 [--scan=<scan>]			 : Scan ID (e.g. rfMRI_REST1_LR)

  --working-dir=<dir>		: Working directory from which to push data

  --resource-suffix=<suffix> : Suffix for resource in which to push data

							   Resource will be named <scan>_<suffix> or
							   simply <suffix> if scan is not specified

 [--reason=<reason>]		 : Reason for data update (e.g. name of pipeline run)

 [--leave-subject-id-level]  : Do NOT move the data in the subject ID directory
							   up one level and remove the subject ID directory.

							   This is the preferred behavior (to NOT move the
							   data in the subject ID directory up one level.)

							   However, the default is to move the data up one level
							   and remove the subject ID directory. Even though leaving
							   the subject id level is now preferred, the default
							   of moving the data up one level is for backward
							   compatibility.

 [--use-http]				: If --use-http is specified:

								  There is NO assumption that the specified working 
								  directory (--working-dir=) is available on the system 
								  running the XNAT SERVER.

							   If --use-http is NOT specified:

								  It is assumed that the specified working directory 
								  (--working-dir=) (containing the files to be pushed to 
								  the XNAT DB archive) is also available on the XNAT 
								  SERVER to which the files are being pushed. 

								  It is also assumed that the path to the working directory 
								  on the server (a.k.a. the SERVER_PATH) is related to the
								  path to the working directory on the CLIENT (a.k.a. the 
								  CLIENT_PATH) such that the SERVER_PATH can be formed by 
								  replacing the first instance of a CLIENT_STRING found
								  in the CLIENT_PATH with a SERVER_STRING.

								  The CLIENT_PATH (which is specified as the --working-dir=
								  value) is where the directory resides on the CLIENT. The
								  SERVER_PATH is where the directory resides on the SERVER.
								  The SERVER_PATH is formed by looking for the first 
								  instance of CLIENT_STRING in the CLIENT_PATH and replacing
								  it with the SERVER_STRING.

								  For example, if the CLIENT_PATH is 
								  '/HCP/hcpdb/build_ssd/chpc/BUILD/HCP_1200/this', the 
								  CLIENT_STRING is 'HCP', and the SERVER_STRING is 'data',
								  then replacing the first instance of 'HCP' (the CLIENT_STRING)
								  in the CLIENT_PATH, yields a SERVER_PATH of
								  '/data/hcpdb/build_ssd/chpc/BUILD/HCP_1200/this'.

								  The CLIENT_STRING and SERVER_STRING can be specified using
								  the --client-string= and --server-string= options specified
								  below. Each of these options has default values.

 [--client-string=<cli_str>] : Specification of CLIENT_STRING to replace with SERVER_STRING
							   in the working directory path (CLIENT_PATH) to form the 
							   SERVER_PATH (See --use-http above.)

							   This value is only used if --use-http is NOT specified.

							   Defaults to 'HCP'

 [--server-string=<ser_str>] : Specification of SERVER_STRING to put in place of the 
							   CLIENT_STRING in the working directory path (CLIENT_PATH) to
							   form the SERVER_PATH (See --use-http above.)

							   This value is only used if --use-http is NOT specified.

							   Defaults to 'data'
 
EOF
}

get_options()
{
	local arguments=($@)

	# initialize global output variables
	unset g_user
	unset g_password
	unset g_server
	unset g_project
	unset g_subject
	unset g_session
	unset g_scan
	unset g_working_dir
	unset g_resource_suffix
	unset g_reason
	unset g_leave_subject_id_level
	unset g_use_http
	unset g_client_string
	unset g_server_string
	
	# default values
	g_leave_subject_id_level="FALSE"
	g_use_http="FALSE"
	g_reason="Unspecified"
	g_client_string="HCP"
	g_server_string="data"

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
			--scan=*)
				g_scan=${argument/*=/""}
				index=$(( index + 1 ))
				;;
			--working-dir=*)
				g_working_dir=${argument/*=/""}
				index=$(( index + 1 ))
				;;
			--resource-suffix=*)
				g_resource_suffix=${argument/*=/""}
				index=$(( index + 1 ))
				;;
			--reason=*)
				g_reason=${argument/*=/""}
				index=$(( index + 1 ))
				;;
			--leave-subject-id-level)
				g_leave_subject_id_level="TRUE"
				index=$(( index + 1 ))
				;;
			--use-http)
				g_use_http="TRUE"
				index=$(( index + 1 ))
				;;
			--client-string=*)
				g_client_string=${argument/*=/""}
				index=$(( index + 1 ))
				;;
			--server-string=*)
				g_server_string=${argument/*=/""}
				index=$(( index + 1 ))
				;;
			*)
				usage
				log_Err_Abort "unrecognized option: ${argument}"
				;;
		esac
	done

	local error_count=0

	# check required parameters
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
		log_Err "server (--server=) required"
		error_count=$(( error_count + 1 ))
	else
		log_Msg "g_server: ${g_server}"
	fi

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

	# --scan= is optional
	if [ ! -z "${g_scan}" ]; then
		log_Msg "g_scan: ${g_scan}"
	fi

	if [ -z "${g_working_dir}" ]; then
		log_Err "working directory (--working-dir=) required"
		error_count=$(( error_count + 1 ))
	else
		log_Msg "g_working_dir: ${g_working_dir}"
	fi

	if [ -z "${g_resource_suffix}" ]; then
		log_Err "resource suffix (--resource-suffix=) required"
		error_count=$(( error_count + 1 ))
	else
		log_Msg "g_resource_suffix: ${g_resource_suffix}"
	fi

	if [ -z "${g_reason}" ]; then
		log_Err "reason (--reason=) required"
		error_count=$(( error_count + 1 ))
	else
		log_Msg "g_reason: ${g_reason}"
	fi

	log_Msg "g_leave_subject_id_level: ${g_leave_subject_id_level}"

	log_Msg "g_use_http: ${g_use_http}"

	if [ -z "${g_client_string}" ]; then
		log_Err "client string (--client-string=) required"
		error_count=$(( error_count + 1 ))
	else
		if [ -z "${g_use_http}" ]; then
			log_Msg "g_client_string: ${g_client_string}"
		fi
	fi

	if [ -z "${g_server_string}" ]; then
		log_Err "server string (--server-string=) required"
		error_count=$(( error_count + 1 ))
	else
		if [ -z "${g_use_http}" ]; then
			log_Msg "g_server_string: ${g_server_string}"
		fi
	fi

	if [ ${error_count} -gt 0 ]; then
		usage
		exit 1
	fi
}

# Main processing
main()
{
	get_options "$@"

	# Determine DB resource name
	log_Msg "-------------------------------------------------"
	log_Msg "Determining database resource name"
	log_Msg "-------------------------------------------------"
	if [ ! -z "${g_scan}" ]; then
		resource="${g_scan}_${g_resource_suffix}"
	else
		resource="${g_resource_suffix}"
	fi
	log_Msg "resource: ${resource}"

	# Delete previous resource
	log_Msg "-------------------------------------------------"
	log_Msg "Deleting previous resource"
	log_Msg "-------------------------------------------------"
	${XNAT_PBS_JOBS}/WorkingDirPut/DeleteResource.sh \
					--user=${g_user} \
					--password=${g_password} \
					--server=${g_server} \
					--project=${g_project} \
					--subject=${g_subject} \
					--session=${g_session} \
					--resource=${resource} \
					--protocol="https" \
					--force
	shadowserver_code=$?
	if [ ${shadowserver_code} -eq 3 ]
	then
		log_Msg "EXIT: all shadow servers are down".
		exit 1
	fi	
	
	# Make processing job log files readable so they can be pushed into the database
	chmod --recursive a+r ${g_working_dir}/*

	# Move resulting files out of the subject-id directory (if not instructed to leave it.)
	if [ "${g_leave_subject_id_level}" = "FALSE" ]; then
		log_Msg "-------------------------------------------------"
		log_Msg "Moving resulting files up one level out of the ${g_subject} directory in ${g_working_dir}"
		log_Msg "-------------------------------------------------"
		mv ${g_working_dir}/${g_session}/* ${g_working_dir}
		rm -rf ${g_working_dir:?}/${g_session}
	fi

	# Mask password
	files=$(find ${g_working_dir}/${g_session}/ProcessingInfo -maxdepth 1 -print)
	for file in ${files} ; do
		${XNAT_PBS_JOBS}/WorkingDirPut/mask_password.sh --password="${g_password}" --file="${file}" --verbose
	done

	# Push the data into the DB

	if [ "${g_use_http}" = "TRUE" ] ; then
		log_Msg "-------------------------------------------------"
		log_Msg "Putting new data into DB using HTTP from working dir: ${g_working_dir}"
		log_Msg "-------------------------------------------------"

		${XNAT_PBS_JOBS}/WorkingDirPut/PutDirIntoResource.sh \
						--user=${g_user} \
						--password=${g_password} \
						--server=${g_server} \
						--project=${g_project} \
						--subject=${g_subject} \
						--session=${g_session} \
						--resource=${resource} \
						--reason=${g_reason} \
						--dir=${g_working_dir} \
						--use-http \
						--protocol="https" \
						--force
		shadowserver_code=$?

	else

		# Build the SERVER_PATH (server_working_dir) based upon the CLIENT_PATH
		# (g_working_dir) replacing the first instance of g_client_string with
		# g_working_string
		
		#server_working_dir=${g_working_dir/HCP/data}
		server_working_dir=${g_working_dir/${g_client_string}/${g_server_string}}

		log_Msg "-------------------------------------------------"
		log_Msg "Putting new data into DB from server dir: ${server_working_dir}"
		log_Msg "-------------------------------------------------"

		${XNAT_PBS_JOBS}/WorkingDirPut/PutDirIntoResource.sh \
						--user=${g_user} \
						--password=${g_password} \
						--server=${g_server} \
						--project=${g_project} \
						--subject=${g_subject} \
						--session=${g_session} \
						--resource=${resource} \
						--reason=${g_reason} \
						--dir=${server_working_dir} \
						--protocol="https" \
						--force
		shadowserver_code=$?
	fi

	if [ ${shadowserver_code} -eq 0 ]
	then
		# Cleanup
		log_Msg "-------------------------------------------------"
		log_Msg "Cleanup"
		log_Msg "-------------------------------------------------"
		log_Msg "Removing g_working_dir: ${g_working_dir}"
		rm -rf ${g_working_dir}
	fi	
}

# Invoke the main function to get things started
main "$@"
