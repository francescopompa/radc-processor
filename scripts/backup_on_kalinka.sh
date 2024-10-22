#! /bin/bash

rsync -cavu --info=progress2 /data/DAQMeasurements/ zm6876@kalinka5.iap.kit.edu:/kalinka/storage/darkmatter/lngs-neutron-detector/DAQMeasurements 

uuid=331C2D4743721BBE
if lsblk -f | grep -wq $uuid; then
	echo "SSD connected"
	rsync -cavu --info=progress2 /data/DAQMeasurements/ /media/mnd/backup/DAQMeasurements
else
	echo "SSD is not connected. Please connect to backup the data"
fi
