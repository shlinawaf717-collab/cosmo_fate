# A-004 — DRAFT post-hoc matched-prior structural audit

**Status:** DRAFT ONLY. Post-hoc. Not signed. Not part of the frozen
preregistration and not an A-001--A-003 historical rewrite.

## Trigger

The major-revision audit made explicit that flat P1 boxes in native coordinates
do not define a shared prior across fitted grammars. Dimensions, early-matter
conditions, future extrapolations, and fate maps differ. A proposed
summary-space importance transport was examined as a possible sensitivity
check.

## Proposed change

Record the structural support audit and its **GLOBAL NO-GO** result. Do not add
matched fate probabilities to the manuscript.

The candidate common object was the seven-vector `w(a_grid)` on
`a_grid = [0.5, 0.67, 0.8, 1.0, 1.5, 2.0, 4.0]`. CPL, JBP, and BA occupy
different two-dimensional supports in this ambient space; BIN4 occupies a
four-dimensional support. Their common intersection consists of constant
histories and has native-prior probability zero.

Therefore a full-dimensional pooled Gaussian cannot be reached by valid
importance reweighting of any registered native pushforward. Adding diagonal
covariance regularization changes the measures and creates artificial overlap;
it is not an exact or approximate matched-prior proof for the registered
priors.

## Timing and contact with real results

- A-004 was drafted after A-001--A-003 and after the phase-3 fitted-grammar
  results existed.
- It had contact with real-result context.
- It remains a method-limit audit, not a preregistered decision rule.

## Gate order and decision

1. Check support geometry and absolute continuity.
2. Only if that gate passes, compute overlap, weights, truncation, and ESS.

Gate 1 fails. ESS and overlap thresholds are therefore inapplicable and are
withheld rather than used to rescue the construction. All grammar rows are
marked `no_go=true` and `matched_fate=null`.

## Consequence for the paper

- Preserve the existing statement that native flat coordinate priors are not
  directly comparable across grammars.
- Do not claim that matched-prior sensitivity has been quantified.
- If the study is restarted, preregister an explicit common generative
  function prior and valid grammar-specific pullbacks, or declare a narrower
  lower-dimensional estimand and its information loss.

## Sign-off placeholders

- Analyst: ____________________
- Internal reviewer: ____________________
- Date signed: ____________________
- Scope approved for manuscript text: ____________________
