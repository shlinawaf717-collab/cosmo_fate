# WP4 F0 external convergence and stopping policy

Status: frozen during F0, before any F0 posterior location, interval, best-fit
likelihood, model-comparison, or fate endpoint was inspected.

Machine-readable authority:
`plan/wp4_f0_external_convergence_policy.json`.

## 1. Scope and reason

F0 was launched as four independent `cobaya-run --no-mpi` processes.  In
Cobaya 3.6.2, that execution mode tests each chain by dividing it into four
temporally adjacent segments and also waits for `Rminus1_cl_stop: 0.2`.
The frozen extension protocol instead names `R-1`, bulk ESS, and tail ESS; it
does not register the confidence-limit statistic.  Standard multi-chain
Gelman--Rubin convergence compares the four independent chains.

PRD-A006 therefore fixes the statistical meaning of the already registered
gates and supplies a reversible, audited external stop.  It changes no target
distribution, likelihood, prior, seed, proposal, CAMB setting, chain content,
or scientific endpoint.  The original YAML and Cobaya checkpoints remain
unaltered.

## 2. Blinding boundary

Before final F0 closure, the external process may read and persist only:

- complete row counts, summed integer weights, file sizes, mtimes, and SHA256;
- the registered convergence statistics and Boolean gate states;
- code, policy, configuration, and input hashes.

It must not output posterior means, marginal intervals, best-fit points,
likelihood values, model-comparison statistics, or fate quantities.  The
diagnostic monitor installed before this policy had
`decision_authority: false`; its observations cannot count as an authoritative
pass.

## 3. Frozen statistics

All inequalities are strict.

### 3.1 Multivariate R-1

The primary statistic exactly reproduces the Cobaya 3.6.2 MPI-chain formula:
after discarding the first 50% of complete rows separately in each chain,
compute the integer-weighted mean and covariance of all 17 sampled parameters
in each chain.  Average within-chain covariances using post-burn row counts,
form the unweighted covariance of the four chain means, normalize as in
Cobaya, and take the largest absolute eigenvalue of
`L^{-1} B L^{-T}`.  The parameter order is:

`logA, ns, theta_MC_100, ombh2, omch2, tau, w, wa, A_planck, amp_143,
amp_217, amp_143x217, n_143, n_217, n_143x217, calTE, calEE`.

The primary gate is `R-1 < 0.01`.  The same calculation at 20% and 70%
row burn-in is a frozen sensitivity guard; both values must be `< 0.02`.
The 50% result remains primary and cannot be replaced by the most favourable
burn-in.

### 3.2 Bulk and tail ESS

ESS uses the 50% primary burn-in.  Integer sample weights are expanded as
Metropolis dwell states.  The four chains are truncated from the earlier end
to the common final weighted length, and each is split into two halves.

For each of `w` and `wa`:

- bulk ESS is computed after pooled rank normalization with the
  `(rank - 3/8)/(S + 1/4)` transform;
- lower and upper tail ESS use binary indicators at the pooled 5th and 95th
  percentiles, and tail ESS is their minimum;
- autocorrelation time uses Geyer's initial-positive and initial-monotone
  paired sequence.

Both `w` and `wa` must have bulk ESS `> 1000` and tail ESS `> 400`.  ESS for
the other 15 sampled parameters is retained diagnostically but is not an
additional stopping gate; the 17-dimensional R-1 already guards their joint
between-chain location.

The versioned implementation frozen for these formulas is
`pipeline/monitor_wp4_f0.py`, SHA256
`8665afd8e04114f2c84fc702b905fe4c003aebbf5b3b7b97a8a413011ffc71ee`,
using NumPy 2.5.0, SciPy 1.16.2, and Cobaya 3.6.2.

## 4. Repeated-pass rule

An external stop becomes eligible only after two authoritative snapshots both
pass every gate above.  Between the first and second pass:

- every chain must gain at least 320 complete rows;
- every chain hash must change;
- the policy and statistics-implementation hashes must be identical.

The 320-row separation equals one observed built-in F0 learning/check interval
under the frozen `learn_every: 40d` configuration.  A failed intervening
snapshot resets the consecutive-pass state.

## 5. Snapshot and stop transaction

Routine monitoring opens each chain read-only, records its initial file size
and mtime, reads no more than that size, discards a partial final line, and
hashes the exact captured prefix.  The four per-file snapshots are not called
simultaneously atomic.

After two eligible passes, the finalizer:

1. verifies the frozen driver, four Cobaya child processes, policy hash, code
   hash, run-plan hash, run-YAML hashes, and chain paths;
2. pauses only the four Cobaya child processes;
3. verifies that chain file sizes are stable;
4. takes a final complete-prefix snapshot and recomputes every gate;
5. if any check fails, resumes all four children and records `ABORTED_RESUMED`;
6. if all checks pass, writes and fsyncs the final audit before terminating
   the children, then records their exit and the driver exit.

The existing Cobaya checkpoints remain `converged: false`; they are not edited
to manufacture an internal pass.  A nonzero driver exit caused solely by the
audited external stop is an expected operational consequence and is
superseded only by the final external-stop audit, not concealed.

If a later integrity audit finds an incomplete file, hash mismatch, parser
error, or implementation defect, F0 is resumed with the same
`pipeline/run_wp4_f0.py --jobs 4` command.  The unchanged checkpoints make
this continuation reversible.  Scientific failure of an already valid F0
gate is not a reason to alter or resume sampling.

## 6. Interpretation

This is a corrective, post-launch stopping-definition amendment, not a
prospective preregistration.  Convergence diagnostics had been inspected
before freezing it; no F0 scientific endpoint had been inspected.  Because
the sampler configuration is unchanged, PRD-A006 does not consume WP4's one
permitted configuration correction.  The confidence-limit statistic may
still be reported as a secondary diagnostic but is not a stopping gate.
