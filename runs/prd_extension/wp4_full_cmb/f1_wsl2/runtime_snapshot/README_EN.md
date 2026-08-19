# WP4 F1 Windows/WSL2 task pack

Run only under x86-64 Ubuntu in WSL2. The Windows run starts four fresh F1
chains; never copy or pool Mac samples/checkpoints. Run
`windows/01_launch_preflight.cmd`, require an explicit PRE-FLIGHT PASS, then
run `windows/02_start_f1.cmd`. Use `windows/03_status.cmd` for blinded status
and `windows/04_package_results.cmd` after the automatic finalizer reports
EXTERNALLY_STOPPED. See `README_中文.md` for the full procedure and boundaries.

The frozen 1,305-file input manifest includes two legacy AppleDouble `._*`
records (711 bytes total). They are not read by any likelihood, but are retained
byte-for-byte so the frozen path, size, and SHA256 manifest remains unchanged.
