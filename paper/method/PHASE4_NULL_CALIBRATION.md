# Phase 4: Null-Calibration Protocol

Draft date: 2026-07-06

This phase turns the boundary-statistic idea into a reproducible reporting
protocol. The output is not a new cosmology result. It is the method-paper rule
for converting a raw fate probability into a calibrated boundary statistic.

## 1. Purpose

Define how to interpret an observed raw class probability near a critical
boundary.

Raw posterior class fractions answer:

```text
How much posterior mass falls in this label region?
```

Null calibration answers:

```text
How unusual is that raw class fraction under a boundary or near-boundary null?
```

Both are needed. The first is a direction or class-mass statement. The second is
a tail-depth statement.

## 2. Protocol

For a predeclared classifier `C(theta)` and label `L`:

1. Compute the observed raw class probability:

   ```text
   p_obs = P(C(theta) = L | observed data)
   ```

2. Choose the relevant null model, usually a boundary or near-boundary model
   such as Lambda-CDM in a fate-classification problem.

3. Generate `N` null mocks from that null model.

4. Run the identical inference and classifier pipeline on every mock:

   ```text
   p_j = P(C(theta) = L | mock_j),  j = 1...N
   ```

5. Compare `p_obs` to the empirical null distribution `{p_j}`.

6. Report tail depths using finite-mock plus-one smoothing:

   ```text
   p_lower = (#{p_j <= p_obs} + 1) / (N + 1)
   p_upper = (#{p_j >= p_obs} + 1) / (N + 1)
   p_two_sided = min(1, 2 * min(p_lower, p_upper))
   ```

7. State the finite-mock floor:

   ```text
   p_min = 1 / (N + 1)
   ```

Never report `p = 0` from finite mocks.

## 3. Interpretation Layers

| Layer | Question | Report |
|---|---|---|
| Direction | Which side has more posterior mass? | raw `P(label | data)` and whether it is above/below 0.5 |
| Depth | Is the raw probability unusual under the null? | lower/upper/two-sided null-calibrated p-values |
| Evidence | Does the expanded model deserve preference? | likelihood ratio, AIC/BIC, or Bayes factor when available |
| Boundary | Is the label sensitive to thresholds? | boundary fraction or threshold-flip rate |
| Horizon | Is the fate decision data-constrained? | constraint horizon or future-scale diagnostic |

Phase 4 implements the direction and depth layers. Later phases can attach
evidence, boundary, and horizon diagnostics.

## 4. Synthetic Demonstration

The implemented script uses the Phase 2 `w0`-`wa` boundary analogue to generate
100 finite null mocks. It then calibrates three synthetic observed values:

```text
central_boundary_like = 0.500
low_tail_example      = 0.018
high_tail_example     = 0.982
```

These are examples only. They do not claim anything about the real universe.

## 5. Implemented Script

Script:

```text
paper/method/scripts/phase4_null_calibration.py
```

Outputs:

```text
paper/method/figures/phase4_null_calibration.png
paper/method/results/phase4_null_calibration.json
```

The figure has four panels:

1. protocol flow,
2. finite null mock histogram with observed markers,
3. high-resolution null CDF showing tail depth,
4. lower- and upper-tail calibrated reports.

## 6. Phase 4 Pass Criteria

Phase 4 passes if:

1. the protocol distinguishes raw class probability from calibrated tail depth,
2. lower-tail, upper-tail, and two-sided p-values are defined,
3. finite-mock plus-one smoothing is used,
4. the mock-count p-value floor is reported,
5. the figure shows central and tail examples,
6. the document explicitly says the synthetic observed values are not cosmology
   claims.

## 7. Interpretation for the Method Paper

The phase supplies the paper's operational rule:

> A raw fate probability near a critical boundary becomes interpretable only
> after comparison with the null distribution produced by the same inference and
> classification pipeline.

This is the bridge from toy boundary theory to the later real-pipeline mock case
study.

## 8. Run Record

Run date: 2026-07-06

Finite null mock settings:

```text
source = Phase 2 w0-wa boundary analogue
N = 100
seed = 20260709
```

Finite null summary:

| Statistic | Value |
|---|---:|
| null mean | 0.51118 |
| null variance | 0.07986 |
| KS p vs Uniform(0, 1) | 0.58819 |
| minimum reportable tail p | 0.00990 |

Synthetic observed calibration examples:

| Case | Raw probability | Lower-tail p | Upper-tail p | Two-sided p |
|---|---:|---:|---:|---:|
| Central boundary-like | 0.500 | 0.44554 | 0.56436 | 0.89109 |
| Low-tail example | 0.018 | 0.03960 | 0.97030 | 0.07921 |
| High-tail example | 0.982 | 0.98020 | 0.02970 | 0.05941 |

Status: **Phase 4 passes.**

Interpretation: the same raw class probability can be described at two levels:
direction (`P` below, near, or above 0.5) and null-calibrated depth (how unusual
that `P` is under boundary mocks). With finite mocks, the report must include
the p-value floor and must not write zero p-values.
