# WP4/WP5 resource-feasibility closure decision

Date: 2026-08-25

Author decision: close the paper without completing the computationally
dominant WP4 F1 nested-sampling campaign or the WP5 three-width full-CMB BIN4
campaign.

## Scientific disposition

- WP4 F1 MCMC is retained as an already completed full-CMB/lensing diagnostic.
  Its imported chains pass the frozen candidate convergence and ESS gates, but
  the external-stop transaction carries an exit warning that must be disclosed
  or resolved by a read-only provenance audit before manuscript use.
- The sparse WP4 MCMC RIP tail is not a publishable rare-event estimate.  The
  registered 12-run PolyChord verification was not started and is closed as a
  computational-feasibility No-Go.  No full-CMB nested evidence, stratified
  regional evidence, or precise full-CMB fate-tail probability will be claimed.
- WP5 is stopped while endpoint-blind and before convergence.  The partial
  chains, logs, checkpoints, and blinded operational diagnostics are preserved
  as an incomplete feasibility record.  They are excluded from posterior,
  likelihood, fate, evidence, and smoothing-width comparisons.  The archived
  compressed-CMB BIN4 result remains visible only as a geometry-conditioned
  diagnostic.
- WP7 and WP8 become the primary structural extension: they quantify loss of
  information outside the observed window and demonstrate two-sided future-fate
  support under observationally invariant continuations.  They do not convert
  the incomplete WP4/WP5 calculations into full-CMB endpoints.

## WP9 boundary

No WP9 inference run is authorized for paper closure.  DESI DR2 Results IV is
added as a dated literature/data update.  A future Ly-alpha AP run may begin
only after an official public data vector/likelihood and covariance are
available and a new prospective overlap rule replaces, rather than adds to,
the overlapping DR2 Ly-alpha BAO block.

## Inspection boundary

Before this decision, WP4 MCMC endpoints and the registered best-fit summaries
had already been inspected under PRD-A012.  For corrected WP5 production, only
process health, row/weight counts, hashes, R-hat/ESS diagnostics, and Boolean
gates were inspected.  No WP5 posterior location, interval, aggregate
likelihood endpoint, fate probability, smoothing-width comparison, or evidence
was inspected or generated.
