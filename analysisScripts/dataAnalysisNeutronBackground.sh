#! /bin/bash

#PBS -N reduceDataNeutronBackground
#PBS -o /nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
#PBS -e /nfs/scratch/$USER/jobs/results_$PBS_JOBID.err
#PBS -l walltime=24:00:00
#PBS -l mem=16000mb
#PBS -q gs-custom

# it must be run as the following:
# qsub -F "-d neutronBackground_GATOR" dataAnalysisNeutronBackground.sh
# it depends on ROOT therefore you must run it in the container
# if you change something, you have to rebuild the container with the script in the ALMOND singularity repository
# otherwise, just use the location of the script in your local repository

exec 1>/nfs/scratch/$USER/jobs/results_$PBS_JOBID.out
exec 2>/nfs/scratch/$USER/jobs/results_$PBS_JOBID.err

singularity exec --bind /nfs/ /nfs/almond/ALMOND_ULITE.simg reduceDataNeutronBackground_v2 "$@"
# singularity exec --bind /nfs/ /nfs/almond/ALMOND_ULITE.simg reduceDataWithClusters "$@"
# singularity exec --bind /nfs/ /nfs/almond/ALMOND_ULITE.simg python -u /users/p/$USER/software/radc-processor/analysisScripts/reduceDataNeutronBackground.py "$@"




