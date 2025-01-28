#!/bin/sh
#SBATCH --job-name=Preprocessing
#SBATCH --partition=tesla.long
#SBATCH --cpus-per-task=16
#SBATCH --output=/kalinka/storage/darkmatter/lngs-neutron-detector/%u/jobs/results_%j.out
#SBATCH --time=2-00:00:00 ##Runtime in D-HH:MM

# The image should first be installed via the script in the ALMOND singularity repository

if [ -z "$1" ]; then
  set -- "${1:-FNG}"
fi

singularity exec --bind /kalinka/:/kalinka/ ~/.local/bin/preprocessData.simg preprocessData ${1}