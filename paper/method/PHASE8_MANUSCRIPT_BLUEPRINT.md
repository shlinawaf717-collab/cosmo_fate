# Phase 8: Manuscript Blueprint

Draft date: 2026-07-06

This phase assembles the completed method-paper work into a controlled
manuscript plan. It does not add new cosmology claims. Its job is to lock the
paper's structure, evidence map, figure plan, and claim boundary before writing
the full draft.

## 1. Working Paper Identity

Working title: **Critical-Boundary Calibration of Cosmic-Fate Probabilities**

Short title: **Cosmic-Fate Probabilities as Boundary Statistics**

Primary claim:

> Posterior cosmic-fate class probabilities near a critical boundary should be
> treated as calibrated boundary statistics, not direct forecasts of the
> universe's fate.

## 2. Source Inventory

| Phase | Artifact | Doc | Result | Figure | Manuscript role |
|---|---|---|---|---|---|
| 0 | PHASE0_BOUNDARY_PROBLEM.md | yes | n/a | n/a | Defines the independent method-paper object and non-goals. |
| 1 | PHASE1_TOY_BOUNDARY.md | yes | yes | yes | One-dimensional boundary-null demonstration. |
| 2 | PHASE2_W0WA_BOUNDARY.md | yes | yes | yes | Cosmology-shaped two-dimensional boundary analogue. |
| 3 | PHASE3_CLASSIFIER_FRAMEWORK.md | yes | yes | yes | Abstract fate classifier with continuous diagnostics. |
| 4 | PHASE4_NULL_CALIBRATION.md | yes | yes | yes | Finite-mock calibration protocol and p-value rule. |
| 5 | PHASE5_COSMOLOGY_MOCK_CASE.md | yes | yes | yes | Read-only real-pipeline LCDM mock case study. |
| 6 | PHASE6_REPORTING_STANDARD.md | yes | yes | yes | Five-layer reporting standard. |
| 7 | PHASE7_ROBUSTNESS.md | yes | yes | yes | Robustness and diagnostic-failure appendix. |

## 3. Key Results to Carry Forward

| Result | Value |
|---|---:|
| Phase 1 boundary-null mean | 0.500960 |
| Phase 1 boundary-null variance | 0.083559 |
| Phase 1 KS p vs Uniform | 0.164593 |
| Phase 2 w0-wa analogue mean | 0.501283 |
| Phase 2 KS p vs Uniform | 0.058189 |
| Phase 5 noisy LCDM mocks | 100 |
| Phase 5 direction rate `P_heat>0.5` | 0.500000 |
| Phase 5 observed `P_RIP` | 0.001792 |
| Phase 5 lower-tail count | 0 / 100 |
| Phase 5 plus-one lower-tail p | 0.009901 |
| Phase 7 calibrated and shifted variants | pass / pass |
| Phase 7 off-boundary and width-mismatch variants | diagnostic failures |
| Phase 7 curved boundary | curvature diagnostic |

## 4. Manuscript Section Plan

| Section | Job | Evidence | Output |
|---|---|---|---|
| 1. Introduction | State why posterior cosmic-fate class masses are unsafe as direct forecasts near Lambda-CDM. | Phase 0 | Problem framing and non-goals. |
| 2. Boundary-statistic formulation | Define deterministic fate labels, posterior class mass, and the critical-boundary problem. | Phase 0, Phase 3 | Mathematical setup and classifier notation. |
| 3. One-dimensional boundary null | Show that calibrated boundary probabilities can be broadly uniform under repeated experiments. | Phase 1 | Toy theorem or simulation with uniform diagnostics. |
| 4. Cosmology-shaped analogue | Translate the boundary result into a local w0-wa-like geometry without claiming a cosmic-fate result. | Phase 2, Phase 3 | Two-dimensional boundary figure and classifier framework. |
| 5. Finite-mock null calibration | Define lower, upper, and two-sided plus-one calibrated p-values. | Phase 4 | Protocol and finite-mock floor. |
| 6. Real-pipeline LCDM mock case study | Demonstrate direction-depth separation using the existing 100 noisy LCDM mocks. | Phase 5 | Observed D0 tail-depth result as a method case study. |
| 7. Reporting standard | Provide the reusable Direction, Depth, Evidence, Boundary, Horizon checklist. | Phase 6 | Citable reporting protocol. |
| 8. Robustness and diagnostics | Show which perturbations preserve uniformity and which correctly fail diagnostics. | Phase 7 | Robustness appendix and diagnostic-failure rules. |
| 9. Limitations | Keep unsupported evidence, horizon, and real-universe fate claims outside the method paper. | Phase 0, Phase 6, Phase 7 | Explicit proof boundary. |

