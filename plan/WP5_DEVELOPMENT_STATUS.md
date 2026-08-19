# WP5 Mac development status

Date: 2026-08-19

Status: development interface passes native limits; the literal piecewise
background gate was blocked before any real-data fit and is superseded by the
author-approved PRD-A013 exact-smoothed validation hierarchy.

## Completed in the first development pass

- implemented the registered three-transition BIN4 history in `x=ln(a)` with
  the frozen tanh kernel and `Delta ln(a)={0.005,0.01,0.02}`;
- constructed deterministic dense CAMB tables ending exactly at `a=1`;
- connected the table to CAMB 1.6.6 `DarkEnergyPPF`, including histories that
  cross `w=-1`;
- added constant-bin and tabulated-CPL machinery limits;
- added exact piecewise density/background diagnostics and the A-006
  early-dark-energy calculation;
- ran a reduced-`lmax` Mac development preflight without a real-data fit.

## Development results

The tabulated machinery is not the problem. Native-vs-table checks give:

| limit | max background error | max spectrum/power error | result |
|---|---:|---:|---|
| LCDM | `2.2e-16` | `5.7e-8` | PASS |
| constant `w=-0.9` | `3.2e-14` | `3.0e-11` | PASS |
| CPL `(-0.85,-0.60)` | `1.5e-7` | `3.3e-7` | PASS |

For the archived compressed-BIN4 posterior-mean diagnostic point, however,
the registered primary smoothing width differs from the exact discontinuous
piecewise background by:

- maximum relative `H(z)` difference: `1.1218e-3`;
- maximum relative distance difference: `1.8331e-5`;
- maximum relative `H(z)` difference at the declared DESI BAO redshifts:
  `6.4533e-4` (near `z=0.706`).

The frozen background threshold is `1e-4`, so the literal gate fails. A milder
step case still gives `2.7691e-4` globally and `1.5303e-4` at a DESI redshift.
Increasing the base table from 1200 to 3600 points changes `H(z)` by only
`7.2e-11` and distance by `2.4e-12`. The failure is therefore the finite model
difference between a tanh-smoothed history and an exact step at the transition,
not CAMB interpolation resolution.

## Decision boundary

No real-data BIN4 likelihood has been evaluated. Two scientifically distinct
dispositions were considered:

1. apply the literal `1e-4` exact-piecewise gate and close WP5 as a documented
   No-Go; or
2. append a corrective amendment before any real-data fit: validate CAMB
   against the exact *smoothed* background at `1e-4`, retain the measured
   smoothed-versus-step difference as a model diagnostic, and let the already
   registered three-width posterior sensitivity gate decide usability.

The author approved the second route on 2026-08-19. It is not a numerical
relaxation: it changes the validation target to the same smooth model whose
perturbations CAMB evolves. PRD-A013 records this explicitly because the
original text says "exact piecewise".

## Progress after PRD-A013

The corrected route has now completed:

- independent exact-smoothed dark-energy density, `H(z)`, and distance
  reconstruction, including CAMB's exact massive-neutrino non-DE density;
- all six exact-smoothed checks (two histories times three widths), with
  `H(z)` residuals between `5e-10` and `1e-8`;
- the formal `lmax=4000`, lens-potential-accuracy 4, mead2016 LCDM,
  constant-w, and CPL limits for TT/TE/EE, lensing PP, and matter power;
- a dynamic Cobaya `BIN4CAMB` transfer theory accepting `w1..w4` at every
  sampled point;
- three frozen full-F1 likelihood configs, P1 `w4<0`, and the A-006
  early-DE likelihood;
- no-sampling initialization of all three widths through DESI DR2,
  Pantheon+SH0ES, both low-l likelihoods, NPIPE, and ACT lensing;
- a positive-definite 20-D block proposal built from the converged F1 shared
  parameters and the archived compressed-BIN4 node covariance. Cross-model
  covariance blocks are zero by construction.

The no-sampling smoke evaluated one initial real-data likelihood point per
width after amendment/config freeze. It produced no chain, posterior, fate
quantity, or aggregate scientific endpoint.

## Remaining workload

1. freeze the 12-chain production topology, seeds, 20-D external convergence
   estimator, repeated-pass rule, and finalizer: 3--5 days;
2. build and validate the Windows task increment plus a bounded throughput
   pilot: 2--4 days;
3. run three widths times four chains on Windows: approximately 2--5 weeks;
4. convergence, early-DE rejection, width-sensitivity, fate and paper audits:
   about 1 week.

Current completion on the corrective route is approximately 45--50%. No WP5
posterior or fate result exists yet.
