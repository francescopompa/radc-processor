#! /bin/bash

if [[ ! -n $1 ]];
then
    echo "No parameter passed."
    $1 = 'neutronDetectorData'
else
    echo "Parameter passed = $1"
fi
echo "${1}"

rsync -cavu --info=progress2 /data/${1} zm6876@kalinka5.iap.kit.edu:/kalinka/storage/darkmatter/lngs-neutron-detector/ 

uuid=331C2D4743721BBE
if lsblk -f | grep -wq $uuid; then
	echo "SSD connected"
	rsync -cavu --info=progress2 /data/${1} /media/mnd/backup/
else
	echo "SSD is not connected. Please connect to backup the data"
fi
