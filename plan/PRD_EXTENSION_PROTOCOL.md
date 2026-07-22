# PRD extension protocol

**Protocol version:** `prd-extension-protocol-v1`

**Author approval:** 2026-07-22, before any WP2--WP7 extension result was run

**Status:** prospectively frozen extension to a completed v1.x study

**Machine-readable specification:** `plan/prd_extension_protocol.json`

**Amendment ledger:** `plan/PRD_EXTENSION_AMENDMENTS.md`

## 1. Identity and separation from the completed paper

This protocol starts a new PRD-strengthening study.  It does not reopen, erase,
or silently redefine the completed v1.x paper.

The immutable v1.x baseline is:

- Git commit `70a47ec89ee474244157b6397ab9b93eece5fd45`;
- annotated tag `paper-v1x-final-20260722`;
- PDF `output/pdf/Zhang_cosmic_fate_audit_major_revision.pdf`;
- PDF SHA-256
  `d0378a4c9615c8486f71509df675790c72214d3de19d47ddae87b47e66598e62`.

The original local preregistration remains the protocol at commit
`98abc2017421f6825e8a2aa36f7cb76b5661db76` and tag `prereg-v1`.  This new
document is a prospective public extension written after the v1.x results were
known.  It must never be described as part of the original preregistration.
Once this file is pushed publicly, the public branch/PR timestamp is an
independently visible timestamp for this extension.  It is not described as a
registry-verified preregistration unless a separate registry archive is later
created and cited.

All new data products go below `runs/prd_extension/`.  The existing
`runs/gate2/`, `runs/phase2/`, and `runs/phase3/` artifacts are read-only v1.x
inputs.  No PRD-extension command may overwrite them.

## 2. Research questions and claim hierarchy

The extension has three primary questions.

1. **Calibration and power:** does the posterior fate-class statistic have the
   advertised null calibration at higher finite-simulation resolution, and
   does it acquire useful power when the CPL truth moves away from the
   `w_a=0` fate boundary?
2. **Perturbation-complete likelihood:** do the finite-redshift dark-energy
   preference and the fate-fragility result survive a full CMB-spectrum and
   growth-sensitive analysis rather than a geometry-only distance prior?
3. **Common function measure:** after replacing incompatible native coordinate
   priors with one explicitly generated function-space prior, how much of the
   fate uncertainty remains?

The claim hierarchy is fixed.

- Direction, depth, evidence, boundary behaviour, and extrapolative fate are
  reported separately.
- A result for one grammar or data combination is not promoted to a
  model-independent fate statement.
- Failure of a validation gate produces a No-Go result and a scope statement,
  not a substituted approximation presented under the failed label.
- The null, power, full-CMB, growth, and function-prior results are reported
  even when they weaken the v1.x interpretation.

## 3. Work packages and ordering

The confirmatory order is:

1. WP1 remote-environment and cross-platform equivalence checks;
2. WP2 expansion of the fitted-truth LCDM null ensemble from 100 to 500;
3. WP3 off-boundary power campaign;
4. WP4 full-CMB CPL reproduction gate;
5. WP5 perturbation-consistent BIN4 feasibility and inference;
6. WP6 growth-data availability/overlap gate and, only after a Go, inference;
7. WP7 direct common-function-prior model;
8. integrated interpretation and manuscript revision.

Software construction, tests, and data-only audits may run in parallel.  A
later inference stage may not be used to tune an earlier stage's frozen truth
grid, stopping rule, or primary endpoint.

## 4. WP1: compute environment and equivalence gate

The preferred remote environment is x86-64 Ubuntu under WSL2 or native Linux.
The environment lock, CPU/RAM inventory, package versions, and data hashes must
be written to `runs/prd_extension/environment/` before production.

Before combining old and new null mocks, the remote implementation must rerun
mock000 and fixed noisy mocks `m001`, `m025`, `m050`, `m075`, and `m100` using
the existing inputs and declared seeds.  For every cosmological parameter the
new and archived posterior means must differ by no more than `0.10` pooled
posterior standard deviations.  For `P(RIP)` and `P(heat)` the absolute
difference must not exceed the larger of `0.02` and three combined Monte Carlo
standard errors.

If any comparison fails after one documented diagnostic rerun, the old 100 and
new 400 may not be pooled.  All 500 null mocks must then be rerun in one locked
environment.  The failure and decision are retained in the amendment ledger.

## 5. WP2: 500-mock fitted-truth LCDM null campaign

### 5.1 Fixed design

- Model: flat LCDM fitted truth already stored in
  `runs/gate2/truth_lcdm_d0.json`.
- Data generator: the same Pantheon+SH0ES, DESI DR2 BAO, and Planck distance-
  prior covariance generator used for v1.x.
