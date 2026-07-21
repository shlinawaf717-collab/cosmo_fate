# Nested interface design note

The nested-sampling scripts share `pipeline/nested_core.py` for the stable pieces of the interface:

- `NestedRunConfig` records the model kind, sampled names, bounds, run controls, seed, and any evidence correction.
- `prior_transform`, `stable_normalized_weights`, and `resample_equal_weight` are pure NumPy utilities that can be tested without Cobaya, CAMB, or dynesty.
- `run_dynesty` is the only core entry point that imports dynesty, and the CLI adapters remain responsible for delayed Cobaya model construction.
- The recorded seed is passed to dynesty's random-state interface and reused for the declared fixed-seed equal-weight resample.
- Fate classification is passed in as a callback so the core does not hard-code CPL or JBP cosmology details.
- JSON output goes through `atomic_write_json`, which creates the parent directory and publishes by `os.replace`.

The legacy JSON keys remain in the adapters, while new audit fields record `schema_version`, `seed`, `resampling_method`, ESS, weighted/equal-weight sample counts, logZ/logZerr, and ncall.  The fixed-seed resampling binomial standard error is explicitly labeled as equal-weight resample variability, not repeated nested-run uncertainty.
