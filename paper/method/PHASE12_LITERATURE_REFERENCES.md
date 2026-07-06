# Phase 12: Literature and Reference Hardening

Draft date: 2026-07-06

This phase upgrades the manuscript from locally sufficient citations to a
submission-ready reference spine.

| Role | References | Purpose |
|---|---|---|
| PIT / boundary-uniform theorem | Rosenblatt 1952 | Supports probability-integral-transform logic used in the toy theorem. |
| Forecast calibration framing | Dawid 1984 | Positions the paper as calibration/reporting rather than fate discovery. |
| Predictive checks | Rubin 1984; Gelman, Meng, and Stern 1996 | Connects null mocks to predictive-model checking language. |
| Finite mock p-values | Phipson and Smyth 2010 | Supports the rule that finite simulation p-values should never be zero. |
| CPL parametrization | Chevallier and Polarski 2001; Linder 2003 | Context for w0-wa geometry. |
| Current data context | DESI DR2; Pantheon+; Planck distance priors | Context only; not used as a science claim in the method paper. |
| Fate lineage | Dyson; Krauss and Turner; Krauss and Starkman; Caldwell et al. | Context for why fate classifications are scientifically meaningful. |

## Output

```text
paper/method/refs_method.bib
```

## Boundary

The added references support the method: PIT, predictive calibration,
posterior/mock checking, finite randomization p-values, and cosmology/fate
context. They do not add a new cosmological claim.

Status: **Phase 12 passes.**
