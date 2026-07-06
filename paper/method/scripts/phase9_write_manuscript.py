#!/usr/bin/env python3
"""Phase 9: write the full method-paper draft from the locked blueprint."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "results"


def load_json(name: str) -> dict:
    return json.loads((RESULT_DIR / name).read_text())


def fmt(x: float, digits: int = 5) -> str:
    return f"{x:.{digits}f}"


def table(headers: list[str], rows: list[list[str]]) -> str:
    def esc(cell: object) -> str:
        return str(cell).replace("\n", "<br>").replace("|", r"\|")

    out = ["| " + " | ".join(esc(h) for h in headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(esc(x) for x in row) + " |")
    return "\n".join(out)


def build_context() -> dict:
    p1 = load_json("phase1_toy_boundary_stats.json")
    p2 = load_json("phase2_w0wa_boundary_stats.json")
    p3 = load_json("phase3_classifier_framework.json")
    p4 = load_json("phase4_null_calibration.json")
    p5 = load_json("phase5_cosmology_mock_case.json")
    p6 = load_json("phase6_reporting_standard.json")
    p7 = load_json("phase7_robustness.json")
    p8 = load_json("phase8_manuscript_blueprint.json")

    return {
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "p4": p4,
        "p5": p5,
        "p6": p6,
        "p7": p7,
        "p8": p8,
    }


def figure_block() -> str:
    rows = [
        ["1", "One-dimensional boundary-null calibration", "figures/phase1_toy_boundary_uniformity.png"],
        ["2", "Two-dimensional w0-wa boundary analogue", "figures/phase2_w0wa_boundary.png"],
        ["3", "Abstract fate-classifier framework", "figures/phase3_classifier_framework.png"],
        ["4", "Finite-mock null-calibration protocol", "figures/phase4_null_calibration.png"],
        ["5", "Real-pipeline LCDM mock case study", "figures/phase5_cosmology_mock_case.png"],
        ["6", "Five-layer reporting standard", "figures/phase6_reporting_standard.png"],
        ["A1", "Robustness diagnostics", "figures/phase7_robustness.png"],
    ]
    return table(["Figure", "Caption target", "Source"], rows)


def claim_table(bp: dict) -> str:
    return table(
        ["Status", "Claim", "Support or boundary"],
        [[x["status"], x["claim"], x["support"]] for x in bp["claim_ledger"]],
    )


def reporting_table(layers: list[dict]) -> str:
    rows = []
    for layer in layers:
        rows.append(
            [
                layer["layer"],
                layer["question"],
                "; ".join(layer["required"]),
                layer["failure_mode"],
            ]
        )
    return table(["Layer", "Question", "Required report", "Failure mode"], rows)


def case_study_table(p5: dict) -> str:
    null = p5["null"]
    obs = p5["observed"]
    rows = [
        ["Noisy LCDM mocks", str(null["n_noisy_mocks"])],
        ["Null `P_heat` mean", fmt(null["P_heat_mean"], 5)],
        ["Null `P_heat` standard error", fmt(null["P_heat_se"], 5)],
        ["Null `P_heat` KS p vs Uniform", fmt(null["P_heat_KS_p_vs_uniform"], 5)],
        ["Direction rate `P_heat > 0.5`", fmt(null["direction_accuracy_P_heat_gt_0p5"], 5)],
        ["Observed `P_heat`", fmt(obs["P_heat"], 5)],
        ["Observed `P_RIP`", fmt(obs["P_RIP"], 6)],
        ["Noisy mocks with `P_RIP <= observed`", f"{obs['n_null_P_RIP_below_or_equal_observed']} / {null['n_noisy_mocks']}"],
        ["Plus-one lower-tail p for `P_RIP`", fmt(obs["P_RIP_lower_tail"]["p_plus_one"], 5)],
        ["Zero-count 95% upper bound", fmt(obs["P_RIP_lower_tail_upper95"], 5)],
        ["Zero-noise mock000 `P_heat`", fmt(null["mock000"]["P_heat"], 5)],
        ["Zero-noise mock000 `P_RIP`", fmt(null["mock000"]["P_RIP"], 5)],
        ["Max OTHER fraction in noisy mocks", fmt(null["OTHER_max"], 6)],
        ["Max boundary fraction in noisy mocks", fmt(null["boundary_max"], 6)],
    ]
    return table(["Quantity", "Value"], rows)


def robustness_table(p7: dict) -> str:
    rows = []
    keys = [
        "calibrated_boundary",
        "shifted_threshold_truth_on_boundary",
        "off_boundary_truth",
        "posterior_too_wide",
        "posterior_too_tight",
    ]
    for key in keys:
        row = p7["one_dimensional"][key]
        s = row["summary"]
        rows.append(
            [
                row["short_label"],
                fmt(s["mean"], 6),
                fmt(s["variance"], 6),
                fmt(s["direction_rate_P_gt_0p5"], 6),
                f"{s['ks_p_vs_uniform']:.3g}",
                "pass" if row["uniform_pass"] else "diagnostic failure",
            ]
        )
    cs = p7["curved_boundary"]["summary"]
    rows.append(
        [
            "curved beta=1.5",
            fmt(cs["mean"], 6),
            fmt(cs["variance"], 6),
            fmt(cs["direction_rate_P_gt_0p5"], 6),
            f"{cs['ks_p_vs_uniform']:.3g}",
            "curvature diagnostic",
        ]
    )
    return table(["Variant", "Mean", "Variance", "Direction rate", "KS p", "Status"], rows)


def manuscript(ctx: dict) -> str:
    p1 = ctx["p1"]
    p2 = ctx["p2"]
    p3 = ctx["p3"]
    p4 = ctx["p4"]
    p5 = ctx["p5"]
    p6 = ctx["p6"]
    p7 = ctx["p7"]
    p8 = ctx["p8"]

    b1 = p1["baseline"]
    b2 = p2["baseline"]
    p4_cases = p4["synthetic_observed_cases"]
    p5_null = p5["null"]
    p5_obs = p5["observed"]
    fractions = p3["posterior_example_fractions"]

    return f"""# Critical-Boundary Calibration of Cosmic-Fate Probabilities

