@echo off

cd /d "%~dp0"

set "RESEARCH_PY=python"

if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set "RESEARCH_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

start "" "http://127.0.0.1:8780/"

"%RESEARCH_PY%" app\generic_host.py

