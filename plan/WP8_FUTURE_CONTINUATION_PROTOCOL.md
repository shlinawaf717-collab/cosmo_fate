# WP8 future-continuation sensitivity protocol

**Protocol version:** `wp8-future-continuation-v1`

**Author approval:** 2026-07-27T11:19:18+08:00

**Status:** prospectively frozen before any WP8 construction, posterior
continuation draw, fate classification, or aggregate endpoint

**Machine-readable specification:**
`plan/wp8_future_continuation_protocol.json`

**Parent amendment:** `PRD-A005` in
`plan/PRD_EXTENSION_AMENDMENTS.md`

## 1. Question and scope

WP8 asks whether the extrapolative fate conclusion is identified by the
posterior history at and before the present, or instead by the rule used to
continue that history into the unobserved future.

WP8 does not alter WP7.  The FS7 rule that holds `w(a)` constant after `a=4`
is retained as one explicitly labelled baseline continuation.  WP8 adds a
separate sensitivity analysis; it does not rewrite the original
`prd-extension-protocol-v1` or present itself as part of its 2026-07-22
freeze.

The primary source is the converged WP7 FS7 posterior under the registered
compressed-CMB D0 likelihood.  Only the marginal posterior history at
`a<=1`, including the present value and left derivative, is carried into
WP8.  The WP7 nodes at `a>1` are treated as part of WP7's future-continuation
choice, not as observations.  If the primary WP7 run is nonconverged, WP8 is
a No-Go; no different posterior may be substituted under the WP8 label.

All WP8 outputs go below
`runs/prd_extension/wp8_future_continuation/`.  No WP8 command may overwrite
WP7 or v1.x artifacts.

## 2. Common boundary information

Let `x=ln(a)`.  For each retained WP7 posterior draw, define

- `w1 = w(x=0)`;
- `s1 = dw/dx |_(x=0-)`, the derivative from the observed-history side.

Every C2/C3 continuation begins at `a=1`, is continuous in both `w` and
`dw/dx`, and leaves all predictions for `a<=1` unchanged.  C1 is the
explicitly labelled derivative-discontinuous limiting diagnostic.

For a finite asymptote `w_inf` and relaxation scale `tau`, the registered
smooth continuation is

`w(x) = w_inf + [A + B*x] exp(-x/tau)`,

where

`A = w1 - w_inf`

and

`B = s1 + A/tau`.

This construction satisfies `w(0)=w1`, `dw/dx(0)=s1`, and
`w(x)->w_inf` as `x->infinity`.

## 3. Registered continuation families

All families and all sensitivity settings are reported.  No family is
selected or dropped because of its fate result.

### C0: frozen FS7 baseline

Use the complete registered FS7 spline through `a=4`, then hold
`w(a)=w(4)` for `a>=4`.  This reproduces WP7's original continuation rule
and is not re-labelled as data identified.

### C1: present-constant continuation

Set `w(a)=w1` for `a>=1`.  This is continuous in `w` but generally not in
the derivative, so it is retained only as a transparent limiting diagnostic
and is excluded from the C1-continuous robust-agreement endpoint.

### C2: relaxation to Lambda

Use the common smooth formula with `w_inf=-1` and report all

`tau = {0.5, 1.0, 2.0}`

in units of `ln(a)`.

### C3: matched free asymptote

Use the common smooth formula with the same three `tau` values.  Draw

`w_inf + 1 ~ Normal(0, 0.5^2)`

properly truncated to `-3 <= w_inf <= 1`.  The future-asymptote draw is
independent of the likelihood and of the WP7 posterior conditional on the
registered bounds.

No equal weights across C0--C3 are interpreted as model probabilities.
WP8 reports the families separately and as an envelope.  Model averaging
over continuation families is prohibited unless a new prospective amendment
defines and justifies family prior probabilities.

## 4. Function admissibility and deterministic seeds

For C2 and C3, evaluate every continuation on 512 fixed log-spaced points
over `a in [1, 10^6]`.  A draw is admissible only if
`-3 <= w(a) <= 1` on that grid.  Rejection depends only on the declared
future function and is recorded by family and `tau`.

The primary Monte Carlo size is 100,000 continuation draws for every
stochastic C3 setting.  The seed formula is

`202607270800 + 10*tau_ordinal + replicate_ordinal`,