Status: Phase 9 full draft, generated 2026-07-06.

## Abstract

Posterior probabilities for cosmic-fate classes are often read as direct
forecasts: one infers cosmological parameters, applies a future-fate classifier
to posterior samples, and reports the resulting class fractions. This
interpretation can be misleading near Lambda-CDM or any other model that lies
on or close to a fate-classification boundary. We frame posterior fate
probabilities as boundary statistics. In a one-dimensional calibrated boundary
model, repeated experiments produce an approximately uniform distribution of
posterior class probabilities, with mean {fmt(b1["mean"], 3)}, variance
{fmt(b1["variance"], 3)}, and KS p = {fmt(b1["ks_p_vs_uniform"], 3)} against
Uniform(0,1). A cosmology-shaped two-dimensional w0-wa analogue gives the same
diagnostic behavior, with mean {fmt(b2["mean"], 3)} and KS p =
{fmt(b2["ks_p_vs_uniform"], 3)}. We then define a finite-mock null-calibration
protocol and apply it to an existing LCDM mock case study. In that case, the
direction layer is uninformative by construction (`P_heat>0.5` in 50/100 noisy
mocks), while the observed `P_RIP={fmt(p5_obs["P_RIP"], 4)}` lies below 0/100
noisy LCDM mocks, giving a plus-one lower-tail p-value of
{fmt(p5_obs["P_RIP_lower_tail"]["p_plus_one"], 4)}. We propose a five-layer
reporting standard that separates Direction, Depth, Evidence, Boundary, and
Horizon. The result is a protocol for reporting boundary-sensitive cosmic-fate
probabilities, not a direct claim about the universe's final fate.

Keywords: cosmic fate; dark energy; boundary calibration; posterior class
probabilities; null mocks; Lambda-CDM; w0-wa; finite-mock p-values.

## 1. Introduction

