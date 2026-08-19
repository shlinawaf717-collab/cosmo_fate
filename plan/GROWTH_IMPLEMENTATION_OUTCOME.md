# WP6 growth-likelihood implementation outcome

Outcome date: 2026-08-19

Status: **DATA GATE PASS; DIRECT INFERENCE NO-GO.**

The earlier data-only decision correctly established that a complete public
DESI DR1 Full-Shape+BAO likelihood exists and that it can only **replace**, not
be added to, the overlapping DESI DR2 BAO likelihood.  The seven official HDF5
files, covariance matrices, release code and direct dependencies were archived
and hash-checked.  The replacement model also passed a no-sampling Cobaya
initialization with the WP4 F1 CMB/lensing and supernova blocks.

The next frozen hard gate did not pass.  Thresholds and two official reference
points were committed as `fc5dd65` before local evaluation:

1. At the public release example point, the registered `solve=marg`
   configuration returned `chi2_FS_BAO = 2377.533` and
   `-log L = 1188.7665`.  The source-code comment's `1176.98` was mistakenly
   labelled as chi-square in the benchmark plan; treating it correctly as a
   log-likelihood magnitude still leaves an absolute discrepancy of `11.7865`,
   far outside the frozen `0.10` tolerance.
2. At the official CPL PantheonPlus+CMB+lensing MAP point, the released result
   records `chi2_FS_BAO = 331.75452`, whereas the public `solve=marg`
   implementation returned `341.11801`, a difference of `9.36349`.

Re-running with the official-chain software generation (CAMB 1.5.4 and Cobaya
3.5) did not materially change either value, so CAMB 1.6.6 is not the cause.
As a diagnostic only, switching the analytic-nuisance setting from
`solve=marg` to `solve=best` reduced the MAP discrepancy to about `0.82` in
chi-square.  That option was not the registered production configuration, it
still misses the frozen tolerance, and selecting it after seeing the failure
would be a post-hoc change.

Consequently the protocol's fail-closed rule applies:

- no WP6 posterior production run is authorized;
- no growth-conditioned fate probability is calculated;
- no marginal `f sigma8` compilation or DR1+DR2 double counting is substituted;
- WP4 F1 remains the full-CMB/lensing result, while direct late-time growth is
  reported as a transparent prospective No-Go caused by reference-likelihood
  non-reproduction, not by an astrophysical null result.

Machine-readable evidence is in
`runs/prd_extension/wp6_growth/reference/reference_audit.json`.
