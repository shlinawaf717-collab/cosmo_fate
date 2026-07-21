# Nested interface design note

The nested-sampling scripts share `pipeline/nested_core.py` for the stable pieces of the interface:

- `NestedRunConfig` records the model kind, sampled names, bounds, run controls, seed, and any evidence correction.
- `prior_transform`, `stable_normalized_weights`, `weighted_class_probabilities`, and `resample_equal_weight` are pure NumPy utilities that can be tested without Cobaya, CAMB, or dynesty.
- `run_dynesty` is the only core entry point that imports dynesty, and the CLI adapters remain responsible for delayed Cobaya model construction.
- The recorded seed is passed to dynesty's random-state interface and reused for the declared fixed-seed equal-weight diagnostic.
- Fate classification is passed in as a callback so the core does not hard-code CPL or JBP cosmology details.
- JSON output goes through `atomic_write_json`, which creates the parent directory and publishes by `os.replace`.

The headline fate probability is the direct sum of normalized original nested
weights. The compressed NPZ archive stores every raw sample, `logwt`, normalized
weight, parameter name, bound, seed, ESS, and optional fate label. The legacy
`P_fate_nested` JSON key remains as an alias of `P_fate_weighted`; equal-weight
resampling and its binomial standard error are diagnostic only. Independent
D0 runs are aggregated with between-seed scatter reported separately from each
run's internal dynesty evidence error.

The v1.2 release uses independent D0 seeds 1, 2, and 3. Each seed writes one
JSON record plus separate CPL and LCDM NPZ archives; `aggregate_nested_d0.py`
then creates `runs/phase2/nested_d0.json`. The six D1--D4/CPL/JBP extension
records retain one declared seed apiece and are not assigned a run-to-run error
bar. `pipeline/audit_nested_archives.py` is the final inexpensive release gate:
it recomputes weights, ESS, and fate probabilities from every archived NPZ and
checks that the D0 aggregate cites three distinct seeds.
