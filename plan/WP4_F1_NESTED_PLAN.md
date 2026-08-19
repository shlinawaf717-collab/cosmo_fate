# WP4 F1 multi-seed nested-evidence and rare-tail plan

Status: frozen after F1 MCMC and best-fit unblinding, before any F1 nested
sample, evidence, or nested fate result exists.

## Engine and common settings

Use Cobaya 3.6.2 with PolyChordLite 1.20.1 under x86-64 WSL2 Linux. PolyChord
is selected because the 18-dimensional full likelihood has a strong slow/fast
hierarchy; the earlier six-dimensional D0 dynesty adapter must not be reused
with fixed CMB/nuisance parameters. Each run uses `nlive=500`,
`num_repeats=5d`, `precision_criterion=0.01`, clustering, original nested
weights, resumable raw output, and a frozen five-sigma truncation
(`confidence_for_unbounded=0.9999995`) for the three shared Gaussian nuisance
priors. Seeds are 2026082001, 2026082002, and 2026082003.

The four F1 MCMC blocks are retained: two slow CAMB blocks at factor 1,
`A_planck` at factor 4, and the remaining fast likelihood/`Mb` block at factor
4. One CPL-family run and one comparison run execute concurrently with four
MPI ranks each; numerical-library threads remain one. Runtime scheduling never
changes scientific settings.

## Runs per seed

Four full-likelihood runs are required for each seed:

1. full CPL+P1, to provide original-weight posterior fate mass and total CPL
   evidence;
2. RIP-stratified CPL+P1 (`wa>0`), to resolve the rare MCMC tail;
3. DECAY-stratified CPL+P1 (`wa<0`), paired with the RIP run;
4. flat LCDM.

The exact zero-width `wa=0` boundary has zero prior measure. The P1 area in the
registered `w in [-3,1]`, `wa in [-3,2]` box is 15.5. Its RIP and DECAY areas
are 4 and 11.5, respectively. Cobaya/PolyChord reports evidence relative to
the rectangular box with the P1 indicator. Conditional-prior log-evidence
corrections are therefore `ln(20/15.5)` (full CPL), `ln(8/4)` (RIP),
`ln(12/11.5)` (DECAY), and zero (LCDM). The stratified total is

`Z_CPL = (4/15.5) Z_RIP,conditional + (11.5/15.5) Z_DECAY,conditional`.

The full-CPL original-weight `P(RIP)` remains mandatory. The stratified
evidence ratio is the registered rare-tail verification and is reported next
to, not substituted silently for, the original-weight estimate. The full CPL
evidence and the RIP+DECAY recombination form an internal closure test.

## Reporting and stopping

- all 12 runs complete; no optional stopping or seed selection;
- per-run internal PolyChord errors and between-seed SDs remain separate;
- original nested weights, global ESS, RIP-tail ESS, raw class counts, and all
  four-run evidence components are retained per seed;
- the primary Bayes factor is the three-seed mean of corrected full-CPL minus
  LCDM log evidence;
- the rare-tail result reports both the three full-CPL original-weight values
  and the three stratified values, their ranges, and between-seed SDs;
- interim status exposes only process health, resume-file timestamps, and
  completion flags, never log evidence, posterior locations, or fate mass.

A bounded pilot may test installation, resume, and wall-clock throughput, but
its evidence and samples are diagnostic-only and never enter any endpoint.
