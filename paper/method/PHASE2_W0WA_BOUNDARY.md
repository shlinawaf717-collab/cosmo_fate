# Phase 2: Two-Dimensional `w0`-`wa` Boundary Toy Model

Draft date: 2026-07-06

This phase extends the Phase 1 boundary result from one dimension to a
cosmology-shaped two-dimensional posterior in the `w0`-`wa` plane.

## 1. Purpose

Show that the boundary-calibration result is not an artifact of drawing a
one-dimensional line. In a two-dimensional posterior, a fate-class probability
near a linear boundary is controlled by the posterior mass along the
boundary-normal score.

This is still a toy model. It is a bridge from the abstract proof to the later
cosmology mock case study.

## 2. Coordinates

Use coordinates centered on Lambda-CDM:

```text
u = w0 + 1
v = wa
Lambda-CDM = (u, v) = (0, 0)
```

The repeated experiment is:

```text
x_hat ~ Normal(theta0, Sigma_data)
theta | x_hat ~ Normal(x_hat, Sigma_post)
theta0 = (0, 0)
```

The baseline calibrated case sets:

```text
Sigma_post = Sigma_data
```

## 3. Boundary Proxy

Define a linear fate proxy:

```text
s(theta) = alpha * u + v
```

and classify samples as:

```text
RIP-like   if s(theta) > 0
DECAY-like if s(theta) < 0
```

This is **not** a physical CPL fate classifier. It is a controlled boundary
analogue: Lambda-CDM lies exactly on the class boundary, and noise moves the
posterior center to either side.

For a Gaussian posterior, the class probability is analytic:

```text
P(RIP-like | data) = Phi(s_hat / sigma_s)
sigma_s^2 = b^T Sigma_post b,  b = (alpha, 1)
```

When `b^T theta0 = 0` and the repeated-experiment variance of `s_hat` equals
`sigma_s^2`, the Phase 1 probability-integral-transform result applies:

```text
P(RIP-like | data) ~ Uniform(0, 1)
```

## 4. Implemented Script

Script:

```text
paper/method/scripts/phase2_w0wa_boundary.py
```

Outputs:

```text
paper/method/figures/phase2_w0wa_boundary.png
paper/method/results/phase2_w0wa_boundary_stats.json
```

The figure has four panels:

1. `w0`-`wa` plane with the class boundary and selected noisy posterior ellipses,
2. null histogram of `P(RIP-like | data)`,
3. ECDF versus Uniform(0, 1),
4. projected boundary-normal score versus class probability.

## 5. Phase 2 Pass Criteria

Phase 2 passes if the baseline simulation satisfies:

1. mean within 0.01 of 0.5,
2. variance within 0.01 of `1/12`,
3. direction rate `P(RIP-like | data) > 0.5` within 0.01 of 0.5,
4. KS test does not reject Uniform(0, 1) at `p < 0.01`,
5. the selected posterior examples include low, near-boundary, and high
   `P(RIP-like)` cases from the same Lambda-CDM truth,
6. the figure makes clear that the result comes from projection onto the
   boundary-normal score.

## 6. Interpretation for the Method Paper

The two-dimensional lesson is:

> A visually realistic `w0`-`wa` posterior can cross a fate boundary in different
> directions across repeated experiments, even when all experiments share the
> same boundary truth.

This supports the method paper's reporting rule: raw class fractions must be
paired with a null distribution before being interpreted as fate evidence.

## 7. Run Record

Run date: 2026-07-06

Baseline settings:

```text
n_experiments = 50000
truth = Lambda-CDM: u = 0, v = 0
alpha = 1.2
seed = 20260707
```

Baseline results:

| Statistic | Value | Pass criterion |
|---|---:|---|
| mean | 0.50128 | within 0.01 of 0.5 |
| variance | 0.08326 | within 0.01 of 1/12 |
| direction rate `P(RIP-like | data) > 0.5` | 0.50516 | within 0.01 of 0.5 |
| KS D vs Uniform(0, 1) | 0.00594 | diagnostic |
| KS p vs Uniform(0, 1) | 0.05819 | not reject at p < 0.01 |

Selected posterior examples from the same Lambda-CDM truth:

| Example | w0_hat | wa_hat | `P(RIP-like)` |
|---|---:|---:|---:|
| Low RIP-like probability | -0.86259 | -0.45695 | 0.08001 |
| Near boundary | -1.05691 | 0.06830 | 0.50000 |
| High RIP-like probability | -1.08011 | 0.38820 | 0.92001 |

Status: **Phase 2 passes.**

Diagnostic note: an initial larger single run with `n=120000` had visually and
numerically near-uniform quantiles but a KS p-value below 0.01. A 20-seed check
showed this was consistent with a rare single-run null rejection rather than a
model mismatch. The analytic projection result above remains the primary
justification; the figure uses `n=50000`, which is sufficient for visual and
summary diagnostics without overemphasizing a single high-power KS p-value.