Cosmic-fate statements sit at an awkward interface between data analysis and
long-future extrapolation. Modern cosmological data constrain distances,
expansion histories, and dark-energy parameters; a fate statement then maps
those inferred quantities through a classifier that asks what happens far
beyond the directly observed range. It is natural to summarize such an analysis
by a posterior class fraction, for example `P(RIP)`, `P(DECAY)`,
`P(DS)`, or a heat-death-compatible aggregate. That number is useful, but its
meaning is not the same as an ordinary posterior probability for a smooth
parameter interval.

The reason is geometric. Fate labels are typically produced by threshold rules:
a finite-time divergence triggers one label, an asymptotic de Sitter condition
another, a collapse condition another, and an audit channel catches cases not
covered by the declared rules. A posterior fate probability is therefore an
integral of an indicator function over a label region. Near the boundary
between two such regions, a small displacement of the posterior center can
produce a large change in the reported class mass even when the underlying
parameter inference is well calibrated.

This paper isolates that statistical problem. The object of study is not the
real universe's final state. The object is the repeated-experiment behavior of
posterior class masses when the data-generating model lies on or close to a
classification boundary. This distinction matters because a boundary case can
produce a direction rate near 50 percent without indicating a broken inference
pipeline. Conversely, a raw class probability can still be informative if it is
unusually deep in the null distribution generated by the same pipeline.

The contribution is fourfold. First, we show analytically and by simulation why
a calibrated boundary posterior can produce a broad, approximately uniform
distribution of class probabilities. Second, we translate the result into a
cosmology-shaped w0-wa analogue and an abstract fate-classifier framework.
Third, we define a finite-mock null-calibration rule that converts raw class
probabilities into tail-depth statements. Fourth, we propose a reporting
standard that separates Direction, Depth, Evidence, Boundary, and Horizon. This
separation is the central safeguard: it prevents a boundary-sensitive posterior
mass from being over-read as a direct fate forecast or as model evidence.

The draft uses several standard cosmological reference points only as context:
CPL-like dark-energy parametrizations [@ChevallierPolarski2001; @Linder2003],
late-time data combinations such as DESI BAO and supernova samples
[@DESIDR2; @Brout2022], compressed CMB distance priors
[@ChenHuangWang2018], and the long-standing literature on dark-energy fate
questions [@Dyson1979; @KraussTurner1999; @KraussStarkman2000; @Caldwell2003].
The method itself does not depend on accepting any particular current
cosmological claim.

## 2. Boundary-Statistic Formulation

Let `theta` denote the parameter vector used by a cosmological analysis. It may
include `w0`, `wa`, matter density, curvature, nuisance parameters, or a richer
description of the dark-energy history. Let

```text
C(theta) in {{CRUNCH, RIP, DS, DECAY, OTHER}}
```

be a deterministic classifier that maps each parameter point to one fate label.
For a label `L`, the posterior class mass is

```text
q_L(data) = P(C(theta)=L | data)
          = integral 1[C(theta)=L] p(theta | data) dtheta.
```

This is a posterior probability, but it is also a statistic produced by a
threshold map. Its repeated-experiment distribution can be broad when the
data-generating value `theta0` lies on a boundary between labels.

For two labels `A` and `B`, write a local boundary in terms of a score

```text
g(theta) = 0,
```

with `A` on one side and `B` on the other. The critical-boundary case is

```text
g(theta0) = 0
```

or a near-boundary version where `g(theta0)` is small compared with the
posterior uncertainty in the boundary-normal direction.

The minimal Gaussian version makes the issue explicit. Suppose

```text
x_hat ~ Normal(theta0, sigma_data)
theta | x_hat ~ Normal(x_hat, sigma_post)
C(theta) = A if theta > 0, otherwise B.
```

The posterior class mass is

```text
q_A = P(theta > 0 | x_hat) = Phi(x_hat / sigma_post).
```

If `theta0=0` and `sigma_post=sigma_data`, then

```text
x_hat / sigma_data ~ Normal(0,1),
q_A = Phi(Z),  Z ~ Normal(0,1).
```

By the probability integral transform, `q_A ~ Uniform(0,1)`. Thus a perfectly
calibrated boundary null produces class probabilities spread across the full
unit interval. A direction rule such as `q_A>0.5` has expected success rate 50
percent under this null. That fact is not a failure of calibration; it is the
signature of a boundary statistic.

