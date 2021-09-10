#!/bin/bash

/ceph/scratch/intradb/build/aux/virtualenv/bin/prunner --verbose  \
        $@  2>&1 | tee ~/pipeline_runner_logs/log.$1.$2.txt
