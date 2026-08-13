# WP4 F1 Windows/WSL2 migration policy

Status: frozen after the Mac F1 launch and before any Windows/WSL2 F1 sample.

The Windows host may replace the Mac as the F1 production environment only
through x86-64 WSL2 Linux. Native Windows execution is not authorized. GPU
acceleration is not part of the target or performance assumption.

## Candidate disposition

- The briefly started Mac F1 chains remain a retained operational record.
- No Mac F1 sample or checkpoint may be copied into a Windows/WSL2 chain.
- Windows/WSL2 starts four fresh chains with the unchanged seeds 4511--4514,
  four jobs, and one numerical-library thread per chain.
- If the WSL2 preflight passes and WSL2 production begins, WSL2 is the sole
  F1 scientific chain set. The Mac chain set is excluded in full, regardless
  of either platform's later convergence speed or scientific result.
- If the WSL2 preflight fails before sampling, no WSL2 production starts and
  the Mac run may continue under its original frozen system.

## Required pre-production gates

All gates below must pass before a Windows/WSL2 chain sample is written:

1. platform reports Linux on x86-64 under WSL2;
2. the task-package SHA256 manifest verifies completely;
3. every likelihood input in the registered WP4 input manifest has the exact
   registered path, byte count, and SHA256;
4. Python and all locked scientific packages install at the declared
   versions, including CAMB 1.6.6, Cobaya 3.6.2, NumPy 2.5.0, SciPy 1.16.2,
   clipy-like 0.15, and act-dr6-lenslike 1.2.1;
5. the existing CAMB geometry/spectrum probe passes its frozen thresholds;
6. at the package's frozen full-F1 fixed point, total likelihood chi-square
   and every likelihood-component chi-square differ from the Mac reference by
   no more than 0.10 in absolute value;
7. the F1 no-sampling smoke test passes, including the two low-l clik
   self-checks, Pantheon+SH0ES, `Mb`, P1, NPIPE, ACT lensing, and DESI BAO;
8. the WSL2-local run YAMLs, run plan, policy, controller, finalizer, proposal,
   input manifest, and environment report are hashed before production.

The fixed-point comparison is an implementation-drift screen, not posterior
equivalence. Its pass does not by itself establish a scientific conclusion.

## Unchanged scientific and stopping rules

The target remains full-CMB/lensing F1 with Pantheon+SH0ES and CPL+P1. The
proposal is the already audited 17-dimensional F0 covariance plus the frozen
scalar proposal for `Mb`; a proposal never changes the target distribution.
The four-chain 18-dimensional R-1, burn-in-sensitivity, ESS, repeated-pass,
blinding, and reversible-finalizer rules in
`plan/WP4_F1_EXTERNAL_CONVERGENCE_POLICY.md` remain unchanged.

The Windows task pack must emit an environment/preflight artifact before
sampling and a result-return archive afterwards. Runtime diagnostics may not
show posterior locations, likelihoods, best fits, model-comparison results,
or fate quantities before the final external-stop audit.
