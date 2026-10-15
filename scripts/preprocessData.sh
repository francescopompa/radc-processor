#!/bin/bash

#PBS -N Preprocessing
#PBS -o /nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
#PBS -e /nfs/scratch/$USER/jobs/results_$PBS_JOBID.err
#PBS -l walltime=24:00:00
#PBS -l mem=16000mb,ncpus=16
#PBS -q gs-custom

# it must be run as the following:
# qsub -F "-f -r ALMOND/sensitivity_GATOR" preprocessData.sh

__conda_setup="$('/nfs/almond/$USER/miniconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/nfs/almond/$USER/miniconda3/etc/profile.d/conda.sh" ]; then
        . "/nfs/almond/$USER/miniconda3/etc/profile.d/conda.sh"
    else
        export PATH="/nfs/almond/$USER/miniconda3/bin:$PATH"
    fi
fi
unset __conda_setup

eval "$(conda shell.bash hook)"
conda activate ALMOND
preprocessData "$@"