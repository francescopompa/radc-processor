#!/bin/bash

#SBATCH --job-name=preprocessing
#SBATCH --partition=tesla.long
#SBATCH --cpus-per-task=4
#SBATCH --time=7-00:00:00
#SBATCH --output=/kalinka/storage/darkmatter/lngs-neutron-detector/%u/jobs/results_%j.out

#PBS -N Preprocessing
#PBS -o /users/p/pompafra/ALMOND/jobs/results.out
#PBS -l walltime=24:00:00

# it must be run as the following:
# qsub -F "-f -r ALMOND/sensitivity_GATOR" preprocessData.sh

# Go to the directory where you submitted the job
cd $PBS_O_WORKDIR

eval "$(conda shell.bash hook)"
conda activate ALMOND

preprocessData "$@"