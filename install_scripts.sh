#! /bin/bash


chmod +x ./scripts/backupData.sh
chmod +x ./scripts/preprocessData.sh
chmod +x ./scripts/dataTaking.sh
chmod +x ./scripts/preprocessDataSingularity.sh
chmod +x ./analysisScripts/dataAnalysisNeutronBackground.sh

mkdir -p "$HOME/.local/bin"

ln -rsf ./scripts/backupData.sh ~/.local/bin/backupData.sh
ln -rsf ./scripts/preprocessData.sh ~/.local/bin/preprocessData.sh
ln -rsf ./scripts/dataTaking.sh ~/.local/bin/dataTaking.sh
ln -rsf ./scripts/preprocessDataSingularity.sh ~/.local/bin/preprocessDataSingularity.sh
ln -rsf ./analysisScripts/dataAnalysisNeutronBackground.sh ~/.local/bin/dataAnalysisNeutronBackground.sh

if ! grep -qF '# radc-processor command wrappers' "$HOME/.bashrc" 2>/dev/null; then
    {
        echo '# radc-processor command wrappers'
        for s in backupData preprocessData dataTaking preprocessDataSingularity dataAnalysisNeutronBackground; do
            echo "alias $s.sh='\$HOME/.local/bin/$s.sh'"
        done
    } >> "$HOME/.bashrc"
fi

