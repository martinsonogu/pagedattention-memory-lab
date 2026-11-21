# Phase 3E-4A controls and analysis readiness

**READY FOR CONTROL-SPECIFICATION DECISION** · 2026-11-21

## Baseline and dataset integrity

Branch `phase-3-memory-aware-scheduling`, local and live origin HEAD
`df794b67e72740bffb6272248b9d609c8decfaea`. The index was empty.
The frozen primary and pilot plans, protocol, scientific sources, and
prior execution evidence were preserved.

| Baseline artifact | SHA-256 |
| --- | --- |
| Primary manifest file | `17983e334c0980cbaabafa9da4fe2e9935977848475043de92db4906105a8b48` |
| Ordered primary inventory | `a578f5f9912c062b6fd9899cba22e7798bffd9be524db44be443796840be90e0` |
| Pilot manifest file | `47b99f9ab09d08a082d0dce5a16bcaf7111bcaa212eb66287b8bb0313212167e` |
| Frozen primary config | `3753af5cb496b4ba395a8f846b4871c0060407de75828e00d445206bad46d8fa` |
| Frozen analysis plan | `eff60269f9fa72efa552be796f432cce46ee231def9b3676999d2d565f860c93` |
| Research-batch protocol | `b74171bf0577ca2b38c71bc5008b7e77271107319966abca32b1743c7b8336c8` |

