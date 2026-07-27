# PRD extension amendment ledger

Protocol: `plan/PRD_EXTENSION_PROTOCOL.md`

Machine specification: `plan/prd_extension_protocol.json`

No amendments have been made after the `prd-extension-protocol-v1` freeze.

## PRD-A001 — 2026-07-23

ID and date: PRD-A001, 2026-07-23

Author: Zhang; recorded by Codex under the author's instruction

Affected work package(s): WP1, WP2

Old rule: WP1 remote-environment equivalence checks must be completed before
the archived m001--m100 results are pooled with the new m101--m500 results.

New rule: The frozen WP1 equivalence checks are performed after the WP2
m101--m500 campaign completed.  The six registered cases, comparison
thresholds, seeds, inputs, and failure action are unchanged.  The combined
500-mock endpoint remains withheld from confirmatory interpretation until WP1
passes.  If WP1 fails after its one permitted diagnostic rerun, all 500 noisy
mocks are rerun in one locked environment as originally specified.

Trigger and scientific reason: The WP2 production campaign was run before the
absence of the required WP1 environment-equivalence artifact was recognized.
This entry preserves the actual order and prevents a post-result equivalence
check from being presented as prospectively completed.

Affected result inspected before change? yes; exact scope: the completed
501-row null ledger and completion audit, the primary lower-tail count
K=2/500 with plus-one value 3/501, the direction count 264/500, and the
old-100 versus new-400 distribution diagnostics were inspected.  No WP1
equivalence result had been generated or inspected.

Classification: corrective; post-result sequencing deviation

Pre-amendment result disposition: All WP2 chains, inputs, and audit artifacts
are retained.  The old/new pooled scientific endpoint is provisional pending
WP1.  No seed, chain, mock, endpoint, threshold, or exclusion rule is changed.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`; implementation and
result commits pending on `agent/prd-extension-wp0`.

Execution note, 2026-07-23: The six registered cases were rerun in the exact
local Mac production environment used for m101--m500, with the installed
environment matching `requirements.lock` exactly.  This local production-
environment gate returned `PASS_LOCAL_ONLY`: all six chains converged; all
frozen inputs matched; all eight compared parameters passed the 0.10
pooled-SD threshold; and both fate endpoints passed their registered
tolerances.  The closest parameter result was the m000 `w` shift at
0.092733 pooled SD.  The largest fate tolerance usage was m025 `P_RIP`,
with absolute difference 0.024696 against tolerance 0.052058.  The
conditional all-500 rerun was therefore not triggered by the local gate.
The registered x86-64 Linux cross-platform gate remains pending because
`cosmo-desktop` was offline and no remote result was substituted.  The
combined endpoint remains labelled provisional with respect to that
cross-platform gate.

## PRD-A002 — 2026-07-23

ID and date: PRD-A002, 2026-07-23

Author: Zhang; recorded by Codex under the author's instruction

Affected work package(s): WP1, WP3

Old rule: Confirmatory production follows the order WP1, WP2, then WP3, with
the registered x86-64 Linux WP1 equivalence gate completed before WP3 truth
construction and inference.

New rule: WP3 software construction, the six registered constrained truth
fits, Asimov diagnostics, and local production may proceed in the exact locked
Mac environment that produced m101--m500 after the local WP1 gate returned
`PASS_LOCAL_ONLY`.  The six truth positions, profiling rule, generator seeds,
MCMC seeds, endpoints, thresholds, and stopping rules are unchanged.  Until
the x86-64 Linux WP1 gate passes, every local WP3 scientific result is labelled
provisional.  If that gate fails after its registered diagnostic rerun, all
local WP3 inference products are invalidated for confirmatory use and WP3 is
rerun in the same unified environment selected for the required null500
rerun.

Trigger and scientific reason: The author instructed the study to proceed to
WP3 while `cosmo-desktop` remained offline.  The local production environment
is exactly locked and passed the six-case archived-versus-current equivalence
gate, but that evidence does not establish the protocol's cross-platform
x86-64 Linux equivalence claim.

Affected result inspected before change? yes; exact scope: completed WP2
null500 endpoints and diagnostics, PRD-A001, and the local six-case WP1
equivalence report were inspected.  No WP3 truth fit, Asimov classification,
noisy mock, power endpoint, or aggregate WP3 result had been generated or
inspected.

Classification: feasibility-driven; pre-WP3-result execution-order amendment

Pre-amendment result disposition: No WP3 result exists.  WP2 and local WP1
artifacts are retained under PRD-A001.  This amendment does not promote the
local WP1 result to a cross-platform pass.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`; WP3 implementation and
result commits pending on `agent/prd-extension-wp0`.

