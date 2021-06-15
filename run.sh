#!/bin/bash

/export/HCP/qunex-hcp/production_containers/miniconda3/bin/prunner --verbose  \
        $@  2>&1 | tee ~/pipeline_runner_logs/log.$1.$2.txt
