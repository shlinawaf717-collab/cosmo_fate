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

## PRD-A009 — 2026-08-13

ID and date: PRD-A009, 2026-08-13

Author: Zhang; recorded by Codex under the author's instruction

Affected work package(s): WP4 F1

Old rule: The extension protocol fixed F1's data combination and the generic
`R-1`, bulk-ESS, and tail-ESS thresholds, but did not freeze F1's execution
topology, estimator details, repeated-pass separation, or stop transaction.

New rule: Before any F1 production sample, F1 is frozen as four independent
one-thread chains with seeds 4511--4514.  It replaces F0 Pantheon+ with
Pantheon+SH0ES, samples `Mb`, and retains the v1.x D0 CPL+P1 condition
`w0+wa<0`.  Its authoritative prospective stopping system applies the
18-dimensional between-chain Cobaya estimator, 20/50/70% burn-in guards,
registered `w`/`wa` ESS gates, two passes separated by 320 rows per chain,
and the reversible paused finalization procedure in
`plan/WP4_F1_EXTERNAL_CONVERGENCE_POLICY.md`.

Trigger and scientific reason: F0 established that independent no-MPI Cobaya
processes otherwise use a different within-chain split estimator and an
unregistered confidence-limit wait.  Freezing F1's intended multi-chain rule
before production prevents both an accidental runtime penalty and any
post-result choice of stopping rule.  Reinstating P1 and `Mb` makes F1 the
registered like-for-like full-CMB replacement of v1.x D0 rather than a silent
change of target.

Affected result inspected before change? no; exact scope: F0 was fully
unblinded and passed before this entry.  The F0-derived proposal covariance
was built and audited.  No F1 sample, posterior, likelihood, best fit,
model-comparison result, or fate endpoint existed or was inspected.

Classification: corrective; prospective pre-F1-production operational
definition

Pre-amendment result disposition: F0 and its audits remain unchanged.  The
17-dimensional F0 covariance is retained as a proposal only and is not
presented as an F1 result.  No F1 result is discarded because none exists.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP4_F1_EXTERNAL_CONVERGENCE_POLICY.md`;
`plan/wp4_f1_external_convergence_policy.json`; F1 configuration, driver,
monitor, evaluator, finalizer, controller, activation manifest, tests, and
freeze commit pending on `agent/prd-extension-wp0`.

## PRD-A010 — 2026-08-13

ID and date: PRD-A010, 2026-08-13

Author: Zhang; recorded by Codex under the author's instruction

Affected work package(s): WP4 F1

Old rule: F1 was frozen and launched on the local ARM64 Mac with four seeds
4511--4514. No cross-platform replacement procedure for an already started F1
candidate was defined.

New rule: An x86-64 WSL2 Linux host may replace the Mac candidate only after
all pre-production gates in `plan/WP4_F1_WINDOWS_MIGRATION_POLICY.md` pass.
The WSL2 run starts from zero with the same seeds, target, proposal, four-job
topology, and stopping rules. Mac chain samples and checkpoints are never
copied, resumed, pooled, or selectively retained. Once WSL2 production starts,
the complete WSL2 set is the sole F1 scientific chain set regardless of later
speed or result; if preflight fails before sampling, WSL2 does not start and
the original Mac candidate may continue.

Trigger and scientific reason: A faster home Windows desktop became available
minutes after Mac F1 launch. The current generated run YAMLs contain Mac
absolute paths, and mixing ARM macOS and x86 Linux segments would obscure the
numerical environment. A from-zero replacement after exact data, dependency,
CAMB, full-likelihood fixed-point, and smoke gates preserves one-platform
production and prevents post-result platform selection.

Affected result inspected before change? yes; exact scope: only Mac F1 runtime
health, elapsed time, proposal acceptance, and complete row counts during the
first minutes were inspected. At this amendment the chains contained only
initial tens of rows. No F1 posterior location, interval, likelihood value,
best fit, model comparison, fate classification, or scientific endpoint was
inspected.

Classification: feasibility-driven; post-Mac-launch and pre-WSL2-production
platform replacement rule

Pre-amendment result disposition: The Mac F1 chain files and logs are retained
as an excluded operational record if WSL2 production starts. They are not
deleted or combined. F0, the proposal audit, the scientific target, and all
stopping thresholds remain unchanged.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP4_F1_WINDOWS_MIGRATION_POLICY.md`; Windows/WSL2 task-package manifest,
environment report, preflight result, and production return archive pending.

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

## PRD-A011 — 2026-08-19

ID and date: PRD-A011, 2026-08-19

