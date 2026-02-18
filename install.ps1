# MIMO Spec installer (PowerShell)
# Usage:  .\install.ps1

Write-Host "Installing MIMO Spec..."

python -m pip install -r requirements.txt
python -m pip install -e .

Write-Host "Done. Try: mimo-pack / mimo-validate / mimo-extract"
