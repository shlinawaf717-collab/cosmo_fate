@echo off
setlocal
wsl -d Ubuntu -- bash -lc "cd $HOME/WP4_F1_WSL2_TASKPACK_20260813 && bash wsl/05_start_f1.sh"
pause
