#! /bin/bash

shopt -s expand_aliases
source /home/mnd/.bash_aliases

if [ -z "$1" ]; then
  set -- "${1:-ALMOND}"
fi

echo "Copying folder /data/${1} on Kalinka"

VPNdisconnect
VPNconnect
rsync -avu --info=progress2 /data/${1}/ zm6876@kalinka5.iap.kit.edu:/kalinka/storage/darkmatter/lngs-neutron-detector/${1}
VPNdisconnect

rsync -avu --info=progress2 -e "sshpass -e ssh -o StrictHostKeyChecking=no" /data/${1}/ $ULITE_USER@linux.lngs.infn.it:/nfs/almond/${1}

uuid=F43E88583E8815B0
if lsblk -f | grep -wq $uuid; then
	echo "External hard disk connected: backing up..."
	rsync -avu /data/${1}/ /media/mnd/backup/${1}
else
	echo "The external HDD is not connected. Please connect to backup the data"
fi