The audit loaded the stored workloads, checked their generator metadata
against the frozen declaration, rebuilt the ordered condition inventory,
and reran the existing scientific and checksum validators on saved records.
All **19,200 primary records** and **384 pilot records** validated, with
no missing, duplicate, or unexpected conditions. The primary has 480
distinct workloads, 20 seeds and exactly 960 conditions per seed. Each
workload contributes 40 conditions. Neither dataset had missing
required metric fields, null aggregate metrics, null first-token
timestamps, incomplete requests, or zero fixed denominators for the
listed primary and secondary outcomes.
[Primary manifest](phase3/research_batch/3e3/primary/manifest.json) ·
[Frozen primary config](phase3/configs/primary.json) ·
[Primary execution and provenance](PHASE3_3E3_REAL_PRIMARY_REPORT.md#L10) ·
[Pilot](PHASE3_3E2_REAL_PILOT_REPORT.md) · [Smoke](PHASE3_3E1_REAL_SMOKE_REPORT.md)

## Original control intent and prospective decision

| Status | What the sources establish |
| --- | --- |
| **PRESPECIFIED** | No complete scientific control configuration was found. The frozen primary comparison already crosses fixed and all three paged block sizes with unlimited and G8 on matched workloads. The separate six-fixture smoke suite and the unit test named compute-limited control are correctness checks. |
| **UNRESOLVED** | The original Phase 3 documentation reserves a separate control suite and quotes 640 as a planning count. It supplies no scientific control hypothesis, treatment/comparator, held-constant variables, seed or workload coverage, required outputs, or derivation of 640. The analysis plan openly leaves conditions to be specified before execution and treats controls as exploratory in reporting. Repository history and the frozen configs reveal no omitted matrix. |
| **EXPLORATORY** | Scheduler or protection ablations, new workload generators, and alternative allocator policies are possible new experiments. No implementation or separate scientific claim is proposed for them. They would need separate design decisions and may require code changes. |

[Analysis plan](PHASE3_ANALYSIS_PLAN.md#L1) ·
[README workload and control scope](PHASE3_README.md#L185) ·
[Correctness smoke scope](PHASE3_README.md#L366) ·
[Historical readiness record](PHASE3_4A_READINESS.md#L1)

**PROSPECTIVELY PROPOSED — ample-memory negative control.** Ask whether the
allocators agree on admission and completion when memory cannot gate progress.
Use the first canonical workload definition, short / generation-heavy / dense,
with all 20 frozen seeds and the exact saved workload documents. Hold FIFO,
protection, M=2048, 200 requests, the event clock and unlimited compute fixed.
Cross fixed, paged8, paged16 and paged32 at a control budget of **409,600
token slots** (200 × 2048). Each live request fits within M after padding,
and the oldest request's allocation plus its protected slack is at most M.
Thus the simultaneous worst-case allocation plus protection fits that
budget without needing a new scheduler or a code change.

The fixed run is the paired comparator at ample memory. As context, link
the existing primary runs for the same workload hashes, allocators and
unlimited compute at budget 2048, the lowest frozen budget. Preserve
request-level admission, first-token and completion times, waiting and
latency, makespan, memory blocking and stall counts, and allocated/used
slot ticks and protected slack. Predict zero memory blocking and stalls and
the same per-request timing across allocators under this control. Allocated
and unused slot ticks may differ by design. **20 matched workloads ×
4 allocators = 80 new conditions**. The 80 constrained references are
already available and require zero reruns. Selection uses canonical order
and a worst-case capacity bound, with no dependence on primary effect sizes.

This is a newly specified mechanism check, with no basis to call it the
original 640. The owner must decide whether to authorize this exact
contrast and accept that the original control suite is unreconstructable
from the checked sources. If the owner requires the historical suite,
obtain its protocol or explicitly resolve the missing definitions first.
[Simulator API and memory rules](phase3_simulator.py#L69) ·
[Headroom calculation](phase3_simulator.py#L125) ·
[Existing research batch entry point](phase3_research_batch.py#L155)

## Frozen analysis and implementation decisions

**PRESPECIFIED.** Ask how each paged block size changes mean end-to-end
latency, nearest-rank p95 latency and makespan relative to fixed, within
each length × split × arrival × budget × compute cell. Pair the identical
realized workload within each seed. The seed is the replication unit.
Report paged minus fixed in ticks, and the mean of seed-level paired
relative differences `(paged − fixed) / fixed` as a percentage. Negative
favors paged for the three primary outcomes. Mean progressing requests
(generated output divided by makespan) is secondary and algebraically
dependent on makespan. Retain ties, regressions, and absolute differences
with zero references. Set their relative differences to null and disclose
the excluded denominator count. Keep null empty-workload p95s undefined.

Report all **2,160** primary comparisons (24 workload definitions × five
budgets × two compute scenarios × three paged contrasts × three primary
outcomes), with equal-weight seed means, distributions, and win/tie/loss
counts. Any overall summary weights cells and seeds equally and accompanies
the cell results. Use 10,000 paired seed-cluster bootstrap draws with
analysis RNG seed 20261118, sampling the 20 seed IDs with replacement
while retaining each sampled seed's entire grid. Report pointwise percentile
95% intervals as descriptive. No family-wise significance is implied.
Budget and compute define strata; separate direct budget, G8–unlimited,
or paged–paged contrasts are exploratory. Waiting, active requests, stalls,
deferrals, and memory metrics are diagnostic. [Frozen analysis plan](PHASE3_ANALYSIS_PLAN.md#L8)

**PROSPECTIVELY PROPOSED implementation clarifications.** Before inference,
fix the RNG implementation, sorted seed order, shared bootstrap draws,
percentile endpoint convention and exact tie convention. Use original
integer timing fields or exact rational means where available. Define the
relative estimate over valid fixed denominators only and return null for
an all-undefined estimate. The plan does not prescribe figure layouts or
specific sensitivity runs. Use a complete cell table, cell heatmaps and
seed-level paired distributions. Keep any separately approved
leave-one-seed-out or other sensitivity display explicitly exploratory,
with no effect-driven selection.

## Data readiness and timing

The checked rows expose every primary and secondary metric and per-request
arrival, admission, completion and latency fields. Pair on workload hash
plus budget and compute, with explicit allocator and block size. Retain
seed and all regime labels as grouping fields. Across all variants of a
seeded workload, the manifest pins the same request list and records bind
its hash. Do not pair unrelated regimes, treat requests as replicates,
pool condition p95s as a request percentile, or merge the pilot into the
primary. Keep wall seconds out of tick-based outcomes. Give memory ratios
explicit denominators and label headroom separately from allocated
fragmentation. Event traces were disabled, so event-by-event reconstruction
is unavailable from these records. No scientific-integrity anomaly emerged
from the schema, identity and invariant checks. This audit computed no final
contrasts, intervals or scientific conclusions.
[Scientific validator](phase3_batch.py#L133) ·
[Simulator metric definitions](phase3_simulator.py#L260)

**UNRESOLVED timing.** Command elapsed was **13 h 7 min 51 s**, versus
**6 h 34 min 32 s** on the runner's monotonic workflow timer and
**6 h 30 min 10 s** summed across condition timers. One logged invocation
completed every condition with no reported runner failures or retries.
The UTC records show long gaps, with a largest intercompletion interval
of 2,433.580 s versus 19.266 s for the following condition timer. Host
suspend state and clock changes were uninstrumented. Report the clocks
separately and make no attribution to simulation, storage or overhead for
the gap. This limits execution-cost claims and does not invalidate the
checked scientific tick metrics. The simulator supports no GPU or vLLM
throughput claim. [Primary timing evidence](PHASE3_3E3_REAL_PRIMARY_REPORT.md#L193)

## Next milestone

Ask the owner to approve or decline the exact 80-condition prospective
specification. If approved, freeze its manifest and predicted invariants
before dispatch, link the existing paired references, and run only that
control inventory in a separate scope with the existing Phase 3E
research-batch API. Preserve the primary and pilot outputs. No simulator
change or F2 reopening is needed. The missing historical control definitions
block claims of reproducing an original 640-run suite. The validated primary
dataset supports the frozen descriptive analysis once separately authorized
and the implementation conventions are settled. No control, inference,
or conclusion is authorized by this report. [Research-batch protocol](PHASE3_RESEARCH_BATCH_PROTOCOL.md) ·
[F2 closure](PHASE3_F2_EXECUTION_TRACK_CLOSURE.md)

## Integrity and stop

All pre-existing files, including the primary and pilot results, frozen
code, configurations, analysis plan, historical v0.4/v0.5 protocols
and F2 closure, remained byte-identical. Only this report was added.
The index was empty and whitespace checks passed. No new scientific
conditions ran. Nothing was staged, committed or pushed.