## 5. Claim Ledger

| Status | Claim | Support or boundary |
|---|---|---|
| supported | Near a calibrated critical boundary, posterior class probabilities can be broad and approximately uniform under repeated experiments. | Phase 1 mean=0.50096, variance=0.08356, KS p=0.16459; Phase 2 KS p=0.05819. |
| supported | A 50 percent direction rate is not automatically a failed classifier near the boundary. | Phase 5 LCDM mocks have P_heat>0.5 in 0.50 of mocks while the P_heat null shape passes KS p=0.25266. |
| supported | Tail depth can still carry information when direction is unstable. | Observed P_RIP=0.00179 is below 0/100 noisy LCDM mocks; plus-one p=0.00990. |
| supported | The reporting unit must separate Direction, Depth, Evidence, Boundary, and Horizon. | Phase 6 defines all five layers and marks Evidence and Horizon as unfilled in the case study. |
| not claimed | The method establishes the real universe's final fate. | Excluded by Phase 0 non-goals and by the Phase 5 case-study scope. |
| not claimed | The case study proves dynamical dark energy or model preference. | Evidence layer is explicitly unavailable in Phase 6 and must be supplied by a separate science analysis. |
| not claimed | Curved or miscalibrated boundaries always preserve uniformity. | Phase 7 shows off-boundary truth and posterior-width mismatch fail; beta=1.5 curvature is labeled a diagnostic. |

## 6. Figure Plan

| Slot | Purpose | Source file | Placement |
|---|---|---|---|
| Figure 1 | Boundary-null toy result | phase1_toy_boundary_uniformity.png | Main text |
| Figure 2 | w0-wa analogue | phase2_w0wa_boundary.png | Main text |
| Figure 3 | Fate-classifier framework | phase3_classifier_framework.png | Main text or methods |
| Figure 4 | Finite-mock calibration protocol | phase4_null_calibration.png | Main text |
| Figure 5 | Real-pipeline LCDM mock case | phase5_cosmology_mock_case.png | Main text |
| Figure 6 | Five-layer reporting standard | phase6_reporting_standard.png | Main text |
| Appendix Figure A1 | Robustness checks | phase7_robustness.png | Appendix |

## 7. Table Plan

| Slot | Purpose | Source |
|---|---|---|
| Table 1 | Claim ledger and evidence boundary | Phase 8 |
| Table 2 | Five-layer reporting checklist | Phase 6 |
| Table 3 | LCDM mock case-study numbers | Phase 5 |
| Appendix Table A1 | Robustness diagnostics | Phase 7 |

## 8. Abstract Draft

Posterior probabilities for cosmic-fate classes are often read as direct
forecasts. This interpretation can be misleading near Lambda-CDM, where the
data-generating model may lie on or close to a fate-classification boundary. We
frame posterior fate probabilities as boundary statistics. In a calibrated
one-dimensional boundary model, repeated experiments produce an approximately
uniform distribution of posterior class probabilities (mean 0.501, variance 0.084, KS p = 0.165), and
a cosmology-shaped w0-wa analogue shows the same behavior. We then define
finite-mock null calibration rules and apply them to an existing LCDM mock case
study. In that case, the direction layer is deliberately uninformative
(`P_heat>0.5` in 50/100 noisy mocks), while the observed
`P_RIP=0.0018` falls below 0/100
noisy LCDM mocks, giving a plus-one lower-tail p-value of
0.0099. We propose a five-layer
reporting standard that separates Direction, Depth, Evidence, Boundary, and
Horizon. The result is a reporting protocol for boundary-sensitive cosmic-fate
probabilities, not a direct claim about the universe's final fate.

## 9. Phase 8 Pass Criteria

| Criterion | Status |
|---|---|
| all phase artifacts present | pass |
| all declared result files present | pass |
| all declared figures present | pass |
| supported claims mapped to phase evidence | pass |
| unsupported science claims excluded | pass |
| manuscript skeleton written | pass |

Status: **Phase 8 passes.**

## 10. Next Step

Phase 9 should write the full manuscript draft from this blueprint without expanding the claim boundary.
