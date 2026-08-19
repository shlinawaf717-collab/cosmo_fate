# WP6 growth-data decision

Decision date: 2026-08-19

Status: **GO for staged implementation using a DR1 FS+BAO replacement; no
growth inference or fate calculation is yet authorized.**

## Current public-data finding

The official DESI DR2 publication page currently exposes the DR2 galaxy/QSO
and Ly-alpha BAO cosmology products and a DR2 Ly-alpha Alcock--Paczynski
result.  It also lists validation work for a DR2 Ly-alpha full-shape analysis,
but the official DR2 public `y3` product root contains only the
`bao-cosmo-params/` cosmology product and no downloadable DR2 full-shape
likelihood/covariance package at the time of this decision.

DESI now separately provides a complete official DR1 Full-Shape+BAO route:

- [DR1 Full-Shape cosmology result documentation](https://data.desi.lbl.gov/doc/releases/dr1/vac/full-shape-cosmo-params/)
  publishes chains and maxima for validation;
- [DR1 Full-Shape+BAO clustering products](https://data.desi.lbl.gov/doc/releases/dr1/vac/full-shape-bao-clustering/)
  publish the data vectors, windows, covariance matrices, systematic
  contributions, and recommended packaged likelihood files;
- [official DESI KP cosmological likelihood repository](https://github.com/cosmodesi/desi-kp-cosmological-likelihoods)
  publishes the Cobaya Full-Shape+BAO likelihood and theory adapter.

The code is pinned to commit
`7d51f4f86dc3bee6bf10f1a684913c943a89a844`.  The data release is
`full-shape-bao-clustering/v1.0`; its 66-file likelihood checksum ledger has
SHA256 `3e1a5f17dcf068eb535c25f5c6c56a028a86e79e5804e4069dcb14d424034065`.

## Selected likelihood

Use the official `desi_fs_bao_all` configuration with observable
`spectrum-poles-rotated+bao-recon` and the recommended
`syst-rotation-hod-photo` GCcomb HDF5 products for:

- BGS, `0.1 < z < 0.4`;
- LRG, `0.4 < z < 0.6`;
- LRG, `0.6 < z < 0.8`;
- LRG, `0.8 < z < 1.1`;
- ELG, `1.1 < z < 1.6`;
- QSO, `0.8 < z < 2.1`;
- Ly-alpha BAO, `1.8 < z < 4.2` (BAO only, not a galaxy full-shape growth
  contribution).

Each galaxy/QSO HDF5 likelihood contains the joint power-spectrum and
post-reconstruction BAO observable, window and covariance, including the
declared HOD, rotation and photometric systematic contributions.  The public
likelihood uses the official per-tracer joint covariance and sums the declared
tracer/redshift likelihood blocks.

The nuisance model samples `b1p`, `b2p`, and `bsp` per full-shape tracer,
fixes `b3p=0`, and analytically marginalizes the registered counterterm and
stochastic subset (`alpha0p`, `alpha2p`, `sn0p`, `sn2p`) with its declared
Gaussian prior scales.  The theory adapter uses CAMB linear density/velocity
power, cosmoprimo filtering, and velocileptors EPT multipoles.

## Overlap and replacement rule

DR1 is a subset of the first-three-year DR2 survey sample.  The DR1 FS+BAO
likelihood uses BGS/LRG/ELG/QSO/Ly-alpha tracers and redshift intervals that
overlap the DR2 BAO points already used by WP4 F1.  No public joint covariance
between the DR1 full-shape likelihood and the DR2 BAO likelihood was found.

Therefore **addition is prohibited**.  The only authorized WP6 combination is
a complete replacement:

1. remove `bao.desi_dr2.desi_bao_all` and every DR2 BAO datum;
2. insert the single official DR1 `desi_fs_bao_all` likelihood, which already
   includes its matched DR1 BAO information;
3. retain the WP4 F1 Pantheon+SH0ES and full-CMB/lensing blocks unchanged.

This produces a secondary **DR1-growth replacement analysis**, not an update
of the primary DR2 F1 result.  Differences combine growth information with the
DR1-versus-DR2 survey-volume change and are interpreted accordingly.

## Model and role

The primary WP6 model is the WP4 F1 flat CPL+P1 model under the replacement
above.  WP6 asks whether adding an executable full-shape growth likelihood in
a non-double-counted data combination materially changes the finite-redshift
CPL posterior and its conditional fate probability.  It does not establish a
model-independent growth measurement or replace WP4.

## Hard pre-inference gates

This GO decision permits implementation only.  Before any WP6 production
sample or fate calculation:

1. download the seven selected HDF5 files and verify their official SHA256;
2. archive the pinned likelihood code and dependency lock, including
   `lsstypes`, `cosmoprimo`, and `velocileptors`;
3. pass a no-sampling Cobaya initialization using the replacement config;
4. reproduce an official DR1 CPL+FS+BAO reference combination at a frozen
   fixed point and posterior/maximization benchmark;
5. freeze chains, seeds, nuisance blocking, convergence and stopping rules;
6. commit and publicly timestamp every artifact before fate classification.

Failure of code installation, data integrity, reference reproduction, or a
non-double-counted replacement implementation converts WP6 to a documented
No-Go.  Marginal `f sigma8` points, covariance-free combinations, importance
reuse of public chains, and simultaneous DR1 FS+BAO plus DR2 BAO remain
forbidden.
