#! /bin/bash

#SBATCH --job-name=preprocessing
#SBATCH --partition=tesla.long
#SBATCH --cpus-per-task=4
#SBATCH --time=7-00:00:00
#SBATCH --output=/kalinka/storage/darkmatter/lngs-neutron-detector/%u/jobs/results_%j.out

eval "$(conda shell.bash hook)"
conda activate pmts
preprocessData "$@"