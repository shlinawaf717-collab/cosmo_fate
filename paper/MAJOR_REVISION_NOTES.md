# Major revision audit (2026-07-20)

This file records interpretive and reproducibility corrections made after the
v1.0 submission archive. It does not alter the frozen preregistration or its
append-only amendments.

1. The registered constraint horizon is no longer reported as `a_h=1`.
   `runs/phase3/fparam/ah.json` already stored `a_h: null`; the revised
   generator shows that BIN4 carries the nonzero `w1` KL into the future.
   `a=1` is now labeled separately as the boundary of direct observational
   support.
2. The 50/50 boundary result is scoped to a regular continuous model/prior
   without point mass on the boundary. Spike-and-slab or explicit model
   averaging can assign posterior mass to exact LambdaCDM.
3. The mock posterior-tail statistic and the two-parameter Wilks likelihood
   ratio are described as non-equivalent diagnostics. Agreement is qualitative,
   not an independent replication of the same test.
4. Fixed-seed equal-weight resampling errors in nested outputs are no longer
   presented as nested-sampling run uncertainty.
5. The four converged fitted grammars receive an explicit in-window fit audit
   and an induced-prior fate audit. “Identical priors” is removed: dimensions,
   early-time constraints, and induced function-space measures differ.
6. The hierarchical GP chain failed the frozen convergence gate
   (`R-1=0.232`). GP node/hyperparameter claims are removed. The GP remains only
   as a transparent construction showing that a mean-reverting future fixes
   the asymptotic class before the likelihood is evaluated.
7. Canonical YAMLs now use portable project-relative Python paths; the data
   manifest contains full SHA256 hashes; CI exercises the classifier and audit
   invariants.
