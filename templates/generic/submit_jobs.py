#!/usr/bin/env python3
import argparse
import subprocess


def shell(cmd, dry_run=False):
    """
    Execute a shell command. Print the command and return the output.
    """
    print(">> ", ' '.join(cmd))
    if dry_run:
        output = '<dry-run: this command was not actually executed.>'
    else:
        output = subprocess.check_output(cmd).decode('utf-8').strip()
    print(f"Output: {output}")
    return output


def slurm_chain(script, prior_job=None, dependency='afterok', dry_run=False):
    """
    Submit a script to the slurm cluster. If a `prior_job` is specified, then submit this script as a dependency of
    the prior job. That way this script will only run if the prior job completes successfully.
    """
    cmd = ['sbatch']

    # if specified, add the dependency to the command
    if prior_job:
        cmd.append(f'--dependency={dependency}:{prior_job}')

    cmd.append(script)
    # run command
    output = shell(cmd, dry_run)

    if dry_run:
        job_id = '<job_id>'
    else:
        # output equals ~ 'Submitted batch job <job_id>', so parse out the job_id
        job_id = output.split(' ')[-1]

    return job_id


def main(start_index, end_index, do_marker=True, dry_run=False, prior_job=None):
    """
    Set up the slurm job chain.
    """
    if do_marker:
        print('Creating "Running Status Marker" file to indicate that jobs are queued.')
        shell([scripts['marker'], '--status=queued'])

    for step in choices[start_index:end_index + 1]:
        prior_job = slurm_chain(scripts[step], prior_job, 'afterok', dry_run)

    if do_marker:
        print('Adding slurm job to remove "Running Status Marker" file to indicate that jobs are no longer queued.')
        prior_job = slurm_chain(scripts['marker'], prior_job, 'afterany', dry_run)

    return prior_job


breakpoint = "{{ BREAKPOINT }}"
choices = ['get', 'process', 'clean', 'put', 'check']
scripts = dict(
    get="{{ GET_DATA_JOB_SCRIPT_NAME }}",
    process="{{ PROCESS_DATA_JOB_SCRIPT_NAME }}",
    clean="{{ CLEAN_DATA_SCRIPT_NAME }}",
    put="{{ PUT_DATA_SCRIPT_NAME }}",
    check="{{ CHECK_DATA_JOB_SCRIPT_NAME }}",
    marker="{{ MARK_NO_LONGER_RUNNING_SCRIPT_NAME }}",
)

parser = argparse.ArgumentParser(description='Submit jobs to the cluster.')
parser.add_argument('--start', '-s', choices=choices, default='get', help='Start from this step.')
parser.add_argument('--end', '-e', choices=choices, default='check', help='Stop after this step.')
parser.add_argument('--dry-run', '-n', action='store_true',
                    help='Do not submit jobs, just print commands that would run.')
parser.add_argument('--all', '-a', action='store_true', help='Run all steps, ignoring the `BREAKPOINT`.')
parser.add_argument('--normal-start', '-b', action='store_true', help='Go from `start` til `BREAKPOINT`.')
parser.add_argument('--resume', '-r', action='store_true', help='Continue from step after the `BREAKPOINT` til end.')
parser.add_argument('--skip-marker', action='store_true', help='Do not add, then remove, a status marker on IntraDB.')

if __name__ == "__main__":
    args = parser.parse_args()

    start_index = choices.index(args.start)
    end_index = choices.index(args.end)
    if start_index > end_index:
        raise ValueError("Start step must be before end step.")

    if args.all:
        start_index = 0
        end_index = len(choices) - 1
    elif args.resume:
        start_index = choices.index(breakpoint) + 1
    elif args.normal_start:
        end_index = choices.index(breakpoint)

    job_id = main(
        start_index=start_index,
        end_index=end_index,
        do_marker=not args.skip_marker,
        dry_run=args.dry_run,
        prior_job=None,
    )
    print(f"Last job id: \n{job_id}")
