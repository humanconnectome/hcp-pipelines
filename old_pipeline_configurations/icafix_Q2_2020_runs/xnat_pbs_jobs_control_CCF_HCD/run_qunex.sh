#!/bin/bash

opts_GetOpt() {
sopt="$1"
shift 1
for fn in "$@" ; do
    if [ `echo $fn | grep -- "^${sopt}=" | wc -w` -gt 0 ]; then
        echo $fn | sed "s/^${sopt}=//"
        return 0
    fi
done
}

# ------------------------------------------------------------------------------
# -- Setup variables
# ------------------------------------------------------------------------------

unset StudyFolder
#unset InputDataLocation
unset ParametersFile

echo "" 
echo " -- Reading inputs... "
echo ""

# -- Define script name
scriptName=$(basename ${0})
#scriptPath=$(dirname ${0})

# =-=-=-=-=-= GENERAL OPTIONS =-=-=-=-=-=
#
# -- key variables to set
ParameterFolder=`opts_GetOpt "--parameterfolder" $@`
StudyFolder=`opts_GetOpt "--studyfolder" $@`
Subject=`opts_GetOpt "--subjects" "$@"`
SubjectPart=`echo "$Subject" | sed -e "s/_.*$//"`
Overwrite=`opts_GetOpt "--overwrite" $@`
HCPpipelineProcess=`opts_GetOpt "--hcppipelineprocess" $@`
Scan=`opts_GetOpt "--scan" $@`

export StudyFolder Subject SubjectPart

TimeStamp=`date +%Y-%m-%d-%H-%M-%S`
mkdir -p $StudyFolder/processing/logs &> /dev/null
LogFile="$StudyFolder/processing/logs/${scriptName}_${TimeStamp}.log"

# only if overriding the default setting of /opt/HCP/HCPpipelines
#export con_HCPPIPEDIR="/opt/HCP/HCPpipelines"
source /opt/qunex/library/environment/qunex_environment.sh  >> ${LogFile}
source /opt/qunex/library/environment/qunex_envStatus.sh --envstatus >> ${LogFile}

cores=1      # the number of subjects to process in parallel
threads=1    # the number of bold files to process in parallel

# -- Derivative variables
SubjectsFolder="${StudyFolder}/subjects"
BatchFile="${StudyFolder}/processing/batch.txt"

# -- Report options
echo "-- ${scriptName}: Specified Command-Line Options - Start --"                2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   QUNEX Study          : $StudyFolder"                                     2>&1 | tee -a ${LogFile}
#echo "   Input data location  : $InputDataLocation"                               2>&1 | tee -a ${LogFile}
echo "   Cores to use         : $cores"                                           2>&1 | tee -a ${LogFile}
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

main() {

#########################	createStudy
${QUNEXCOMMAND} createStudy --studyfolder="${StudyFolder}"
cd ${SubjectsFolder}

if [ "${HCPpipelineProcess}" == "MultiRunIcaFixProcessing" ]; then


	BoldList=`opts_GetOpt "--boldlist" $@`
	## Using a template file here instead of a generated file.  The generated file needs modifications before it's useful.
	StudyFolderRepl=`printf ${StudyFolder} | sed -e 's/[\/&]/\\\\&/g'`
	## Remove runs from batch template that aren’t part of BoldList, preserving the order in the template
	cat /opt/xnat_pbs_jobs_control/batch.txt.tmpl | sed -e "s/@@@Subject@@@/${Subject}/g" -e "s/@@@SubjectPart@@@/${SubjectPart}/g" -e "s/@@@StudyFolder@@@/${StudyFolderRepl}/g" |\
		 grep -v "^[0-9][0-9]*:" > $BatchFile
	cat /opt/xnat_pbs_jobs_control/batch.txt.tmpl | grep "^[0-9][0-9]*:" | egrep "filename\((${BoldList})\)" >> $BatchFile

else

	## Copy in ParameterFiles and SpecFiles (NOTE:  Not necessary for MR-FIX)
	if [ ! -z "$ParameterFolder" ]; then
		cp ${ParameterFolder}/* "${StudyFolder}/subjects/specs"
	fi
	
	${QUNEXCOMMAND} HCPLSImport \
		--subjectsfolder="${StudyFolder}/subjects"  \
		--inbox="${StudyFolder}/unprocessed" \
		--action="link" \
		--overwrite="${Overwrite}" \
		--archive="leave"
	
	#########################	setupHCP
	${QUNEXCOMMAND} setupHCP \
	    --subjectsfolder="${StudyFolder}/subjects" \
	    --sessions="${Subject}" \
		--filename="original"
	 
	#########################	createBatch
	${QUNEXCOMMAND} createBatch \
	 --subjectsfolder="${StudyFolder}/subjects" \
	 --overwrite="append"

fi

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

if [ "${HCPpipelineProcess}" == "StructuralPreprocessing" ]; then

	######################### hcp1
	${QUNEXCOMMAND} hcp1 \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--cores="${cores}" 
				
	######################### hcp2
	${QUNEXCOMMAND} hcp2 \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--cores="${cores}" 

	######################### hcp3
	${QUNEXCOMMAND} hcp3 \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--cores="${cores}" 
		
elif [ "${HCPpipelineProcess}" == "FunctionalPreprocessing" ]; then
	mv ${StudyFolder}/T*w "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	mv ${StudyFolder}/MNINonLinear "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 

	######################### hcp4
	${QUNEXCOMMAND} hcp4 \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--cores="${cores}" 
		
	######################### hcp5
	${QUNEXCOMMAND} hcp5 \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--cores="${cores}" 
		
elif [ "${HCPpipelineProcess}" == "MultiRunIcaFixProcessing" ]; then
	mkdir -p "${StudyFolder}/subjects/${Subject}/hcp/${Subject}" 
	mv ${StudyFolder}/T*w "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	mv ${StudyFolder}/MNINonLinear "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	#mv ${StudyFolder}/*fMRI_* "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 

	#IcaFixBolds=`opts_GetOpt "--icafixbolds" $@`
	#ReapplyFixBolds=`opts_GetOpt "--reapplyfixbolds" $@`

	######################### hcp_ICAFix
	${QUNEXCOMMAND} hcp_ICAFix \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--hcp_matlab_mode="compiled" \
		--cores="${cores}" 
		## NOTE:  We've included only scans that exist int the batch.txt file, and they're in the preferred order
		#--hcp_icafix_bolds="${IcaFixBolds}" \
		
	## No ReapplyFix
	########################## hcp_ReApplyFix
	#${QUNEXCOMMAND} hcp_ReApplyFix \
	#	--sessions="${StudyFolder}/processing/batch.txt" \
	#	--subjectsfolder="${StudyFolder}/subjects" \
	#	--overwrite="${Overwrite}" \
	#	--hcp_icafix_bolds="${ReapplyFixBolds}" \
	#	--hcp_matlab_mode="compiled" \
	#	--cores="${cores}" \
	#	--nprocess="0"

elif [ "${HCPpipelineProcess}" == "DiffusionPreprocessing" ]; then
	mv ${StudyFolder}/T*w "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	mv ${StudyFolder}/MNINonLinear "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	
	######################### hcpd
	${QUNEXCOMMAND} hcpd \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--cores="${cores}" 
		
fi

${QUNEXCOMMAND} mapIO \
    --subjectsfolder="${StudyFolder}/subjects" \
    --sessions="${StudyFolder}/processing/batch.txt" \
    --maptype="toHCPLS" \
    --mapaction="link" \
    --mapto="${StudyFolder}" \
    --overwrite="yes" \
    --verbose="no" 

}

main $@
