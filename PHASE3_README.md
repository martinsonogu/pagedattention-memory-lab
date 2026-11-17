# Phase 3 core: frozen scheduler specification

Milestone 1 implements deterministic simulation replay and unit tests. Milestone 2
adds independent workload generation, canonical serialization, validation, and
replay adapters. There is no experiment runner, full matrix execution, or
performance claim. Phase 1 and Phase 2 files and canonical CSVs remain unchanged;
Milestone 2 also preserves the Milestone 1 simulator and its tests.

## API and validation

```python
from phase3_simulator import Request, simulate

result = simulate(
    [Request(arrival=0, prompt=8, output=24), Request(0, 1, 31)],
    "paged", budget=64, maximum=32, block_size=8,
    compute_budget=2, trace=True,
)
```

`simulate` returns `config`, `metrics`, input-order `requests` records, and optional
event `trace`. Input positions are stable request IDs. Input objects are immutable
and replay does not mutate them. No files are read or written by the simulator.

Strategy is `fixed` or `paged`. Paged block sizes are 8, 16, or 32; fixed ignores
its nonnegative integer block-size argument and reports 0. `compute_budget=None`
means unlimited; otherwise it is an integer G >= 1. Budget and common maximum M
are positive integers. Arrival/output are nonnegative integers, prompt is positive,
and prompt + output <= M. Integer parameters reject booleans and floats. Budget
must fit one worst-case allocation R. Invalid inputs raise `ValueError` before
replay; invariant breaches raise `RuntimeError`, never a partial success result.

The private execution component holds realized output lengths. Scheduler-visible
requests contain only ID, arrival, and prompt. Completion is observed after
prefill or after a successful token, never consulted to decide admission/growth.
Full lengths are used for input validation, not scheduling.

## Allocation, protection, and FIFO admission

Fixed allocation is M slots per active request; its R = M. Paged allocation at
resident length l is b * ceil(l / b); its R = b * ceil(M / b). All requests in a
run share M and R. Memory is fungible token slots, not address-space extents.

Let A be total physical allocation, U live tokens, and o the oldest active
request. Protected unallocated headroom is H = R - allocation(o), or zero for an
empty active set. Every atomic transition enforces:

```text
0 <= U <= A
0 <= H
A + H <= budget
```

Arrivals are ordered by (arrival, input ID). All subsequent priority is admission
order. Examine only the queue head. Admit it if its prompt allocation and the
prospective protection satisfy A' + H' <= budget. With no active requests the
candidate becomes oldest and H' = R - its allocation. A failed head blocks all
later queued requests. There is no concurrency cap, bypass, eviction, or swapping.

## Prompt-only completion and tick ordering

At time t, releases from generation ending at t have already occurred:

1. Enqueue all arrivals at or before t.
2. Attempt FIFO admissions. Every request, including a prompt-only one, must pass
   the same memory/protection check before prefill completion is observed.
3. A prompt-only request completes immediately at t after admission. Release its
   allocation and recompute H atomically from the remaining oldest request before
   trying another admission. It consumes no token-generation opportunity.
4. After the admission loop and all immediate releases, freeze the ordered set E_t
   of active requests still requiring output. This is the accounting population.
5. Visit E_t in admission order, attempting at most one token per request during
   [t, t+1). Successful tokens become available at t+1.
6. Sample memory after all token attempts and before any generation completion
   releases. Charge those values to this interval.
7. At t+1, release all newly completed requests in admission order and recompute
   protection after each release, before the next tick's arrivals/admissions.

Requests emitting their last token remain allocated and retain their position
through step 6; early knowledge of EOS does not release their memory/headroom
mid-tick. Prompt-only requests can affect instantaneous peaks but contribute no
slot-ticks and never belong to E_t. Pure idle intervals are skipped; makespan
still includes them from time zero. There is no trailing idle tick.

## Exhaustive request-tick accounting

Every member of E_t receives exactly one outcome:

- **Compute-deferred:** G successful tokens have already been generated this tick.
  Do not inspect this request's memory eligibility.
- Otherwise compute its next-token allocation increment delta. If A + delta > B,
  record a **physical-capacity growth stall**. If physical capacity fits but
  A' + H' > B, record a **protected-headroom growth stall**.
- Otherwise allocate, generate one token, and record **generated**.

