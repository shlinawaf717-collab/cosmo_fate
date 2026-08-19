# WP5 three-width external convergence and stopping policy

Status: frozen after full-likelihood no-sampling initialization and before any
WP5 production sample.

WP5 has three separate four-chain posterior campaigns at
`Delta ln(a)={0.005,0.01,0.02}`.  Each samples the same 20 parameters and uses
one numerical-library thread per chain.  Fixed chain seeds are:

- `0.005`: 2026082511--2026082514;
- `0.010`: 2026082521--2026082524;
- `0.020`: 2026082531--2026082534.

The Windows scheduler may keep at most eight chains active, but scheduling is
not a scientific setting.  No chain segment, seed, or width may be moved
between platforms or pooled across widths.

For each width independently, the authoritative rule uses Cobaya's between-
chain multivariate estimator over all 20 sampled parameters.  After 50% row
burn-in, `R-1` must be strictly below 0.01; after 20% and 70% burn-in it must
be strictly below 0.02.  At 50% burn-in, each of `w1,w2,w3,w4` must have
rank-normalized split bulk ESS strictly above 1000 and 5%/95% tail ESS
strictly above 400.

All gates pass twice, with every chain adding at least 320 complete rows and
changing its captured-prefix SHA256.  A failed intervening evaluation resets
the sequence.  Each width has its own pass state and final stop audit.

The finalizer pauses only the four mapped Cobaya children for that width,
checks stable file sizes, recomputes every gate, fsyncs the audit, and then
terminates those children.  On any pre-commit failure it resumes every paused
child without editing a checkpoint.  A completed width is never restarted
while other widths continue.

Sampling-phase output is limited to process health, row/weight counts, hashes,
the registered R-1/ESS statistics, and Boolean gates.  Parameter locations,
intervals, likelihoods, width comparisons, early-DE rejection composition,
fate probabilities, and model-comparison quantities remain hidden until all
three width final audits are valid.
