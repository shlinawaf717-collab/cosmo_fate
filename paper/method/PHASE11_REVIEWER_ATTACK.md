# Phase 11: Reviewer Attack Pass

Draft date: 2026-07-06

This phase treats the manuscript as if it has reached a skeptical referee. The
goal is not to defend every sentence; it is to identify which objections should
change the paper before public release.

| Severity | Attack | Response | Action |
|---|---|---|---|
| Major | Uniformity theorem is too narrow: Gaussian, local linear boundary, calibrated posterior width. | Accept. State theorem as local benchmark only; use robustness and full-pipeline mocks for applications. | Already limited in Sections 2, 9, 11; retain as explicit limitation. |
| Major | Curved boundary example fails KS; this may look like a failed method. | Reframe as a diagnostic success: arbitrary curvature is not claimed to preserve uniformity. | Keep Figure A1 in appendix and mention curvature in the claim ledger. |
| Major | LCDM mock case may be overread as a science result about the real universe. | Keep it as a method case study; preserve the guardrail that Evidence and Horizon are unfilled. | Do not write 'the universe will' or model-preference language. |
| Major | The 0/100 result is finite-resolution and may be unstable under more mocks. | Report plus-one floor, zero-count upper bound, and no p=0. | Cite Phipson and Smyth 2010; recommend larger mock ensembles for deep-tail claims. |
| Major | The paper needs statistical lineage beyond cosmology references. | Add PIT, prequential/probability forecast calibration, posterior predictive checking, finite simulation p-values. | Handled in Phase 12 references and polished manuscript. |
| Moderate | Seven figures are too many for a compact method paper. | Main text should carry four figures; remaining figures move to appendix/supplement. | Handled in Phase 14. |
| Moderate | Text still reads like a project report if it says Phase 1/2/5. | Remove phase language from the polished manuscript. | Handled in Phase 15. |
| Minor | LaTeX source exists but local TeX engine is unavailable. | Document the local limitation and provide build files for a TeX environment. | Handled in Phase 13. |

## Verdict

The paper is not yet submission-clean unless Phases 12-16 are completed. The
core method claim is defensible, but only if the manuscript keeps the proof
boundary explicit: local boundary calibration, finite-mock tail depth, and
reporting discipline. It must not read as a new cosmic-fate discovery.
