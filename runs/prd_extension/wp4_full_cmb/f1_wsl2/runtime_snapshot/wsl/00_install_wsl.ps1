$ErrorActionPreference = "Stop"
Write-Host "Installing/updating WSL and Ubuntu..."
wsl --install -d Ubuntu
Write-Host "If Windows asks for a reboot, reboot, open Ubuntu once, create its user, then run windows\\01_launch_preflight.cmd."
