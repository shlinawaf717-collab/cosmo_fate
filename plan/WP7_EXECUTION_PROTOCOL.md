# WP7 FS7 execution protocol

Status: frozen after endpoint-blind method development and before every WP7
posterior sample, SBC posterior rank, prior fate composition, or fate endpoint.

Parent: PRD-A014.  The scientific FS7 target remains the model frozen in the
original extension and PRD-A007.

## Normalized function prior

For each fixed hyperparameter setting, sample `z~N(0,I_7)`, transform with the
registered Cholesky factor, and accept only if both the seven nodes and all 512
registered spline-grid values lie in `[-3,1]`.  Direct rejection and the Cobaya
external-prior indicator call the same vectorized operator.  The resulting
draws are exactly from the normalized conditional prior.  The setting-specific
normalization is estimated by eight scrambled Sobol sequences for audit; no
Bayes factor or cross-setting evidence is authorized.

## Real-data production

Run four independent chains for each of `primary`, `sig025`, `sig100`,
`ell035`, and `ell140`, using the seeds in the machine JSON.  At most six
single-threaded chains run concurrently.  Every setting closes independently
only when all eleven sampled parameters and all seven derived nodes have
rank-normalized split R-hat below `1.01`, node bulk and tail ESS above `400`,
and the hidden batch-means MCSE of the final-node sign probability below
`0.01`.  The complete gate must pass twice, with changed hashes and at least
320 new complete rows per chain between passes.  The finalizer pauses only the
mapped children, checks stable files, recomputes all gates, and resumes all
children if the transaction fails.

Runtime output may show processes, complete rows, hashes, R-hat/ESS and boolean
gate states.  It must not show parameter locations, intervals, likelihoods,
the final-node sign probability, fate composition, hyperparameter comparison,
KL, or any physical endpoint until every registered setting is closed.

## Simulation-based calibration

Generate 50 primary-setting datasets.  FS7 truth histories are direct
normalized-truncation draws.  `ombh2`, `omegam`, `H0`, and `Mb` use the D0 P1
one-dimensional priors, conditioned only on positive derived CDM density,
positive dark-energy density today, and successful finite background
evaluation--the implicit physical domain of the likelihood implementation.
SN, BAO and compressed-CMB noise use the exact registered covariance matrices.

Each dataset has two independent posterior chains.  A dataset enters the rank
audit only if node split R-hat is below `1.01` and node bulk/tail ESS exceed
`400`.  From the converged posterior, deterministically resample 400
equal-weight draws and form randomized normalized truth ranks.  For each node,
Holm-adjusted `alpha=0.05` KS tests must not reject uniformity; empirical 50%
and 90% central-interval coverage must lie in the corresponding two-sided 95%
exact binomial acceptance intervals.  Failure is reported as SBC failure and
blocks a confirmatory WP7 claim; datasets or nodes are never deleted after
rank inspection.

## Information decomposition

For every hyperparameter setting, draw a fixed 200,000-sample normalized prior
reference.  For each node, form 40 equal-prior-mass bins and estimate
`KL(posterior||prior)` from the weighted posterior histogram; repeat with 20
and 80 bins as declared discretization sensitivity.

For the final node also report:

1. the analytic conditional mean weights, conditional SD and multiple R2 from
   free nodes at `a<=1`;
2. the conditional residual `r_f=y_f-C_fo C_oo^-1 y_o` and its prior-to-
   posterior KL using the same quantile-bin rule;
3. deterministic unit-node spline responses over the actual SN/BAO/CMB
   likelihood window and a fixed-point whitened response norm.

A posterior shift at `a=4` is called data information only through this full
decomposition.  A half-sign result with negligible residual KL is prior
symmetry plus non-identification.

## Completion and failure

The primary posterior, all four sensitivities, all 50 SBC datasets, convergence
audits, information decomposition, prior/posterior fate composition, boundary
and OTHER budgets must all be reported.  `ell140` is never silently replaced;
failure after the one original tuning allowance is reported nonconverged.  No
full-CMB WP7 cross-check starts before the compressed-D0 FS7 analysis is closed.