Author: Zhang; recorded by Codex under the author's instruction to continue WP4

Affected work package(s): WP4 F1 model comparison

Old rule: The extension required F1 Wilks `Delta chi2`, AIC, BIC, and
multi-seed nested evidence, but did not state the F1 optimizer initialization,
proposal metric, free-parameter count, or the nominal data count used by BIC.

New rule: Before either F1 model is optimized, freeze the Py-BOBYQA settings,
starts, chain-derived proposal metric, likelihood-component sum, `Delta k=2`,
and nominal `N=11712` convention in
`plan/WP4_F1_MODEL_COMPARISON_PLAN.md`. BIC is labelled descriptive because
the low-l likelihoods are not ordinary independent Gaussian data vectors;
nested evidence remains the separate Bayesian result.

Trigger and scientific reason: F1 MCMC has closed and its posterior and fate
tail have been unblinded, making efficient posterior-informed optimizer starts
available. Fixing their efficiency-only role and the otherwise ambiguous BIC
data count before seeing either best fit prevents a result-dependent penalty
choice while preserving the already completed MCMC endpoint.

Affected result inspected before change? yes; exact scope: the closed F1 MCMC
posterior moments and `P(RIP)` endpoint were inspected. No F1 CPL or LCDM
optimizer output, `Delta chi2`, AIC, BIC, nested evidence, or nested fate tail
exists or was inspected.

Classification: prospective post-MCMC operational definition for a still
uncomputed model-comparison endpoint

Pre-amendment result disposition: The WSL2 MCMC chains, convergence audit, and
MCMC fate endpoint remain unchanged. Optimizer starts and covariance are not
scientific endpoints and do not alter either model target.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP4_F1_MODEL_COMPARISON_PLAN.md`;
`pipeline/run_wp4_f1_bestfits.py`; tests and frozen run plan pending.

## PRD-A012 — 2026-08-19

ID and date: PRD-A012, 2026-08-19

Author: Zhang; recorded by Codex under the author's instruction to continue WP4

Affected work package(s): WP4 F1 nested evidence and sub-percent fate tail

Old rule: The extension required multi-seed nested evidence with original
weights and nested verification of MCMC fate tails below 1%, but inherited only
the six-dimensional compressed-CMB dynesty adapter. Applying that adapter to
F1 would fix the CMB and nuisance parameters and would not evaluate the
18-dimensional full-likelihood model that generated F1.

New rule: Use the full 18-dimensional CPL/16-dimensional LCDM targets with
PolyChord's slow/fast blocking. Run three fixed seeds for full CPL and LCDM,
retain original-weight fate probabilities, and add prospectively declared
RIP/DECAY stratified runs to resolve the `5.7e-5` MCMC tail. Settings, exact P1
area corrections, seed handling, closure check, and reporting are frozen in
`plan/WP4_F1_NESTED_PLAN.md` before any F1 nested sample exists.

Trigger and scientific reason: The closed MCMC endpoint contains only three
post-burn RIP rows (weight eight), while direct reuse of the old nested adapter
would answer a lower-dimensional question. Stratified evidence measures the
rare tail without relying on accidental tail visits, and the simultaneous full
CPL run preserves the protocol's original-weight estimator.

Affected result inspected before change? yes; exact scope: F1 MCMC posterior
and fate endpoints plus CPL/LCDM best fits, `Delta chi2`, AIC, and descriptive
BIC were inspected. No F1 nested sample, evidence, internal error, nested fate
probability, or regional evidence exists or was inspected.

Classification: corrective and prospective pre-nested implementation

Pre-amendment result disposition: MCMC endpoints and best fits remain
unchanged. The compressed-CMB D0 nested results remain historical comparators
and are not reinterpreted as full-likelihood evidence.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP4_F1_NESTED_PLAN.md`; nested preparation, driver, aggregation, tests,
and Windows incremental task package pending.

## PRD-A013 — 2026-08-19

ID and date: PRD-A013, 2026-08-19

Author: Zhang; recorded by Codex after explicit author approval

Affected work package(s): WP5 perturbation-consistent BIN4

Old rule: The tanh-smoothed BIN4 history evolved by CAMB had to agree with the
exact discontinuous piecewise `BackgroundW` history to relative `1e-4` in
`H(z)` and distance over the likelihood range.

New rule: Implementation accuracy is tested against an independent exact
integration of the same registered tanh-smoothed history at the unchanged
`1e-4` threshold. The discontinuous piecewise history remains a mandatory,
separately reported model-difference diagnostic at all three registered
widths. The width-posterior thresholds, spectra/power thresholds, bin edges,
kernel, P1 intent, early-DE gate, likelihood and No-Go action are unchanged.

