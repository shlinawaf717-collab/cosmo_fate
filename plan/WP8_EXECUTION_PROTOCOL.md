# WP8 future-continuation execution protocol

Status: **implementation details frozen after WP7 closure and before any WP8
continuation endpoint, support-set fraction, C1 fate composition, C2
admissibility fraction, or C3 draw was calculated.**

Parents: `WP8_FUTURE_CONTINUATION_PROTOCOL.md` v1 and its corrective
`WP8_FUTURE_CONTINUATION_AMENDMENT_V2.md`.  This document resolves mechanical
pooling, pairing, and artifact details left open by those documents.  It does
not change a continuation family, prior, tau, bound, seed, endpoint, or
validation tolerance.

## Source identity and boundary extraction

The only source is the audited-prefix primary WP7 posterior already used in
`wp7_endpoints.json`.  Its four chains are cut at the byte counts and SHA-256
digests in `postprocessing_authorization_v2.json`, then burned by 50 percent
of complete rows per chain and pooled with their native integer Metropolis
dwell weights.  A mismatch is a hard failure.

For every retained row:

- `w1` is `fs7_w4`, the registered node at `a=1`;
- `s1` is the exact derivative at `x=ln(a)=0` of the registered global
  clamped cubic spline, evaluated from the observed-history side;
- `c0_winf` is `fs7_w7`, retained only to reproduce the labelled C0 baseline
  and its per-history support-set member.

The release contains a deterministic gzip-compressed CSV ledger with these
three values, the native dwell weight, chain number, and retained row number.
The gzip timestamp is fixed to zero and its SHA-256 is reported.

## Native-weight endpoints

C0, C1, all C2 settings, and the analytic partial-identification support set
use every retained source row with its native dwell weight.  C0 must reproduce
the archived WP7 primary fate composition to absolute `1e-10` before any WP8
artifact is accepted.  C1 uses `w_inf=w1` and remains explicitly diagnostic.

For C2 and C3, the registered 512 points are uniform in `x=ln(a)` from zero
to `ln(10^6)`.  At fixed `(w1,s1,tau)`, write the continuation as

`w(x) = alpha(x) + beta(x) w_inf`.

The admissible `w_inf` interval is the intersection of `[-3,1]` with every
linear interval implied by `-3 <= w(x) <= 1`.  The implementation handles the
zero coefficient at `x=0` separately and cross-checks analytic intervals
against direct grid evaluation in synthetic tests.  C2 fate composition is
reported conditional on admissibility, alongside the native-weight rejection
fraction.  An all-rejected C2 setting is a hard failure.

The partial-identification category for a source row is the union of the
thermodynamic sides reached by its C0 member, every admissible C2 setting, and
the complete C3 admissible interval at every tau.  Exact `w_inf=-1` belongs to
the heat side.  A category is `empty/invalid` only if no registered member is
admissible; because C0 is a validated member, any such row is a hard failure.
No threshold is applied to the aggregate categories.

## C3 Monte Carlo pairing

Each registered C3 `(tau, replicate)` contains exactly 100,000 proposals.
The source histories are the deterministic inverse-weight empirical quantiles
at `(i+0.5)/100000`, `i=0..99999`, in fixed chain and retained-row order.
This systematic expansion introduces no extra random seed and is identical
for every C3 setting.

For each proposal, `w_inf` is drawn independently from the registered
truncated Normal using inverse-CDF sampling and NumPy `PCG64` with the v1 seed
formula.  A proposal is retained exactly when `w_inf` lies in the analytic
admissible interval for its paired history.  Fate composition, boundary
fraction, and Bernoulli MCSE are reported among accepted proposals; rejection
is reported against all 100,000 proposals.  These are labelled
selection-conditioned and never described as a likelihood update.

The two replicates are both reported.  Their fate probabilities must agree
within the larger of `0.005` and three combined Monte Carlo standard errors.
The unconditioned C3 measure is reported analytically as 0.5 RIP / 0.5 heat,
with the realized proposal composition retained only as a sampler audit.
For every tau and replicate, analytic interval membership is checked against
direct evaluation of the registered 512-point path at 512 proposal indices
spaced deterministically across the complete proposal order.

## Invariance and release transaction

Alternative continuations use the unmodified registered FS7 history for
`a<=1`.  Boundary value and derivative matching are tested at `1e-10`; direct
grid equality of the source and alternative histories for `a<=1` is tested
at `1e-12`.  Since every registered likelihood observable has `z>=0`, this
identity makes its prediction vector and likelihood contribution invariant;
the release records this as an identity-by-construction gate, not as evidence
about the future.

The reporter is authorized only after its protocol, source hashes, code, and
synthetic tests are committed and the result directory contains no endpoint.
It writes once, refuses overwrite, and produces:

- `source_history.csv.gz` and its hash inventory;
- `wp8_endpoints.json`;
- `wp8_audit.json`;
- a later prose outcome that cannot change the machine endpoint.

No full-CMB secondary cross-check is part of this primary transaction.