## PRD-A003 — 2026-07-23

ID and date: PRD-A003, 2026-07-23

Author: Zhang; recorded by Codex under the author's instruction

Affected work package(s): WP1, WP2, WP3--WP7

Old rule: WP1 required an x86-64 Linux rerun of six registered cases before
old and new null mocks could be pooled, and PRD-A002 provisionally conditioned
local WP3 results on that future cross-platform gate.

New rule: The x86-64 Linux comparison is retired as a blocking work package
and becomes an optional cross-platform reproducibility exercise.  The
effective environment gate is the locked production environment actually used
for the study: the Mac environment must match `requirements.lock` exactly,
record platform, package, code, and data hashes, and pass the six registered
archived-versus-current reruns at the unchanged WP1 thresholds.  That gate has
passed in `runs/prd_extension/wp1_equivalence/local_m5_audit.json`.
Consequently, WP2 pooling is technically accepted and WP3--WP7 may proceed in
the same locked Mac environment without an outstanding remote-WP1 condition.
The conditional all-500 rerun remains tied to failure of the effective local
equivalence gate; it was not triggered.  A future Linux rerun is reported as
replication evidence and cannot retroactively change inclusion rules unless it
reveals a documented implementation defect.

Trigger and scientific reason: All new WP2 inference and the planned WP3
campaign use the same local production machine, exact dependency lock, code
paths, and data products.  The registered six-case local rerun passed all
parameter and fate thresholds.  Requiring an offline second machine would test
portability rather than the comparability of the chains actually pooled in
this study, and would unnecessarily block the declared scientific work.

Affected result inspected before change? yes; exact scope: the WP2 null500
results, the old-100/new-400 diagnostics, the six-case local equivalence
chains and audit, and PRD-A001--A002 were inspected.  No WP3 truth fit, Asimov
classification, noisy mock, or power endpoint had been generated or
inspected.

Classification: feasibility-driven; post-WP2 and pre-WP3-result amendment

Pre-amendment result disposition: WP2 and the local equivalence artifacts are
retained.  The WP2 sequencing deviation remains disclosed under PRD-A001.
PRD-A002's remote-WP1 provisional condition is superseded prospectively for
WP3--WP7.  The historical frozen protocol text is retained rather than
silently rewritten.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`; implementation and
result commits pending on `agent/prd-extension-wp0`.

## PRD-A004 — 2026-07-23

ID and date: PRD-A004, 2026-07-23

Author: Zhang; recorded by Codex during protocol implementation

Affected work package(s): WP3

Old rule: For truth ordinal \(j=1,\ldots,6\) and noisy mock
\(k=1,\ldots,100\), the frozen protocol specifies MCMC seed
`310000 + 1000*j + k`.  It requires one Asimov diagnostic per truth but does
not explicitly assign those six diagnostic chains an MCMC seed.

New rule: The Asimov diagnostic for each truth uses the natural non-overlapping
`k=0` extension of the frozen formula, namely `310000 + 1000*j`.  No noisy
mock seed, truth definition, endpoint, threshold, or stopping rule changes.

Trigger and scientific reason: A deterministic sampler seed is required to
execute and reproduce the registered Asimov diagnostics.  Extending the
already frozen formula to the reserved Asimov index avoids discretionary seed
selection and cannot collide with the 600 registered noisy-mock seeds.

Affected result inspected before change? no; the six truth fits and generated
mock-input audit were inspected, but no WP3 MCMC chain, posterior
classification, Asimov result, noisy-mock result, or power endpoint existed.

Classification: corrective; pre-WP3-inference implementation clarification

Pre-amendment result disposition: The frozen truth fits and 606 generated
mock inputs are retained.  They contain no posterior inference affected by
this clarification.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`; WP3 inference runner and
result commits pending on `agent/prd-extension-wp0`.

