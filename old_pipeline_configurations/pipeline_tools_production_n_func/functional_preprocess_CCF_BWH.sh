module load singularity-3.2.1

export XNAT_PBS_JOBS_CONTROL=${HOME}/processing/pipeline_tools_production_n_func/xnat_pbs_jobs_control_CCF_BWH

singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2,\
$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs:/pipeline_tools/xnat_pbs_jobs \
/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_3.sif \
/pipeline_tools/xnat_pbs_jobs/FunctionalPreprocessing/SubmitFunctionalPreprocessingBatch intradb

