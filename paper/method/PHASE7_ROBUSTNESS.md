# Phase 7: Robustness Checks

Draft date: 2026-07-06

This phase checks whether the boundary-calibration story is robust to controlled
changes in the toy setup. The goal is not to make every variant uniform. The
goal is to identify which variants preserve the boundary-null result and which
variants correctly trigger diagnostics.

## 1. Purpose

Stress-test the method paper's central claim:

> At a calibrated critical boundary, raw posterior class probabilities can be
> broadly distributed and approximately uniform under repeated experiments.

The robustness checks ask what happens when we change:

1. the boundary location,
2. the truth's distance from the boundary,
3. the posterior width relative to repeated-experiment noise,
4. local boundary curvature,
5. the finite number of null mocks.

## 2. One-Dimensional Variants

The base model remains:

```text
x_hat ~ Normal(theta0, sigma_data)
theta | x_hat ~ Normal(x_hat, sigma_post)
C(theta) = A if theta > threshold
P(A | data) = Phi((x_hat - threshold) / sigma_post)
```

Variants:

| Variant | Change | Expected result |
|---|---|---|
| calibrated boundary | `theta0=threshold`, `sigma_post=sigma_data` | uniform pass |
| shifted threshold | move both `theta0` and threshold together | uniform pass |
| off-boundary truth | move `theta0` away from threshold | non-uniform, direction information expected |
| posterior too wide | `sigma_post > sigma_data` | non-uniform, under-confident class probabilities |
| posterior too tight | `sigma_post < sigma_data` | non-uniform, over-confident class probabilities |

## 3. Curved Boundary Variant

A two-dimensional local boundary is tested:

```text
score = v + alpha*u + beta*u^2
class A if score > 0
truth = (u, v) = (0, 0)
```

For weak enough local curvature, the distribution should remain close to the
linear-boundary result. Larger curvature does not invalidate the framework; it
becomes a boundary-model diagnostic that must be reported. The implemented
`beta=1.5` case is intentionally kept as this kind of diagnostic-stress case.

## 4. Finite Mock Resolution

For a low observed raw probability such as `P_obs=0.018`, the finite number of
null mocks limits what can be claimed:

```text
p_floor = 1 / (N + 1)
Pr[zero mocks below observed under Uniform null] = (1 - P_obs)^N
```

This check supports the Phase 4 rule: never report `p=0`; report the finite-mock
floor and, when useful, a zero-count upper bound.

## 5. Implemented Script

Script:

```text
paper/method/scripts/phase7_robustness.py
```

Outputs:

```text
paper/method/figures/phase7_robustness.png
paper/method/results/phase7_robustness.json
```

The figure has four panels:

1. ECDFs for one-dimensional robustness variants,
2. mean/variance diagnostics by variant,
3. moderate curved-boundary histogram,
4. finite-mock tail-resolution curves.

## 6. Phase 7 Pass Criteria

Phase 7 passes if:

1. calibrated boundary and shifted-threshold variants pass uniform diagnostics,
2. off-boundary and posterior-width-mismatch variants fail uniform diagnostics
   in the expected direction,
3. moderate local curvature is either near-uniform or explicitly reported as a
   curvature diagnostic,
4. finite-mock resolution is quantified for multiple `N`,
5. the document distinguishes expected diagnostic failures from method failures.

## 7. Run Record

Run date: 2026-07-06

One-dimensional robustness results:

| Variant | mean | variance | direction `P>0.5` | KS p | status |
|---|---:|---:|---:|---:|---|
| calibrated | 0.498806 | 0.083597 | 0.497925 | 0.146848 | pass |
| shifted | 0.499364 | 0.083356 | 0.497250 | 0.245159 | pass |
| off-boundary | 0.638641 | 0.075633 | 0.691025 | 0 | diagnostic failure |
| too wide | 0.499690 | 0.049937 | 0.499387 | 0 | diagnostic failure |
| too tight | 0.499530 | 0.117285 | 0.498800 | 0 | diagnostic failure |

Curved-boundary result:

| Case | mean | variance | direction `P>0.5` | KS p | status |
|---|---:|---:|---:|---:|---|
| `beta=1.5`, truth on boundary | 0.524333 | 0.086348 | 0.540333 | 2.51e-06 | curvature diagnostic |

Finite-mock tail resolution for `P_obs=0.018`:

| N mocks | expected count below `P_obs` | Pr zero below | plus-one floor |
|---:|---:|---:|---:|
| 25 | 0.450 | 0.635020 | 0.038462 |
| 50 | 0.900 | 0.403250 | 0.019608 |
| 100 | 1.800 | 0.162611 | 0.009901 |
| 250 | 4.500 | 0.010663 | 0.003984 |
| 500 | 9.000 | 0.000114 | 0.001996 |
| 1000 | 18.000 | 1.29e-08 | 0.000999 |

Phase 7 passes its criteria: the two calibrated boundary cases pass; the three
miscalibrated or off-boundary cases fail in the intended diagnostic direction;
the curved case is explicitly labeled as a curvature diagnostic; and finite mock
resolution is quantified.

## 8. Interpretation for the Method Paper

This phase supplies the robustness appendix:

> The boundary-uniform result is invariant to boundary location when the truth
> remains on the boundary and calibration is correct. It is not invariant to
> moving the truth off the boundary or miscalibrating posterior width, and those
> deviations should be visible in the diagnostics rather than hidden.