The two stall reasons are mutually exclusive, with physical capacity checked
first. Stalled attempts consume no generation opportunity; a later eligible
request may use it. Memory checks themselves have no modeled compute cost. The
same ordering and rules apply to fixed and paged allocation and to unlimited G.
Requests still queued, future arrivals, prompt-only completions, and requests
completed before t are excluded from E_t. A request completing at t+1 is included
and classified as generated on tick t.

The implementation checks that eligible request-ticks equal generated tokens +
both growth-stall counts + compute deferrals. Admission blocking has separate
counters and is never counted as a growth stall.

## Progress and safe protection transfer

For oldest growth by delta, A increases by delta and H decreases by delta, leaving
A + H unchanged. The oldest is visited first, so with G >= 1 it always generates.
Younger growth must preserve protection. Thus every busy tick makes progress.

Before oldest release write A = a_o + S. The invariant implies S + R <= B. After
release, A' = S; for next-oldest n, H' = R - a_n, hence:

```text
A' + H' = S + R - a_n <= S + R <= B
```

Only a_o slots are released; early completion may have a_o < R. Total free space
after release is at least R because it includes previously protected free space.
Other simultaneous releases only reduce A'. With no remaining requests H' = 0.
The proof uses rounded R, so non-aligned M is covered. It does not establish
contiguous-placement feasibility or cover heterogeneous maximum contracts.

For finite valid input, FIFO and oldest progress guarantee draining without
discarding requests. Makespan is bounded by latest arrival plus total output
tokens. Actual outputs are used to check this bound in tests, not to schedule.

## Returned measurements

Primary outcomes are mean/p95 end-to-end latency (completion minus arrival),
makespan from time zero, and mean progressing requests (generated tokens divided
by makespan). At identical total output, the last two are mathematically linked,
not independent evidence. p95 uses nearest rank ceil(0.95 * N); empty percentiles
are `None`, empty means and makespan are zero.

Diagnostics include admissions/completions, mean/p95 admission waiting, per-request
first-token timestamps (None for prompt-only requests), peak active count, both
growth-stall reasons, compute deferrals, and queue request-ticks. Per-request
records also contain admission/completion timestamps and all outcome counts.
Admission-blocked counters count the unsuccessful head attempt once per tick,
split by reason; they do not count every queued request. Queue request-ticks equal
the sum of admission waiting times.

Memory metrics are allocated, used, protected-headroom, and unused-allocation
slot-ticks. Unused allocation = allocated minus used; protection is separate.
Peak occupancy = peak allocated / budget, while peak live occupancy = peak used /
budget. Peaks inspect every event, including pre-release states. Final allocated,
used, and protected amounts must all be zero. External fragmentation is not modeled.

## Validation and limits

Milestone 2 workloads are described below; the scheduler specification above is
unchanged.

Run all existing and new tests with:

```sh
python3 -B -m unittest -v
```

The 17 Phase 3 simulator tests cover strict validation, rounding, conservation, early and
simultaneous release, exact-fit budgets, FIFO ties and blocking, prompt-only
population exclusion, both growth-stall causes, compute conservation and reuse,
latency/percentiles, future-length noninterference, deterministic replay, and
exhaustive small and randomized finite-workload termination. Milestone 2 adds 20
workload tests, bringing the suite to 60 tests including the unchanged 23 Phase
1/2 tests. Workload tests cover independent streams, exact inclusive boundaries,
mixed-choice thresholds, types, IDs, arrival ordering, splits, burst groups,
canonical hashes, malformed input, round trips, separate-process reproducibility,
empty input, and tiny simulator API replays. This is correctness validation, not
the 72-case smoke matrix or the full experiment matrix; neither was run here.

No GPU, prefill compute, allocator runtime, bandwidth, batching, swapping, block
sharing, or contiguous fragmentation is modeled. Admission can occur early while
completion is delayed by stalls or compute deferrals. Larger active counts need
not mean more useful concurrency. The implementation favors explicit invariant
checks and readable traces over simulation speed. Experiment runners, full-matrix
controls, and statistical analysis remain future milestones; this core cannot
reproduce real vLLM GPU throughput.

## Milestone 2: workload generation and replay

`phase3_workloads.py` generates one workload at a time. Its frozen generator v1
uses M=2048 and defaults to 200 requests. The declarative
`phase3/configs/primary.json` records all 20 seeds (20261117 through 20261136),
length/split/arrival regimes, distributions, and planned allocation/budget/compute
dimensions. It is not an executable runner. It specifies 480 unique workloads:
4 length regimes * 2 splits * 3 arrival regimes * 20 seeds. Replaying those over
5 budgets * 4 allocations * 2 compute settings would give 19,200 primary runs;
the separate 640-control suite is not specified or executed by this file.

