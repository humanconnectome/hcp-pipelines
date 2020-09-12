#!/bin/bash

module load singularity-3.2.1

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

# -- Clear variables
unset StudyFolder
unset InputDataLocation
unset ParametersFile

echo "" 
echo " -- Reading inputs... "
echo ""

# -- Define script name and script path
scriptName=$(basename ${0})
scriptPath=$(dirname ${0})

# =-=-=-=-=-= GENERAL OPTIONS =-=-=-=-=-=
#
# -- key variables to set
ContainerPath=`opts_GetOpt "--containerpath" $@`
ParameterFolder=`opts_GetOpt "--parameterfolder" $@`
StudyFolder=`opts_GetOpt "--studyfolder" $@`
Subject=`opts_GetOpt "--subjects" "$@"`
SubjectPart=`echo "$Subject" | sed -e "s/_.*$//"`
Overwrite=`opts_GetOpt "--overwrite" $@`
HCPpipelineProcess=`opts_GetOpt "--hcppipelineprocess" $@`
Scan=`opts_GetOpt "--scan" $@`
ContainerDir=$(dirname $ContainerPath)

PATH=$PATH:${ContainerDir}

export PATH StudyFolder Subject SubjectPart

TimeStamp=`date +%Y-%m-%d-%H-%M-%S`
mkdir -p $StudyFolder/processing/logs &> /dev/null
LogFile="$StudyFolder/processing/logs/${scriptName}_${TimeStamp}.log"

export con_HCPPIPEDIR="/opt/HCP/HCPpipelines"
#source /opt/qunex/library/environment/qunex_environment.sh  >> ${LogFile}
#source /opt/qunex/library/environment/qunex_envStatus.sh --envstatus >> ${LogFile}

cores=1      # the number of subjects to process in parallel
threads=1    # the number of bold files to process in parallel

# -- Derivative variables
SubjectsFolder="${StudyFolder}/subjects"
BatchFile="${StudyFolder}/processing/batch.txt"
BashPost="source /opt/qunex/library/environment/qunex_environment.sh; source /opt/qunex/library/environment/qunex_envStatus.sh --envstatus"

# -- Report options
echo "-- ${scriptName}: Specified Command-Line Options - Start --"                2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}
echo "   QUNEX Study          : $StudyFolder"                                     2>&1 | tee -a ${LogFile}
echo "   Input data location  : $InputDataLocation"                               2>&1 | tee -a ${LogFile}
echo "   Cores to use         : $cores"                                           2>&1 | tee -a ${LogFile}
echo "   Threads to use       : $threads"                                         2>&1 | tee -a ${LogFile}
echo "   QUNEX subjects folder: $SubjectsFolder"                                  2>&1 | tee -a ${LogFile}
echo "   QUNEX batch file     : $BatchFile"                                       2>&1 | tee -a ${LogFile}
echo "   Overwrite HCP step   : $Overwrite"                                       2>&1 | tee -a ${LogFile}
echo "   Subjects to run      : $Subject"                                         2>&1 | tee -a ${LogFile}
echo "   Log file output      : $LogFile"                                         2>&1 | tee -a ${LogFile}
echo ""                                                                           2>&1 | tee -a ${LogFile}
echo "-- ${scriptName}: Specified Command-Line Options - End --"                  2>&1 | tee -a ${LogFile}
echo ""                                                                           2>&1 | tee -a ${LogFile}
echo "   "                                                                        2>&1 | tee -a ${LogFile}

# -- Define QUNEX command
QUNEXCOMMAND="qunexContainer"

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

if [ "${HCPpipelineProcess}" == "MultiRunIcaFixProcessing" ]; then


	BoldList=`opts_GetOpt "--boldlist" $@`
	## Using a template file here instead of a generated file.  The generated file needs modifications before it's useful.
	StudyFolderRepl=`printf ${StudyFolder} | sed -e 's/[\/&]/\\\\&/g'`
	echo "GENERATING BATCH.TXT FILE FROM TEMPLATE"
	cat $scriptPath/batch.txt.tmpl | \
		sed -e "s/@@@Subject@@@/${Subject}/g" -e "s/@@@SubjectPart@@@/${SubjectPart}/g" -e "s/@@@StudyFolder@@@/${StudyFolderRepl}/g" | \
		tee >(grep -v "^[0-9][0-9]*:") >(sleep 1;egrep "filename\((${BoldList})\)") > $BatchFile
	echo "DONE"

