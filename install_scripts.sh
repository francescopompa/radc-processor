#! /bin/bash


chmod +x ./scripts/backupData.sh
chmod +x ./scripts/preprocessData.sh
chmod +x ./scripts/dataTaking.sh
chmod +x ./scripts/preprocessDataSingularity.sh

ln -rsf ./scripts/backupData.sh ~/.local/bin/backupData.sh
ln -rsf ./scripts/preprocessData.sh ~/.local/bin/preprocessData.sh
ln -rsf ./scripts/dataTaking.sh ~/.local/bin/dataTaking.sh
ln -rsf ./scripts/preprocessDataSingularity.sh ~/.local/bin/preprocessDataSingularity.sh
