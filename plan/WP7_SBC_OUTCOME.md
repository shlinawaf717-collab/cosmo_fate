# WP7 FS7 simulation-based calibration outcome

Outcome date: 2026-08-21

Status: **PASS.** All 50 registered primary-prior datasets completed their
two-chain repeated-pass convergence transaction.  No dataset was excluded and
no failed chain was replaced.

## Registered gates

- all 50 convergence audits: PASS;
- per-node randomized truth-rank KS tests with Holm familywise correction at
  `alpha=0.05`: no rejection;
- empirical central 50% coverage within the registered exact-binomial 95%
  acceptance interval `[18,32]` for every node;
- empirical central 90% coverage within `[41,49]` for every node.

The 50% coverage counts for nodes `w1..w7` are
`[30,24,30,27,23,24,29]`; the 90% counts are
`[45,47,48,45,44,44,45]`.

Per-node KS p-values are
`[0.570,0.658,0.316,0.0447,0.629,0.749,0.846]`.  The unadjusted `w4`
value is below 0.05, but it does not cross the predeclared seven-test Holm
threshold and is disclosed rather than promoted to a calibration failure.
With only 50 simulations, passing these gates supports the registered
sampler/interval calibration at coarse resolution; it does not prove exact
finite-sample calibration or that FS7 is the true cosmological model.

No fate endpoint was calculated during SBC.  The PASS result authorizes the
separate, hash-bound start of the five-setting real-data campaign.

Machine-readable artifacts:

- `runs/prd_extension/wp7/sbc/sbc_report.json`;
- `runs/prd_extension/wp7/sbc/sbc_ranks.csv`;
- `runs/prd_extension/wp7/sbc/s001..s050/convergence_audit.json`.