- Inference: identical CPL+P1 pipeline and fate classifier.
- Noisy mock indices: `1..500`.
- Existing noisy mocks retained: `1..100`.
- New noisy mocks: `101..500`.
- Generator seed stream: existing seed `42`, continued by the append-safe RNG
  replay rule.
- MCMC seed: `3000 + mock_index`, unchanged.
- mock000 remains a zero-noise mechanism diagnostic and is never counted in
  the finite null distribution.

The existing mock tree must first be copied or content-addressed into
`runs/prd_extension/null500/`; production may not append in place to the v1.x
tree.  Input hashes and the migration source are recorded before generation.

### 5.2 Primary endpoints

Let `p_obs` be the v1.x observed `P(RIP)` and let `K` be the number of the 500
noisy null mocks satisfying `P(RIP)_j <= p_obs`.

- primary depth report: `K/500`;
- finite-simulation lower-tail value: `(K+1)/(500+1)`;
- exact 95% Clopper--Pearson interval for the underlying tail probability;
- direction report: fraction with `P(heat)>0.5` and its exact interval;
- distribution diagnostic: KS statistic and p-value for `P(heat)` against
  `U(0,1)`;
- boundary budget: maximum and distribution of OTHER and boundary fractions.

No result is reported as `p=0`.  The campaign cannot stop early.  The current
`0/100` result is not treated as a prediction that `K=0` at 500.

### 5.3 Chain acceptance and exclusions

Every retained chain must satisfy the same Cobaya convergence settings used
in v1.x, contain no unresolved checkpoint, and yield a readable classified
posterior.  A failed chain is rerun with the same data and seed after the
failure is logged.  Changing the seed is allowed only after two failed runs
and must retain both failures and the replacement mapping.  No mock is
excluded because its fate probability is extreme.

## 6. WP3: off-boundary power campaign

### 6.1 Truth grid

The primary CPL truth grid is fixed at

`w_a = {-0.60, -0.30, -0.15, +0.15, +0.30, +0.60}`.

For each fixed `w_a`, all remaining baseline parameters are obtained by a
constrained D0 maximum-likelihood fit before any noisy mock at that truth is
generated.  The fitted vector, optimizer restarts, objective value, and input
hashes are frozen in a truth JSON.  This profiling makes each point a declared
local alternative; truth parameters may not be retuned after mock results are
seen.

Each truth has 100 noisy mocks plus one zero-noise Asimov diagnostic.  Truth
IDs and generator seeds are:

| Truth ID | `w_a` | generator seed |
|---|---:|---:|
| `wam060` | -0.60 | 2026072201 |
| `wam030` | -0.30 | 2026072202 |
| `wam015` | -0.15 | 2026072203 |
| `wap015` | +0.15 | 2026072204 |
| `wap030` | +0.30 | 2026072205 |
| `wap060` | +0.60 | 2026072206 |

Within truth position `j=1..6` and mock `k=1..100`, the MCMC seed is
`310000 + 1000*j + k`.  The same covariance generator, CPL+P1 inference, and
classifier are used at every point.

### 6.2 Power endpoints

For negative `w_a`, the correct direction is heat-death compatible; for
positive `w_a`, it is RIP.  At each truth the protocol reports:

- direction power: fraction assigning more than 0.5 posterior mass to the
  correct thermodynamic side;
- one-sided depth power: fraction rejected by the empirical 500-null CDF at
  `alpha=0.05` in the truth-consistent direction;
- false-sign fraction;
- median posterior class mass and central 68% interval;
- exact binomial 95% intervals for all rates;
- the complete six-point power curve, without selecting a favourable subset.

There are no separate discovery claims at the six points, so no multiplicity-
adjusted individual p-values are used.  If either outer point (`|w_a|=0.60`)
has direction power below 0.80, the paper may describe the calibration but may
not call the classifier demonstrably powerful.  Non-monotonic power beyond
binomial uncertainty triggers a model/implementation diagnostic and must be
reported.

## 7. WP4: full-CMB CPL reproduction gate

The reproduction-gate combination is the one used by the archived official
DESI DR2 CPL chains already recorded in `data/MANIFEST.md`:

- DESI DR2 all BAO;
- Pantheon+ (the non-SH0ES official comparison combination);
- Planck 2018 low-l TT `clik`;
- Planck 2018 low-l EE `clik`;
- Planck NPIPE high-l CamSpec TTTEEE;
- joint Planck + ACT DR6 lensing.

The official data/product directory is
`https://data.desi.lbl.gov/public/papers/y3/bao-cosmo-params/`.
All likelihood versions, nuisance priors, input files, and hashes must be added
to `data/MANIFEST.md` before inference.

The first full-likelihood run (`F0`) is this official flat CPL model, not
BIN4.  The gate passes only when:

- marginalized means of `w0`, `wa`, `Omega_m`, and `H0` are within `0.20`
  pooled standard deviations of the official chains;
