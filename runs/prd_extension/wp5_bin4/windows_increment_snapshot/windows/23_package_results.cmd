@echo off
setlocal
set INC_WIN=%~dp0..
for /f "delims=" %%i in ('wsl wslpath -a "%INC_WIN%"') do set INC_WSL=%%i
wsl -d Ubuntu -- bash -lc "cd $HOME/WP4_F1_WSL2_TASKPACK_20260813 && bash wp5_increment_20260819/wsl/23_package_results.sh && cp WP5_BIN4_RESULTS.tar.gz WP5_BIN4_RESULTS.tar.gz.sha256 '%INC_WSL%/'"
pause
