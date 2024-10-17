#! /bin/bash

#SBATCH --job-name=preprocessing
#SBATCH --time=0-12:00:00
#SBATCH --output=/kalinka/storage/darkmatter/lngs-neutron-detector/zm6876/jobs/results_%j.out

if [[ ! -n $1 ]];
then 
    echo "No parameter passed."
    $1 = 'neutronDetectorData'
else
    echo "Parameter passed = $1"
fi


eval "$(conda shell.bash hook)"
conda activate pmts
preprocessData $1