#!/bin/bash

#PBS -N Preprocessing
#PBS -o localhost:/nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
#PBS -e localhost:/nfs/scratch/$USER/jobs/results_$PBS_JOBID.err
#PBS -l walltime=24:00:00
#PBS -l mem=32000mb,ncpus=16
#PBS -q gs-custom

# it must be run as the following:
# qsub -F "-f -r ALMOND/sensitivity_GATOR" preprocessData.sh

exec 1>/nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
exec 2>/nfs/scratch/$USER/jobs/results_$PBS_JOBID.err

# The image should first be installed with the script in the ALMOND singularity repository

singularity exec --bind /nfs/ /nfs/almond/ALMOND_ULITE.simg preprocessData "$@" 