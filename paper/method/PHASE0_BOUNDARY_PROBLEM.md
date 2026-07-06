# Phase 0: Critical-Boundary Problem Definition

Draft date: 2026-07-06

Working title: **Critical-Boundary Calibration of Cosmic-Fate Probabilities**

This document defines the independent method paper. It is intentionally separate
from the main cosmic-fate data paper. The goal is to fix the research object
before toy simulations, cosmology mocks, or writing begin.

## 1. Core Question

When a cosmological model is close to a fate-classification boundary, how should
posterior fate probabilities such as `P(RIP)`, `P(DECAY)`, and
`P(heat-death-compatible)` be calibrated and reported?

The paper studies fate probabilities as **boundary statistics**, not as direct
forecasts of the universe's fate.

## 2. Problem Statement

Cosmic-fate inference is often described as if it were ordinary parameter
estimation:

> Infer dark-energy parameters, classify each posterior sample, then read class
> fractions as fate probabilities.

That shortcut is unsafe near Lambda-CDM. Fate classes are defined by long-future
behavior, thresholds, and discontinuous or near-discontinuous maps from
parameters to labels. If the null model lies on or very near a classification
boundary, repeated experiments can produce widely varying class fractions even
when the inference pipeline is correctly calibrated.

The method paper asks how to distinguish:

1. directional instability caused by a boundary,
2. unusually deep tail suppression or enhancement,
3. model evidence for or against dynamical dark energy,
4. long-future extrapolation beyond the data-constrained region.

## 3. Minimal Mathematical Abstraction

Let `theta` be a model parameter or a vector of parameters, and let

```text
C(theta) in {A, B, OTHER}
```

be a deterministic classification rule. A posterior sample induces

```text
P(A | data) = integral 1[C(theta)=A] p(theta | data) dtheta.
```

The critical-boundary problem occurs when the data-generating value `theta0`
satisfies, or is close to satisfying,

```text
theta0 in boundary(A, B).
```

In that case, the raw class probability can be a calibrated random variable
under repeated experiments rather than a stable direction decision.

The first toy case will use a one-dimensional Gaussian posterior:

```text
x_hat ~ Normal(theta0, sigma)
theta | x_hat ~ Normal(x_hat, sigma_post)
C(theta) = A if theta > 0, else B
theta0 = 0
```

The expected diagnostic result is that repeated experiments produce a broad,
approximately uniform distribution of `P(A | data)` under appropriate symmetric
calibration assumptions. A 50 percent direction accuracy is therefore not, by
itself, evidence of a broken classifier.

## 4. Cosmology Translation

For the cosmic-fate setting:

- `theta` can include `w0`, `wa`, `Omega_m`, `H0`, curvature, nuisance
  parameters, or a nonparametric representation of `w(a)`.
- `C(theta)` is a fate classifier such as `RIP`, `DECAY`, `DS`, `CRUNCH`, or
  `OTHER`.
- Lambda-CDM, or a near-Lambda-CDM data-generating model, is a critical case
  because small posterior shifts can move samples across future-fate boundaries.

The method paper will use cosmology only as a case study. Its primary claim is
statistical: class probabilities near critical boundaries need null calibration.

## 5. Non-Goals

This paper will not claim that:

- the real universe will undergo heat death,
- the real universe will undergo a Big Rip,
- DESI evidence proves dynamical dark energy,
- a specific future fate has been discovered,
- compressed CMB likelihoods are equivalent to full Planck likelihoods.

The paper may use existing cosmology mocks and real-data numbers as an
illustrative case study, but the main result must remain method-level.

## 6. Testable Claims

The paper should establish or falsify these claims:

1. **Boundary-uniformity claim**: In a symmetric boundary toy model with the true
   value on the class boundary, repeated experiments produce a broad,
   approximately uniform distribution of the posterior class probability.
2. **Accuracy-failure claim**: In such boundary cases, a high fixed direction
   accuracy threshold, such as 90 percent, is not a valid calibration criterion.
3. **Depth-information claim**: A real-data class probability can still be
   informative if it lies unusually deep in the null distribution, even when
   direction accuracy under the null is near 50 percent.
4. **Layer-separation claim**: Raw fate probability, null-calibrated tail depth,
   model evidence, and extrapolation horizon answer different questions and must
   be reported separately.

Failure of any claim should be visible in plots or simulation summaries, not
resolved by prose.

## 7. Required Diagnostics

Every case study in the method paper should report:

| Layer | Quantity | Purpose |
|---|---|---|
| Direction | `P(class)`, direction accuracy under mocks | Shows whether the class side is stable |
| Depth | null CDF / calibrated p-value of the observed class probability | Shows whether the observed probability is unusually extreme |
| Evidence | likelihood ratio, AIC/BIC, or Bayes factor when available | Separates better fit from model preference |
| Boundary | boundary-sample fraction or threshold-flip rate | Shows sensitivity to classifier thresholds |
| Horizon | constraint horizon or future-scale dependence when available | Shows whether the classification is data-constrained |

The method paper can introduce the full table, then use only the rows supported
by each experiment.

## 8. Phase 1 Entry Criteria

Phase 0 is complete when the following are true:

1. The research object is limited to boundary calibration.
2. Non-goals explicitly prevent claims about the real universe's final fate.
3. The toy theorem or simulation target is defined.
4. The cosmology case study is framed as an example, not the main conclusion.
5. The required diagnostics are fixed before generating new figures.

If these criteria are accepted, Phase 1 should implement the one-dimensional
toy model and generate the first figure: the null distribution of
`P(theta > 0 | data)` when `theta0 = 0`.

## 9. Working Abstract Seed

Posterior probabilities for cosmic-fate classes are often read as direct
forecasts. We argue that near Lambda-CDM they should instead be treated as
calibrated boundary statistics. In simple boundary models, when the true model
lies on the class boundary, repeated experiments can yield a broad, nearly
uniform distribution of posterior class probabilities, making high direction
accuracy an invalid calibration target. We propose a reporting protocol that
separates direction, tail depth, model evidence, classifier-boundary sensitivity,
and extrapolation horizon. A cosmology-motivated mock case study illustrates how
an apparently failed 50 percent direction rate can coexist with an informative
tail-depth signal.
