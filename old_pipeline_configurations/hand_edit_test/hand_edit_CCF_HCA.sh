module load singularity-3.2.1

export XNAT_PBS_JOBS_CONTROL=${HOME}/processing/hand_edit_test/xnat_pbs_jobs_control_CCF_HCA
#export FS_EXTRA_RECONALL=`echo $2 | sed -e "s/\[//g"  -e "s/\]//g" -e "s/,/|/g"`
export FS_EXTRA_RECONALL="$2"

#singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2,\
#$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs:/pipeline_tools/xnat_pbs_jobs \
#/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT.sif \
#$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/StructuralPreprocessingHandEdit/StructuralPreprocessingHandEditControl intradb

singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build,/usr/local/torque-6.1.2,/export/HCP/qunex-hcp,/scratch/${USER}/hand_edit_buildspace,\
$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs:/pipeline_tools/xnat_pbs_jobs \
/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_4.sif \
$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/StructuralPreprocessingHandEdit/SubmitStructuralPreprocessingHandEditBatch intradb $1 

