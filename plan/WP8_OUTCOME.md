# WP8 future-continuation outcome

Outcome date: 2026-08-24

Status: **PASS.** WP8 used the converged primary WP7 audited prefixes, exactly
reproduced the WP7 C0 fate endpoint, passed every registered numerical and
Monte Carlo gate, and returned a fully two-sided partial-identification result.
No continuation-family probability, family model average, or full-CMB
secondary result was calculated.

## Source posterior

The source contains 96,658 post-burn rows with native Metropolis weight
308,657.  It carries only the present boundary state `(w1,s1)` into the
alternative continuations; `fs7_w7` is retained solely for the labelled C0
reproduction and per-history support union.  The weighted boundary-state means
are `w1=-0.94378` and `s1=0.09312`.

C0 reproduces the archived WP7 primary fate composition at exact reported
precision: `P(RIP)=0.50631`, `P(heat)=0.49369`, and boundary fraction
`0.01685`.

## Conditional continuation results

| family | continuation | P(RIP) | P(heat) | role |
|---|---|---:|---:|---|
| C0 | registered FS7 through `a=4`, then constant | 0.50631 | 0.49369 | WP7 baseline |
| C1 | hold the present value constant | 0.19716 | 0.80284 | derivative-discontinuous diagnostic |
| C2 | smooth relaxation to `w_inf=-1`, `tau=0.5` | 0 | 1 | deterministic DS |
| C2 | smooth relaxation to `w_inf=-1`, `tau=1.0` | 0 | 1 | deterministic DS |
| C2 | smooth relaxation to `w_inf=-1`, `tau=2.0` | 0 | 1 | deterministic DS |
| C3 | matched free asymptote, `tau=0.5` | 0.49950 | 0.50050 | primary MC replicate |
| C3 | matched free asymptote, `tau=1.0` | 0.50037 | 0.49963 | primary MC replicate |
| C3 | matched free asymptote, `tau=2.0` | 0.49980 | 0.50020 | primary MC replicate |

All C2 source histories and all 600,000 C3 proposals across the two replicates
were admissible.  C3 fate MCSE is about `0.00158` and every replicate
comparison passes its frozen tolerance.  The C3 values remain at the symmetric
asymptote measure's half point; they are not a likelihood posterior update.

The descriptive registered envelope is

- `P(RIP)` from `0` to `0.50631`, span `0.50631`;
- `P(heat)` from `0.49369` to `1`, span `0.50631`.

These extrema summarize conditional families.  They are not an interval with
a probability distribution over its points.

## Partial identification

For every source posterior history, the registered admissible continuation
support reaches both thermodynamic sides:

| support set | native-weight fraction |
|---|---:|
| `{RIP}` | 0 |
| `{heat}` | 0 |
| `{RIP,heat}` | 1.00000 |
| `empty/invalid` | 0 |

For `tau=0.5` and `1.0`, every C3 history admits the complete registered
`w_inf in [-3,1]` range.  For `tau=2.0`, 99.027% of native weight admits the
complete range; the remaining intervals narrow, but every one still crosses
`w_inf=-1`.  The two-sided conclusion therefore does not depend on Monte Carlo
family averaging or on a rare rejected path.

## Scientific interpretation

WP8 isolates the extrapolation problem more directly than WP7.  The
observed-history posterior and every `z>=0` prediction are held fixed while
only the unobserved future continuation is changed.  Valid registered
continuations of the same present history can then yield RIP, DS, or DECAY.
Consequently the thermodynamic side of the infinite future is not identified
by the finite-redshift history under this continuation class.

This is stronger and more specific than saying that two parameterizations give
different answers.  WP7 showed sensitivity to the function-prior measure and
past--future covariance.  WP8 shows that even after conditioning on the same
observed-history draw, the future grammar itself supplies information that the
data do not contain.

The result does **not** establish that all continuations are equally probable,
microphysically stable, or realizable by a covariant field theory.  WP8 assigns
no probabilities across C0--C3.  Its supported conclusion is partial
identification: the registered observations do not select a unique
thermodynamic side without an additional physical continuation assumption.

## Validation and provenance

- C0 reproduction maximum absolute error: `0`;
- boundary value/derivative errors: below `4.5e-16`;
- past-history, observable, and likelihood differences: `0` by the registered
  identical `a<=1` branch;
- analytic support membership: exact agreement with direct 512-point checks;
- source ledger: 96,658 unique `(chain,row)` entries;
- all six C3 seed/ledger recomputations: exact;
- release and independent completion audits: PASS.

Machine-readable artifacts:

- `runs/prd_extension/wp8_future_continuation/wp8_endpoints.json`;
- `runs/prd_extension/wp8_future_continuation/wp8_audit.json`;
- `runs/prd_extension/wp8_future_continuation/completion_audit.json`;
- `runs/prd_extension/wp8_future_continuation/source_inventory.json`;
- `runs/prd_extension/wp8_future_continuation/source_history.csv.gz`.
