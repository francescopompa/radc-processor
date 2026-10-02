#! /bin/bash

#PBS -N reduceDataNeutronBackground
#PBS -o /nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
#PBS -l walltime=24:00:00
#PBS -l select=1:ncpus=1:mem=32gb

# it must be run as the following:
# qsub -F "-d neutronBackground_GATOR" dataAnalysisNeutronBackground.sh
# it depends on ROOT therefore you must run it in the container
# if you change something, you have to rebuild the container with the script in the ALMOND singularity repository

exec 1>/nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
exec 2>/nfs/scratch/$USER/jobs/results_$PBS_JOBID.err

singularity exec --bind /nfs/ /nfs/almond/ALMOND_ULITE.simg -u reduceDataNeutronBackground "$@"




