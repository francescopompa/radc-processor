#!/bin/bash

#PBS -N Preprocessing
#PBS -o /nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
#PBS -e /nfs/scratch/$USER/jobs/results_$PBS_JOBID.err
#PBS -l walltime=24:00:00
#PBS -l mem=16000mb,ncpus=16
#PBS -q gs-custom

# it must be run as the following:
# qsub -F "-f -r ALMOND/sensitivity_GATOR" preprocessData.sh

# The image should first be installed with the script in the ALMOND singularity repository

singularity exec --bind /nfs/ /nfs/almond/ALMOND_ULITE.simg preprocessData "$@" 