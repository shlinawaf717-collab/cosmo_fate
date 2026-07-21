# A-004 — post-hoc matched-prior structural audit

**Status:** Author-confirmed audit record, 2026-07-21. Post-hoc and not a
preregistered amendment. It does not alter A-001--A-003, the frozen analysis,
or any reported posterior result.

## Trigger

The major-revision audit made explicit that flat P1 boxes in native coordinates
do not define a shared prior across fitted grammars. Dimensions, early-matter
conditions, future extrapolations, and fate maps differ. A proposed
summary-space importance transport was examined as a possible sensitivity
check.

## Candidate common object

The proposed object was the seven-vector `w(a_grid)` on
`a_grid = [0.5, 0.67, 0.8, 1.0, 1.5, 2.0, 4.0]`. CPL, JBP, and BA occupy
different two-dimensional supports in this ambient space; BIN4 occupies a
four-dimensional support. Their common intersection consists of constant
histories and has native-prior probability zero.

## Decision

**GLOBAL NO-GO.** A full-dimensional pooled Gaussian cannot be reached by
valid importance reweighting of any registered native pushforward. Adding
diagonal covariance regularization changes the measures and creates artificial
overlap; it is not an exact or approximate matched-prior construction for the
registered priors.

The structural support and absolute-continuity check precedes overlap, weight
truncation, and ESS. Because that first gate fails, all grammar rows are marked
`no_go=true`, all `matched_fate` values are `null`, and ESS/overlap values are
withheld.

## Timing and consequence

A-004 was performed after A-001--A-003 and after phase-3 results existed. It
therefore had contact with real-result context and is reported only as a
post-hoc method-limit audit. Existing conclusions remain unchanged. A future
matched-prior study would need an explicit common generative function prior
with valid grammar-specific pullbacks, or a preregistered lower-dimensional
estimand with its information loss stated in advance.

## Record

- Analyst/author: Jiacheng Zhang
- Date confirmed: 2026-07-21
- Scope: method-limit audit and reviewer-facing reproducibility note only
- Manuscript use: No-Go statement; no matched fate probabilities
