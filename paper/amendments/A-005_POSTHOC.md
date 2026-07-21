# A-005 — finite-limit fate semantics correction

**Date:** 2026-07-21
**Status:** author-confirmed corrective post-hoc amendment
**Identity:** not preregistered; correction of an A-003 implementation error

## Error

A-003 used the interval `|w_inf + 1| <= 0.01` as a de Sitter fate class.  That
is not physically correct.  For positive persistent dark energy, every
constant or finite-limit phantom future with `w_inf < -1` reaches a Big Rip in
finite proper time, including `-1.01 < w_inf < -1`.  Likewise, a finite-limit
future with `w_inf > -1` is not de Sitter.  Exact de Sitter asymptotics occupy
the boundary `w_inf = -1`.

## Correction

For parametrizations with a finite future limit:

- `RIP` iff `w_inf < -1` and the dark-energy density is positive;
- `DS` iff `w_inf = -1` and the dark-energy density is positive;
- `DECAY` iff `w_inf > -1` (or no positive persistent dark-energy component).

The registered value `epsilon = 0.01` is retained only as a
boundary-adjacent flag, `|w_inf + 1| <= epsilon`.  It no longer changes the
physical fate label.  Divergent-future CPL and JBP samples continue to use the
original numerical classifier.

## Scope and consequences

The correction changes the BA and BIN4 fate summaries and their induced-prior
audits.  It does not change the likelihood fits, CPL baseline, D0--D4 data
axis, P2/P3 prior axis, null mocks, Wilks statistics, or Bayes evidence.  The
old A-003 record is retained verbatim as historical provenance; current
results are explicitly labelled A-005.
