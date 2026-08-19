# WP7 FS7 development status

Status date: 2026-08-19

Status: **READY TO AUTHORIZE.** Deterministic implementation, normalized-prior
calibration, fixed points, five real-data smokes, 50 frozen SBC inputs, SBC
smoke, information plan, and both production activations pass.  Posterior
production and fate calculation remain deliberately unauthorized until the
separate start command is executed.

## Completed in this development pass

- Implemented the frozen seven-node FS7 covariance and non-centred Cholesky
  map for all five registered `(sigma_f, ell)` settings.
- Implemented the global clamped cubic spline in `ln(a)`, the fixed
  `w=-1` early extension, the constant `a>=4` future extension, and the
  registered 512-point function-bound check.
- Added a vectorized latent-space truncation indicator and a Cobaya external
  prior for each fixed hyperparameter setting.
- Verified exact LCDM identities: node interpolation, both clamped endpoint
  derivatives, both constant extensions, and `ln f_DE=0` all pass at numerical
  zero in the deterministic fixtures.
- Built five endpoint-blind compressed-CMB D0 configs using standard-normal
  latent coordinates and loaded DESI DR2 BAO, Pantheon+SH0ES, the Chen et al.
  distance prior, and `BackgroundW(model=fs7)` together.
- Every setting passed Cobaya `--test`; no chain row or fate endpoint was
  generated.

## Prior geometry and truncation feasibility

The registered analytic geometry is reproduced.  The final `a=4` residual
given the four free nodes at `a<=1` has:

| sigma_f | ell | conditional SD | multiple R2 |
|---:|---:|---:|---:|
| 0.50 | 0.70 | 0.4651 | 0.1348 |
| 0.25 | 0.70 | 0.2325 | 0.1348 |
| 1.00 | 0.70 | 0.9302 | 0.1348 |
| 0.50 | 0.35 | 0.5000 | 0.00000053 |
| 0.50 | 1.40 | 0.1406 | 0.9209 |

The `ell=1.40` covariance retains its registered warning: condition number
`2.51e8`.  It passes the deterministic Cholesky/round-trip checks but must
still satisfy the original posterior convergence gates.

Eight scrambled Sobol estimates show that direct rejection from the
registered normalized truncated prior is computationally feasible.  Estimated
admissibility probabilities are approximately `0.99949`, `1.00000`, `0.81487`,
`0.99944`, and `0.99963` in the table order above.  The broad-amplitude
`sigma_f=1` setting has the only material truncation selection and must not be
treated as an untruncated symmetric Gaussian in prior/posterior comparisons.
No final-node sign or fate composition was calculated in this audit.

## Interpretation boundary

The primary setting leaves most final-node variance in a residual not
explained by the registered observed-history nodes.  Conversely, `ell=1.40`
transports strong prior correlation to the future node but is numerically
ill-conditioned.  In every setting, the registered global spline also has
deterministic past--future leakage.  A future-node posterior shift therefore
cannot be called a direct observational constraint without decomposing:

1. prior correlation from `a<=1` nodes;
2. the global-spline likelihood response over `a<1`;
3. likelihood information in the conditional final-node residual.

## Completed after the first development pass

1. The direct-rejection sampler and external prior now share one vectorized
   admissibility operator; symmetry and deterministic replay tests pass.
2. The first nontrivial 4000-vs-5000 trapezoid comparison failed the frozen
   `2e-5` gate at `5.49e-5`.  The gate was not relaxed: FS7 now integrates its
   cubic spline with an exact antiderivative and agrees with independent
   adaptive quadrature to `1.75e-15`.
3. At the LCDM point, FS7 and CPL-LCDM DESI BAO, Pantheon+SH0ES and compressed
   CMB log-likelihoods agree exactly at reported precision.
4. The nodewise 20/40/80-bin prior-quantile KL estimator, conditional future
   residual, analytic prior-correlation term, and actual likelihood-window
   spline response have been frozen from 200,000 prior draws per setting.
5. Fifty physical primary-prior SBC truth/noise inputs and 100 two-chain
   inference configs are frozen and audited.  No aggregate truth/fate
   composition or SBC rank has been calculated.
6. Twenty real-data configs, four per setting, are frozen with six-way
   execution, blinded rank-Rhat/node-ESS/hidden-sign-MCSE monitoring, two-pass
   separation, and transactional finalization.
7. Both production-system no-sampling smokes and the final public-commit
   readiness audit pass.

## Start boundary

`runs/prd_extension/wp7/production_readiness.json` is
`READY_TO_AUTHORIZE_WP7`.  It verifies 20 real-data and 100 SBC configs, all 50
SBC datasets, both activations, the remote source commit, absence of posterior
sample files, absence of start authorizations, and absence of a fate endpoint.

The next action is intentionally separate and state-changing:

```bash
PYTHONPATH=. .venv/bin/python pipeline/authorize_wp7.py sbc
PYTHONPATH=. .venv/bin/python pipeline/run_wp7_sbc.py
```

The academically conservative order is to complete and audit SBC before
authorizing the real-data campaign.  Real data can later be authorized with
`pipeline/authorize_wp7.py real`; authorization has not been run here.

Evidence artifacts:

- `runs/prd_extension/wp7_development/preflight.json`;
- `runs/prd_extension/wp7/truncation_preflight.json`;
- `runs/prd_extension/wp7/smoke_audit.json`;
- `runs/prd_extension/wp7/config_plan.json`.
- `runs/prd_extension/wp7/production_readiness.json`.
