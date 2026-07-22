# WP2 local throughput benchmark

**Frozen before the first new WP2 MCMC result:** 2026-07-22
**Scope:** operational scheduling only; no scientific endpoint or stopping rule changes.

## Fixed pilot

- Machine: local Apple M5 MacBook Air, 10 CPU cores, 24 GB RAM.
- Batch A: mocks `m101`--`m108`, `--jobs=4` (two full waves).
- Batch B: mocks `m109`--`m120`, `--jobs=6` (two full waves).
- All 20 chains are production WP2 chains and remain in the 500-null ensemble.
- Seeds, likelihoods, convergence thresholds, and classification are unchanged.
- The campaign still runs through `m500`; speed measurements cannot stop it early.

## Scheduling decision

Use six workers for `m121`--`m500` only if Batch B improves completed-mock
throughput by at least 15% relative to Batch A, has no failed chain, and shows
no memory-pressure or thermal warning. Otherwise use four workers. A later
reduction in workers is allowed only for machine stability; it is logged and
does not alter any scientific setting.

Report wall time, mocks/hour, per-chain median and 90th-percentile elapsed time,
failure count, and final convergence/checkpoint status for both batches.
