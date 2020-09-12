# HCP Pipelines
This repo contains the configuration files for running the HCP pipelines on the
HPC cluster.

## Usage
To run the pipelines in production, the only requirement is prunner:
```
(env) $ pip install prunner
```


## Executing a pipeline
```sh
(env) $ prun PIPELINE_NAME project:subject_id:classifier:extra server

# example:
(env) $ prun structural CCF_HCA_STG:HCA0123456789:V1_MR:all hcpi-shadow11
```

## Setting up environment for Development
```sh
$ python3 -m venv env
$ source env/bin/activate
(env) $ pip install -r requirements.txt
```
