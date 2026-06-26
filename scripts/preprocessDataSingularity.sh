#!/bin/sh
#SBATCH --job-name=Preprocessing
#SBATCH --partition=tesla.long
#SBATCH --cpus-per-task=16
#SBATCH --output=/kalinka/storage/darkmatter/lngs-neutron-detector/%u/jobs/results_%j.out
#SBATCH --time=24:00:00 ##Runtime in D-HH:MM:SS

# The image should first be installed with the script in the ALMOND singularity repository

singularity exec --bind /kalinka/:/kalinka/ /home/ws/zm6876/DAQMeasurements/almond-singularity/ALMOND_new.simg preprocessData "$@"