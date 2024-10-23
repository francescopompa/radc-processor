#! /bin/bash


chmod +x ./scripts/backupData.sh
chmod +x ./scripts/preprocessData.sh
chmod +x ./scripts/dataTaking.sh

sudo ln -rsf ./scripts/backupData.sh ~/.local/bin/backupData.sh
sudo ln -rsf ./scripts/preprocessData.sh ~/.local/bin/preprocessData.sh
sudo ln -rsf ./scripts/dataTaking.sh ~/.local/bin/dataTaking.sh