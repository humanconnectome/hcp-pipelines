module load singularity-3.2.1

export XNAT_PBS_JOBS_CONTROL=${HOME}/processing/bwh_struc_preproc/xnat_pbs_jobs_control_CCF_BWH

#singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2 \
#/NRG-data/NRG/intradb/build_ssd/chpc/BUILD/junilc/production_container/HCA_HCD/HCPpipelines_XNAT.sif \
#/pipeline_tools/xnat_pbs_jobs/StructuralPreprocessing/SubmitStructuralPreprocessingBatch intradb

singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2,/export/HCP/qunex-hcp,\
$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/StructuralPreprocessing/SubmitStructuralPreprocessingBatch:\
/pipeline_tools/xnat_pbs_jobs/StructuralPreprocessing/SubmitStructuralPreprocessingBatch,\
$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/lib/ccf/structural_preprocessing/SubmitStructuralPreprocessingBatch.py:\
/pipeline_tools/xnat_pbs_jobs/lib/ccf/structural_preprocessing/SubmitStructuralPreprocessingBatch.py \
/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_3.sif \
$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/StructuralPreprocessing/SubmitStructuralPreprocessingBatch intradb $1

