# Phase 2: dynamic KV-cache allocation simulation

This standalone, standard-library experiment adds arrivals, FIFO queuing, token
generation, completion, and memory reuse. Phase 1 code, documentation, and results
are preserved. It investigates allocation mechanisms inspired by PagedAttention;
it is not a reproduction of vLLM GPU throughput or the paper's performance results.

## Reproduce

```sh
python3 -B -m unittest -v
python3 -B dynamic_experiment.py --output phase2_results.csv --seed 20261117 --trials 20
```

`-B` prevents writing Python bytecode. It is optional for
normal use: `python3 dynamic_experiment.py --output phase2_results.csv` also works.
No dependencies or GPU are needed. CLI options also include `--requests` (100),
`--budget` (32768 slots), `--maximum` (2048 slots), and `--concurrency` (see below).
Positive trial counts and feasible configurations are required. The output is
replaced if it exists; the CLI refuses to overwrite the repository's Phase 1
`results.csv`. Parent output directories are created when necessary.

The Python API requires built-in integers for seed, trial/request counts, budget,
maximum length, block size, concurrency, and request fields. Booleans, floats
(including integral-valued floats), strings, and other types raise `ValueError`;
values are never silently coerced. Only `concurrency=None` is allowed as an
automatic-setting sentinel. Seeds may be negative. Trials, budgets, and explicit
concurrency must be positive; request counts may be zero. Workload generation
requires a maximum of at least 2; direct simulation permits 1. Arrivals and output
lengths may be zero, prompts must be positive, and total length cannot exceed the
maximum. Paging supports blocks 8, 16, and 32; fixed allocation ignores its
nonnegative integer block-size field (0 is the CSV convention).

## Workloads and strategies

Trial `i` uses a private `random.Random(seed + i)` generator. Starting at time zero,
each request's arrival adds an independent uniform integer in [0, 8]. Its prompt
is uniform in [1, min(256, maximum - 1)] and its output length is uniform in
[1, min(512, maximum - prompt)]. Draw order is arrival gap, prompt, output for
each request. These are synthetic distributions, not production traces; defaults
are intentionally different from the Phase 1 snapshot workload. The same immutable
request list is replayed for all four strategies in each trial.

Fixed reservation allocates `maximum` slots at admission and holds them until
completion. Paged allocation reserves `ceil(current_length / block_size) *
block_size` slots, with block sizes 8, 16, and 32, growing at block boundaries.
Every token has equal memory cost. Neither strategy needs advance knowledge of
the actual output length for admission; both know the common maximum length.
The simulator uses output lengths only to decide completion.

## Shared scheduler and memory safety

All strategies use stable FIFO order by arrival, breaking ties by input position.
There is no bypass, eviction, rejection, recomputation, or swapping. The default
shared concurrency cap is

```text
budget // max(round_up(maximum, b) for b in (8, 16, 32))
```

This is 16 for the defaults. A user-specified cap must be positive and no larger
than this bound. Admission waits at the head of the FIFO queue when the cap is
reached. Unallocated growth headroom is an admission constraint, not physical
allocation; it is not counted as allocated memory for paging.

With identical workloads and the same cap, timing equality is inevitable in this
simulator. Admission depends only on FIFO order and the active-request count;
the safety bound prevents physical allocation from delaying either strategy.
Every active request then generates one token per tick, so both strategies have
identical admission and completion times, waiting times, and makespans. Paging's
free slots cannot admit extra requests past the shared cap. This is true even
when arrivals are sparse enough that the cap never binds. Timing equality is a
consequence of the model, not an empirical throughput result.

The cap guarantees enough space for every active request to reach the maximum,
even with rounding. A configuration unable to hold one worst-case request, an
unsafe cap, or a request longer than the maximum raises `ValueError` before
simulation (CLI reports an error and exits). Requests are never silently dropped.
Every active request with remaining output advances each tick and finishes in
finite time. For finite inputs, completion is bounded by the latest arrival plus
the sum of output lengths. An unexpected admission/growth allocation failure
raises `RuntimeError` immediately as an implementation invariant violation;
no successful CSV row is emitted for such a failure.

