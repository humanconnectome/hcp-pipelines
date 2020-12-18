#!/bin/bash

unset StudyFolder
#unset InputDataLocation
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
ParameterFolder='{{ QUNEX_PARAMETER_FILES }}'
StudyFolder='{{ STUDY_FOLDER_SCRATCH }}'
Session='{{ SUBJECT_SESSION }}'
SubjectPart='{{ SUBJECT_ID }}'
Overwrite='{{ QUNEX_OVERWRITE|default("yes", true) }}'
HCPpipelineProcess='{{ PIPELINE_NAME }}'
Scan='{{ SUBJECT_EXTRA }}'

export StudyFolder Session SubjectPart

TimeStamp=`date +%Y-%m-%d-%H-%M-%S`
mkdir -p $StudyFolder/processing/logs &> /dev/null
LogFile="$StudyFolder/processing/logs/${scriptName}_${TimeStamp}.log"

# only if overriding the default setting of /opt/HCP/HCPpipelines
#export con_HCPPIPEDIR="/opt/HCP/HCPpipelines"
source /opt/qunex/library/environment/qunex_environment.sh  >> ${LogFile}
source /opt/qunex/library/environment/qunex_envStatus.sh --envstatus >> ${LogFile}

parsessions=1      # the number of subjects to process in parallel
threads=1    # the number of bold files to process in parallel

# -- Derivative variables
SessionsFolder="${StudyFolder}/sessions"
BatchFile="${StudyFolder}/processing/batch.txt"

# -- Report options
echo "-- ${scriptName}: Specified Command-Line Options - Start --"                2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   QUNEX Study          : $StudyFolder"                                     2>&1 | tee -a ${LogFile}
#echo "   Input data location  : $InputDataLocation"                               2>&1 | tee -a ${LogFile}
echo "   Cores to use         : $parsessions"                                           2>&1 | tee -a ${LogFile}
echo "   Threads to use       : $threads"                                         2>&1 | tee -a ${LogFile}
echo "   QUNEX subjects folder: $SessionsFolder"                                  2>&1 | tee -a ${LogFile}
echo "   QUNEX batch file     : $BatchFile"                                       2>&1 | tee -a ${LogFile}
echo "   Overwrite HCP step   : $Overwrite"                                       2>&1 | tee -a ${LogFile}
echo "   Subjects to run      : $Session"                                         2>&1 | tee -a ${LogFile}
echo "   HCP pipelne process  : $HCPpipelineProcess"                              2>&1 | tee -a ${LogFile}
echo "   Log file output      : $LogFile"                                         2>&1 | tee -a ${LogFile}
echo ""                                                                           2>&1 | tee -a ${LogFile}
echo "-- ${scriptName}: Specified Command-Line Options - End --"                  2>&1 | tee -a ${LogFile}
echo ""                                                                           2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}

# -- Define QUNEX command
QUNEXCOMMAND="bash $QUNEXCONNPATH/qunex"

log_Msg()
{
	local msg="$*"
	local dateTime
	dateTime=$(date)
	local toolname

	if [ -z "${log_toolName}" ]; then
		toolname=$(basename ${0})
	else
		toolname="${log_toolName}"
	fi

	echo ${dateTime} "-" ${toolname} "-" "${msg}"
}

main() {

#########################	createStudy
${QUNEXCOMMAND} createStudy --studyfolder="${StudyFolder}"
cd ${SessionsFolder}
### qunex_setup ###
#{% block qunex_setup %}

	## Copy in ParameterFiles and SpecFiles (NOTE:  Not necessary for MR-FIX)
	if [ ! -z "$ParameterFolder" ]; then
		cp ${ParameterFolder}/* "${StudyFolder}/sessions/specs"
	fi

	${QUNEXCOMMAND} importHCP \
		--sessionsfolder="${StudyFolder}/sessions"  \
		--inbox="${StudyFolder}/unprocessed" \
		--action="link" \
		--overwrite="${Overwrite}" \
		--archive="leave"

	#########################	setupHCP
	${QUNEXCOMMAND} setupHCP \
	    --sessionsfolder="${StudyFolder}/sessions" \
	    --sessions="${Session}"
	 
	#########################	createBatch
	${QUNEXCOMMAND} createBatch \
	 --sessionsfolder="${StudyFolder}/sessions" \
	 --overwrite="append" \
	 --paramfile="${StudyFolder}/sessions/specs/batch_parameters.txt"

#{% endblock qunex_setup %}



sleep 5
mkdir ${StudyFolder}/ProcessingInfo

if [ ! -z "${Scan}" ]; then
	subject_name="${Session}_${Scan}"
else
	subject_name="${Session}"
fi

start_time_file="${StudyFolder}/ProcessingInfo/${subject_name}.${HCPpipelineProcess}.starttime"
g_script_name=$(basename "${0}" .sh)
filename="${StudyFolder}/ProcessingInfo/${subject_name}.${HCPpipelineProcess}.${g_script_name}.execinfo"
echo $(date) > ${start_time_file}
log_Msg "PBS_JOBID: ${PBS_JOBID}" > ${filename}
log_Msg "PBS execution node: $(hostname)" >> ${filename}


### pipeline_specific ###
#{% block pipeline_specific %}
#{% endblock pipeline_specific %}

${QUNEXCOMMAND} exportHCP \
    --sessionsfolder="${StudyFolder}/sessions" \
    --sessions="${StudyFolder}/processing/batch.txt" \
    --mapaction="link" \
    --mapto="${StudyFolder}" \
    --overwrite="yes" \
    --verbose="no"

}

main $@
