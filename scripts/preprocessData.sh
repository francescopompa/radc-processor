#! /bin/bash

#SBATCH --job-name=preprocessing
#SBATCH --time=0-12:00:00
#SBATCH --output=/kalinka/storage/darkmatter/lngs-neutron-detector/zm6876/jobs/results_%j.out

if [ -z "$1" ]; then
  set -- "${1:-DAQMeasurements}"
fi

echo "Preprocessing directory /kalinka/storage/darkmatter/lngs-neutron-detector/${1}."

eval "$(conda shell.bash hook)"
conda activate pmts
preprocessData $1