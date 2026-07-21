# A-004 — DRAFT post-hoc matched-prior sensitivity audit

**Status:** DRAFT ONLY. Post-hoc. Not signed. Not part of the frozen preregistration and not an A-001--A-003 historical rewrite.

## Trigger

The major-revision audit made explicit that the fitted grammars do **not** share a prior merely because their native coordinates use flat P1 boxes. Different dimensions, early-matter constraints, future extrapolation rules, and fate maps induce different function-space measures. Reviewers therefore need a reproducible check that separates native-coordinate prior effects from any claim about cross-grammar posterior fate sensitivity.

## Proposed change

Add a matched-prior sensitivity audit that is clearly labeled exploratory and post-hoc. The audit defines a common object before computing any matched fate summaries:

- **Common object:** the dark-energy function evaluated on a fixed scale-factor grid, `w(a_grid)`.
- **Measure:** a pilot importance-reweighting / transport measure toward a pooled Gaussian reference in that common function-summary space.
- **Inputs:** existing registered grammar definitions and fixed-seed synthetic prior samples only; no new data, no full MCMC, and no nested-sampling run.

If exact cross-grammar prior equality is not identifiable in the original native coordinates, the audit reports the limitation rather than asserting equality.

## Timing and contact with real results

- A-004 is drafted after A-001--A-003 and after the phase-3 fitted-grammar results existed.
- The draft therefore had contact with real-result context.
- It must be described as a sensitivity audit and not as a preregistered decision rule.

## Decision thresholds

A matched-prior row is admissible only if both diagnostics pass:

1. truncated effective sample size fraction `ESS / n_accepted >= 0.05`;
2. support-overlap fraction with the common reference `>= 0.20`.

Weights are normalized, reported before and after truncation, and capped by a declared quantile. Any row failing either threshold is marked **No-Go** and the matched fate probabilities are withheld (`null`) rather than forced.

## Possible consequences

- If all grammars pass, compare native and matched fate probabilities as a sensitivity pilot, not as a replacement for the main result.
- If one or more grammars fail, state that the requested cross-grammar matched prior is unsupported by the chosen summary transport and cannot adjudicate the main grammar sensitivity.
- Do not edit the existing main-text conclusions until and unless this draft is signed and a later amendment specifies exactly how it should be used.

## Sign-off placeholders

- Analyst: ____________________
- Internal reviewer: ____________________
- Date signed: ____________________
- Scope approved for manuscript text: ____________________