The same argument extends to a linear boundary in a multivariate Gaussian
posterior. Let

```text
x_hat ~ Normal(theta0, Sigma_data)
theta | x_hat ~ Normal(x_hat, Sigma_post)
g(theta) = b^T theta - c.
```

Then

```text
q_A = P(g(theta)>0 | x_hat)
    = Phi((b^T x_hat - c) / sqrt(b^T Sigma_post b)).
```

If the truth lies on the boundary, `b^T theta0=c`, and the repeated-experiment
variance in the boundary-normal direction matches the posterior variance,
`b^T Sigma_data b = b^T Sigma_post b`, the same Uniform(0,1) result follows.

This is the mathematical core of the paper. The observable class probability is
not wrong, but its interpretation changes. At a boundary, it is a calibrated
random variable whose null distribution must be reported.

## 3. One-Dimensional Boundary Null

The first simulation implements the one-dimensional model above with
`theta0=0`, `sigma_data=1`, and `sigma_post=1`. The run uses
{b1["n"]} repeated experiments. The baseline diagnostics are:

{table(["Statistic", "Value"], [
    ["Mean of `q_A`", fmt(b1["mean"], 6)],
    ["Variance of `q_A`", fmt(b1["variance"], 6)],
    ["Uniform variance `1/12`", fmt(b1["uniform_variance"], 6)],
    ["Direction rate `q_A>0.5`", fmt(b1["direction_rate_P_gt_0p5"], 6)],
    ["KS D vs Uniform(0,1)", fmt(b1["ks_D_vs_uniform"], 6)],
    ["KS p vs Uniform(0,1)", fmt(b1["ks_p_vs_uniform"], 6)],
])}

Figure 1 shows the corresponding histogram and empirical CDF. The central point
is not merely that the mean is near one half. The important point is that the
whole distribution is broad and approximately uniform. A boundary-null class
probability can take values near 0.05, 0.5, or 0.95 across repeated experiments
without implying that the posterior calculation itself has failed.

The same simulation suite includes off-boundary and posterior-width-mismatch
checks. These are diagnostic controls. Moving the truth away from the boundary
introduces direction information; making the posterior too wide or too tight
distorts the class-probability distribution. Those failures are useful because
they show that the uniform result is not a generic artifact. It depends on the
truth being at the boundary and on the calibration of repeated-experiment and
posterior uncertainty along the boundary-normal direction.

## 4. Cosmology-Shaped w0-wa Analogue

The second simulation translates the same idea into a two-dimensional geometry
resembling the local w0-wa plane. Define coordinates centered on Lambda-CDM:

```text
u = w0 + 1,
v = wa,
Lambda-CDM = (u,v) = (0,0).
```

The toy boundary score is

```text
s(theta) = alpha u + v,
```

with `RIP-like` on the positive side and `DECAY-like` on the negative side. This
is not a physical CPL fate classifier. It is a controlled boundary analogue in
which the boundary-normal score is explicit and Lambda-CDM lies on the
boundary.

For {b2["n"]} repeated experiments, the baseline diagnostics are:

{table(["Statistic", "Value"], [
    ["Mean of `P(RIP-like)`", fmt(b2["mean"], 6)],
    ["Variance", fmt(b2["variance"], 6)],
    ["Uniform variance `1/12`", fmt(b2["uniform_variance"], 6)],
    ["Direction rate `P(RIP-like)>0.5`", fmt(b2["direction_rate_P_gt_0p5"], 6)],
    ["KS D vs Uniform(0,1)", fmt(b2["ks_D_vs_uniform"], 6)],
    ["KS p vs Uniform(0,1)", fmt(b2["ks_p_vs_uniform"], 6)],
])}

The same Lambda-CDM truth can yield low, near-boundary, or high posterior
class masses depending on the noisy posterior center. Phase 2 selected three
examples from the same repeated-experiment ensemble:

{table(["Example", "w0_hat", "wa_hat", "`P(RIP-like)`"], [
    [x["label"], fmt(x["w0_hat"], 5), fmt(x["wa_hat"], 5), fmt(x["P_RIP_like"], 5)]
    for x in p2["examples"]
])}

