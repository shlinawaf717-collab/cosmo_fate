# Matched-prior audit (author-confirmed post-hoc method note)

This note records the structural audit implemented in
`pipeline/matched_prior_audit.py`. It is post-hoc, not preregistered, and does
not change the paper's frozen conclusions.

## Verdict

**GLOBAL NO-GO:** the requested exact cross-grammar matched prior is not
identified by importance reweighting of the registered native-prior draws.
Matched fate probabilities are therefore withheld for every grammar.

## Structural check

Each grammar maps its native parameters to

```text
S(theta) = [w(0.5), w(0.67), w(0.8), w(1.0), w(1.5), w(2.0), w(4.0)].
```

This is a seven-dimensional ambient vector, but the pushforward supports have
lower intrinsic dimensions:

| Grammar | Native parameters controlling `S` | Intrinsic dimension in 7D |
|---|---:|---:|
| CPL | 2 | 2 |
| JBP | 2 | 2 |
| BA | 2 | 2 |
| BIN4 | 3 (`w1,w2,w3`; `w4` lies outside this grid) | 3 |

For BIN4 the production binning function gives
`S=[w3,w2,w1,w1,w1,w1,w1]`. The largest grid redshift is `z=1`, below the
`w4` bin that starts at `z=1.5`; the early-time parameter `w4` affects the
native support condition but not this candidate summary.

The supports are different linear subspaces. Their common intersection is the
one-dimensional set of constant histories, `w(a)=c`, which has probability
zero under each continuous native prior. Consequently, none of the four
pushforward priors has a density with respect to seven-dimensional Lebesgue
measure, and no non-degenerate common target density is dominated by all four
native pushforwards.

## Why the v1 pilot is rejected

The first draft added a small diagonal term to singular native covariance
matrices and evaluated Gaussian density ratios. That operation manufactures a
full-dimensional density around each lower-dimensional support. The resulting
weights are not Radon--Nikodym derivatives of the declared native pushforward
measures. Reported overlap and ESS values therefore diagnose the artificial
regularized Gaussians, not the registered priors.

Weight truncation cannot repair this problem. ESS is meaningful only after a
valid importance ratio exists, so the corrected audit reports both ESS and
support overlap as `null`.

## What remains reported

The JSON artifact records the support dimensions, codimensions, intersection
dimension, global reason code, and fixed-seed native-prior fate frequencies for
context. Those native frequencies are not described as matched results. Every
`matched_fate` field is `null`.

## Restart conditions

A later matched-prior study needs a new estimand and construction specified
before looking at its fate outputs. Examples include:

1. an explicit common generative prior on functions together with a valid
   grammar-specific pullback or conditioning rule; or
2. a deliberately lower-dimensional common estimand, with the information
   discarded by that projection stated in advance.

Either construction needs its own support proof and sensitivity plan. It
cannot be recovered post hoc by covariance regularization of the current
native-prior samples.
