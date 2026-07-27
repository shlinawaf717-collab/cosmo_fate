# WP7 analytic prediction and numerical preflight

Status: frozen before WP7 prior simulation, likelihood evaluation, posterior
sampling, or fate classification.

Parent correction: PRD-A007.

## Analytic prediction

Write the FS7 node variables as `y_i=w_i+1`.  The fate boundary at the final
node is `y_4=0`.  Partition the Gaussian function prior into the nodes at
`a<=1`, denoted `y_o`, and the final node at `a=4`, denoted `y_f`.  Before
truncation,

`y_f | y_o ~ Normal(C_fo C_oo^{-1} y_o,
                    C_ff-C_fo C_oo^{-1} C_of)`.

Therefore

`P(RIP | y_o) = Phi[-mu_f|o / sigma_f|o]`.

The following prediction is registered before WP7 inference:

> If the prior is symmetric about `w=-1` at the final fate node, and the
> likelihood supplies negligible information about the final-node residual
> after conditioning on the observed-history subspace, then
> `P(RIP)` approaches one half.  Such a result is prior-symmetry plus
> non-identification, not evidence that the two fates are physically equally
> likely.

Both conditions must be tested.  The prediction is not asserted for a setting
where prior correlation or spline coupling allows the likelihood to constrain
the final-node residual.

WP7 must report, for every registered hyperparameter setting:

- the prior and posterior final-node sign probabilities;
- the conditional standard deviation and multiple `R^2` of the `a=4` node
  given the registered nodes at `a<=1`;
- likelihood information at each node;
- a decomposition separating prior correlation from deterministic spline
  leakage.

## Numerical preflight

The deterministic preflight is versioned in
`runs/prd_extension/wp7_wp8_preflight/preflight.json`.

The `ell=1.4` covariance has a high condition number but passes Cholesky and
linear-solve residual checks in the frozen double-precision implementation.
It remains a registered sensitivity setting; its jitter is not increased
after seeing this warning.  It must meet the original convergence and ESS
gates or be reported nonconverged.  A numerical failure may use the one
already registered non-centred tuning revision, but no post-result
hyperparameter substitution is allowed.

The registered clamped cubic spline is global.  A unit change in a future
node produces a nonzero response over `a<1`, even though interpolation forces
the response to zero at the `a=1` knot.  This is not a software error: it is a
property of the registered model.  Consequently, a future-node posterior
shift cannot be described as a direct observational constraint on the future
without reporting the leakage response and the prior-correlation pathway.
FS7 remains unchanged as a common global function prior; the limitation is
made explicit rather than repaired after results.