This policy makes allocation failures and growth stalls zero by construction.
The successful-run fields are fixed zeros guaranteed by the scheduling policy,
not measurements of how an overcommitted allocator handles memory pressure.
They are explicit CSV fields, not empirical evidence that arbitrary workloads
can grow safely under unrestricted admission. The cap deliberately excludes
overcommitment and its recovery policies. In particular it prevents measuring
whether paging could support greater concurrency. For non-aligned maxima it can
also limit fixed reservation below its own feasible concurrency; this maintains
identical scheduling but is not an optimal fixed scheduler.

## Tick semantics

At integer time `t`, enqueue arrivals with arrival time at most `t`, then admit
FIFO requests while below the shared cap. Prefill is instantaneous. Prompt-only
requests (supported by the API, not generated by default) complete immediately,
so their capacity can be reused at `t`.

Each active request produces one token during `[t, t+1)`, including newly admitted
requests. Grow allocation before storing the token. Sample occupancy after all
generation and before any release; charge that sample to this tick. At `t+1`,
release all completed requests. Newly freed capacity is available for admission
at `t+1`. Idle ticks from time zero are included. No post-completion idle ticks
are counted. Optional `trace=[]` passed to `simulate` captures arrival, admission,
generation, and completion event snapshots for auditing. Memory invariants are
checked after every event, including before release.

## CSV metrics

One row describes one trial and strategy. `trial` is zero-based; `seed` is that
trial's actual seed. `strategy`, `block_size` (0 for fixed), `requests`, `budget`,
`maximum`, and `concurrency` record the configuration. Time is in simulated ticks.

| Metric | Definition |
| --- | --- |
| `completed_requests` | Number of requests completed, including prompt-only requests. All valid input requests must complete. |
| `makespan` | Time of the last completion measured from time zero, including initial idle time; zero for an empty workload. |
| `total_waiting_ticks` | Sum over requests of admission time minus arrival time. |
| `mean_waiting_ticks` | Total waiting ticks divided by completed requests, or zero for empty input. |
| `allocated_slot_ticks` | Sum of physically reserved slots at the post-generation, pre-release sample of every tick. |
| `used_slot_ticks` | Sum of prompt plus generated tokens resident at the same samples. |
| `mean_allocated_slots` | Allocated slot-ticks divided by makespan, or zero if makespan is zero. |
| `mean_used_slots` | Used slot-ticks divided by makespan, or zero if makespan is zero. |
| `peak_allocated_slots` | Maximum physically allocated slots across all event snapshots, including admission and before release. |
| `peak_used_slots` | Maximum resident tokens across all event snapshots. |
| `peak_occupancy` | Peak allocated slots divided by the total budget; not a measure of useful tokens or internal fragmentation. |
| `admission_stall_request_ticks` | Sum of the queue length after admission on every tick. Equals total waiting ticks under this FIFO policy. |
| `allocation_failures` | Number of unsuccessful physical allocation attempts in a successful run: always zero under the safety bound. An invariant breach aborts the run. |
| `growth_stall_request_ticks` | Active request-ticks without progress due to growth capacity: always zero under the safety bound. |
| `final_allocated_slots`, `final_used_slots` | Remaining allocation and resident tokens after all completions; both must be zero. |

Prompt-only requests contribute to instantaneous peaks but no slot-ticks. Mean
occupancies include idle ticks. Internal unused allocation can be derived as
`allocated_slot_ticks - used_slot_ticks`; free capacity is a different quantity.
The console reports arithmetic means of per-trial metrics, including a mean of
per-trial peak occupancies, rather than a pooled or global peak.

Peak occupancy measures allocated reservations, not live-token usage. Fixed's
100% peak means 16 reservations of 2048 slots fill the 32768-slot budget; it does
not mean 32768 tokens are resident. Live-token peak occupancy can instead be
computed as `peak_used_slots / budget`. Live-token usage is identical across
strategies under the common schedule, while reserved capacity differs.