- corresponding marginalized standard deviations agree within 10%;
- the reproduced best-fit likelihood difference relative to LCDM agrees
  within `|Delta chi2| <= 1.0`;
- all reported chains satisfy `R-1 < 0.01`, bulk ESS > 1000, and tail ESS >
  400 for `w0` and `wa`.

One documented configuration correction is allowed when it is determined
without inspecting fate classifications.  If the rerun still fails, full-CMB
inference is a No-Go and WP5 may not start.

After `F0` passes, the primary scientific run (`F1`) replaces Pantheon+ with
the Pantheon+SH0ES likelihood used by v1.x D0 while keeping DESI DR2 BAO and
the same full-CMB/lensing block.  This is the like-for-like compressed-versus-
full CMB comparison for the v1.x headline.  `F0` remains the external
reproduction result; `F1` is the primary fate result.  Neither may substitute
for the other.  An optional secondary `F2` repeats the no-SH0ES combination
only if needed to diagnose the bridge between them.

The full-CMB primary model comparison reports Wilks `Delta chi2`, AIC, BIC,
and multi-seed nested evidence using original nested weights.  MCMC fate tails
below 1% require nested verification, as in v1.x.

## 8. WP5: perturbation-consistent BIN4 gate

BIN4 may enter the full-CMB likelihood only through a validated Boltzmann
perturbation implementation.  Substituting distance priors, background-only
quantities, or the CPL full/ compressed difference is prohibited.

The implementation uses tabulated `w(a)` with PPF handling of `w=-1`
crossings.  It preserves the registered bin edges `z={0,0.3,0.7,1.5,1100}`
and the A-006 hard condition
`rho_DE/rho_m(z=1059) < 0.01`.  Because a Boltzmann solver interpolates a
table, transition handling is itself audited rather than silently assumed.
For `x=ln(a)`, each ordered left/right bin boundary at `x_e` is smoothed as
`w_left + 0.5*(w_right-w_left)*[1+tanh((x-x_e)/Delta)]`.  No other smoothing
kernel is part of the primary analysis.

Before real-data fitting, it must pass:

1. all-bin `w=-1` reproduction of native LCDM;
2. all-bin-equal reproduction of native constant-w calculations;
3. a tabulated CPL reproduction check;
4. background agreement with the exact piecewise `BackgroundW` solution to
   relative `1e-4` in `H(z)` and comoving distance over the likelihood range;
5. CMB TT and EE and matter-power agreement with the corresponding native
   limit to relative `1e-3`; because TE crosses zero, its error is normalized
   by `sqrt(C_TT*C_EE)` and must also remain below `1e-3`;
6. transition-width sensitivity at `Delta ln(a)={0.005,0.01,0.02}`.

The primary transition width is `Delta ln(a)=0.01`.  It is usable only if the
three-width posterior means differ by less than 0.10 pooled standard
deviations and `P(RIP)` differs by less than 0.02 absolute.  Otherwise the
full-CMB BIN4 result is a No-Go.  A No-Go leaves the v1.x compressed-CMB BIN4
diagnostic unchanged and visible.

The primary BIN4 full-CMB fit uses the WP4 `F1` combination and P1 intent.  The
official `F0` combination is a secondary bridge.  No other grammar or data
axis is required for the primary full-CMB claim.

## 9. WP6: growth-data gate

The full-CMB combination already contains growth-sensitive CMB lensing.  A
separate RSD/full-shape likelihood is not automatically added to DESI DR2 BAO.
As of this freeze, the public DESI DR2 product is a BAO cosmology release while
the documented public full-shape cosmology products are from DESI DR1.  A
naive addition can double-count overlapping clustering information.

The extension therefore freezes this rule:

- no hand-compiled collection of marginal `f sigma8` points;
- no addition of a full-shape/RSD likelihood to overlapping DESI BAO without
  a documented joint covariance or an official combination;
- DESI DR1 full-shape chains may first be used as an external, clearly labelled
  replication reference;
- a direct growth likelihood may proceed only after a data-only audit records
  its public files, full covariance, tracer/redshift overlap, nuisance model,
  likelihood code, and a replacement/non-overlap rule in
  `plan/GROWTH_DATA_DECISION.md`;
- that decision file must be committed and publicly timestamped before any
  fate calculation using the growth likelihood.

If no qualifying likelihood is available, WP6 is a prospective No-Go, not a
license to use covariance-free points.  This gate does not block WP4, WP5, or
WP7.

Official discovery sources for the data-only audit are:

- `https://data.desi.lbl.gov/doc/papers/dr2/`;
- `https://data.desi.lbl.gov/doc/papers/dr1/`.

## 10. WP7: direct common-function-prior model