Trigger and scientific reason: Mac development showed native LCDM,
constant-w, and CPL tabulated-PPF limits agreeing at `1e-7` or better and a
1200-versus-3600-point `H(z)` difference of only `7.2e-11`, while finite tanh
smoothing differed from the discontinuous target by `2.77e-4` even for mild
steps and `1.12e-3` at the archived BIN4 posterior-mean diagnostic point. The
old gate therefore treated a declared model approximation as numerical error.

Affected result inspected before change? yes; exact scope: implementation
limit residuals, resolution residuals, and smooth-versus-step background
diagnostics were inspected. The archived compressed-CMB BIN4 posterior mean
was used as a declared diagnostic point. No WP5 real-data likelihood, best
fit, posterior, parameter interval, fate result, evidence, or width endpoint
exists or was inspected.

Classification: corrective; post-implementation-diagnostic and pre-real-data-
inference amendment

Pre-amendment result disposition: The development diagnostic and literal-gate
failure remain visible. No result is discarded. WP5 may proceed only through
the corrected hierarchy; failure of the exact-smoothed, spectra/power, early-
DE, convergence, or three-width posterior gates remains a No-Go.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP5_SMOOTH_BACKGROUND_AMENDMENT.md`;
`plan/wp5_smooth_background_amendment_a013.json`; implementation and tests
pending.

## PRD-A014 — 2026-08-19

ID and date: PRD-A014, 2026-08-19

Author: Zhang; recorded by Codex under the author's instruction to continue
until WP7 is ready to start

Affected work package(s): WP7 FS7 execution and simulation-based calibration

Old rule: The frozen protocol specified the FS7 generative function prior,
five hyperparameter settings, 50 SBC datasets, nodewise information outputs,
and final R-hat/ESS/MCSE gates, but did not specify the normalized-truncation
sampler, SBC scalar-parameter truth domain, mock seeds, number of SBC chains,
rank construction, information estimator, real-data chain seeds, repeated-pass
transaction, or endpoint-withholding implementation.

New rule: `plan/WP7_EXECUTION_PROTOCOL.md` and its JSON companion freeze these
missing execution details before any WP7 posterior sample.  FS7 latent draws
are exact rejection draws from `N(0,I)` conditioned by the same node/spline
operator used in the external prior.  Fifty primary-prior SBC datasets use
fixed truth/noise/chain seeds and two independent chains each; real data use
four chains for every registered setting.  Nodewise KL uses fixed
prior-quantile histograms with 40 bins and 20/80-bin sensitivity, while the
final-node decomposition separately reports analytic prior correlation,
deterministic likelihood-window spline response, and KL in the conditional
future residual.  All real-data settings close only after two blinded passes
of the frozen R-hat/ESS/hidden sign-MCSE gates.

Trigger and scientific reason: Method development established that all five
targets initialize, that the normalized truncation is directly sampleable,
that `sigma_f=1` has material path rejection, that the primary final-node
multiple R2 is only 0.135, and that the registered global spline leaks future
nodes into the observed window.  Freezing execution and decomposition now
prevents a posterior-dependent sampler, information estimator, or stopping
choice.

Affected result inspected before change? yes; exact scope: deterministic
covariance eigenvalues, Cholesky residuals, spline basis responses, prior
admissibility rates, LCDM/nontrivial-background fixed points, and five Cobaya
no-sampling initialization logs were inspected.  No WP7 posterior row, prior
fate composition, posterior fate composition, node constraint, KL endpoint,
SBC rank, real-data likelihood result, or scientific fate endpoint exists or
was inspected.

Classification: corrective implementation clarification; post-method-
development and pre-WP7-inference

Pre-amendment result disposition: The original FS7 model, nodes, kernel,
hyperparameters, jitter, spline, D0 likelihood, 50-dataset count, and endpoint
thresholds remain unchanged.  The initial 4000-vs-5000 trapezoid fixed-point
failure remains recorded; the implementation now uses the exact cubic-spline
antiderivative without relaxing the frozen numerical threshold.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP7_EXECUTION_PROTOCOL.md`; `plan/wp7_execution_protocol.json`; FS7
sampler, SBC, information, monitor, controller, finalizer, tests, and frozen
run manifests pending.

## PRD-A015 — 2026-08-24

ID and date: PRD-A015, 2026-08-24

Author: Zhang; recorded by Codex under the author's instruction to continue
WP7 after all registered settings closed

Affected work package(s): WP7 FS7 post-processing and audit provenance

