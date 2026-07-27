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
