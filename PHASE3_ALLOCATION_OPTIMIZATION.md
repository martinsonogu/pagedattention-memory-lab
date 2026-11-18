# Milestone 4F: next-token allocation

## Derivation recorded before implementation

Reference commit: 393658751c71af88980f8443f80dba7d815800b0.
Reference simulator SHA-256:
7a20f2ea4529347864b0d51f36a9b5cd51d7fb428b040a48e6a05bb2675644b0.

Previous hot path: required = allocation(state.length + 1). For paged requests
this calls rounded and validates integer length/block size on every inspected
resident, including repeated stalled attempts.

Length is prompt plus successful generated tokens, before this tick's generation.
Admission and every generation validate 1 <= length <= M and allocated equals
the general allocation formula. For fixed residents required is M. For paged
residents a=b*ceil(l/b), so a-b < l <= a. If l<a, integer l+1<=a and the ceiling
remains a. If l=a, l+1 crosses exactly one boundary and requires a+b.

An eligible unfinished request has l<M: public validation bounds prompt+output
by M, prompt-only requests release immediately, and execution completion is
observed after each successful token and released before the next tick. A
resident completing at M is never inspected for another generation. This
argument does not expose future output lengths to scheduling. Nonaligned M may
have rounded allocation above M, but actual generated length never exceeds M.

Change only next-token required allocation. Keep public rounded/simulate checks,
admission allocation, all existing resident checks, compute exhaustion before
memory inspection, physical-first failures, counters, snapshots, and release
unchanged. No new scheduler, caching structure, event jump, or API.

## Verification and timing protocol

New tests independently load the pinned Git object and verify its hash. Each
module receives its own Request instances. Reuse only the existing workload-case
enumerator; do not use its old reference for the new comparison. Compare exact
complete dictionaries and canonical JSON with both trace modes: 784 established
comparisons, 96 pressure/release comparisons, and 32 boundary/M33 comparisons.
Also exercise invalid public inputs, classification transitions, and 16 runner
rows accepted by the unchanged batch validator under identical metadata.

Benchmark four previously specified cases, seed20261117, 200 requests, M2048,
generation-heavy splits, tracing disabled. Use isolated subprocesses with a
20-second per-call limit and a 110-second remaining-time guard; total study must
stay below 120 seconds. Wall times include startup/import/generation/termination,
so they differ from earlier simulator-only timings. No profiling in these timed
pairs; compare hashes of complete serialized outputs when both complete. Count
allocation/rounding calls separately on five (0,1,31) requests, M32 B64 paged8.
Finally cap a hard-case optimized cProfile sample at five seconds. Profile times
are diagnostic and never used as completed wall-time speedups. No pilot runs.

## Differential and benchmark results

Dedicated module: 6 tests in 35.214s, OK. All 912 complete-output comparisons
passed exactly, plus the targeted classification test and invalid public-input
checks. Sixteen canonical runner rows matched and passed the unchanged batch
validator. No mismatches, tolerances, or source-metadata exclusions were needed;
runner metadata was held identical while changing the simulator adapter.

| Case | Reference process seconds | Optimized process seconds | Ratio | Tokens / makespan |
| --- | ---: | ---: | ---: | --- |
| Short/dense/fixed B8192 unlimited | 0.262422 | 0.235704 | 1.11x | 16876 / 4258, both |
| Short/moderate/paged8 B8192 G8 | 0.257775 | 0.226987 | 1.14x | 16876 / 6663, both |
| Long/moderate/fixed B2048 G8 | 1.258582 | 1.245019 | 1.01x | 296588 / 296588, both |
| Long/dense/paged8 B8192 unlimited | Censored at 20.006386 | Completed 17.257891 | Unavailable | optimized only: 296588 / 259671 |

All completed pairs had identical hashes of complete serialized outputs. The
hard reference did not complete, so its full output was not compared in this
benchmark and no full-case speedup ratio is established. The optimized hard run
is one completed measurement, not evidence that the pilot fits its execution cap.
Total benchmark/profile wall time was 45.790 seconds, below 120 seconds.

Each process was isolated, tracing disabled, without concurrent regression runs.
Single samples and reference-first ordering limit conclusions. Process times
include imports, workload generation, and the reference worker's Git-object load;
these asymmetric setup costs can affect small ratios. The completed easy-case
ratios therefore do not establish a material simulator-only improvement. No
performance threshold is asserted from them.

The separate small diagnostic reduced allocation calls from 496 to 165 and
rounded calls from 497 to 166. Both yielded 155 tokens and makespan87. Remaining
calls include admission checks and unchanged resident validation. This count
reduction is not an estimate for all workloads.

A five-second optimized partial cProfile recorded 2,444,562 memory calls
(1.848s cumulative), 2,363,820 failure checks (0.381s), 80,664 allocation calls
(0.132s), and 43,034 snapshots (0.241s). Replay self time was 2.465s. Times overlap;
do not add them or compare this profiled prefix as a completed benchmark. Resident
iteration and memory lookup remain major costs; traced runs retain full checks.

Temporary harness and detailed measurements: `/tmp/phase3_4f_benchmark.py` and
`/tmp/phase3_4f_benchmark.log`. These are diagnostic artifacts, not pilot data.
The unchanged pilot gate still requires its complete preflight and feasibility
check. Neither the pilot nor primary/control matrices ran. No paging effects or
GPU-throughput claims are made.

## Final regression and preservation

`python3 -B -m unittest -v`: 98 tests in 80.775s, OK. This includes the
unchanged older-reference tests, snapshot tests, batch tests, and six new tests.
Fresh smoke run: 72 distinct cases, 72 deterministic replays, zero invariant
failures, 0.324s. Output: `/tmp/phase3-4f-smoke-mtxt9ie_/smoke.jsonl`.

All 27 other tracked files remain byte-identical to the starting commit.
`git diff --check` passes. Branch and HEAD remain unchanged, index empty.
Expected scope only: simulator, this document, and the new allocation test module.
No commits or pushes. Ready for independent audit; pilot feasibility remains
unestablished despite the single completed optimized hard-case measurement.
