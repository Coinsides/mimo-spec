@echo off
setlocal

REM Usage:
REM   mimo-pack.bat --in <dir> --out <dir> --split line_window:400 --source file --workspace ws_x --vault-id default

python -m mimo_spec.tools.mimo_pack %*
