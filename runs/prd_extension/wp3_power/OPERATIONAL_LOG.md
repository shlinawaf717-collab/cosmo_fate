# WP3 operational log

- 2026-07-24 approximately 09:05 CST: the Codex-owned persistent terminal
  driver disappeared after 485 of 600 noisy results had been committed to the
  append-only ledger.  No error record, fatal log signature, input failure,
  disk pressure, or memory pressure was found.  The registered command was
  restarted with `--jobs 6`; completed ledger pairs were skipped.
- 2026-07-24 approximately 11:13 CST: the replacement Codex terminal driver
  disappeared after 514 of 600 noisy results.  The same diagnostic checks
  passed.  The identical command was restarted in detached macOS `screen`
  session `wp3_power_mcmc`, still with `--jobs 6`.
- Incomplete cases present at either interruption were rerun with their
  original deterministic seeds.  No completed `(truth_id, k)` ledger pair was
  duplicated.  No truth, input, seed, sampler setting, endpoint, threshold, or
  stopping rule changed.
- 2026-07-24 approximately 15:00 CST: all six Asimov and 600 noisy cases were
  present in the unique result ledger; the detached session exited normally.
