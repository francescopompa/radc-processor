#! /bin/bash

if [ -z "$1" ]; then
  set -- "${1:-DAQMeasurements}"
fi

echo "Copying folder /data/${1} on Kalinka"

rsync -cavu --info=progress2 /data/${1}/ zm6876@kalinka5.iap.kit.edu:/kalinka/storage/darkmatter/${1}lngs-neutron-detector/ 

uuid=331C2D4743721BBE
if lsblk -f | grep -wq $uuid; then
	echo "SSD connected: backing up..."
	rsync -cavu --info=progress2 /data/${1}/ /media/mnd/backup/${1}
else
	echo "SSD is not connected. Please connect to backup the data"
fi
