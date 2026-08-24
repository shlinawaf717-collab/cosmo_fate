# WP7 FS7 post-processing protocol

Status: corrected and re-frozen after all five registered real-data settings
closed and before any WP7 posterior location, interval, final-node sign
probability, fate composition, KL endpoint, or between-setting comparison was
read.  The correction concerns an append-only launchd race, not an endpoint.

Parent: PRD-A014 and `plan/WP7_EXECUTION_PROTOCOL.md`.  This document fills
implementation details already required by those frozen documents; it does not
change the FS7 model, data, prior, chains, convergence gates, or scientific
endpoints.

## Input and pooling

Only chain prefixes recorded in the five successful transactional final-stop
audits are eligible.  The reporter verifies every audited complete-row count,
captured-byte boundary, and prefix SHA-256 digest against the post-termination
audit before reading a posterior value.  A file may contain an append-only
suffix only when the complete audited prefix still matches exactly.  Such a
suffix is retained on disk, counted and disclosed, but is excluded from every
WP7 endpoint.  Truncation, mutation, or a mismatch inside the audited prefix is
a hard failure.

This prefix rule is operative for `ell140`.  Its finalizer committed four
stable, converged prefixes at 2026-08-21 09:21 UTC.  The launchd driver restarted
during the roughly three-second interval before the audit status became
`EXTERNALLY_STOPPED`, then appended samples.  The mismatch was found by the
pre-endpoint authorizer on 2026-08-24.  All four audited prefixes end at a
complete newline and reproduce their registered hashes and row counts.  Using
the audited stopping-time prefixes preserves the registered two-pass stopping
rule; using the unplanned suffix would silently give one sensitivity setting a
different, post-stop sample horizon.

Within each eligible prefix, the reporter discards the first 50 percent of
complete rows separately in each chain, retains the original integer
Metropolis dwell weights, and pools the four post-burn chains by those weights.
Chains are not resampled or given equal total weight.

For every registered node and the conditional final-node residual, report the
right-continuous weighted empirical-CDF quantiles at 2.5, 16, 50, 84, and 97.5
percent, together with the weighted mean and population SD.  These summaries
are descriptive; no posterior location was used to choose them.

## Information endpoints

The frozen 200,000-draw prior references and seeds in
`runs/prd_extension/wp7/information_plan.json` are regenerated exactly.  Their
stored quantile edges must reproduce numerically before an endpoint is written.
For 20, 40, and 80 equal-prior-mass bins, posterior mass is estimated with the
native dwell weights and

`KL(posterior||prior) = sum_j p_j log[p_j/(1/B)]`.

The finite Monte Carlo extrema stored as the first and last prior edges are
extended to negative and positive infinity for histogram assignment.  This
conserves all posterior mass while leaving every internal frozen edge
unchanged.  Empty posterior bins contribute zero and no pseudocount is added.

The same estimator is used for
`r_f = y_f - C_fo C_oo^-1 y_o`.  The report copies the prospectively frozen
conditional SD, multiple R2, deterministic spline leakage, and local whitened
likelihood-response diagnostics.  No binary threshold for “negligible KL” was
registered, so the reporter returns the quantitative residual KL and does not
manufacture a post-result PASS/FAIL label.

## Fate and Monte Carlo precision

FS7 has a finite asymptotic value `w_inf=fs7_w7`.  For positive present-day
dark-energy density, physical labels are analytic: `w_inf<-1` is RIP, exact
`w_inf=-1` is DS, and `w_inf>-1` is DECAY.  Any non-positive-density draw is
sent through the frozen background classifier rather than silently discarded.
The separately reported boundary budget is `abs(w_inf+1)<=0.01`; it does not
replace the exact physical label.  CRUNCH and OTHER remain explicit budgets.

The posterior RIP Monte Carlo SE is exactly the hidden stopping diagnostic:
after per-chain row burn and integer-weight expansion, equalize to the shortest
chain, retain the largest multiple of 32, form 32 contiguous batch means per
chain, and report the SD of the 128 batch means divided by `sqrt(128)`.  The
prior sign SE is the ordinary Bernoulli Monte Carlo SE for 200,000 independent
registered prior draws.

## Authorization and outputs

Post-processing is authorized only after: all five final-stop audits are
successful, all post-termination gates pass, all 20 chain identities match,
the 50-dataset SBC report is PASS, no WP7 sampler remains alive, and the
post-processing protocol, reporter, and tests are hashed.  Authorization is an
immutable new artifact and never rewrites the pre-sampling protocol.

The required outputs are a versioned JSON endpoint artifact, a machine audit,
and a prose outcome.  They include all five settings, nodewise 20/40/80-bin KL,
conditional-residual KL, prior/posterior fate composition, boundary and OTHER
budgets, final-sign MCSE, sensitivity relative to the primary setting, and the
frozen information-pathway diagnostics.  No model evidence or cross-setting
Bayes factor is authorized.
