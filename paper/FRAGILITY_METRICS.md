# Registered fragility metrics (A-005 semantics)

The registered metric is `max(log10 P) - min(log10 P)` along each axis.

| Axis | Quantity | Result | Status | Range |
|---|---|---:|---|---|
| F_prior | P_RIP | infinite | structurally_unbounded_by_exact_zero | 0--0.0017919573 |
| F_prior | P_heat | 0.002 dex | finite | 0.9933293--0.99820804 |
| F_param | P_RIP | infinite | structurally_unbounded_by_exact_zero | 0--0.49958712 |
| F_param | P_heat | 0.301 dex | finite | 0.50041288--1 |
| F_param_fitted_four_diagnostic | P_RIP | 2.380 dex | finite | 0.0020812783--0.49958712 |
| F_param_fitted_four_diagnostic | P_heat | 0.300 dex | finite | 0.50041288--0.99791872 |
| F_data | P_RIP | 2.665 dex | finite | 8.131696e-06--0.003761024 |
| F_data | P_heat | 0.002 dex | finite | 0.99615922--0.99999187 |

Exact prior/construction zeros and finite-sampling zeros are not conflated.
