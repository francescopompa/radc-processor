#!/bin/sh

#SBATCH --job-name=Preprocessing
#SBATCH --partition=tesla.long
#SBATCH --cpus-per-task=16
#SBATCH --output=/kalinka/storage/darkmatter/lngs-neutron-detector/%u/jobs/results_%j.out
#SBATCH --time=24:00:00 ##Runtime in D-HH:MM:SS

#PBS -N Preprocessing
#PBS -o /users/p/pompafra/jobs/results.out
#PBS -l walltime=24:00:00

# The image should first be installed with the script in the ALMOND singularity repository

singularity exec --bind /kalinka/:/kalinka/ /users/p/pompafra/software/ALMOND.simg preprocessData "$@"