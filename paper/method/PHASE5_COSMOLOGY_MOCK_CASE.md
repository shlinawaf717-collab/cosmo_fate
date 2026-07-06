# Phase 5: Real-Pipeline LCDM Mock Case Study

Draft date: 2026-07-06

This phase applies the Phase 4 null-calibration protocol to existing
cosmology-pipeline outputs. It is a case study for the independent method paper,
not a new run of the main cosmic-fate analysis.

## 1. Purpose

Demonstrate that the boundary-calibration protocol works on the real inference
pipeline:

1. use 100 noisy LCDM mocks as the null distribution,
2. keep the zero-noise mock separate as a mechanism diagnostic,
3. compare the observed D0 CPL+P1 fate probability with the null distribution,
4. report direction and depth separately.

## 2. Source Files

Inputs are read-only:

```text
runs/gate2/results.jsonl
runs/gate2/gate2_final_stats.json
runs/phase2/fate/d0_cpl_p1.json
```

The `results.jsonl` file has 101 rows:

```text
k = 0      zero-noise mock000, mechanism diagnostic
k = 1..100 noisy LCDM null mocks
```

Only `k = 1..100` define the finite null distribution.

## 3. Quantities

For each mock:

```text
P_heat = P(DS) + P(DECAY)
P_RIP  = P(RIP)
```

For the observed D0 result:

```text
P_heat_obs = 0.998208...
P_RIP_obs  = 0.001792...
```

The method-paper interpretation separates:

| Layer | Quantity |
|---|---|
| Direction | how often `P_heat > 0.5` under LCDM mocks |
| Null shape | whether `P_heat` is compatible with Uniform(0, 1) |
| Depth | whether observed `P_RIP` is unusually low under LCDM mocks |
| Guardrail | zero-noise mock and boundary/OTHER budgets |

## 4. Implemented Script

Script:

```text
paper/method/scripts/phase5_cosmology_mock_case.py
```

Outputs:

```text
paper/method/figures/phase5_cosmology_mock_case.png
paper/method/results/phase5_cosmology_mock_case.json
```

The figure has four panels:

1. `P_heat` null histogram with observed and zero-noise markers,
2. `P_RIP` null histogram showing the observed lower-tail depth,
3. null CDF position of observed `P_heat`,
4. text summary of direction, depth, finite-mock floor, and guardrails.

## 5. Phase 5 Pass Criteria

Phase 5 passes if:

1. `mock000` is excluded from the noisy null distribution,
2. the noisy null contains exactly 100 mocks,
3. direction accuracy is reported separately from tail depth,
4. observed `P_RIP` is calibrated with plus-one finite-mock smoothing,
5. the zero-count 95 percent upper bound is reported,
6. OTHER and boundary budgets are reported as guardrails,
7. the document explicitly says this is a method-paper case study, not a
   standalone cosmic-fate claim.

## 6. Interpretation for the Method Paper

This phase is the bridge from toy models to real-pipeline behavior:

> Under an LCDM boundary null, the direction layer can be uninformative
> (`P_heat > 0.5` in about half of mocks) while the depth layer can still show an
> unusually extreme observed tail probability.

That is the method paper's core message in operational form.

## 7. Run Record

Run date: 2026-07-06

Null distribution:

| Quantity | Value |
|---|---:|
| noisy LCDM mocks | 100 |
| `P_heat` mean | 0.52515 |
| `P_heat` SE | 0.03026 |
| `P_heat` KS D vs Uniform(0, 1) | 0.10000 |
| `P_heat` KS p vs Uniform(0, 1) | 0.25266 |
| direction rate `P_heat > 0.5` | 0.50000 |
| `P_RIP` null minimum | 0.01518 |
| `P_RIP` null median | 0.49244 |

Observed D0 CPL+P1 result:

| Quantity | Value |
|---|---:|
| observed `P_heat` | 0.99821 |
| observed `P_RIP` | 0.00179 |
| noisy null mocks with `P_RIP <= observed` | 0 / 100 |
| plus-one lower-tail p for `P_RIP` | 0.00990 |
| zero-count 95% Clopper-Pearson upper bound | 0.02951 |
| noisy null mocks with `P_heat >= observed` | 0 / 100 |

Mechanism and guardrails:

| Quantity | Value |
|---|---:|
| zero-noise mock000 `P_heat` | 0.52275 |
| zero-noise mock000 `P_RIP` | 0.47577 |
| max OTHER fraction across noisy mocks | 0.00142 |
| max boundary fraction across noisy mocks | 0.00087 |

Status: **Phase 5 passes.**

Interpretation: in the real-pipeline case study, the LCDM null makes the
direction layer effectively uninformative (`P_heat > 0.5` in 50/100 mocks and
mock000 near 52/48), while the observed `P_RIP` is lower than every noisy null
mock. This is exactly the separation Phase 4 was designed to enforce: direction
and tail depth are different statements.
