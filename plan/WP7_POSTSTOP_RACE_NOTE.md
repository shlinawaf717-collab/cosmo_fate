# WP7 ell140 post-stop launchd race

Status: corrective operational record written before any WP7 real-data
posterior location, interval, sign probability, fate composition, KL endpoint,
or between-setting comparison was read.

At 2026-08-21 09:21:26 UTC the transactional finalizer stopped the four
`ell140` children after the second authoritative convergence pass.  The driver
exited while `final_stop_audit.json` still held its transactional commit state.
launchd immediately restarted the driver at 09:21:29 UTC, just before the
finalizer replaced that state with `EXTERNALLY_STOPPED`.  The restarted driver
therefore resumed the four `ell140` checkpoints.  They later stopped internally
and appended complete rows to the same files.

The pre-endpoint authorizer discovered the mismatch on 2026-08-24 because it
initially required each complete file to equal the final-stop snapshot.  No
authorization or endpoint artifact was written.  A byte-prefix audit then
established for all four chains that:

- the registered `captured_bytes` boundary ends in a newline;
- the exact prefix row count equals the post-termination audit;
- the prefix SHA-256 equals the post-termination audit;
- the current file is an append-only extension of that intact prefix.

The excluded suffix contains 43,979, 40,918, 45,646, and 46,090 complete rows
for chains 1--4 respectively.  The files are preserved unchanged.  Every WP7
endpoint uses only the convergence-time audited prefixes.  This preserves the
registered stopping rule and avoids silently giving `ell140` a longer sampling
horizon than the other sensitivity settings.  The suffix is not used as an
informal robustness analysis and no scientific endpoint is discarded after
inspection.
