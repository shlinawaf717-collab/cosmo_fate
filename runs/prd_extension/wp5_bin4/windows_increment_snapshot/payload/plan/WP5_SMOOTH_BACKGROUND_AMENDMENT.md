# WP5 exact-smoothed background validation amendment

Status: corrective amendment approved after Mac implementation diagnostics and
before any WP5 real-data likelihood evaluation, posterior, fate probability,
or model-comparison result.

## Diagnosis

The original WP5 text simultaneously required the Boltzmann solver to evolve
the registered tanh-smoothed BIN4 history and required that history to agree
pointwise with the discontinuous piecewise `BackgroundW` target to relative
`1e-4` in `H(z)`. For finite bin jumps, smoothing changes the local integral
of `1+w` by order `Delta ln(a) * Delta w`. The Mac diagnostic measured
`H(z)` differences of `2.77e-4` for mild steps and `1.12e-3` at the archived
compressed-BIN4 posterior-mean diagnostic point, while increasing the CAMB
table from 1200 to 3600 base points changed `H(z)` by only `7.2e-11`.

The failed comparison therefore mixed implementation error with a declared
model approximation. It did not diagnose a CAMB, PPF, or table-resolution
failure: native LCDM, constant-w, and CPL table limits all passed by several
orders of magnitude.

## Corrected validation hierarchy

Before any WP5 real-data fit:

1. CAMB's tabulated-PPF background must agree with an independent high-
   accuracy integration of the **same tanh-smoothed history** to relative
   `1e-4` in `H(z)` and comoving distance over the likelihood range.
2. The exact discontinuous piecewise history remains mandatory as a separate
   model-difference diagnostic. Its signed and maximum differences in
   `H(z)`, distance, and the declared DESI BAO redshift quantities are
   reported for each registered smoothing width; they are not relabelled as
   numerical error.
3. Native LCDM, constant-w, tabulated-CPL, TT, TE, EE, lensing, and matter-
   power gates retain their original thresholds.
4. `Delta ln(a)=0.01` remains primary. The complete registered set
   `{0.005,0.01,0.02}` must be run without optional selection.
5. The posterior-width gate is unchanged: all three widths are usable only if
   posterior means differ by less than `0.10` pooled SD and `P(RIP)` differs
   by less than `0.02` absolute. Failure is WP5 No-Go.
6. The registered bin edges, tanh kernel, priors, P1 intent, A-006
   `rho_DE/rho_m(z=1059)<0.01` hard gate, full-CMB F1 likelihood, seeds, and
   convergence rules are unchanged.

No alternative smoothing kernel, width, transition centre, or favourable
subset may replace the registered three-width family. The amendment changes
only which mathematical target is used to test implementation accuracy.

## Evidential timing

Inspected before this amendment: fixed-point implementation diagnostics,
native/table limit residuals, table-resolution residuals, and smooth-versus-
step background residuals, including the already archived compressed-BIN4
posterior mean used as a diagnostic point.

Not generated or inspected: any WP5 full-likelihood value, best fit, posterior,
parameter interval, width comparison, fate endpoint, evidence, or real-data
scientific result.

This is a transparent corrective pre-inference amendment. It is not described
as part of the original local preregistration.
