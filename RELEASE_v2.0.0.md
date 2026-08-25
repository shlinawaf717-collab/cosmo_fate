# Release v2.0.0 — manuscript closure freeze

Date: 2026-08-25

This release freezes the JCAP-ready manuscript and the completed scientific
scope after the author-directed closure of the computationally dominant WP4
nested and WP5 production campaigns.

## Reported scientific scope

- completed 500-mock fitted-truth LCDM calibration and registered
  truth-specific power study;
- four converged native-prior parametrization sensitivity results;
- completed WP7 seven-node SBC and real-data information-localization audit;
- completed WP8 fixed-history future-continuation and partial-identification
  audit.

WP4's unstarted nested verification and WP5's endpoint-blind, unconverged
production chains are preserved only as feasibility/provenance records. They
do not supply a posterior, likelihood, fate, evidence, or width-comparison
claim. No WP9 inference is included.

## Submission artifacts

- `output/pdf/cosmic_fate_jcap_submission_v1.pdf`
  - SHA-256: `817920acdd7f271814107d8923f34f98c3578958d91951df5387f6438acea5e6`
- `output/submission/cosmic_fate_jcap_submission_v1.tar.gz`
  - SHA-256: `d10c20c8aca39a0b34aa91a00703483c9306dddf454d20b2a7b10f92685dd4e4`
- `output/submission/cosmic_fate_jcap_submission_v1.zip`
  - SHA-256: `72b74a8ffe4d1e962076fe2cd2f9ebe00dacfc3eb453a6c51fd72f1c72b89602`

The source archives contain `main.tex`, `main.bbl`, `refs.bib`,
`numbers.tex`, the official JCAP style and bibliography files, and all seven
used figures. They exclude the compiled PDF, build intermediates, and unused
repository files. The archive compiles independently with Tectonic.

## Release verification

- paper-number generator rerun with byte-identical `paper/numbers.tex`;
- isolated source-archive compilation: PASS;
- `qpdf --check`: PASS;
- full 24-page visual contact-sheet review: PASS;
- all seven packaged figures byte-identical to their repository sources;
- full pipeline test suite: 231 passed.
