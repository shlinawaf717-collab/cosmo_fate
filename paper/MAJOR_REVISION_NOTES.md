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
8. A-004 is recorded as an author-confirmed post-hoc structural audit, not a
   preregistered amendment. The declared seven-dimensional summary has
   grammar-specific supports of dimensions 2, 2, 2, and 3 whose common
   one-dimensional intersection has zero native-prior mass. The earlier
   covariance-regularized weighting pilot is rejected; no matched fate
   probabilities are reported.
9. A-005 corrects the finite-limit fate boundary: `w_inf=-1` is the exact
   de Sitter locus and the former epsilon band is boundary-adjacent only.
   BA and BIN4 posterior fate tables and the induced-prior audit are rebuilt.
10. Nested fate probabilities now sum original normalized weights. Equal-weight
    resampling is diagnostic only; D0 is repeated across independent seeds and
    run-to-run scatter is kept separate from internal evidence errors.
11. The registered fragility metrics are reported as a formal fulfilment table.
    Structural zeros and finite-sampling zeros are treated differently.
12. A-006 adds an explicit BIN4 early-dark-energy gate. The archived posterior
    passes, while a full-Planck run is a documented No-Go until a perturbation
    implementation and official likelihood package are available.
13. Figure 4 now reads the original-weight nested outputs it claims to show,
    rather than the MCMC fate files. D3 retains a weighted positive tail even
    though its equal-weight diagnostic contains zero RIP draws; the data-axis
    tail span is therefore finite (2.665 dex), not unidentified.
