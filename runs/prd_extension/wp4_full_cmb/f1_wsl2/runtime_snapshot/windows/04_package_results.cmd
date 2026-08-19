@echo off
setlocal
set PACK_WIN=%~dp0..
for /f "delims=" %%i in ('wsl wslpath -a "%PACK_WIN%"') do set PACK_WSL=%%i
wsl -d Ubuntu -- bash -lc "cd $HOME/WP4_F1_WSL2_TASKPACK_20260813 && bash wsl/07_package_results.sh && cp WP4_F1_WSL2_RESULTS.tar.gz WP4_F1_WSL2_RESULTS.tar.gz.sha256 '%PACK_WSL%/'"
pause
