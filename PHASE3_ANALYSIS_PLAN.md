# Phase 3 paired analysis plan v1 — frozen before pilot execution

Milestone 4A validates execution and integrity only. No comparative effect sizes
are computed here. Primary dimensions remain in `phase3/configs/primary.json`:
480 realized workloads and 19,200 runs. The proposed 640 controls remain separate;
their concrete conditions require a separate specification before execution.

## Estimands and pairing

For each length/split/arrival regime, budget, compute setting, and seed, compare
each paged block size against fixed on the identical realized workload hash.
The primary outcomes are mean end-to-end latency, nearest-rank p95 end-to-end
latency, and makespan. Secondary mean progressing requests equals total generated
output / makespan, so it is not independent corroboration of makespan.

Report absolute paired difference `paged - fixed` and relative paired difference
`(paged - fixed) / fixed`, multiplying by 100 only for presentation as percent.
Negative differences improve latency/makespan; positive differences improve mean
progressing requests. Always report regressions and ties. If fixed is zero, the
relative difference is undefined (`null`), including zero/zero; retain the absolute
difference and report the number of excluded relative comparisons. Do not silently
substitute zero or infinity. Empty-workload percentiles are undefined; the frozen
200-request positive-output workloads do not have empty populations.

## Aggregation, uncertainty, and multiplicity

The seed is the unit of replication, not an individual request. Within each full
regime/budget/compute cell report equal-weight means of seed-level paired absolute
and relative differences, their distributions, and win/tie/loss counts. Do not
replace mean paired percentages with a ratio of pooled means. Any overall summary
weights all specified cells and seeds equally and must accompany the cell-level
results; it is a designed-grid summary, not a production traffic estimate.

Use a paired seed-cluster bootstrap with 10,000 resamples and independent analysis
RNG seed 20261118. Resample the 20 seed IDs with replacement, retaining all strategies,
regimes, budgets, and compute settings for each sampled seed. This preserves
cross-condition dependence from reused RNG streams. Report pointwise percentile
95% intervals, clearly labeled descriptive and not family-wise significant.
One pilot seed cannot estimate across-seed uncertainty; no pilot confidence
intervals or effect-based condition selection are permitted.

Three paged comparisons times three primary outcomes over 24 regime cells, five
budgets, and two compute settings yields 2,160 planned cell comparisons. The
initial report is descriptive: no confirmatory significance declarations based
on unadjusted pointwise intervals. Any later confirmatory testing must preregister
a smaller hypothesis family or a family-wise procedure before inspecting full
results. Secondary metrics, additional subgroup analyses, controls, and any
post-hoc changes are labeled exploratory. Report all planned cells, missingness,
and exclusions; do not choose workloads, seeds, budgets, or block sizes from
favorable smoke/pilot outcomes. Execution timing may govern resource planning
only, never scientific condition selection.

## Interpretation limits

Admission waiting, peak active requests, growth stalls, compute deferrals, and
memory allocation are diagnostic. Earlier admission may coexist with later
completion. Compute-limited or sparse-arrival cases may show no scheduling gain;
rounding and protection may worsen results. Do not assume paging wins.

This deterministic scheduler models fungible token slots, not GPU throughput,
allocator cost, prefill compute, bandwidth, block sharing, swapping, or vLLM's
implementation. Seed uncertainty reflects the specified workload generator, not
hardware variability or representativeness of production requests. Timing this
Python program assesses experimental execution cost only.
