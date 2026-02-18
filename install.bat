@echo off
REM MIMO Spec installer (Windows CMD)
REM Usage: install.bat

python -m pip install -r requirements.txt
python -m pip install -e .

echo Done. Try: mimo-pack / mimo-validate / mimo-extract