## PRD-A005 — 2026-07-27

ID and date: PRD-A005, 2026-07-27

Author: Zhang; recorded by Codex under the author's instruction

Affected work package(s): WP7, new WP8, integrated interpretation

Old rule: The frozen extension ended its inferential work packages with WP7.
WP7 defined one common function-space model, FS7, whose final free node is at
`a=4` and whose future is held constant at `w(4)` for all `a>=4`.  That rule
made the asymptotic fate explicit but did not vary the unobserved continuation
while holding the observed history fixed.

New rule: A new WP8 future-continuation sensitivity analysis is established
after WP7 and before integrated manuscript interpretation.  WP8 leaves WP7
unchanged and retains its constant-after-`a=4` rule as one labelled baseline.
Its primary analysis takes only the converged WP7 marginal history at `a<=1`
and compares prospectively frozen continuations that preserve the present
value and, except for one limiting diagnostic, the present derivative.  It
reports every registered family separately and as an envelope; assigning
equal or post-result weights to continuation families is prohibited.  The
complete design, seeds, endpoints, validation thresholds, and interpretation
gate are frozen in `plan/WP8_FUTURE_CONTINUATION_PROTOCOL.md` and
`plan/wp8_future_continuation_protocol.json`.

Trigger and scientific reason: Review of the residual limitations after
WP1--WP7 identified that a common measure over functions through `a=4` does
not itself test the rule connecting a finite, wholly unobserved future
interval to `a=infinity`.  Histories identical over the observed domain can
have different asymptotic fates under different continuations.  WP8 isolates
that otherwise unmeasured source of fate uncertainty.

Affected result inspected before change? yes; exact scope: completed WP2 and
WP3 results, the frozen WP7 design, and WP4 input/preflight plus runtime-health
information were known.  No WP4 aggregate scientific endpoint or fate
classification was inspected, and no WP5, WP6, WP7, or WP8 inference result
exists.  No continuation-family fate result was generated before this entry.

Classification: exploratory; prospective pre-WP8-result design expansion

Pre-amendment result disposition: All existing v1.x and WP1--WP4 artifacts
remain unchanged.  WP7 remains a separately reportable common-function-prior
model.  Its constant-after-`a=4` fate result, if produced, is interpreted as
conditional on C0 rather than invalidated or overwritten by WP8.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP8_FUTURE_CONTINUATION_PROTOCOL.md`;
`plan/wp8_future_continuation_protocol.json`;
`pipeline/test_wp8_future_continuation_protocol.py`; implementation and result
commits pending on `agent/prd-extension-wp0`.

## PRD-A006 — 2026-07-27

ID and date: PRD-A006, 2026-07-27

Author: Zhang; recorded by Codex under the author's instruction

Affected work package(s): WP4 F0

Old rule: The frozen protocol required `R-1 < 0.01`, bulk ESS `> 1000`, and
tail ESS `> 400` for `w0` and `wa`, but did not state the R-1 estimator,
burn-in, ESS algorithm, repeated-pass rule, or operational stop transaction.
F0 was launched as four independent `cobaya-run --no-mpi` processes.  Under
that mode Cobaya 3.6.2 applies a within-chain four-segment R-1 separately to
each process and additionally waits for `Rminus1_cl < 0.2`, even though the
confidence-limit statistic is absent from the registered protocol gate.  The
initial driver also accepted completion only when Cobaya wrote
`converged: true` to every checkpoint.

New rule: The registered R-1 is defined as Cobaya 3.6.2's MPI-chain
multivariate estimator across the four independent chains and all 17 sampled
parameters, using a 50% row burn-in, with `R-1 < 0.01`.  The same estimator at
20% and 70% burn-in must be `< 0.02` as a sensitivity guard.  At 50% burn-in,
rank-normalized split bulk ESS must exceed 1000 and binary 5%/95% tail ESS
must exceed 400 for each of `w` and `wa`, using the frozen algorithm and
versions in `plan/WP4_F0_EXTERNAL_CONVERGENCE_POLICY.md`.  Every gate must pass
in two authoritative snapshots separated by at least 320 new complete rows in
every chain, with changed chain hashes and unchanged policy/code hashes.  The
finalizer then pauses the four Cobaya children, verifies stable files,
recomputes all gates, fsyncs the audit, and either resumes all children on
failure or terminates them on success.  It does not edit the YAML or Cobaya
checkpoints.  The confidence-limit statistic becomes secondary and cannot
block or establish the registered stop.

Trigger and scientific reason: Source inspection showed that `--no-mpi`
silently changed the intended multi-chain convergence estimator into a
stricter and different within-chain split estimator, and added an unregistered
confidence-limit stopping requirement.  The new rule fixes the meaning of the
already registered gates, retains independent-chain replication, avoids an
irrelevant multi-fold runtime penalty, and adds repeatability, burn-in
sensitivity, snapshot integrity, and reversible-stop safeguards.

Affected result inspected before change? yes; exact scope: F0 runtime health,
complete chain-row counts, Cobaya's within-chain progress R-1 values, and
read-only candidate between-chain R-1/ESS diagnostics were inspected.  The
CAMB 1.5.4 versus 1.6.6 fixed-point drift screen was also inspected.  No F0
posterior mean, marginal interval, best-fit point, likelihood value,
model-comparison statistic, fate classification, or aggregate scientific
endpoint was inspected.

Classification: corrective; post-launch and pre-scientific-endpoint
stopping-definition amendment

Pre-amendment result disposition: All original F0 chain samples, seeds,
inputs, run YAMLs, proposals, checkpoints, and driver logs are retained.  The
pre-policy diagnostic monitor is non-authoritative and none of its readings
counts toward the two required passes.  No existing sample is excluded except
by the frozen burn-in definitions.  Because no sampler configuration or
scientific rule changes, this amendment does not consume WP4's one permitted
configuration correction.  The amendment is disclosed as post-launch and is
not called preregistered.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP4_F0_EXTERNAL_CONVERGENCE_POLICY.md`;
`plan/wp4_f0_external_convergence_policy.json`; authoritative evaluator,
finalizer, activation manifest, and result commits pending on
`agent/prd-extension-wp0`.

