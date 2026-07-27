# WP3 off-boundary power report

| Truth | wa | profile chi2 | delta chi2 | Correct side | Direction power (exact 95%) | Depth power (exact 95%) | False sign (exact 95%) | Correct mass median [central 68%] |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| wam060 | -0.60 | 1489.46 | 0.00 | heat_death_compatible | 1.00 [0.964, 1.000] | 0.90 [0.824, 0.951] | 0.00 [0.000, 0.036] | 0.997 [0.968, 1.000] |
| wam030 | -0.30 | 1491.14 | 1.67 | heat_death_compatible | 0.93 [0.861, 0.971] | 0.47 [0.369, 0.572] | 0.07 [0.029, 0.139] | 0.922 [0.590, 0.988] |
| wam015 | -0.15 | 1493.52 | 4.05 | heat_death_compatible | 0.84 [0.753, 0.906] | 0.33 [0.239, 0.431] | 0.16 [0.094, 0.247] | 0.873 [0.526, 0.978] |
| wap015 | +0.15 | 1502.18 | 12.71 | RIP | 0.77 [0.675, 0.848] | 0.18 [0.110, 0.269] | 0.23 [0.152, 0.325] | 0.729 [0.411, 0.933] |
| wap030 | +0.30 | 1508.91 | 19.45 | RIP | 0.93 [0.861, 0.971] | 0.57 [0.467, 0.669] | 0.07 [0.029, 0.139] | 0.948 [0.670, 0.996] |
| wap060 | +0.60 | 1528.83 | 39.37 | RIP | 1.00 [0.964, 1.000] | 0.98 [0.930, 0.998] | 0.00 [0.000, 0.036] | 0.999 [0.984, 1.000] |

- Outer-point direction-power gate (`>=0.80`): **PASS**.
- Positive claim: direction classifier is powerful under the two registered outer-point alternatives (wam060 and wap060).
- Coarse monotonicity diagnostic: **NO_DISJOINT_INTERVAL_REVERSAL**; coarse descriptive safeguard only; overlapping exact intervals make this insensitive to moderate non-monotonicity, so a clear status is not separate evidence of classifier power.

Power is truth-specific. The six declared alternatives have different profile chi-square penalties against the observed D0 data and are not a symmetric sequence of equally supported effect sizes. WP3 establishes strong direction power under the two registered outer-point alternatives; it does not establish that the observed universe occupies any one off-boundary truth.