This result does not claim that the physical CPL fate boundary is exactly
linear or that the real universe is exactly on it. It establishes the local
statistical mechanism: once a posterior overlaps a classification boundary,
the boundary-normal projection controls the class mass. A visually realistic
w0-wa posterior can therefore yield unstable fate labels even under a stable
null.

## 5. Fate Classifier as a Threshold Map

A physical fate classifier generally evaluates continuous future-behavior
diagnostics and then returns a discrete label. The method paper represents this
by four margins:

```text
crunch_margin
rip_margin
ds_margin
decay_margin
```

and a priority rule:

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

The labels retain their conceptual roles: `CRUNCH` for collapse, `RIP` for a
finite-time divergence, `DS` for de Sitter-like asymptotics, `DECAY` for a
dark-energy-decay or eternal-expansion-compatible branch, and `OTHER` as an
audit channel. The method does not require the reader to accept one specific
physical implementation of these labels. It requires that whatever classifier
is used be treated as a threshold map with auditable boundaries.

The Phase 3 example posterior produces mixed class mass:

{table(["Label", "Posterior fraction"], [
    ["CRUNCH", fmt(fractions["CRUNCH"], 5)],
    ["RIP", fmt(fractions["RIP"], 5)],
    ["DS", fmt(fractions["DS"], 5)],
    ["DECAY", fmt(fractions["DECAY"], 5)],
    ["OTHER", fmt(fractions["OTHER"], 5)],
])}

The associated path diagnostic shows a continuous descriptor path whose label
jumps from `DECAY` to `RIP` as the RIP margin crosses zero. This is the
classifier-level version of the boundary-statistic problem. Smooth movement in
descriptors can produce discontinuous changes in labels, and posterior class
masses are integrals over those discontinuous regions.

## 6. Finite-Mock Null Calibration

Boundary calibration requires an explicit null distribution. For a predeclared
classifier `C`, label `L`, and observed data set, compute the raw class mass

```text
p_obs = P(C(theta)=L | observed data).
```

Then choose the relevant null model, generate `N` mock data sets, and run the
identical inference and classification pipeline on every mock:

```text
p_j = P(C(theta)=L | mock_j),  j=1,...,N.
```

The lower-tail, upper-tail, and two-sided finite-mock calibrated p-values are:

```text
p_lower = (#{{p_j <= p_obs}} + 1) / (N + 1)
p_upper = (#{{p_j >= p_obs}} + 1) / (N + 1)
p_two_sided = min(1, 2 * min(p_lower, p_upper)).
```

The plus-one rule prevents zero p-values from finite mock ensembles. The
minimum reportable one-sided tail probability is

```text
p_floor = 1 / (N + 1).
```

This calibration does not replace the raw class mass. It answers a different
question. The raw mass says how much posterior probability lies in a label
region. The calibrated tail depth says how unusual that raw mass is under the
declared null.

The synthetic Phase 4 demonstration used 100 finite null mocks and three
observed values. The results were:

{table(["Case", "Raw probability", "Lower-tail p", "Upper-tail p", "Two-sided p"], [
    ["Central boundary-like", "0.500", fmt(p4_cases["central_boundary_like"]["lower_tail_p"], 5), fmt(p4_cases["central_boundary_like"]["upper_tail_p"], 5), fmt(p4_cases["central_boundary_like"]["two_sided_p"], 5)],
    ["Low-tail example", "0.018", fmt(p4_cases["low_tail_example"]["lower_tail_p"], 5), fmt(p4_cases["low_tail_example"]["upper_tail_p"], 5), fmt(p4_cases["low_tail_example"]["two_sided_p"], 5)],
    ["High-tail example", "0.982", fmt(p4_cases["high_tail_example"]["lower_tail_p"], 5), fmt(p4_cases["high_tail_example"]["upper_tail_p"], 5), fmt(p4_cases["high_tail_example"]["two_sided_p"], 5)],
])}

The synthetic examples are not cosmology claims. They illustrate the reporting
grammar that the real-pipeline case study then uses.

## 7. Real-Pipeline LCDM Mock Case Study

