# Milestone 4B: incremental memory accounting

## Design frozen before simulator edits

Replace repeated sums of active allocated/used slots with two integer totals.
Admission adds the new resident's allocation and prompt length. Successful
generation adds the allocation delta and one used slot; a stall or compute
deferral changes neither. Completion subtracts the resident's actual allocation
and current live length, including immediate prompt-only completion. Headroom is
still derived from the first active resident as R minus its allocation, or zero
when empty. Fixed reservation, block rounding, oldest protection, physical-first
stall classification, FIFO order, and compute-opportunity consumption stay intact.

At every existing snapshot, retain global bounds and peak updates. Validate the
changed resident on admission/generation; other residents cannot change on those
transitions. Release removes already validated state. When trace=True, additionally
recompute both totals and all resident invariants on every event. This existing
trace option supplies the explicit debug path without adding an API parameter.
Detailed event tuples, order, sampling, tick-end slot charges, and aggregate
formulas stay unchanged. Output schemas and validation of caller inputs stay intact.

The optimization removes per-event resident summations/full invariant scans from
normal execution. It still visits every eligible request, including stalls and
compute deferrals; no tick skipping, policy rewrite, or future-output look-ahead
is introduced. Trace mode intentionally retains full scans and large snapshots.

## Frozen reference and exact differential interface

Reference commit: f7edb22819ba5ece5094327c321544c633c7b877.
Reference simulator SHA-256:
`602be794f3ed6c8197237ccb708fc9641440e7173d6c8f85fc1a2d4d695636fa`.

Before editing, the exact Git object was saved outside the repository and 368
complete baseline outputs were captured for smoke/edge cases in both trace modes.
`test_phase3_optimization.py` loads the pinned Git object into a separate module
and verifies its checksum. It constructs each module's own Request objects from
identical immutable values, then compares complete return dictionaries with exact
equality, including floats. No tolerances, summary-only comparisons, or silent
reference updates are permitted. Tests require the pinned Git object to remain
available; shallow exports without it fail explicitly.

Coverage: 72 smoke conditions, 112 edge conditions, 48 generated-workload
conditions across three seeds, and 160 deterministic randomized pressure conditions.
Each runs with tracing off and on: 784 complete-output differential comparisons.
Compute settings cover unlimited, 1, 2, and 8; allocation covers fixed and all
three block sizes. The smoke tests explicitly verify that all four tick-outcome
categories occur. The preserved Milestone 4A files are not edited by this work.

## Bounded benchmark protocol

Use 200 requests, M=2048, seed 20261117, generation-heavy splits, and the same
realized workload per reference/optimized pair. Cases: short/dense/fixed B=8192
unlimited; short/moderate/paged-8 B=8192 G=8; long/moderate/fixed B=2048 G=8;
long/dense/paged-8 B=8192 unlimited. Trace=False. Each implementation gets a
30-second wall-clock cap; an outer watchdog bounds the entire eight-run benchmark
at 250 seconds. Run without cProfile, report censored runs honestly, and compute
speedup only when both finish and their complete outputs match. One timing per
case is a feasibility measurement, not a statistically stable speedup estimate.
Measure process peak RSS with platform-normalized resource.getrusage units.
No pilot, primary, or control matrix is executed.

## Validation and bounded measurements

`python3 -B -m unittest -v`: 88 tests in 10.709s, OK, including the
Milestone 4A batch tests and 784 exact differential comparisons. No mismatches
were found. All 368 pre-edit captured outputs also matched after canonical
encoding. A fresh `python3 -B phase3_smoke.py --output <unused-temporary-path>`
run passed 72 distinct cases and 72 deterministic replays with zero invariant
failures (0.308s).

| Case | Reference seconds | Optimized seconds | Ratio | Generated tokens | Makespan ticks | Peak RSS bytes, reference / optimized |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Short/dense/fixed, B8192, unlimited | 0.152921 | 0.059005 | 2.59x | 16,876 | 4,258 | 18,903,040 / 18,763,776 |
| Short/moderate/paged8, B8192, G8 | 0.169427 | 0.068363 | 2.48x | 16,876 | 6,663 | 19,738,624 / 19,202,048 |
| Long/moderate/fixed, B2048, G8 | 4.439433 | 2.065262 | 2.15x | 296,588 | 296,588 | 18,280,448 / 18,874,368 |
| Long/dense/paged8, B8192, unlimited | Timeout at 30.004 | Timeout at 30.002 | Unavailable | Unavailable | Unavailable | 18,776,064 / 18,485,248 |

Both implementations produced identical complete outputs in each completed pair.
Timeouts are censored measurements, not completed runtimes. Temporary workloads,
completed outputs, and the machine-readable benchmark report are retained in
`/tmp/phase3-4b-benchmark-n0wsyznc`; the bounded harness is
`/tmp/phase3_4b_benchmark.py`. These temporary artifacts are not repository files.

All 17 other protected tracked files match the pinned commit, and all six
preexisting Milestone 4A files match their pre-optimization hashes. The index
remains empty. No experiment matrix was run.

The three completed cases show reduced interpreter runtime, but the hardest case
remains unresolved under the cap. Single samples, execution order, and system
load limit timing conclusions; this does not establish pilot feasibility or any
allocator performance advantage. Trace mode still scans residents, and normal
mode still visits eligible requests each tick, including stalled requests.
Ready for independent correctness review; stop before further experiments.