## PRD-A007 — 2026-07-27

ID and date: PRD-A007, 2026-07-27

Author: Zhang; recorded by Codex under the author's instruction

Affected work package(s): WP7, WP8, integrated interpretation

Old rule: WP8 v1 treated a worst-case robust-side fraction across C0, C2, and
the full admissible C3 support as a primary numerical endpoint with a `0.90`
interpretation threshold.  It also thresholded `Delta_cont_RIP` and
`Delta_cont_heat`, called changes in the admitted C3 asymptote marginal an
implementation failure, and required Monte Carlo fate estimates even where
the family construction fixed them analytically.  WP7 registered a symmetric
GP node prior and global clamped spline but did not predeclare the analytic
non-identification prediction, the `ell=1.4` conditioning diagnostic, or a
past--future spline leakage test.

New rule: WP8 v1 and PRD-A005 remain immutable historical checkpoints.
`plan/WP8_FUTURE_CONTINUATION_AMENDMENT_V2.md` replaces the thresholded robust
fraction with an analytic partial-identification support set and removes all
three structurally determined interpretation thresholds.  C2 is an analytic
DS control; the unconditioned symmetric C3 measure is exactly 50/50 across the
RIP/heat boundary; any asymmetry after path-admissibility conditioning is
labelled selection-conditioned rather than a likelihood update.  C3
admissible support is computed by deterministic interval intersection on the
registered grid, with Monte Carlo retained only as verification.  Conditional
family outputs, the envelope, and the support set are always reported because
no family probabilities exist.

For WP7, `plan/WP7_ANALYTIC_PREDICTION.md` freezes the conditional prediction
that `P(RIP)` approaches one half only when the final-node prior is symmetric
and the likelihood supplies negligible information about the final-node
residual.  A half result under those conditions is interpreted as prior
symmetry plus non-identification.  The registered `ell=1.4` setting and jitter
remain unchanged; its high condition number is disclosed and it must pass the
original convergence gates.  The registered global spline also remains
unchanged, but deterministic future-node response over `a<1` is measured and
must accompany any claim that future nodes are data constrained.