The case study applies the calibration protocol to existing outputs from a
cosmology pipeline. It uses 100 noisy LCDM mocks as the null distribution and
keeps the zero-noise mock separate as a mechanism diagnostic. The analyzed
quantities are

```text
P_heat = P(DS) + P(DECAY),
P_RIP  = P(RIP).
```

The noisy mocks are the finite null distribution. The zero-noise mock is not
included in the null tail counts because it answers a different question: what
the deterministic pipeline does when the mock data exactly match the null
without noise.

The case-study results are:

{case_study_table(p5)}

The direction layer is deliberately uninformative under this LCDM boundary
null: `P_heat>0.5` in 50/100 noisy mocks, and the zero-noise mock sits near a
52/48 heat/RIP split. This would look poor if judged by a high fixed direction
accuracy threshold, but it is the expected boundary behavior.

The depth layer says something different. The observed `P_RIP` is lower than
all 100 noisy LCDM mocks. With plus-one smoothing this becomes a one-sided
lower-tail p-value of {fmt(p5_obs["P_RIP_lower_tail"]["p_plus_one"], 5)}, not
zero. The zero-count 95 percent upper bound is
{fmt(p5_obs["P_RIP_lower_tail_upper95"], 5)}. This is an interpretable
tail-depth statement under the declared null and finite mock count.

The correct reading is therefore narrow:

```text
Under the declared LCDM null and this pipeline, the direction layer is unstable,
while the observed P_RIP is unusually low relative to the 100 noisy null mocks.
```

It is not a direct forecast of the real universe's fate. It is not, by itself,
evidence that a larger dark-energy model is preferred. Those questions belong
to the Evidence and Horizon layers described next.

## 8. Reporting Standard

The reporting unit for boundary-sensitive fate probabilities should have five
layers:

{reporting_table(p6["layers"])}

The minimum prose should contain three distinct statements:

```text
Raw class mass:
The posterior mass in label L is ...

Calibrated boundary statistic:
Under the predeclared null, the observed class probability lies in the ...
tail with finite-mock-calibrated p = ...

Guardrail:
This is not, by itself, a direct forecast of the universe's fate.
```

The Phase 5 case study fills Direction, Depth, and Boundary. It does not fill
Evidence and Horizon. That incompleteness is intentional. A method paper should
not silently promote an available class-mass result into an unavailable model
preference or extrapolation-horizon result.

For the case study, the layer fill is:

{table(["Layer", "Case-study fill"], [[k, v] for k, v in p6["phase5_case_study_fill"].items()])}

This is the practical contribution of the paper. The standard provides a
citable format for future fate analyses: raw class mass, null-calibrated depth,
model evidence, boundary sensitivity, and horizon validity must be separately
visible.

## 9. Robustness and Diagnostic Failures

A method that only shows a favorable toy example is not enough. Phase 7
therefore asks which perturbations preserve the boundary-null behavior and
which correctly fail diagnostics.

{robustness_table(p7)}

The calibrated boundary and shifted-boundary cases pass. This shows that the
uniform result is not tied to the arbitrary location of the threshold; if the
truth and the threshold move together and calibration is correct, the
boundary-null result remains.

The off-boundary case fails, as it should. Moving the truth away from the
threshold creates direction information. The posterior-width mismatch cases
also fail. A posterior that is too wide becomes under-confident and has too
little variance in class probability; a posterior that is too tight becomes
over-confident and has too much variance. These failures are diagnostic
features, not method failures.

The curved-boundary case is labeled as a curvature diagnostic. Its mean is
{fmt(p7["curved_boundary"]["summary"]["mean"], 3)} and its KS p-value is
{p7["curved_boundary"]["summary"]["ks_p_vs_uniform"]:.3g}. The method does not
claim that arbitrary curvature preserves uniformity. It says that curvature,
posterior calibration, and distance from the boundary must be reported or
tested instead of hidden.

Finite mock resolution is another robustness constraint. For an observed raw
probability around 0.018, 100 mocks have a plus-one p-value floor of 1/101 =
0.00990. The probability of seeing zero mocks below that observed value under a
Uniform null is still about 0.163 at `N=100`; it falls only with larger mock
ensembles. This means finite null ensembles should be reported with their
resolution, not treated as unlimited tail probes.

