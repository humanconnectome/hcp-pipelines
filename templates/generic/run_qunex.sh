#!/bin/bash

unset StudyFolder
unset ParametersFile

echo ""
echo " -- Reading inputs... "
echo ""

# -- Define script name
scriptName=$(basename ${0})
scriptPath=$(dirname ${0})

# =-=-=-=-=-= GENERAL OPTIONS =-=-=-=-=-=
#
# -- key variables to set
StudyFolder='{{ STUDY_FOLDER_SCRATCH }}'
ParametersFile="$StudyFolder/sessions/specs/batch_parameters.txt"
Session='{{ SESSION }}'
SubjectPart='{{ SUBJECT }}'
Overwrite='{{ QUNEX_OVERWRITE|default("yes", true) }}'
HCPpipelineProcess='{{ PIPELINE_NAME }}'
start_time_file="{{ STARTTIME_FILE_NAME }}"
parsessions=1   # the number of sessions to process in parallel
threads=1       # the number of bold files to process in parallel
BatchFile="${StudyFolder}/processing/batch.txt"

export StudyFolder Session SubjectPart parsessions threads BatchFile

TimeStamp=`date +%Y-%m-%d-%H-%M-%S`
mkdir -p $StudyFolder/processing/logs &> /dev/null
LogFile="$StudyFolder/processing/logs/${scriptName}_${TimeStamp}.log"

source /opt/qunex/env/qunex_environment.sh  >> ${LogFile}
source /opt/qunex/env/qunex_container_env_status.sh --envstatus >> ${LogFile}


# -- Report options
echo "-- ${scriptName}: Specified Command-Line Options - Start --"                2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   QUNEX Study          : $StudyFolder"                                     2>&1 | tee -a ${LogFile}
echo "   Cores to use         : $parsessions"                                     2>&1 | tee -a ${LogFile}
echo "   Threads to use       : $threads"                                         2>&1 | tee -a ${LogFile}
echo "   QUNEX sessions folder: ${StudyFolder}/sessions"                          2>&1 | tee -a ${LogFile}
echo "   QUNEX batch file     : $BatchFile"                                       2>&1 | tee -a ${LogFile}
echo "   Overwrite?           : $Overwrite"                                       2>&1 | tee -a ${LogFile}
echo "   Sessions to run      : $Session"                                         2>&1 | tee -a ${LogFile}
echo "   HCP pipeline process : $HCPpipelineProcess"                              2>&1 | tee -a ${LogFile}
echo "   Log file output      : $LogFile"                                         2>&1 | tee -a ${LogFile}
echo ""                                                                           2>&1 | tee -a ${LogFile}
echo "-- ${scriptName}: Specified Command-Line Options - End --"                  2>&1 | tee -a ${LogFile}
echo ""                                                                           2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}

# -- Define QUNEX command
QUNEXCOMMAND="bash $QUNEXPATH/bin/qunex"


#########################	createStudy
${QUNEXCOMMAND} create_study --studyfolder="${StudyFolder}"
cd ${StudyFolder}/sessions

### BEGIN qunex_setup ### {% block qunex_setup %}
# {% if USE_CUSTOM_BATCH is defined %}
## This pipeline uses a template-based approach to generate the id/scan portion of batch.txt, rather than 'createBatch'
# {% else %}
  #########################	importHCP
	${QUNEXCOMMAND} import_hcp \
		--sessionsfolder="${StudyFolder}/sessions"  \
		--inbox="${StudyFolder}/unprocessed" \
		--action="link" \
		--overwrite="${Overwrite}" \
		--archive="leave"

	#########################	setupHCP
	${QUNEXCOMMAND} setup_hcp \
	    --sessionsfolder="${StudyFolder}/sessions" \
	    --sessions="${Session}" \
	    --hcp_filename="original" 

	#########################	createBatch
	${QUNEXCOMMAND} create_batch \
	 --sessionsfolder="${StudyFolder}/sessions" \
	 --overwrite="append" \
	 --paramfile="$ParametersFile"

#{% endif %}{% endblock qunex_setup %}
### END qunex_setup ###

sleep 5
mkdir ${StudyFolder}/ProcessingInfo
echo $(date) > ${start_time_file}


### BEGIN pipeline_specific ###
#{% block pipeline_specific %} NOT YET IMPLEMENTED !!! {% endblock pipeline_specific %}
### END pipeline_specific ###