Old rule: The post-processing authorizer initially required each current chain
file to equal the corresponding final-stop snapshot in its entirety.

New rule: Every endpoint uses exactly the byte prefix committed by the
transactional final-stop audit.  The prefix must reproduce its registered row
count, captured-byte boundary, complete trailing newline, and SHA-256.  A
current file may have only an intact append-only suffix; the suffix is retained,
counted, disclosed, and excluded.  Any mutation or truncation inside the
audited prefix remains a hard failure.

Trigger and scientific reason: The endpoint-blind authorizer found that all
four `ell140` files were larger than their final-stop snapshots.  Operational
events showed that launchd restarted the driver in the approximately
three-second interval between driver exit and the final audit becoming
`EXTERNALLY_STOPPED`, causing an unintended checkpoint continuation.  All four
audited prefixes match exactly.  Selecting the registered stopping-time prefix
preserves the common stopping rule; using the unplanned suffix would silently
give one sensitivity setting a different sample horizon.

Affected result inspected before change? yes; exact scope: file sizes, complete
row counts, modification times, process events, byte-boundary newlines, and
SHA-256 digests were inspected.  No posterior value, location, interval,
likelihood, sign probability, fate composition, KL endpoint, or setting
comparison was read, and the failed authorizer wrote no authorization or
endpoint artifact.

Classification: corrective operational provenance; post-convergence and
pre-endpoint

Pre-amendment result disposition: All original files and the append-only
suffixes remain preserved.  No scientific result is deleted or selected after
inspection.  The registered converged prefixes remain the sole confirmatory
inputs.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP7_POSTPROCESSING_PROTOCOL.md`;
`plan/wp7_postprocessing_protocol.json`;
`plan/WP7_POSTSTOP_RACE_NOTE.md`; authorizer, reporter, and tests.

## PRD-A016 — 2026-08-24

ID and date: PRD-A016, 2026-08-24

Author: Zhang; recorded by Codex under the author's instruction to continue
WP7

Affected work package(s): WP7 post-processing authorization validation

Old rule: The v1 authorization stored the post-processing protocol identity as
`postprocessing_protocol_sha256`, while the reporter validation mistakenly
looked for `protocol_sha256`.

New rule: The reporter validates the stored field by its exact machine name.
The original authorization remains immutable; a v2 authorization must cite and
supersede its hash before any endpoint calculation.

Trigger and scientific reason: The first report invocation failed at the
authorization-identity check.  Validation occurs before chain loading, prior
regeneration, or endpoint calculation, so this is a pure provenance-key repair.
The first v2 authorization construction attempt then exposed a control-flow
regression in the supersession patch (`_setting_identity` returned `None` and
the supersession block followed an early return).  That attempt also failed
before writing an authorization or reading a posterior value; the repaired
path is covered by a synthetic v2-supersession unit test.

Affected result inspected before change? no.  No chain value, posterior
location, interval, likelihood, sign probability, fate composition, KL
endpoint, or setting comparison was read.  No endpoint or post-processing audit
file was created.

Classification: corrective machine-provenance repair; pre-endpoint

Pre-amendment result disposition: The v1 authorization is retained as a failed
historical artifact.  The scientific model, samples, stopping prefixes,
estimators, thresholds, and outputs are unchanged.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP7_POSTPROCESSING_PROTOCOL.md`;
`plan/wp7_postprocessing_protocol.json`; authorizer and reporter.

## PRD-A017 — 2026-08-24

ID and date: PRD-A017, 2026-08-24

Author: Zhang; recorded by Codex under the author's instruction to diagnose
and correct the recurring WP5 failures

Affected work package(s): WP5 perturbation-consistent BIN4

Old rule: `BIN4CAMB.set()` allowed the inherited CAMB setter to solve sampled
`theta_MC` for `H0` using the base dark-energy history, then installed the
sampled BIN4 table.  The registered early-DE exclusion was implemented only
as a downstream likelihood, and the WP5 convergence wrapper reused WP4's
model-specific `w`/`wa` candidate-gate assembly.

New rule: The sampled BIN4 table is installed during every `theta_MC`-to-`H0`
root evaluation and retained on the final `CAMBparams` object.  The identical
registered `rho_DE/rho_m < 0.01` predicate at `z=1059` is also evaluated as a
theory precondition before transfer and thermodynamics calculation, while the
existing likelihood gate is retained.  The WP5 monitor assembles its own
20-dimensional payload and gates `w1` through `w4`; it reuses only the frozen
WP4 numerical estimators.