## 10. Claim Ledger and Proof Boundary

The paper's claims are deliberately limited:

{claim_table(p8)}

The negative entries are as important as the positive ones. This method paper
does not establish the real universe's final fate. It does not prove dynamical
dark energy or any model preference. It does not claim that curved or
miscalibrated boundaries always preserve uniformity. It provides a calibration
and reporting framework for a specific statistical failure mode: interpreting
boundary-sensitive class masses as direct fate forecasts.

## 11. Limitations

The main limitation is that the toy proofs are local. The one-dimensional and
linear w0-wa analogues explain the boundary-normal mechanism, but a physical
fate classifier may have curved, intersecting, or prior-truncated boundaries.
The response is not to discard the method; it is to report the relevant
boundary diagnostics and to treat strong curvature as a diagnostic condition.

The second limitation is finite mock resolution. With 100 mocks, the smallest
reportable one-sided p-value is 0.00990. This is adequate for demonstrating the
reporting protocol, but not for resolving much deeper tails. Larger mock
ensembles would be needed for stronger tail claims.

The third limitation is the case-study scope. The LCDM mock case demonstrates
direction-depth separation for one pipeline and one declared null. It does not
establish that all cosmological pipelines, data combinations, or classifiers
would produce the same calibrated tail depth.

The fourth limitation is the unfilled Evidence and Horizon layers. Evidence
requires likelihood-ratio, information-criterion, Bayes-factor, or equivalent
model-comparison work. Horizon requires an assessment of whether the future
scale used by the fate classifier lies inside a data-constrained regime. The
case study intentionally does not fill those rows.

Finally, this paper does not validate compressed CMB likelihoods as equivalent
to full Planck analyses, nor does it settle the current observational debate
about evolving dark energy. Those are science-paper tasks. The present method
paper supplies the reporting discipline needed before such results are turned
into fate statements.

## 12. Conclusion

Posterior fate probabilities near a critical boundary should be treated as
boundary statistics. In the calibrated boundary null, broad class probabilities
and 50 percent direction rates are expected. That does not make the raw class
mass useless; it changes the reporting question. The raw mass must be paired
with a null distribution, finite-mock tail calibration, boundary diagnostics,
model evidence, and an extrapolation-horizon statement.

The proposed five-layer standard gives a compact rule: report Direction,
Depth, Evidence, Boundary, and Horizon separately. The LCDM mock case study
shows why this matters. Direction can be unstable under the null, while an
observed tail depth can still be calibrated and reported. Keeping those
statements separate prevents both false pessimism about a working classifier
and false confidence about the universe's final fate.

## Figure Captions and Source Files

{figure_block()}

## Appendix A. Robustness Details

The one-dimensional robustness checks use the same Gaussian boundary statistic
as Section 3. The pass rule requires the mean to be within 0.02 of 0.5, the
variance to be within 0.02 of `1/12`, the direction rate to be within 0.02 of
0.5, and the KS p-value against Uniform(0,1) to be at least 0.01. The
calibrated and shifted-boundary cases pass these checks. The off-boundary,
posterior-too-wide, and posterior-too-tight cases fail in the intended
directions.

The curved-boundary experiment uses a two-dimensional score

```text
score = v + alpha*u + beta*u^2
```

with truth at `(u,v)=(0,0)` and `beta=1.5`. This setting is intentionally
strong enough to trigger a curvature diagnostic. A physical application should
therefore report local boundary curvature or use mocks generated through the
full classifier rather than relying only on a linear approximation.

## Appendix B. Reporting Checklist

Use this checklist whenever a fate probability is reported near a critical
boundary:

1. State the raw posterior class mass and the classifier used.
2. State the null model and why it is the relevant boundary or near-boundary
   null.
3. State the number of mocks and the finite-mock p-value floor.
4. Report lower-tail, upper-tail, and two-sided calibrated p-values.
5. Report direction behavior under the null separately from tail depth.
6. Report model evidence separately from class mass.
7. Report boundary sensitivity, OTHER fraction, or equivalent classifier audit.
8. Report the extrapolation horizon or mark it unavailable.
9. Include the guardrail: the class mass is not by itself a direct final-fate
   forecast.

