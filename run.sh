#!/bin/bash
module load singularity-3.5.2

# The first bind statement should be removed in production.
# It overrides the container builtin pipelines folder for the current
# development hcp-pipelines folder.
singularity run \
        --bind ./:/pipeline_tools/pipelines/ \
        --bind /NRG-data/NRG/intradb/archive \
        --bind /export/HCP/qunex-hcp/production_containers \
        --bind /act/ \
        --bind /NRG-data/NRG/intradb/build \
        --bind /NRG-data/NRG/intradb/build_ssd \
        --bind /usr/local/torque-6.1.2 \
        --bind /scratch/$USER \
        /export/HCP/qunex-hcp/production_containers/hcp-pipelines-runner.sif \
        --verbose  $@  2>&1 | tee ~/pipeline_runner_logs/log.$1.$2.txt
