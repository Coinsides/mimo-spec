@echo off
setlocal

REM Usage:
REM   mimo-pack.bat --in <dir> --out <dir> --split line_window:400 --source file --vault-id default
REM
REM Note:
REM   Workspace scope must NOT be written into MU. Scope is expressed via membership.jsonl in the memory system.

python -m mimo_spec.tools.mimo_pack %*
