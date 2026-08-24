# WP7 common-function-prior outcome

Outcome date: 2026-08-24

Status: **PASS.** The 50-dataset FS7 simulation-based calibration campaign
passed its registered gates, all five real-data settings completed four-chain
transactional stopping, and the authorized endpoint report passed its source,
prefix, Monte Carlo precision, and accounting gates.  No model evidence or
between-setting Bayes factor was calculated.

## Registered fate endpoints

The fate boundary is the finite asymptotic node `w(a=4)`: `w<-1` is RIP,
exact `w=-1` is DS, and `w>-1` is DECAY.  The separate boundary budget is
`abs(w+1)<=0.01`; it does not replace the physical classification.

| setting | sigma_f | ell | prior P(RIP) | posterior P(RIP) | P(DECAY) | boundary | RIP MCSE |
|---|---:|---:|---:|---:|---:|---:|---:|
| primary | 0.50 | 0.70 | 0.4994 | 0.5063 | 0.4937 | 0.0168 | 0.00539 |
| sig025 | 0.25 | 0.70 | 0.4986 | 0.4821 | 0.5179 | 0.0321 | 0.00671 |
| sig100 | 1.00 | 0.70 | 0.4997 | 0.5220 | 0.4780 | 0.0088 | 0.00562 |
| ell035 | 0.50 | 0.35 | 0.5009 | 0.4996 | 0.5004 | 0.0158 | 0.00701 |
| ell140 | 0.50 | 1.40 | 0.5015 | 0.2676 | 0.7324 | 0.0187 | 0.00527 |

DS, CRUNCH, and OTHER posterior mass is zero in all five settings.  All five
registered RIP MCSE values are below `0.01`.  Across the frozen sensitivities,
posterior `P(RIP)` ranges from `0.2676` to `0.5220`; the maximum absolute
change from the primary setting is `0.2388`, at `ell=1.40`.

## Where the information comes from

The registered decomposition separates the marginal final-node posterior from
the residual

`r_f = y_f - C_fo C_oo^-1 y_o`,

which removes the part predicted from the four nodes at `a<=1` by the prior
covariance.  Forty-bin KL values are:

| setting | multiple R2 | conditional SD | final-node KL (nat) | residual KL (nat) |
|---|---:|---:|---:|---:|
| primary | 0.1348 | 0.4651 | 0.00148 | 0.00066 |
| sig025 | 0.1348 | 0.2325 | 0.00160 | 0.00042 |
| sig100 | 0.1348 | 0.9302 | 0.00214 | 0.00086 |
| ell035 | 0.00000053 | 0.5000 | 0.00065 | 0.00069 |
| ell140 | 0.9209 | 0.1406 | 0.19542 | 0.00058 |

The primary, amplitude-sensitivity, and short-correlation settings therefore
leave the asymptotic sign almost exactly at the symmetric-prior half point.
The long-correlation setting is different: its marginal final node moves, but
the conditional-residual KL remains about `5.8e-4` nat.  Its change in fate is
therefore overwhelmingly associated with the registered prior correlation
between observed-history and future nodes, not with appreciable independent
likelihood information in the future residual.

The deterministic global spline does give future-labelled nodes a small local
likelihood pathway over `a<=1`; the frozen squared whitened responses fall
from `57.10` at `a=1.5`, to `5.32` at `a=2`, to `0.0394` at `a=4`.  This is a
property of the global basis, not an observation made at future scale factor.

## Scientific interpretation

WP7 supports the paper's non-identifiability claim and makes it more precise.
A common function-space coordinate system does not by itself make cosmic fate
data-identified.  With weak coupling between the observed window and the
asymptotic node, the posterior fate remains approximately the symmetric prior
split.  With a long correlation length, the same data can instead be
transported into the future by the prior covariance and materially change the
marginal fate probability.  Thus the relevant sensitivity is not merely a
change of parameter coordinates: it is sensitivity to the prior measure and
to its assumed past--future coupling.

The `ell=1.40` result must not be described as observational evidence that
DECAY is the physical fate of the Universe.  It is a model-conditional
continuation result.  Conversely, the near-half results are not evidence that
RIP and DECAY are physically equiprobable; they show that the registered data
and weakly coupled symmetric prior do not resolve the sign of the asymptotic
node.

## Provenance and stopping note

Only the byte-exact prefixes stored in the five final-stop audits were read.
For `ell=1.40`, launchd restarted the driver during a roughly three-second
post-stop race and appended 176,633 complete rows across four chains.  Those
suffix rows remain preserved but were excluded from every endpoint; all four
audited prefixes reproduced their recorded SHA-256 hashes, row counts, and
newline boundaries.  The other four settings have no excluded suffix.

Machine-readable artifacts:

- `runs/prd_extension/wp7/production_system/wp7_endpoints.json`;
- `runs/prd_extension/wp7/production_system/postprocessing_audit.json`;
- `runs/prd_extension/wp7/production_system/postprocessing_authorization_v2.json`;
- `runs/prd_extension/wp7/production_system/*/external_monitor/final_stop_audit.json`;
- `runs/prd_extension/wp7/sbc/sbc_report.json`.
