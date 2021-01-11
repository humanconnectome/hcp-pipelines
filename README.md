# HCP Pipelines
This repo contains the configuration files for running the HCP pipelines on the
HPC cluster.

## Usage
Two positional arguments are expected:
1. **Pipeline Name** - possible values include:
    * DiffusionPreprocessing
    * FunctionalPreprocessing
    * MsmAllProcessing
    * MultiRunIcaFixProcessing
    * StructuralPreprocessing
    * StructuralPreprocessingHandEdit

2. **Subject string** - a colon-delimited (:) string consisting of four components:
```
project:subject_id:classifier:extra
```

### Using singularity container on WashU HPC
If using the container specified in [hcp-pipelines-singularity](https://github.com/mobalt/hcp-pipelines-singularity),
placed in location `/export/HCP/qunex-hcp/production_containers/hcp-pipelines-runner.sif`.
Then just clone the repo on your HPC home directory and run the
[run.sh](https://github.com/mobalt/hcp-pipelines/blob/master/run.sh) script as is, for example:
```
$ ./run.sh StructuralPreprocessing CCF_HCA_STG:HCA0123456789:V1_MR:all
```

### Using Native Python
After cloning this repo, the only requirement is prunner:
```
(env) $ pip install prunner
```
Then run like so:
```
(env) $ prunner StructuralPreprocessing CCF_HCA_STG:HCA0123456789:V1_MR:all
```


### Setting up environment for Development
```sh
$ python3 -m venv env
$ source env/bin/activate
(env) $ pip install -r requirements.txt
```