Trigger and scientific reason: The first-start trial produced two independent
`0p005` chain exits with CAMB's fatal Fortran `thermo out of bounds` branch and
one controller exit with `KeyError: 'w'`.  Source inspection then established
that the acoustic-scale solve occurred before the dynamic dark-energy history
was installed, contrary to CAMB's explicit ordering requirement.  At the
three registered fixed diagnostic points, correcting the order changed total
likelihood chi-square by approximately `-970.92`, `-971.68`, and `-974.56`.
This is a target-implementation defect, not a convergence fluctuation.

Affected result inspected before change? yes; exact scope: process health,
exit codes, row and step counts, fatal error text, controller traceback, and
the three already-declared fixed-point implementation diagnostics.  No
posterior mean, interval, best fit, aggregate likelihood endpoint, fate
probability, width comparison, or evidence was inspected.

Classification: corrective; post-failed-start and pre-valid-WP5-inference

Pre-amendment result disposition: Every first-start sample, checkpoint, log,
and monitor artifact is preserved as one failed implementation checkpoint and
excluded from scientific and convergence calculations.  All twelve corrected
chains restart at row zero.  Widths, seeds, priors, proposal covariance,
likelihood data, numerical accuracy, early-DE threshold, and stopping policy
remain unchanged.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/wp5_theta_order_correction_a017.json`; `pipeline/wp5_camb.py`;
`pipeline/monitor_wp5_bin4.py`;
`runs/prd_extension/wp5_bin4/theta_order_correction_audit.json`;
`runs/prd_extension/wp5_bin4/failed_start_20260824/manifest.json`; corrected
tests, archived first start, and regenerated production activation complete.

## PRD-A018 — 2026-08-25

ID and date: PRD-A018, 2026-08-25

Author: Zhang; recorded by Codex under the author's explicit instruction to
stop the two computationally dominant packages and begin paper closure

Affected work package(s): WP4 F1 nested verification, WP5 perturbation-
consistent BIN4, extension completion and reporting

Old rule: WP4 F1 required three-seed full/stratified PolyChord verification of
the sparse sub-percent MCMC fate tail and full-CMB evidence.  WP5 required all
three four-chain smoothing-width campaigns to pass their repeated convergence
gates before any endpoint inspection.  The extension completion rule required
each package to pass or return its registered scientific No-Go.

New rule: The already imported WP4 F1 MCMC chains remain a full-CMB/lensing
diagnostic, subject to explicit disposition of their external-stop warning.
The sparse MCMC RIP tail remains provisional and is withheld; the unstarted
WP4 nested campaign is a computational-feasibility No-Go and produces no
evidence or rare-tail endpoint.  Corrected WP5 production is stopped while
endpoint-blind and before convergence; all partial artifacts are preserved but
excluded from scientific inference.  This is reported as a resource-
feasibility No-Go, not as evidence for or against the BIN4 model.  The paper
closes around the completed WP2/WP3 calibration and the WP7/WP8 structural
future-continuation results.

Trigger and scientific reason: The registered WP4 nested campaign alone was
planned for a 2--6 week runtime and WP5 required twelve expensive full-CMB
chains with no reliable completion date.  These calculations refine the
full-CMB rare tail and one perturbation-complete grammar, but they do not decide
the completed WP7/WP8 partial-identification result.  Continuing both would
delay a coherent, accurately scoped paper without being necessary for its
central structural claim.

Affected result inspected before change? yes for WP4, limited to the MCMC and
best-fit outputs already disclosed under PRD-A012.  For corrected WP5
production, no scientific endpoint was inspected: only blinded process health,
row/weight counts, hashes, R-hat/ESS diagnostics, and Boolean gates were
visible.  No WP5 posterior location, interval, likelihood endpoint, fate
probability, smoothing-width comparison, or evidence was generated or read.

Classification: author-directed computational-feasibility closure; post-WP4
MCMC, pre-WP4-nested, and endpoint-blind preconvergence WP5

Pre-amendment result disposition: WP4 MCMC inputs and outputs remain unchanged;
its sparse fate tail is explicitly non-reportable without the registered
nested verification.  Every corrected WP5 partial chain, checkpoint, log, and
monitor artifact is retained as an incomplete record and excluded from all
science tables and figures.  No hidden endpoint is calculated after stopping.

Files and commits: `plan/PRD_EXTENSION_AMENDMENTS.md`;
`plan/WP4_WP5_CLOSURE_DECISION.md`;
`plan/wp4_wp5_closure_decision_a018.json`;
`runs/prd_extension/wp5_bin4/resource_stop_20260825/stop_audit.json`;
manuscript and release integration pending.