WP7 does not importance-reweight the incompatible CPL/JBP/BA/BIN4 native
priors.  It defines a new model, `FS7`, with one proper generative measure on
functions.  Native-grammar fate probabilities remain the v1.x finite-family
sensitivity diagnostic and are not renamed as matched results.

Let `x=ln(a)`.  The free values of `w(a)` are placed at

`a = {0.40, 1/1.7, 1/1.3, 1.00, 1.50, 2.00, 4.00}`.

The early anchor is fixed at `w(0.25)=-1`, with `w(a)=-1` for `a<=0.25`.
Between the anchor and free nodes, `w(x)` is the unique clamped cubic spline
with `dw/dx=0` at both endpoints.  For `a>=4`, `w(a)` is held at the last-node
value, so both joins have zero first derivative and the model has an explicit
finite asymptotic limit.  Fate is classified analytically using that last-node
`w_inf`; the numerical tolerance is used only as a boundary flag.

For the seven free node values, define `y_i=w_i+1` and

`y ~ N(0, C)`, with
`C_ij = sigma_f^2 exp[-(x_i-x_j)^2/(2 ell^2)] + 1e-10 delta_ij`,

properly truncated to `-3 <= w_i <= 1`.  The primary hyperparameters are
`sigma_f=0.50` and `ell=0.70`.  Four predeclared one-at-a-time sensitivity
settings are:

- `(sigma_f,ell)=(0.25,0.70)`;
- `(1.00,0.70)`;
- `(0.50,0.35)`;
- `(0.50,1.40)`.

The truncated prior is sampled directly with its normalization treated
consistently; covariance regularization followed by importance weighting is
forbidden.  Spline overshoot is checked on 512 fixed log-spaced points over
`a in [0.25,4]`; a draw leaving `-3 <= w(a) <= 1` is outside the declared
function prior.  This truncation depends only on the function draw, not on the
cosmological likelihood parameters.  Sampling uses a non-centred Cholesky
parameterization.  Bayes
factors against native grammars are not reported unless the truncation
normalization and evidence calculation are independently validated.

The primary FS7 likelihood is the v1.x compressed-CMB D0 combination, so that
the function-prior effect is not confounded with WP4.  After the primary
analysis is frozen, the WP4 full-CMB combination may be a secondary cross-
check if the Boltzmann spline interface passes the WP5-style theory tests.

WP7 reports:

- prior and posterior fate composition;
- prior-to-posterior KL information at every node;
- observed-window and future-node constraints separately;
- posterior sensitivity across all five predeclared hyperparameter settings;
- boundary and OTHER fractions;
- 50 simulation-based-calibration datasets under the primary prior and
  likelihood;
- four-chain `R-hat < 1.01`, bulk and tail ESS > 400 for every node, and fate-
  probability Monte Carlo standard error below 0.01.

If the sampler fails these gates after one predeclared non-centred tuning
revision, WP7 is reported as nonconverged.  A different kernel or model is a
new amendment and cannot replace FS7 silently.

## 11. Reporting, blinding, and stopping rules

- All production seeds and truth grids are fixed above or in the machine file.
- WP2 and WP3 run to their declared counts; no optional stopping is allowed.
- Interim dashboards may show operational status but must hide aggregate fate
  endpoints until the declared batch completes.  Error logs remain visible.
- Any accidental interim inspection is recorded with date, scope, and affected
  endpoint in the amendment ledger.
- Primary and secondary/exploratory outputs are stored separately.
- Every table number must be generated from a versioned JSON artifact.
- A conclusion may be strengthened only when its relevant gate passes; failed
  or mixed gates are shown in the abstract/discussion when material.

## 12. Amendment policy

Changes after the freeze are allowed only through
`plan/PRD_EXTENSION_AMENDMENTS.md`.  Every amendment records:

1. date and author;
2. exact old and new rule;
3. trigger and scientific reason;
4. whether any affected result or aggregate endpoint had been inspected;
5. affected work packages and files;
6. whether the change is corrective, feasibility-driven, or exploratory;
7. the disposition of pre-amendment results.

Protocol errors are corrected; they are never concealed.  When a change was
made after an affected result was seen, both the original and amended analyses
are retained where computationally feasible, and the amended result is not
called preregistered.

## 13. Completion criteria

The PRD extension is complete only when:

- WP2 and WP3 reach their declared sample counts and pass artifact audits;
- WP4 passes or produces a documented No-Go;
- WP5 passes or produces a documented No-Go;
- WP6 passes its data gate or produces a documented No-Go;
- WP7 passes convergence/SBC or is reported as nonconverged;
- all results, including weakening results, are integrated into one claim
  matrix;
- code, manuscript, PDF, release, and archived artifacts resolve to one commit.

Completion of the protocol does not guarantee PRD acceptance.  It creates a
reviewable evidence package with predeclared failure paths.
