module load singularity-3.2.1

export XNAT_PBS_JOBS_CONTROL=${HOME}/processing/ls_struc_preproc/xnat_pbs_jobs_control_CCF_HCD

#singularity exec -B /NRG-data/NRG/intradb/archive,/NRG-data/NRG/intradb/build_ssd,/usr/local/torque-6.1.2 \
#/NRG-data/NRG/intradb/build_ssd/chpc/BUILD/junilc/production_container/HCA_HCD/HCPpipelines_XNAT.sif \
#/pipeline_tools/xnat_pbs_jobs/StructuralPreprocessing/SubmitStructuralPreprocessingBatch intradb

#    -B ${HOME}/pipeline_tools/xnat_pbs_jobs:/pipeline_tools/xnat_pbs_jobs \
singularity exec \
    -B /NRG-data/NRG/intradb/archive \
    -B /NRG-data/NRG/intradb/build \
    -B /usr/local/torque-6.1.2 \
    -B /export/HCP/qunex-hcp \
    -B /scratch/${USER}/scratch_buildspace \
/export/HCP/qunex-hcp/production_containers/Process/HCPpipelines_XNAT_1_0_5.sif \
/pipeline_tools/xnat_pbs_jobs/StructuralPreprocessing/SubmitStructuralPreprocessingBatch intradb $1