with `tau_ordinal=1,2,3` corresponding to `0.5,1.0,2.0` and the primary
`replicate_ordinal=1`.  A second replicate with ordinal 2 is run only for
the predeclared Monte Carlo reproducibility audit, not selected after seeing
the first result.

There is no optional stopping.

## 5. Fate calculation

For C0, use the frozen WP7 analytic classifier based on its last-node
asymptote.  For C1--C3, use the registered finite-limit analytic criteria:

- `w_inf < -1`: RIP;
- `w_inf = -1`: DS;
- `w_inf > -1`: DECAY;
- non-positive asymptotic dark-energy density, if encountered: DECAY.

The `0.01` neighbourhood of `w_inf=-1` is a boundary flag only and never
changes the physical label.  CRUNCH and OTHER remain available audit labels
for an implementation failure or an inadmissible background; they are not
silently reassigned.

## 6. Primary endpoints

WP8 reports:

1. `P(RIP)`, `P(DS)`, `P(DECAY)`, `P(CRUNCH)`, `P(OTHER)`, and
   `P(heat)=P(DS)+P(DECAY)` for C0, C1, every C2 `tau`, and every C3 `tau`;
2. the minimum and maximum `P(RIP)` and `P(heat)` across all registered
   continuation settings, without assigning family probabilities;
3. `Delta_cont_RIP = max P(RIP) - min P(RIP)` and the corresponding
   `Delta_cont_heat`;
4. the fraction of posterior observed-history draws whose thermodynamic side
   is unchanged across C0, every C2 setting, and every admissible C3
   continuation over the full registered `w_inf in [-3,1]` support; this is
   the robust-identification fraction, not a Monte Carlo family average;
5. prior and posterior fate composition for the independent C3 asymptote
   measure;
6. continuation rejection, boundary, and OTHER fractions;
7. Monte Carlo standard errors and the absolute difference between the two
   registered C3 replicates;
8. KL information at the present boundary and the future-asymptote
   information statement.  Since C3 `w_inf` is likelihood independent by
   construction, any non-zero likelihood update of its marginal distribution
   beyond Monte Carlo error is an implementation failure.

No logarithm of an observed zero is reported without a finite Monte Carlo
upper limit.

## 7. Validation and interpretation gates

Before classification, the implementation must pass:

1. C0 reproduces the archived WP7 fate composition to absolute `1e-10`;
2. every C2/C3 function matches `w1` and `s1` at `a=1` to absolute
   `1e-10`;
3. changing only the continuation leaves every evaluated observable and
   log-likelihood contribution at `z>=0` unchanged to absolute `1e-8`;
4. the C3 asymptote sampler passes normalization and fixed-seed replay tests;
5. fate-probability Monte Carlo standard error is at most `0.002`;
6. the two C3 replicates agree in every fate probability within the larger of
   `0.005` and three combined Monte Carlo standard errors.

Failure after one documented implementation correction is a WP8 No-Go.

The interpretation gate is fixed:

- if `Delta_cont_RIP > 0.10`, `Delta_cont_heat > 0.10`, or the robust-side
  fraction is below `0.90`, the manuscript may not report a single
  continuation-unqualified fate probability;
- it must instead report conditional family results and the registered
  continuation envelope;
- disagreement among valid families is a scientific result, not a failed
  validation gate.

## 8. Secondary full-CMB cross-check

Only after the primary WP8 output is frozen may the validated WP7
full-CMB secondary posterior be used as a cross-check.  It must use the same
families, `tau` values, asymptote measure, seeds, endpoints, and gates.
Absence of a validated full-CMB FS7 posterior is reported as not run and does
not invalidate the primary WP8 analysis.

## 9. Required release artifacts

The release must contain:

- a source-posterior hash inventory;
- the extracted `(w1,s1)` ledger or a content-addressed equivalent;
- continuation configuration and seed manifest;
- per-family and per-setting results;
- validation, Monte Carlo, boundary, rejection, and duplicate audits;
- the interpretation-gate decision;
- code and environment hashes;
- a manuscript table that distinguishes observed-history information,
  continuation assumptions, and conditional fate results.

WP8 is a kinematic continuation audit.  It does not establish the
microphysical stability or covariant-field-theory realizability of every
admissible `w(a)` path; that limitation remains explicit.