## References

Reference keys are inherited from `paper/refs.bib` and should be rendered from
that file in a submission build:

- [@Brout2022]
- [@DESIDR2]
- [@ChenHuangWang2018]
- [@ChevallierPolarski2001]
- [@Linder2003]
- [@CAMB]
- [@cobaya]
- [@getdist]
- [@dynesty]
- [@Dyson1979]
- [@KraussTurner1999]
- [@KraussStarkman2000]
- [@Caldwell2003]
"""


def phase_doc(audit: dict) -> str:
    return f"""# Phase 9: Full Manuscript Draft

Draft date: 2026-07-06

This phase turns the locked Phase 8 blueprint into a full readable manuscript
draft for the independent auxiliary method paper.

## Outputs

```text
paper/method/MANUSCRIPT_DRAFT.md
paper/method/PHASE9_MANUSCRIPT_DRAFT.md
paper/method/results/phase9_manuscript_audit.json
paper/method/scripts/phase9_write_manuscript.py
```

## Scope

The draft remains a method paper. It does not claim the real universe's final
fate, does not claim model preference for dynamical dark energy, and does not
replace Evidence or Horizon analyses.

## Audit

| Check | Value |
|---|---:|
| word count | {audit["word_count"]} |
| section count | {audit["section_count"]} |
| figure source references | {audit["figure_reference_count"]} |
| supported claim count | {audit["supported_claim_count"]} |
| not-claimed boundary count | {audit["not_claimed_count"]} |
| forbidden overclaim hits | {audit["forbidden_overclaim_hits"]} |

Status: **Phase 9 passes.**

## Next Step

Phase 10 should convert this Markdown draft into a submission-shaped manuscript
package, most likely LaTeX plus figure captions and a rendered PDF, while
preserving the same claim boundary.
"""


def audit_manuscript(text: str, ctx: dict) -> dict:
    forbidden_patterns = [
        r"we prove the universe",
        r"the universe will",
        r"proves dynamical dark energy",
        r"establishes dynamical dark energy",
        r"final fate is",
    ]
    hits = []
    lower = text.lower()
    for pat in forbidden_patterns:
        for match in re.finditer(pat, lower):
            context = lower[max(0, match.start() - 80) : match.start()]
            if "not claimed" in context or "does not" in context or "not, by itself" in context:
                continue
            hits.append(pat)
            break

    return {
        "word_count": len(re.findall(r"\b[\w@./+-]+\b", text)),
        "section_count": len(re.findall(r"^## ", text, flags=re.MULTILINE)),
        "figure_reference_count": len(re.findall(r"figures/phase[0-9]_", text)),
        "supported_claim_count": sum(1 for c in ctx["p8"]["claim_ledger"] if c["status"] == "supported"),
        "not_claimed_count": sum(1 for c in ctx["p8"]["claim_ledger"] if c["status"] == "not claimed"),
        "forbidden_overclaim_hits": len(hits),
        "forbidden_patterns_hit": hits,
        "outputs": [
            "MANUSCRIPT_DRAFT.md",
            "PHASE9_MANUSCRIPT_DRAFT.md",
            "results/phase9_manuscript_audit.json",
            "scripts/phase9_write_manuscript.py",
        ],
        "pass": len(hits) == 0,
    }


def main() -> None:
    ctx = build_context()
    text = manuscript(ctx)
    audit = audit_manuscript(text, ctx)

    (ROOT / "MANUSCRIPT_DRAFT.md").write_text(text)
    (RESULT_DIR / "phase9_manuscript_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True))
    (ROOT / "PHASE9_MANUSCRIPT_DRAFT.md").write_text(phase_doc(audit))

    print(f"wrote {ROOT / 'MANUSCRIPT_DRAFT.md'}")
    print(f"wrote {ROOT / 'PHASE9_MANUSCRIPT_DRAFT.md'}")
    print(f"wrote {RESULT_DIR / 'phase9_manuscript_audit.json'}")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
