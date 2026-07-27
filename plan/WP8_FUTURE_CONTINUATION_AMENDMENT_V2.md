# WP8 future-continuation corrective supplement v2

Status: frozen before WP8 construction, posterior continuation draws, or
fate endpoints.

This document appends to, and does not overwrite,
`WP8_FUTURE_CONTINUATION_PROTOCOL.md` v1.  PRD-A005/v1 remains the historical
checkpoint.  PRD-A007 controls wherever the two conflict.

## 1. Structural controls

C2 fixes `w_inf=-1`.  Its fate is therefore analytically DS and
`P(RIP)=0` for every `tau`; `tau` changes only path admissibility.

Before path-admissibility conditioning, the C3 asymptote measure is symmetric:
a Normal distribution centred at `-1`, truncated symmetrically at four
standard deviations.  Its measure assigns exactly one half to `w_inf<-1`
and one half to `w_inf>-1`, with zero point mass at DS.  This is a prior
measure statement, not a data result.

At fixed `(w1,s1,tau)`, every grid value is affine in `w_inf`.  The complete
registered admissible `w_inf` support is therefore obtained by intersecting
linear intervals from the 512 grid constraints.  WP8 computes this interval
analytically.  Monte Carlo may verify the calculation but is not the primary
fate estimator.

Conditioning on path admissibility can reweight `w_inf` because admissibility
depends jointly on `(w1,s1,tau,w_inf)`.  Any resulting accepted-draw
composition is labelled **selection-conditioned**, not a likelihood posterior
update of the independent C3 asymptote measure.  The v1 instruction treating
any such marginal change as an implementation failure is retired.

## 2. Partial-identification endpoint

The v1 robust-identification fraction and its `0.90` interpretation threshold
are retired as primary endpoints.  For each observed-history draw, WP8 instead
reports the support-identified thermodynamic set:

- `{RIP}` if every registered admissible continuation is on the RIP side;
- `{heat}` if every registered admissible continuation is on the DS/DECAY
  side;
- `{RIP,heat}` if registered admissible continuations reach both sides;
- `empty/invalid` only when no registered continuation is admissible, reported
  as an implementation or support failure.

C0 and C2 are included as labelled deterministic members; C3 contributes its
complete admissible support interval for each `tau`.  C1 remains a separate
derivative-discontinuous diagnostic.

The aggregate fractions of these support-set categories may be reported, but
there is no pass/fail threshold.  A two-sided set is the analytic
partial-identification conclusion, not a failed measurement.

## 3. Disposition of the v1 spans and interpretation gate

`Delta_cont_RIP` and `Delta_cont_heat` may be retained as descriptive family
spans, but they are structurally influenced by deterministic C2 and the
chosen C3 asymptote measure.  They are not evidence that data created or
resolved the span and no longer trigger a thresholded gate.

WP8 never reports a family-averaged, continuation-unqualified fate
probability because no probabilities over C0--C3 were registered.  It reports
conditional family results, the continuation envelope, and the
partial-identification support set regardless of whether numerical family
outputs happen to agree.

All v1 validation rules concerning boundary matching, past-observable
invariance, fixed-seed replay, rejection accounting, and C0 reproduction
remain active.