Lengths are uniform inclusive integers: short 32..256, medium 257..1024, long
1025..2048. Mixed independently draws an integer 0..99 for each request: 0..59
selects short, 60..89 medium, 90..99 long, followed by uniform sampling in that
range. The probabilities are represented exactly as rational pairs in the
manifest; a realized sample need not contain exactly those proportions.

Generation-heavy samples the prompt from 1..min(128,total-1), with output the
remainder. Prompt-heavy samples the output instead. First arrival is always at
tick zero: no arrival RNG draw is consumed for request 0. Subsequent dense gaps
are uniform 0..8 and moderate gaps 0..64. Bursty arrivals are
`128 * (request_id // 32)`, including a partial final group.

Three private `random.Random` streams are named `arrivals`, `lengths`, and `splits`.
Each integer seed is the unsigned big-endian SHA-256 digest of canonical JSON:

```text
["phase3-workloads-v1", seed, stream_name]
```

Canonical encoding is defined below and includes its final newline in this seed
hash. Regimes and request counts are not seed-derivation inputs. Changing arrival
regime cannot alter lengths or splits; changing split regime cannot alter lengths
or arrival timing. Python's randomized `hash()` and global RNG are never used.
Reproducibility is tested on Python 3.12; cross-version RNG compatibility is not
promised. Saved realized workloads are the replay source of truth.

### Versioned format and hash boundary

A workload JSON document has exactly four top-level keys:

- `schema_version`: integer 1.
- `manifest`: generator version, `config` (seed, M as `maximum`, request count,
  length/split/arrival regime), complete `distribution_definitions`, and `rng`.
- `requests`: ordered realized records with `request_id`, `arrival`, `prompt`,
  and `output`. IDs must be exactly 0..N-1, matching simulator input positions.
- `sha256`: lowercase hexadecimal digest of the canonical document with this
  top-level field omitted. The schema version, manifest, and requests are hashed.

Both payload and complete-file encodings use UTF-8, sorted object keys, compact
`,`/`:` separators, ASCII string escaping, no non-finite numbers, and exactly one
final LF. The hash includes the payload LF. `sha256` is therefore a payload hash,
not `sha256sum` of the complete file: the checksum never hashes itself.

Loading rejects unknown/missing fields, duplicate JSON keys, incompatible schema
or generator versions, malformed distributions/RNG metadata, non-integer numeric
fields (including booleans), invalid counts/IDs/order, unsupported regimes,
out-of-range gaps/splits/lengths, and mismatched hashes. JSON whitespace/key order
may differ on input; saving normalizes them. Canonically saved files round-trip
byte-for-byte. Existing files are never overwritten by `save` or the CLI.

Generator v1 fixes M=2048 but permits nonnegative seeds and request counts outside
the primary plan for small tests, including count zero. The workload format
describes this generator's distributions rather than arbitrary custom traces.
Those splits always produce positive output lengths; although the simulator
supports prompt-only requests, such traces are outside this generator's support.

Loading validates stored realizations and the checksum without RNG calls or
regeneration. It cannot prove that a valid saved realization actually came from
the claimed seed. The checksum detects un-rehashed tampering; it is not an
authentication signature. A provenance audit would be a separate explicit step.

### Reproduction commands and adapter

These commands generate and verify just one small example; choose an unused path:

```sh
python3 -B phase3_workloads.py generate --seed 20261117 --length-regime mixed --split-regime generation-heavy --arrival-regime dense --request-count 3 --output /tmp/phase3-example.json
python3 -B phase3_workloads.py verify /tmp/phase3-example.json
python3 -B -m unittest -v
```

The CLI prints only request count and payload hash, never simulator performance.
No workload files or comparative results are created in the repository by the
tests; temporary files are used for serialization checks.

```python
from phase3_workloads import load

workload = load("/tmp/phase3-example.json")
requests = workload.to_simulator_requests()
# Pass this same tuple and maximum=workload.config.maximum to simulate().
```

The adapter preserves ordering and returns an immutable tuple of the existing
`phase3_simulator.Request` type; no simulator change is required. It does not run
the simulator or regenerate data. Realized outputs are provided to the existing
execution component, whose scheduler-visible records still exclude output lengths.
Use the same loaded workload for every allocation strategy, budget, and compute
setting; never regenerate condition-specific traces during an experiment.