Trigger and scientific reason: Analytic inspection showed that C2 fate is
constant by definition, the unconditioned C3 asymptote probability is fixed by
its symmetric prior, and a worst-case support containing both sides makes the
v1 robust threshold a structural consequence rather than an empirical
measurement.  Conditioning C3 on path admissibility can itself reweight the
asymptote and must not be confused with likelihood information.  Independent
numerical preflight also found a high-condition-number `ell=1.4` covariance
and nonzero global-spline past--future coupling.  Correcting these points
before WP7/WP8 inference prevents structural prior facts from being presented
as data-driven endpoints.

Affected result inspected before change? yes; exact scope: the algebra of the
registered WP7/WP8 priors and continuations, deterministic probe-state
admissible intervals, covariance eigenvalues/condition numbers, and spline
basis responses were inspected.  Completed WP2/WP3 results and WP4 runtime
health were already known.  No WP7 or WP8 prior simulation, likelihood,
posterior, fate classification, aggregate endpoint, or family result exists.

Classification: corrective; post-design and pre-WP7/WP8-result amendment

Pre-amendment result disposition: PRD-A005, WP8 v1, and their tests remain
versioned and are not rewritten.  No WP7/WP8 inference product is discarded
because none exists.  The v2 supplement controls future execution and
interpretation.  FS7's hyperparameters, jitter, interpolation, seeds,
likelihood, and convergence gates are unchanged.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP7_ANALYTIC_PREDICTION.md`; `plan/wp7_analytic_prediction.json`;
`plan/WP8_FUTURE_CONTINUATION_AMENDMENT_V2.md`;
`plan/wp8_future_continuation_amendment_v2.json`;
`pipeline/wp7_wp8_preflight.py`; tests and preflight result pending on
`agent/prd-extension-wp0`.

## PRD-A008 — 2026-07-27

ID and date: PRD-A008, 2026-07-27

Author: Zhang; recorded by Codex under the author's instruction

Affected work package(s): WP4, WP6, integrated interpretation

Old rule: Research question 2 promised a “full CMB-spectrum and
growth-sensitive analysis rather than a geometry-only distance prior,” even
though WP6 separately allowed the direct late-time growth likelihood to return
a data-availability or overlap No-Go.

New rule: Research question 2 asks whether the finite-redshift preference and
fate-fragility result survive a full CMB-spectrum and CMB-lensing-sensitive
analysis.  CMB lensing remains part of WP4.  A direct late-time growth
likelihood is a separate conditional WP6 extension and is run only if its
registered availability, covariance, and double-counting gate returns Go.  A
WP6 No-Go satisfies the protocol and is not described as a completed direct
growth inference.

Trigger and scientific reason: The old question promised an inference that the
registered data gate was explicitly permitted to prohibit.  Separating
full-CMB/lensing completion from direct late-time growth removes that internal
contradiction without weakening WP4 or bypassing WP6.

Affected result inspected before change? yes; exact scope: completed WP2 and
WP3 endpoints, WP4 operational health and blinded convergence diagnostics, and
the CAMB fixed-point version diagnostic were known.  No WP4 posterior mean,
interval, best fit, likelihood endpoint, fate classification, or model
comparison was inspected; no WP6 inference exists.

Classification: corrective; pre-WP4-scientific-endpoint and pre-WP6-inference

Pre-amendment result disposition: WP2, WP3, all existing WP4 samples, the
frozen F0/F1 likelihood definitions, and the WP6 data gate are unchanged.
Only the claim scope is corrected.  The original question remains visible in
the historical protocol text with an explicit supersession note.

Files and commits: `plan/PRD_EXTENSION_PROTOCOL.md`;
`plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/prd_extension_scope_amendment_a008.json`; tests and commit pending on
`agent/prd-extension-wp0`.

Every future entry must append, never rewrite, the following fields:

```text
ID and date:
Author:
Affected work package(s):
Old rule:
New rule:
Trigger and scientific reason:
Affected result inspected before change? yes/no; exact scope:
Classification: corrective / feasibility-driven / exploratory:
Pre-amendment result disposition:
Files and commits:
```

Corrections remain visible even when they weaken or invalidate a planned
analysis.  A post-result amendment is labelled post-result and is not promoted
to prospectively frozen status.
