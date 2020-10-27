#!/bin/sh
module load singularity-3.5.2

# The first bind statement should be removed in production.
# It overrides the container builtin pipelines folder for the current
# development hcp-pipelines folder.
singularity run \
        --bind ./:/pipeline_tools/pipelines/ \
        --bind /NRG-data/NRG/intradb/archive \
        --bind /act/ \
        --bind /NRG-data/NRG/intradb/build \
        --bind /usr/local/torque-6.1.2 \
        --bind /export/HCP/qunex-hcp \
        --bind /scratch/$USER \
        /export/HCP/qunex-hcp/production_containers/pipelines.sif \
        --verbose  $@  > "run.$1.$2.txt"
