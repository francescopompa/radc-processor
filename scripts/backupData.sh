#! /bin/bash

if [ -z "$1" ]; then
  set -- "${1:-DAQMeasurements}"
fi

echo "Copying folder /data/${1} on Kalinka"

rsync -cavu --info=progress2 /data/${1}/ zm6876@kalinka5.iap.kit.edu:/kalinka/storage/darkmatter/lngs-neutron-detector/${1}

uuid=F43E88583E8815B0
if lsblk -f | grep -wq $uuid; then
	echo "External hard disk connected: backing up..."
	rsync -cavu --info=progress2 /data/${1}/ /media/mnd/backup/${1}
else
	echo "The external HDD is not connected. Please connect to backup the data"
fi
