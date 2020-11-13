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
ParameterFolder='{{ SINGULARITY_QUNEXPARAMETER_PATH }}'
StudyFolder='{{ STUDY_FOLDER_SCRATCH }}'
Subject='{{ SUBJECT_SESSION }}'
SubjectPart='{{ SUBJECT_ID }}'
Overwrite='{{ QUNEX_OVERWRITE|default("yes", true) }}'
HCPpipelineProcess='{{ PIPELINE_NAME }}'
Scan='{{ SUBJECT_EXTRA }}'

export StudyFolder Subject SubjectPart

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
SubjectsFolder="${StudyFolder}/sessions"
BatchFile="${StudyFolder}/processing/batch.txt"

# -- Report options
echo "-- ${scriptName}: Specified Command-Line Options - Start --"                2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   QUNEX Study          : $StudyFolder"                                     2>&1 | tee -a ${LogFile}
#echo "   Input data location  : $InputDataLocation"                               2>&1 | tee -a ${LogFile}
echo "   Cores to use         : $parsessions"                                           2>&1 | tee -a ${LogFile}
echo "   Threads to use       : $threads"                                         2>&1 | tee -a ${LogFile}
echo "   QUNEX subjects folder: $SubjectsFolder"                                  2>&1 | tee -a ${LogFile}
echo "   QUNEX batch file     : $BatchFile"                                       2>&1 | tee -a ${LogFile}
echo "   Overwrite HCP step   : $Overwrite"                                       2>&1 | tee -a ${LogFile}
echo "   Subjects to run      : $Subject"                                         2>&1 | tee -a ${LogFile}
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
old_setup_code_for_msmall_multirunicafix_diffusion() {
# this is now replaced by template located in "generic/batch.txt.jinja2"
#if [ "${HCPpipelineProcess}" == "MultiRunIcaFixProcessing" ] || [ "${HCPpipelineProcess}" == "MsmAllProcessing" ] ; then

	## For these pipelines, we use a template-based approach to generate batch.txt rather than 'createBatch'.
	## hcp_icafix_bolds: Not specified directly in batch.txt -- instead both hcp_ICAFix and hcp_MSMAll will
	##   internally construct this parameter from the runs (and their order) listed in the resulting batch.txt.
	##   It is important that this parameter is identical in both pipelines for the processing to work correctly,
	##   which is why both pipelines are handled in an integrated fashion within this same conditional.
	## hcp_msmall_bolds: Controls which runs contribute to the MSMAll registration, which should be just the
	##   resting-state scans. Irrelevant to hcp_ICAFix, but harmless to include in its batch.txt file.

	BoldList=`opts_GetOpt "--boldlist" $@`
 	MsmAllBolds=`echo "${BoldList}" | sed -e "s/|/,/g" -e "s/,tf[^,]*//g"`  # exclude runs starting with 'tf'
	StudyFolderRepl=`printf ${StudyFolder} | sed -e 's/[\/&]/\\\\&/g'`

	## The template file needs modifications before it's appropriate.
	cat /opt/xnat_pbs_jobs_control/batch.txt.tmpl | \
		sed -e "s/@@@Subject@@@/${Subject}/g" -e "s/@@@SubjectPart@@@/${SubjectPart}/g" -e "s/@@@StudyFolder@@@/${StudyFolderRepl}/g" -e "s/@@@MsmAllBolds@@@/${MsmAllBolds}/g" |\
        grep -v "^[0-9][0-9]*:" > $BatchFile
	## Add the lines in the template that are in BoldList into the batch file.
 	## Note that the order of runs in BoldList does NOT alter their order in batch.txt.
        cat /opt/xnat_pbs_jobs_control/batch.txt.tmpl | grep "^[0-9][0-9]*:" | egrep "filename\((${BoldList})\)" >> $BatchFile
}

main() {

#########################	createStudy
${QUNEXCOMMAND} createStudy --studyfolder="${StudyFolder}"
cd ${SubjectsFolder}
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
	    --sessions="${Subject}" \
		--hcp_filename="original"

	#########################	createBatch
	${QUNEXCOMMAND} createBatch \
	 --sessionsfolder="${StudyFolder}/sessions" \
	 --overwrite="append" \
	 --paramfile="${StudyFolder}/sessions/specs/batch_parameters.txt"

#{% endblock qunex_setup %}



sleep 5
mkdir ${StudyFolder}/ProcessingInfo

if [ ! -z "${Scan}" ]; then
	subject_name="${Subject}_${Scan}"
else
	subject_name="${Subject}"
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
