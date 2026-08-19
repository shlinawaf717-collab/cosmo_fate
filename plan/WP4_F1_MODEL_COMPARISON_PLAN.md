# WP4 F1 best-fit and information-criterion plan

Status: frozen after the closed F1 MCMC posterior was unblinded and before any
F1 CPL or LCDM optimization result was generated.

The F1 CPL and flat-LCDM posterior maxima use Cobaya 3.6.2 Py-BOBYQA with the
same likelihood-only component-sum convention used for F0.  Gaussian nuisance
priors remain active while locating each posterior maximum; the reported
`Delta chi2` sums only the six non-aggregated likelihood components.  This is
the registered F0 convention and is not relabelled as a pure unconstrained MLE.

- one optimization per model, run in parallel with one numerical-library
  thread each;
- fixed seeds 2026081901 (CPL) and 2026081902 (LCDM);
- `max_evals=2000`, `rhoend=0.05`, `best_of=1`;
- the CPL start is the lowest-minus-log-posterior post-burn F1 MCMC row;
- the LCDM start uses the post-burn F1 weighted means of its 16 free
  parameters, with `w=-1` and `wa=0` fixed;
- the proposal metric is the integer-weighted post-burn F1 covariance, with
  the `w,wa` rows/columns removed for LCDM.  Starts and covariance affect only
  optimization efficiency, not the target.

Information criteria use `Delta IC = IC_CPL - IC_LCDM`.  Both models share all
nuisance parameters and `Mb`; CPL has two additional free parameters, so
`Delta k=2`, `Delta AIC=Delta chi2+4`.  The descriptive BIC uses the frozen
nominal concatenated data-vector size

`N=13 (DESI BAO) + 1701 (Pantheon+SH0ES) + 9915 (NPIPE CamSpec)`
` + 28 (low-l TT multipoles) + 28 (low-l EE multipoles)`
` + 27 (ACT+Planck lensing bandpowers) = 11712`,

so `Delta BIC=Delta chi2+2 ln(11712)`.  Because the two low-l likelihoods are
not ordinary independent Gaussian vectors, BIC is explicitly a descriptive
large-sample penalty, not an evidence substitute.  Multi-seed nested evidence
is reported separately.
