module load singularity-3.2.1

export XNAT_PBS_JOBS_CONTROL=${HOME}/processing/diffusion_Q3_2020_runs/xnat_pbs_jobs_control_CCF_HCA

#singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2,/export/HCP/qunex-hcp,\
#$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs:/pipeline_tools/xnat_pbs_jobs \
#/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_3.sif \
#$HOME/pipeline_tools/HCPpipelinesXnatPbsJobs/MsmAllProcessing/SubmitMsmAllProcessingBatch intradb $1

singularity exec \
    -B /NRG-data/NRG/intradb/archive \
    -B /NRG-data/NRG/intradb/build_ssd \
    -B /usr/local/torque-6.1.2 \
    -B /export/HCP/qunex-hcp \
    -B $HOME/pipeline_tools/HCPpipelinesXnatPbsJobs:/pipeline_tools/xnat_pbs_jobs \
/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_4.sif \
/pipeline_tools/xnat_pbs_jobs/DiffusionPreprocessing/SubmitDiffusionPreprocessingBatch intradb $1
