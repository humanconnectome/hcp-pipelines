module load singularity-3.2.1

export XNAT_PBS_JOBS_CONTROL=${HOME}/processing/pipeline_tools_production_n_func/xnat_pbs_jobs_control_CCF_HCA

singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2 \
/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT.sif \
/pipeline_tools/xnat_pbs_jobs/FunctionalPreprocessing/FunctionalPreprocessingControl intradb

