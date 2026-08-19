# WP7 FS7 development status

Status date: 2026-08-19

Status: **deterministic implementation and all five D0 no-sampling smokes pass;
posterior production and fate calculation remain unauthorized.**

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

## Remaining gates before production

1. implement an auditable direct-rejection prior sampler for SBC and prior
   diagnostics, using the same truncation operator as the external prior;
2. freeze the nodewise information and prior-correlation/leakage decomposition;
3. validate the FS7 D0 background at fixed points against the corresponding
   LCDM and CPL limits;
4. freeze 50 SBC datasets, production seeds, four-chain execution, proposal,
   stopping, R-hat/ESS/MCSE, and endpoint-withholding logic;
5. commit and timestamp the complete production system before any WP7
   posterior sampling or fate classification.

Evidence artifacts:

- `runs/prd_extension/wp7_development/preflight.json`;
- `runs/prd_extension/wp7/truncation_preflight.json`;
- `runs/prd_extension/wp7/smoke_audit.json`;
- `runs/prd_extension/wp7/config_plan.json`.
