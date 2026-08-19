@echo off
setlocal
set INC_WIN=%~dp0..
for /f "delims=" %%i in ('wsl wslpath -a "%INC_WIN%"') do set INC_WSL=%%i
wsl -d Ubuntu -- bash -lc "set -e; ROOT=$HOME/WP4_F1_WSL2_TASKPACK_20260813; test -d \"$ROOT\"; DEST=$ROOT/nested_increment_20260819; mkdir -p \"$DEST\"; cp -a '%INC_WSL%'/README_中文.md '%INC_WSL%'/INCREMENT_MANIFEST.json '%INC_WSL%'/pipeline '%INC_WSL%'/wsl \"$DEST/\"; cd \"$ROOT\"; bash \"$DEST/wsl/10_install_and_preflight.sh\""
pause
