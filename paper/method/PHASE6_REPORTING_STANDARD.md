# Phase 6: Reporting Standard

Draft date: 2026-07-06

This phase turns the method paper's results into a reusable reporting standard.
The goal is to prevent raw fate probabilities from being reported as direct
forecasts when they are boundary-sensitive posterior class masses.

## 1. Purpose

Define the minimum report required for any posterior fate probability near a
critical boundary.

The standard separates five layers:

```text
Direction, Depth, Evidence, Boundary, Horizon
```

These layers answer different questions and must not be collapsed into one
sentence.

## 2. Required Layers

| Layer | Question | Required report |
|---|---|---|
| Direction | Which label has more posterior mass? | raw `P(label | data)`, direction threshold, same quantity under null mocks |
| Depth | How unusual is the raw probability under the null? | null model, mock count, finite-mock floor, lower/upper/two-sided calibrated p-values |
| Evidence | Does the enlarged model deserve preference? | likelihood ratio, AIC/BIC, or Bayes factor; separated from fate probability |
| Boundary | Is the label threshold-sensitive? | boundary-flip rate, OTHER fraction, classifier limitations |
| Horizon | Is the fate decision data-constrained? | future scale, constraint horizon, or explicit unavailable status |

## 3. Minimum Language

A properly calibrated report should use three distinct statements:

```text
Raw class mass:
The posterior mass in label L is ...

Calibrated boundary statistic:
Under the predeclared null, the observed class probability lies in the ...
tail with finite-mock-calibrated p = ...

Guardrail:
This is not, by itself, a direct forecast of the universe's fate.
```

## 4. Phase 5 Case-Study Fill

The reporting standard is demonstrated using the Phase 5 real-pipeline case:

| Layer | Case-study fill |
|---|---|
| Direction | observed `P_heat=0.99821`; LCDM null has `P_heat > 0.5` in 50/100 mocks |
| Depth | observed `P_RIP=0.00179`; 0/100 null mocks lower; plus-one p=0.00990; 95% CP upper=0.02951 |
| Evidence | not evaluated by Phase 5; must be supplied separately in a science paper |
| Boundary | max OTHER=0.00142; max boundary fraction=0.00087; mock000 `P_heat=0.52275` |
| Horizon | not evaluated by Phase 5; must report constraint horizon or mark unavailable |

This fill is intentionally incomplete for Evidence and Horizon. That is a
feature, not a defect: the checklist forces unsupported claims to remain visibly
unsupported.

## 5. Implemented Script

Script:

```text
paper/method/scripts/phase6_reporting_standard.py
```

Outputs:

```text
paper/method/figures/phase6_reporting_standard.png
paper/method/results/phase6_reporting_standard.json
paper/method/REPORTING_CHECKLIST_TEMPLATE.md
```

## 6. Phase 6 Pass Criteria

Phase 6 passes if:

1. all five reporting layers are defined,
2. each layer has a required field list,
3. failure modes are stated,
4. the Phase 5 case study is filled only where supported,
5. unsupported Evidence and Horizon layers are explicitly marked as requiring
   separate work,
6. a reusable markdown template is generated,
7. the figure makes the layer separation readable.

## 7. Interpretation for the Method Paper

This phase supplies the method paper's practical contribution:

> Cosmic-fate probabilities near a critical boundary should be reported as a
> five-layer calibrated statement, not as a single fate forecast.

This is the form in which the method paper can be cited by future fate analyses.

## 8. Run Record

Run date: 2026-07-06

Generated outputs:

```text
paper/method/figures/phase6_reporting_standard.png
paper/method/results/phase6_reporting_standard.json
paper/method/REPORTING_CHECKLIST_TEMPLATE.md
```

Checklist layers:

| Layer | Status |
|---|---|
| Direction | defined and filled from Phase 5 |
| Depth | defined and filled from Phase 5 |
| Evidence | defined; marked as requiring separate science-paper evidence |
| Boundary | defined and filled from Phase 5 guardrails |
| Horizon | defined; marked as requiring separate constraint-horizon work |

Status: **Phase 6 passes.**

Interpretation: the reporting standard now forces future writeups to separate
raw fate probability, null-calibrated tail depth, model evidence, classifier
boundary sensitivity, and extrapolation horizon. The Phase 5 case-study fill is
intentionally partial: unsupported Evidence and Horizon claims remain visibly
unfilled.