else

	#########################	createStudy
	${QUNEXCOMMAND} createStudy --studyfolder="${StudyFolder}"
	cd ${SubjectsFolder}
	if [ ! -z "$ParameterFolder" ]; then
		cp ${ParameterFolder}/* "${StudyFolder}/subjects/specs"
	fi
	
	${QUNEXCOMMAND} HCPLSImport \
		--subjectsfolder="${StudyFolder}/subjects"  \
		--inbox="${StudyFolder}/unprocessed" \
		--action="link" \
		--container="${ContainerPath}" \
		--overwrite="${Overwrite}" \
		--archive="leave"
	
	#########################	setupHCP
	${QUNEXCOMMAND} setupHCP \
	    --subjectsfolder="${StudyFolder}/subjects" \
	    --container="${ContainerPath}" \
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
		--container="${ContainerPath}" \
		--cores="${cores}" \
		--nprocess="0"
				
	######################### hcp2
	${QUNEXCOMMAND} hcp2 \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--container="${ContainerPath}" \
		--cores="${cores}" \
		--nprocess="0"

	######################### hcp3
	${QUNEXCOMMAND} hcp3 \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--container="${ContainerPath}" \
		--cores="${cores}" \
		--nprocess="0"
		
elif [ "${HCPpipelineProcess}" == "FunctionalPreprocessing" ]; then
	mv ${StudyFolder}/T*w "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	mv ${StudyFolder}/MNINonLinear "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 

	######################### hcp4
	${QUNEXCOMMAND} hcp4 \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--container="${ContainerPath}" \
		--cores="${cores}" \
		--nprocess="0"
		
	######################### hcp5
	${QUNEXCOMMAND} hcp5 \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--container="${ContainerPath}" \
		--cores="${cores}" \
		--nprocess="0"
		
elif [ "${HCPpipelineProcess}" == "MultiRunIcaFixProcessing" ]; then
	echo "PREPARE FOLDERS FOR hcp_ICAFix PROCESSING"
	mkdir -p "${StudyFolder}/subjects/${Subject}/hcp/${Subject}" 
	mv ${StudyFolder}/T*w "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	mv ${StudyFolder}/MNINonLinear "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	which ${QUNEXCOMMAND}
	echo "BEGIN hcp_ICAFix PROCESSING"
	${QUNEXCOMMAND} hcp_ICAFippp \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--hcp_matlab_mode="compiled" \
		--container="${ContainerPath}" \
		--cores="${cores}" \
		--nprocess="0"
	#mv ${StudyFolder}/*fMRI_* "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	## QuNex fails on certain files that are symlinks
	#find ${StudyFolder}/subjects/${Subject}/hcp/${Subject} -name "*fMRI*_[AP][PA].nii.gz" | grep "Results" | xargs -I '{}' sh -c 'cp --remove-destination $(readlink {}) {}' 
	#find ${StudyFolder}/subjects/${Subject}/hcp/${Subject} | grep "MNINonLinear" | xargs -I '{}' sh -c 'cp --remove-destination $(readlink {}) {}' 

	#IcaFixBolds=`opts_GetOpt "--icafixbolds" $@`
	#ReapplyFixBolds=`opts_GetOpt "--reapplyfixbolds" $@`
	#--hcp_icafix_bolds="${IcaFixBolds}" \
	#--hcp_icafix_bolds="${ReapplyFixBolds}" \

	######################### hcp_ICAFix
	echo "BEGIN hcp_ICAFix PROCESSING"
	echo ${QUNEXCOMMAND} hcp_ICAFix \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--hcp_matlab_mode="compiled" \
		--container="${ContainerPath}" \
		--bash_post="${BashPost}" \
		--cores="${cores}" \
		--nprocess="0"
	${QUNEXCOMMAND} hcp_ICAFix \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--hcp_matlab_mode="compiled" \
		--container="${ContainerPath}" \
		--bash_post="${BashPost}" \
		--cores="${cores}" \
		--nprocess="0"
		
elif [ "${HCPpipelineProcess}" == "DiffusionPreprocessing" ]; then
	mv ${StudyFolder}/T*w "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	mv ${StudyFolder}/MNINonLinear "${StudyFolder}/subjects/${Subject}/hcp/${Subject}/" 
	
	######################### hcpd
	${QUNEXCOMMAND} hcpd \
		--sessions="${StudyFolder}/processing/batch.txt" \
		--subjectsfolder="${StudyFolder}/subjects" \
		--overwrite="${Overwrite}" \
		--container="${ContainerPath}" \
		--cores="${cores}" \
		--nprocess="0"
		
fi

echo "BEGIN hcp_mapIO PROCESSING"
${QUNEXCOMMAND} mapIO \
    --subjectsfolder="${StudyFolder}/subjects" \
    --sessions="${StudyFolder}/processing/batch.txt" \
    --maptype="toHCPLS" \
    --mapaction="link" \
    --mapto="${StudyFolder}" \
    --container="${ContainerPath}" \
    --overwrite="yes" \
    --verbose="no" 

}

main $@
