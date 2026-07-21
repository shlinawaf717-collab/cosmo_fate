# Matched-prior audit (DRAFT post-hoc method note)

This note describes the reproducible pilot implemented in `pipeline/matched_prior_audit.py`. It is a post-hoc sensitivity audit, not a preregistered result and not a change to the paper's frozen conclusions.

## Method

The audit samples each registered P1 native prior with a fixed random seed, applies the grammar's early-time support condition, and maps accepted draws into a common function-summary vector:

```text
S(theta) = [w(0.5), w(0.67), w(0.8), w(1.0), w(1.5), w(2.0), w(4.0)].
```

The public object being matched is therefore the distribution of `S(theta)`, with Lebesgue measure approximated by deterministic Monte Carlo draws from each grammar's native coordinate support. The pilot constructs a pooled Gaussian reference in this summary space and importance-reweights each grammar toward that reference. This is a transport diagnostic, not proof that the full function-space priors are identical.

## Diagnostics and No-Go conditions

For every grammar the JSON output reports:

- native fate probabilities;
- matched fate probabilities when diagnostics pass;
- accepted sample count;
- raw and truncated effective sample size (ESS);
- ESS fraction;
- maximum raw and truncated normalized weight;
- support-overlap fraction;
- truncation quantile and cap;
- warnings.

A matched row is **No-Go** when either `ESS / n_accepted < 0.05` or support overlap is below `0.20`. In that case the matched fate vector is left `null`; the audit refuses to manufacture a comparable number from inadequate support.

## Assumptions

1. The chosen grid is a sufficient low-dimensional summary for a reviewer-checkable pilot.
2. The pooled Gaussian reference is a transparent common target, not a unique or physically privileged prior.
3. Synthetic fixed-seed prior samples are acceptable because this audit tests prior geometry only and does not touch new data.
4. Truncation regularizes extreme weights and is reported as part of the result.

## Interpretation

Passing rows may be read as: "under this explicitly declared summary-space transport, native prior fate probabilities change to the reported matched values." Failing rows mean the common target is not supported well enough by that grammar's native prior sample, so the cross-grammar comparison is not identifiable under this pilot. Either outcome is compatible with the manuscript's existing claim that native flat coordinate priors are not directly comparable across grammars.
