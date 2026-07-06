# Fate-Probability Reporting Checklist

Use this template whenever reporting a posterior fate probability near a
critical boundary.

## Metadata

- Dataset / mock set:
- Model / parameterization:
- Classifier version:
- Null model:
- Number of null mocks:
- Finite-mock p-value floor:

## Required Layers

### Direction

Question: Which label has more posterior mass?

Required fields:

- [ ] raw P(label | data)
- [ ] direction threshold, usually 0.5
- [ ] same quantity under null mocks

Failure mode to avoid: Treating P > 0.5 as a discovery near a boundary.

### Depth

Question: How unusual is the raw probability under the null?

Required fields:

- [ ] predeclared null model
- [ ] mock count and finite-mock floor
- [ ] lower-tail, upper-tail, and two-sided calibrated p-values

Failure mode to avoid: Reporting a raw tail probability without null calibration.

### Evidence

Question: Does the enlarged model deserve preference?

Required fields:

- [ ] likelihood-ratio or delta chi2 where appropriate
- [ ] AIC/BIC or Bayes factor where available
- [ ] clear separation from fate-class probability

Failure mode to avoid: Confusing a class probability with evidence for the model.

### Boundary

Question: Is the label sensitive to thresholds or classifier defects?

Required fields:

- [ ] boundary-flip fraction or threshold sensitivity
- [ ] OTHER fraction and audit rule
- [ ] known classifier limitations

Failure mode to avoid: Hiding that posterior mass lies near a label boundary.

### Horizon

Question: Is the fate decision inside the data-constrained region?

Required fields:

- [ ] future scale used by the classifier
- [ ] constraint horizon or equivalent diagnostic
- [ ] statement when the horizon diagnostic is unavailable

Failure mode to avoid: Interpreting unconstrained far-future extrapolation as data.

## Minimum Claim Language

Raw class probability:

> The posterior mass in label L is ...

Calibrated boundary statistic:

> Under the predeclared null, the observed class probability lies in the ... tail with finite-mock-calibrated p = ...

Guardrail:

> This is not, by itself, a direct forecast of the universe's fate.
