#!/bin/bash
module load singularity-3.5.2

singularity run \
        --bind=./:/pipeline_tools/pipelines/ \
        /export/HCP/qunex-hcp/production_containers/pipelines.sif \
        --verbose  $@  > latest.out

