# Milestone 4A execution-readiness record

Implementation and correctness validation completed; execution feasibility is
blocked pending review. No performance effect sizes were computed.

## Frozen execution scope

Pilot configuration and paired-analysis plan were written before preflight.
The pilot remains exactly 24 workloads and 384 strategy runs; primary conditions
remain 480 workloads and 19,200 runs. The additional 640 controls are separate and
still need a concrete execution specification. No full matrix was executed.

## Validation

`python3 -B -m unittest -v`: 82 tests in 2.717s, OK (72 baseline plus 10 batch tests).
Tests use two-request fixtures through a test-only configuration substitution;
the production CLI strictly validates the frozen 200-request pilot configuration.

`python3 -B phase3_smoke.py --output /tmp/phase3-4a-smoke.jsonl`:
72 distinct cases and 72 deterministic verification replays passed, zero invariant
failures, 0.334s. Every fixture passed 12/12 conditions.

## Preflight outcome

Executed:

```sh
python3 -B phase3_batch.py preflight --output /tmp/phase3-4a-preflight.jsonl
```

The fixed 32-run preflight hit its preregistered 120-second wall-clock cap and
exited with an explicit timeout error. The short/generation-heavy/dense workload
completed all 16 conditions. The last read-only observation of the unpublished
file showed 25 complete result records (including long/generation-heavy/dense,
B=8192, fixed, unlimited); this is a progress observation, not an exact final count
or an accepted partial dataset. No conditions were changed or selected afterward.

The destination dataset does not exist and the caught timeout cleaned up the
hidden temporary file. The empty stdout capture was removed. A separate external
machine-readable failure status is `/tmp/phase3-4a-preflight-status.json`.
There is no completed preflight report, so the pilot gate did not pass:
**zero of the 384 pilot runs were executed**. Preflight cases overlap the pilot
by design but are not counted as a completed pilot or reused as pilot results.

The cap records a 120-second execution limit, not a completed runtime measurement.
Mean/median per-run time, a reliable slowest-condition ranking, peak RSS, and final
dataset size are unavailable because no completion record was produced. Do not
infer that the last observed condition was the slowest. The completed smoke
artifact is separate and not a substitute for pilot results.

## Feasibility assessment and next decision

A completed preflight would have exceeded 120 seconds for 32 runs. A purely linear
amortized extrapolation of that threshold is `120 / 32 * 19,840 = 74,400 seconds`
(20 hours 40 minutes). This is a lower bound for that naive preflight-based scaling,
NOT a lower bound on actual full-matrix runtime: preflight deliberately uses only
two generation-heavy/dense regimes, other budgets/seeds can differ, and the 640
controls are unspecified. A defensible full-matrix point estimate is unavailable.

Likewise, the allotted preflight budget already scales to over 24 minutes for
384 conditions, compared with the preregistered 15-minute pilot cap. This indicates
an execution-cost concern, not a claim about paged versus fixed performance.

The unchanged simulator repeatedly scans resident state for memory and invariant
checks even without traces; per-tick work can increase substantially with active
population. The batch layer stores only the workload manifest, one result at a
time, and timing records in memory; it retains per-request outcomes on disk for
offline validation, but no event traces. Source hashing is once per workload in
the runner plus batch boundary checks. Profiling or changing the validated core,
extending execution limits, or scheduling a longer pilot requires review before
further execution. Do not narrow conditions based on pilot outcomes.

The implementation is ready for a correctness/reproducibility audit. Milestone
4A has not established that the full pilot or primary matrix is practical within
the chosen execution window. No protected-code changes are proposed or made here.
