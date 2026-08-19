@echo off
setlocal
set PACK_WIN=%~dp0..
for /f "delims=" %%i in ('wsl wslpath -a "%PACK_WIN%"') do set PACK_WSL=%%i
wsl -d Ubuntu -- bash -lc "set -e; TARGET=$HOME/WP4_F1_WSL2_TASKPACK_20260813; if [ ! -d \"$TARGET\" ]; then cp -a '%PACK_WSL%' \"$TARGET\"; fi; cd \"$TARGET\"; bash wsl/01_setup_and_preflight.sh"
pause
