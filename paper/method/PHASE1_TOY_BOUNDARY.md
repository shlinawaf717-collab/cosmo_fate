# Phase 1: One-Dimensional Boundary Toy Model

Draft date: 2026-07-06

This phase implements the first test from
`PHASE0_BOUNDARY_PROBLEM.md`: a one-dimensional calibrated boundary model.

## 1. Purpose

Show, in the simplest possible setting, why a posterior class probability can be
fully calibrated while direction accuracy remains only 50 percent.

The point is not cosmology yet. The point is to isolate the statistical
structure of a true value sitting on a classification boundary.

## 2. Model

The repeated experiment is:

```text
x_hat ~ Normal(theta0, sigma_data)
theta | x_hat ~ Normal(x_hat, sigma_post)
C(theta) = A if theta > 0, otherwise B
```

For the calibrated boundary null:

```text
theta0 = 0
sigma_post = sigma_data
```

The class probability is:

```text
P(A | data) = P(theta > 0 | x_hat)
            = Phi(x_hat / sigma_post)
```

Because `x_hat / sigma_data ~ Normal(0, 1)` and `sigma_post = sigma_data`,

```text
P(A | data) = Phi(Z),  Z ~ Normal(0, 1).
```

By the probability integral transform, `Phi(Z) ~ Uniform(0, 1)`.

## 3. Expected Result

Across repeated null experiments:

- `P(A | data)` should be approximately Uniform(0, 1).
- `mean(P(A | data))` should be near 0.5.
- `Var(P(A | data))` should be near `1/12`.
- `Pr[P(A | data) > 0.5]` should be near 0.5.

Therefore, a 90 percent direction-accuracy rule is not valid when the true value
is exactly on the class boundary.

## 4. Implemented Script

Script:

```text
paper/method/scripts/phase1_toy_boundary.py
```

Outputs:

```text
paper/method/figures/phase1_toy_boundary_uniformity.png
paper/method/results/phase1_toy_boundary_stats.json
```

The script also includes two off-boundary simulations (`theta0 = 0.5 sigma` and
`theta0 = 1.0 sigma`) and two posterior-width mismatch checks. These are not the
main result; they are included to make the boundary condition visible.

## 5. Phase 1 Pass Criteria

Phase 1 passes if the baseline calibrated boundary simulation satisfies:

1. mean within 0.01 of 0.5,
2. variance within 0.01 of `1/12`,
3. direction rate `P(A | data) > 0.5` within 0.01 of 0.5,
4. KS test does not reject Uniform(0, 1) at `p < 0.01`,
5. the figure shows the histogram and ECDF are visually consistent with uniformity.

If these fail, the method paper cannot use the 50 percent direction-rate result
as a boundary-calibration claim without first diagnosing the mismatch.

## 6. Interpretation for the Method Paper

This toy model proves the first conceptual step:

> A low direction accuracy can be the expected behavior of a calibrated posterior
> when the data-generating model lies on the class boundary.

The cosmology translation is not that the universe is at exactly such a toy
boundary. The translation is narrower: if Lambda-CDM or a near-Lambda-CDM model
lies on a fate-classification boundary, raw fate class fractions require null
calibration before they are interpreted as evidence about cosmic fate.

## 7. Run Record

Run date: 2026-07-06

Baseline settings:

```text
n_experiments = 200000
theta0 = 0
sigma_data = 1
sigma_post = 1
seed = 20260706
```

Baseline results:

| Statistic | Value | Pass criterion |
|---|---:|---|
| mean | 0.50096 | within 0.01 of 0.5 |
| variance | 0.08356 | within 0.01 of 1/12 |
| direction rate `P(A | data) > 0.5` | 0.50202 | within 0.01 of 0.5 |
| KS D vs Uniform(0, 1) | 0.00250 | diagnostic |
| KS p vs Uniform(0, 1) | 0.16459 | not reject at p < 0.01 |

Status: **Phase 1 passes.**

Interpretation: the calibrated boundary null produces an approximately uniform
posterior class probability, so 50 percent direction accuracy is the expected
null behavior, not a classifier failure.
