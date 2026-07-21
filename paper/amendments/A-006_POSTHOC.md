# A-006 — BIN4 early-dark-energy gate and full-Planck scope audit

**Date:** 2026-07-21
**Status:** author-confirmed post-hoc robustness and scope amendment
**Identity:** not preregistered

## Trigger

The earlier condition `w4 < 0` was described as keeping early dark energy
subdominant. That implication is false: values just below zero can retain a
non-negligible dark-energy fraction near recombination/drag.

## Hard gate

All future BIN4 fits must impose

`rho_DE / rho_m (z = 1059) < 0.01`.

The gate is implemented in `pipeline.early_de_gate.Bin4EarlyDEGate`, with a
replication configuration in `pipeline/fparam_bin4_a006.yaml`. A weighted
audit of the archived post-burn BIN4 chains finds zero violating posterior
mass; the largest sampled ratio is `8.62e-5`. The existing posterior therefore
does not require refitting for this gate, and its fate probabilities are
unchanged.

## Full-Planck feasibility

A full Planck likelihood run was examined as the stronger validation. It is a
No-Go for the current pipeline: `BackgroundW` is a geometry-only background
solver and does not provide CMB angular spectra or perturbation evolution.
The full likelihood also requires the official likelihood/nuisance package.
Replacing it with the existing distance prior would not constitute a
full-Planck run.

## Consequence

BIN4 results are explicitly reported as **compressed-CMB-conditioned**. They
are not promoted to full-Planck constraints. Restart requires a validated
Boltzmann perturbation implementation for BIN4, installed Planck likelihood
data, and a CPL full-likelihood reproduction gate before the BIN4 fit.
