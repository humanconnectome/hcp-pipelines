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

# -- Clear variables
unset StudyFolder
unset InputDataLocation
unset ParametersFile

echo "" 
echo " -- Reading inputs... "
echo ""

# -- Define script name
scriptName=$(basename ${0})

# =-=-=-=-=-= GENERAL OPTIONS =-=-=-=-=-=
#
# -- key variables to set
StudyFolder=`opts_GetOpt "--studyfolder" $@`
Subject=`opts_GetOpt "--subjects" "$@"`
Overwrite=`opts_GetOpt "--overwrite" $@`

TimeStamp=`date +%Y-%m-%d-%H-%M-%S`
mkdir -p $StudyFolder/processing/logs &> /dev/null
LogFile="$StudyFolder/processing/logs/${scriptName}_${TimeStamp}.log"

export con_HCPPIPEDIR="/opt/HCP/HCPpipelines"
source /opt/qunex/library/environment/qunex_environment.sh  >> ${LogFile}

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
echo "----------------- Start of ${scriptName} -----------------------"           2>&1 | tee -a ${LogFile}
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

mkdir ${StudyFolder}/ProcessingInfo
start_time_file="${StudyFolder}/ProcessingInfo/${Subject}.StructuralPreprocessing.starttime"
g_script_name=$(basename "${0}" .sh)
filename="${StudyFolder}/ProcessingInfo/${Subject}.StructuralPreprocessing.${g_script_name}.execinfo"
echo $(date) > ${start_time_file}
log_Msg "PBS_JOBID: ${PBS_JOBID}" > ${filename}
log_Msg "PBS execution node: $(hostname)" >> ${filename}


###############	createStudy
${QUNEXCOMMAND} createStudy --studyfolder="${StudyFolder}"
cd ${SubjectsFolder}
cp $HOME/processing/bwh_struc_preproc/xnat_pbs_jobs_control_CCF_BWH/SpecFiles_v3/* "${StudyFolder}/subjects/specs"

################	HCPLSImport
${QUNEXCOMMAND} HCPLSImport \
	--subjectsfolder="${StudyFolder}/subjects"  \
	--inbox="${StudyFolder}/unprocessed" \
	--action="link" \
	--overwrite="${Overwrite}" \
	--archive="leave"

####################	setupHCP
${QUNEXCOMMAND} setupHCP \
    --subjectsfolder="${StudyFolder}/subjects" \
    --sessions="${Subject}" \
	--boldnamekey="name"
 
####################	createBatch
${QUNEXCOMMAND} createBatch \
 --subjectsfolder="${StudyFolder}/subjects" \
 --overwrite="append"
 
######################### hcp1
${QUNEXCOMMAND} hcp1 \
	--sessions="${StudyFolder}/processing/batch.txt" \
    --subjectsfolder="${StudyFolder}/subjects" \
    --overwrite="${Overwrite}" \
    --cores="${cores}" \
	--nprocess="0"
				
######################### hcp2
${QUNEXCOMMAND} hcp2 \
	--sessions="${StudyFolder}/processing/batch.txt" \
	--subjectsfolder="${StudyFolder}/subjects" \
	--overwrite="${Overwrite}" \
	--cores="${cores}" \
	--nprocess="0"

########################### hcp3
${QUNEXCOMMAND} hcp3 \
	--sessions="${StudyFolder}/processing/batch.txt" \
	--subjectsfolder="${StudyFolder}/subjects" \
	--overwrite="${Overwrite}" \
	--cores="${cores}" \
	--nprocess="0"

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

echo ""                                                                       2>&1 | tee -a ${LogFile}
echo "   Check log file for final outputs --> $LogFile"                       2>&1 | tee -a ${LogFile}
echo ""                                                                       2>&1 | tee -a ${LogFile}
echo "----------------- End of ${scriptName} -----------------------"         2>&1 | tee -a ${LogFile}
