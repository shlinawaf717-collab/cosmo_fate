# Phase 3: Abstract Fate-Classifier Framework

Draft date: 2026-07-06

This phase defines the method-paper version of a fate classifier. It turns the
toy boundary idea into a general reporting object: continuous diagnostics enter
threshold rules, and threshold rules return discrete fate labels.

## 1. Purpose

Formalize why fate classification is not ordinary continuous parameter
estimation.

The classifier takes continuous future-behavior diagnostics and returns one
label:

```text
CRUNCH, RIP, DS, DECAY, OTHER
```

The method paper studies the statistical behavior of this map. It does not need
to reuse every physical detail of the main paper's CPL classifier.

## 2. Abstract Classifier

Define four continuous margins:

```text
crunch_margin
rip_margin
ds_margin
decay_margin
```

A positive margin means the corresponding criterion is triggered. The classifier
is priority-ordered:

```text
if crunch_margin > 0:
    CRUNCH
elif rip_margin > 0:
    RIP
elif ds_margin > 0:
    DS
elif decay_margin > 0:
    DECAY
else:
    OTHER
```

This mirrors the structure of a physical fate classifier without binding the
method paper to a specific cosmological model.

## 3. Statistical Object

For posterior samples `theta_i`, the fate probability is:

```text
P(label = L | data) = mean_i 1[C(theta_i) = L]
```

This is an integral of an indicator function. It can change abruptly when the
posterior mass moves across a threshold, even when the underlying parameters
move continuously.

Therefore, a fate probability must be interpreted together with:

1. the boundary location,
2. the amount of posterior mass near the boundary,
3. the null distribution under a boundary or near-boundary truth,
4. the model evidence for the parameterization producing the samples.

## 4. Relationship to Physical Fate Labels

The labels retain their conceptual meaning:

| Label | Method-paper meaning |
|---|---|
| CRUNCH | A collapse criterion triggers before other labels |
| RIP | A finite-time divergence criterion triggers |
| DS | A de Sitter-like asymptotic criterion triggers |
| DECAY | A dark-energy-decay / eternal-expansion-compatible criterion triggers |
| OTHER | No predeclared criterion triggers; audit channel |

This phase does not decide which physical formulas are best. It defines the
statistical wrapper needed for any such formulas.

## 5. Implemented Script

Script:

```text
paper/method/scripts/phase3_classifier_framework.py
```

Outputs:

```text
paper/method/figures/phase3_classifier_framework.png
paper/method/results/phase3_classifier_framework.json
```

The figure has four panels:

1. priority decision tree,
2. example descriptor plane,
3. posterior mass split into class regions,
4. continuous path whose label indicators jump at thresholds.

## 6. Phase 3 Pass Criteria

Phase 3 passes if:

1. the classifier is defined as a priority-ordered threshold map,
2. all five labels have explicit method-paper meanings,
3. the figure shows class regions in a descriptor plane,
4. an example posterior produces nonzero mass in multiple classes,
5. the figure shows a continuous path with discontinuous label indicators,
6. the document states that this is a statistical wrapper, not a new physical
   fate model.

## 7. Interpretation for the Method Paper

The phase supplies the method paper's central language:

> Fate probabilities are posterior masses of threshold-defined label regions.
> Near a boundary, they are boundary statistics and require null calibration.

This bridges the toy results from Phase 1 and Phase 2 to the later cosmology mock
case study.

## 8. Run Record

Run date: 2026-07-06

Example posterior class fractions:

| Label | Fraction |
|---|---:|
| CRUNCH | 0.00000 |
| RIP | 0.36857 |
| DS | 0.03286 |
| DECAY | 0.50729 |
| OTHER | 0.09129 |

Continuous path diagnostic:

```text
label just before RIP margin = 0: DECAY
label just after RIP margin = 0:  RIP
```

Status: **Phase 3 passes.**

Interpretation: the same continuous descriptor space can yield mixed posterior
class mass and discontinuous label changes at thresholds. This validates the
method-paper claim that fate probabilities are posterior masses over label
regions and must be treated as boundary statistics.
