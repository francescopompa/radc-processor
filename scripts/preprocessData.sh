#! /bin/bash

#SBATCH --job-name=preprocessing
#SBATCH --cpus-per-task=16
#SBATCH --time=0-12:00:00
#SBATCH --output=/kalinka/storage/darkmatter/lngs-neutron-detector/%u/jobs/results_%j.out

eval "$(conda shell.bash hook)"
conda activate pmts
preprocessData "$@"