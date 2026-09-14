#!/bin/bash

#PBS -N Preprocessing
#PBS -o /nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
#PBS -l walltime=24:00:00
#PBS -l select=1:ncpus=4:mem=16gb

# it must be run as the following:
# qsub -F "-f -r ALMOND/sensitivity_GATOR" preprocessData.sh

exec 1>/nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
exec 2>/nfs/scratch/$USER/jobs/results_$PBS_JOBID.err


# The image should first be installed with the script in the ALMOND singularity repository

singularity exec --bind /nfs/:/nfs/ /nfs/almond/ALMOND_ULITE.simg preprocessData "$@" 