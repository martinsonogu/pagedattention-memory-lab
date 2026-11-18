# Milestone 4D snapshot suppression

## Local argument recorded before implementation

Reference: c4c5e091537c53bdb96f7d0d97cba5c4f7e4d671.
Simulator SHA-256: d1540010475c52caaeb2c6c86e8fb6b40c602ab74ca507e3897527ee66002b6b.

Retain unconditional snapshots for admit, generate, and complete. These cover
all changes to allocated/used slots, resident population, and protected headroom.
Admission includes transient prompt-only peaks. Generation includes both growth
and within-block used-slot changes. Complete includes prompt-only and ordinary
release; each release must validate reassigned headroom, even as allocation falls.

Guard arrival, admission_blocked, tick_begin, compute_deferred, growth_stalled,
and tick_end snapshots with tracing. Those events do not change resident memory
or its peaks; the initial empty state is valid and every memory mutation remains
checked. Queue/counter changes are still executed. Tick-end slot-time sampling
and progress/accounting assertions stay in their original positions. Tracing
retains every snapshot and full recomputation. No policy, API, metric, arithmetic,
completion-oracle access, event ordering, or scheduler iteration changes.

## Verification plan

Compare complete dictionaries and canonical JSON against the independently
loaded pinned Git source, with both trace modes. Retain older-reference tests.
Cover all smoke combinations, compute budgets None/1/2/8, fixed and paged8/16/32,
empty/prompt-only, early/consecutive completion, M33 rounding, pressure,
classification transitions, high population, and independently seeded workloads.
Verify runner serialization and batch validation using the same metadata.

Benchmark protocol fixed before timing: four requested 200-request cases,
M2048, generation-heavy, seed20261117, trace disabled. Each implementation gets
20 seconds; eight calls have an outer 110-second limit. No profiling in timed
runs. Count snapshots separately on a small fixed diagnostic. Compare complete
outputs when both finish; no speedup for censored pairs. No experiment matrix.

## Results

Four new tests passed: 880 exact simulator comparisons (784 inherited cases plus
96 additional pressure/consecutive-release conditions across both trace modes),
a targeted protection-to-physical classification assertion, and 16 runner rows
compared as canonical JSON and accepted by the batch validator. The new reference
is independently loaded; each module receives its own Request objects. Fixtures
reuse the established case generator, not its older reference implementation.
No mismatches or numerical tolerances. Metadata is held identical for runner
comparison; source metadata still truthfully identifies the current checkout.

`python3 -B -m unittest -v`: 92 tests in 47.217s, OK, including all older
Milestone 4A/4B tests. New module alone: 4 tests in 34.141s, OK.
Fresh smoke output `/tmp/phase3-4d-smoke-xmvnkyy1/smoke.jsonl`: 72 distinct cases,
72 verification replays, zero invariant failures, 0.301s.

| Case | Reference seconds | Optimized seconds | Ratio | Tokens | Makespan |
| --- | ---: | ---: | ---: | ---: | ---: |
| Short/dense/fixed B8192 unlimited | 0.054335 | 0.040401 | 1.34x | 16876 | 4258 |
| Short/moderate/paged8 B8192 G8 | 0.063908 | 0.048742 | 1.31x | 16876 | 6663 |
| Long/moderate/fixed B2048 G8 | 1.958702 | 1.008271 | 1.94x | 296588 | 296588 |
| Long/dense/paged8 B8192 unlimited | Timeout 20.002409 | Timeout 20.003211 | Not available | Not available | Not available |

Completed pairs had identical complete outputs. Total benchmark wall time was
43.217 seconds, below 120 seconds. Timed calls used plain wall time, no profiler.
Single samples ran reference first, without systematic warmup; regression tests
ran concurrently. Thus timing ratios are preliminary and sensitive to system
load, not stable speedup estimates. Per-run memory usage was not measured.
The expensive pair is censored; it supplies neither a completed ratio nor final
simulation metrics. No shortened expensive workload was substituted after seeing
these outcomes.

A separate untimed call-count diagnostic used five requests (arrival0,prompt1,
output31), M32, paged8, B64, unlimited compute. Snapshot calls decreased from 520
to 165 (68.27%), with identical 155 generated tokens and makespan87. This is a
small diagnostic, not a call-reduction estimate for the full expensive workload.
External benchmark harness/results: `/tmp/phase3_4d_bench.py`,
`/tmp/phase3_4d_bench.json`, `/tmp/phase3_4d_bench.log`.

All 25 other tracked files remain byte-identical to HEAD, including canonical
results, frozen conditions, and the analysis plan. No Git staging/commit/push.
Only the simulator and the two new Milestone 4D artifacts change.

Remaining work still visits each eligible resident every tick, recomputes growth
allocation, and updates per-request outcomes. Trace mode intentionally retains
all checks and events. The hardest workload still exceeds its cap; pilot
feasibility is not established. This is interpreter-runtime evidence only, not
paging-effect or GPU-throughput evidence. Ready for independent audit.
