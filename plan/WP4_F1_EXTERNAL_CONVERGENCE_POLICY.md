# WP4 F1 prospective convergence and stopping policy

Status: prospectively frozen before any F1 production sample exists.

Machine-readable authority: `plan/wp4_f1_external_convergence_policy.json`.

F1 uses four independent one-thread `cobaya-run --no-mpi` chains with fixed
seeds 4511--4514.  The scientific target is the protocol's full-CMB/lensing
F1 combination: the F0 Pantheon+ likelihood is replaced by
Pantheon+SH0ES, `Mb` is sampled, and the v1.x D0 CPL+P1 condition
`w0+wa<0` is retained.  The F0 posterior covariance is only an efficiency
proposal for its 17 shared parameters; `Mb` uses its frozen scalar proposal.

The authoritative stopping rule is defined before production and uses the
same statistical algorithms audited for F0.  Across all 18 sampled F1
parameters, Cobaya's MPI-chain multivariate `R-1` after 50% row burn-in must
be strictly below 0.01.  The same statistic after 20% and 70% burn-in must
both be below 0.02.  At 50% burn-in, rank-normalized split bulk ESS must be
strictly above 1000 and binary 5%/95% tail ESS strictly above 400 for both
`w` and `wa`.

All gates must pass twice, with at least 320 new complete rows and changed
prefix hashes in every chain.  A failed intervening evaluation resets the
sequence.  The finalizer pauses only the four mapped Cobaya children, checks
stable chain sizes and every hash, recomputes all gates, and either resumes
them on any failure or fsyncs its audit before terminating them.  Cobaya
checkpoints are not edited.  The built-in no-MPI split-chain thresholds are
set more strictly so they cannot pre-empt this prospectively declared rule.

During sampling the controller may report only counts, hashes, convergence
statistics, ESS and Boolean gate state.  It may not expose posterior
locations, intervals, likelihoods, best fits, model-comparison results, or
fate quantities.  Scientific unblinding begins only after the final external
stop audit is valid.

If an integrity defect is found after stopping, the run is resumed with the
same command, seeds, configuration and checkpoints:

`PYTHONPATH=. .venv/bin/python pipeline/run_wp4_f1.py --jobs 4`.
