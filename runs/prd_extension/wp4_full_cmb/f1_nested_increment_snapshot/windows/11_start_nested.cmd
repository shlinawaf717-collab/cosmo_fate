@echo off
setlocal
wsl -d Ubuntu -- bash -lc "cd $HOME/WP4_F1_WSL2_TASKPACK_20260813 && bash nested_increment_20260819/wsl/11_start_nested.sh"
pause
