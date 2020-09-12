module load singularity-3.2.1

export XNAT_PBS_JOBS_CONTROL=${HOME}/processing/icafix_Q2_2020_runs/xnat_pbs_jobs_control_CCF_HCA

#singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2,/export/HCP/qunex-hcp \
#/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT.sif \
#/pipeline_tools/xnat_pbs_jobs/MultiRunIcaFixProcessing/SubmitMultiRunIcaFixProcessingBatch intradb

#singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2,/export/HCP/qunex-hcp,\
#$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs:/pipeline_tools/xnat_pbs_jobs \
#/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT.sif \
#$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/MultiRunIcaFixProcessing/SubmitMultiRunIcaFixProcessingBatch intradb $1

#singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2,/export/HCP/qunex-hcp \
#/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_3.sif \
#/pipeline_tools/xnat_pbs_jobs/MultiRunIcaFixProcessing/SubmitMultiRunIcaFixProcessingBatch intradb

#singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2,/export/HCP/qunex-hcp,\
#$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/lib/ccf/multirunicafix_processing/one_subject_job_submitter.py:\
#/pipeline_tools/xnat_pbs_jobs/lib/ccf/multirunicafix_processing/one_subject_job_submitter.py \
#/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_4.sif \
#$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/MultiRunIcaFixProcessing/SubmitMultiRunIcaFixProcessingBatch intradb $1

singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2,/export/HCP/qunex-hcp \
/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_5.sif \
$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/MultiRunIcaFixProcessing/SubmitMultiRunIcaFixProcessingBatch intradb $1