## Validation and recorded run

The original commands above were run with Python 3.12. All 17 original tests
passed (6 Phase 1, 11 Phase 2). Phase 2 tests cover deterministic seeds, rounding, explicit arrival
and generation timing, exact hand-calculated metrics, FIFO ties, release/reuse,
safe and unsafe caps, pressure termination, randomized memory invariants, empty
and prompt-only workloads, shared timing, and CLI CSV output/protection.
A non-aligned maximum test demonstrates that paging can use more allocated
memory than fixed reservation due to block rounding.

Original test summary:

```text
Ran 17 tests in 0.287s

OK
```

Phase 2A adds six regression tests for integer-type and range validation,
request-field types, arrivals at simultaneous completion boundaries, mixed
prompt-only/generating requests, and nonbinding limits. This brings the full
suite to 23 tests (6 Phase 1, 17 Phase 2). The scheduler, default configuration,
and canonical `phase2_results.csv` are unchanged. Phase 2A verification runs the
full suite and regenerates the same experiment into a temporary file for a
byte-for-byte comparison with the canonical CSV.

To verify without replacing the canonical file:

```sh
python3 -B -m unittest -v
python3 -B - <<'PY'
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as directory:
    output = Path(directory) / "phase2_results.csv"
    subprocess.run([sys.executable, "-B", "dynamic_experiment.py",
                    "--output", str(output), "--seed", "20261117",
                    "--trials", "20"], check=True)
    if output.read_bytes() != Path("phase2_results.csv").read_bytes():
        raise SystemExit("CSV comparison failed")
    print("CSV byte-identical: True")
PY
```

Experiment output:

```text
fixed block= 0 completed=100.00 makespan=1884.75 wait=489.82 mean_allocated=28275.90 peak_occupancy=100.000% failures=0
paged block= 8 completed=100.00 makespan=1884.75 wait=489.82 mean_allocated=4235.85 peak_occupancy=19.598% failures=0
paged block=16 completed=100.00 makespan=1884.75 wait=489.82 mean_allocated=4291.09 peak_occupancy=19.783% failures=0
paged block=32 completed=100.00 makespan=1884.75 wait=489.82 mean_allocated=4401.46 peak_occupancy=20.151% failures=0
Wrote 80 rows to phase2_results.csv
```

All strategies completed all requests with equal timing under this shared policy.
Paging used fewer reserved slots for this short-length workload and conservative
fixed baseline. This does not establish better throughput or lower latency.

## Limitations and next research steps

There is no GPU, attention computation, bandwidth contention, batching cost,
prefill cost, variable generation rate, allocator runtime, contiguous placement,
external fragmentation, block sharing, prefix caching, or real serving trace.
Slots are abstract accounting units, not measured bytes. Fixed reservation is a
conservative maximum-length baseline, not a claim about contemporary allocators.
The shared cap and constant token rate force equal timing, so timing equality is
a correctness check, not a performance discovery. Smaller blocks have no modeled
metadata or management cost. Memory savings depend on lengths, maximum, budget,
and workload; they are not guaranteed across configurations.

Per-trial rows are retained, but confidence intervals, broader distribution and
load sweeps, less conservative contiguous baselines, fragmentation accounting,
and overcommitment/recovery policies remain future work. These results cannot
support numerical comparisons with the PagedAttention paper or predictions of
production vLLM throughput, latency, or optimal block size.

## Git hygiene

`.gitignore` ignores `__pycache__/` and `*.pyc`. With explicit approval for Phase
2A, the following command removed the two Phase 1 bytecode files from the Git
index while preserving their local copies. These removals are staged; no commit
or push was performed:

```sh
git rm --cached -- __pycache__/experiment.cpython-312.pyc __pycache__/test_experiment.cpython-312.pyc
```

The ignore rules now apply to those local copies. Canonical research CSVs remain
eligible for version control; `.gitignore` does not exclude generated CSVs.
