# Phase 3E-5 analysis implementation conventions

Frozen before calculating final contrasts, 2026-11-21.
Authority: [Phase 3 paired analysis plan](../../../PHASE3_ANALYSIS_PLAN.md).

## PRESPECIFIED

Use only the complete 19,200-condition 20-seed primary grid for primary
inference. The seed is the experimental unit. Within each seed, compare
paged8, paged16 and paged32 separately against fixed at the identical
workload hash, workload definition, memory budget and compute scenario.
Retain all 2,160 primary cells. The outcomes are mean end-to-end latency,
nearest-rank p95 end-to-end latency, and makespan, all in simulator ticks.
The seed-level absolute difference is paged minus fixed. The relative
difference is that difference divided by the fixed value, multiplied by
100 for presentation only. Negative is improvement for these outcomes.
Retain exact ties, adverse outcomes and absolute differences with zero
fixed denominators. Relative differences with zero denominators are
undefined and excluded from relative means, with exclusions counted.
Use equal-weight means over seed pairs within each cell.

Use 10,000 seed-cluster draws of size 20 with replacement, analysis RNG
seed 20261118, with the entire matched grid retained for each sampled
seed. Pointwise percentile 95% intervals are descriptive, without
multiplicity adjustment. No confirmatory significance declarations follow
from pointwise intervals. Secondary and diagnostic comparisons and the
ample-memory control are exploratory. Keep pilot and control records
outside the primary contrasts.

## PROSPECTIVELY CLARIFIED

Sort numeric seed IDs. Generate one shared index matrix with
`random.Random(20261118)` using `randrange(20)` in row-major order.
Record the matrix checksum. A draw's relative mean includes only defined
relative values, including repeats. An all-undefined draw is omitted and
counted. An all-undefined estimand and its endpoints remain null.
For sorted finite values of length n, interpolate linearly at zero-based
index `(n − 1) × p`, using p=0.025 and 0.975 for interval endpoints.
The same convention applies to distribution quartiles. Reconstruct latency
means from integer request ticks as exact fractions, use nearest rank
`ceil(0.95 × n)` for p95, and take makespan from the validated metric.
Determine signs and ties before numerical conversion. Retain fractions
for seed-level values and convert to float only for bootstrap arithmetic
and decimal display. Relative reports use percent.

Designed-grid summaries average the 240 cells with equal seed and cell
weights for each outcome and allocator. Their bootstrap uses the same
shared draws on seed-level grid averages. A designed-grid relative
summary is omitted if any grid cell contains an undefined relative
denominator. Diagnostic occupancy uses the budget denominator; pooled
fragmentation divides unused allocated slot-ticks by total allocated
slot-ticks and keeps protected headroom separate. For progressing
requests, higher is favorable and the field is dependent on makespan.
Figures plot unsmoothed observed cell summaries or explicitly labeled
marginal means. No choice of contrasts depends on their observed values.
