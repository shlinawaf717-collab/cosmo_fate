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

## Remaining workload if the corrective route is approved

1. exact-smoothed analytic background implementation and high-resolution
   table convergence tests: 2--4 days;
2. dynamic Cobaya/CAMB BIN4 theory adapter and parameter plumbing: 1--2 weeks;
3. formal `lmax=4000` LCDM/constant-w/CPL TT/TE/EE/matter-power gates: 3--7 days;
4. full-likelihood initialization, early-DE rejection and proposal preflight:
   3--7 days;
5. primary plus three-width multi-chain inference on Windows: 2--5 weeks;
6. convergence, width-sensitivity, fate and paper audits: about 1 week.

Current completion on the corrective route is approximately 20--25%. Under
the literal route, the core feasibility question is already answered No-Go and
only the formal closure audit and manuscript disposition remain.
