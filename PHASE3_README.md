# Phase 3 core: frozen scheduler specification

This milestone implements only deterministic replay and unit tests. There is no
workload generator, experiment CLI, full matrix execution, or performance claim.
Phase 1 and Phase 2 code and canonical CSVs remain unchanged.

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

Run all existing and new tests with:

```sh
python3 -B -m unittest -v
```

The 17 Phase 3 tests cover strict validation, rounding, conservation, early and
simultaneous release, exact-fit budgets, FIFO ties and blocking, prompt-only
population exclusion, both growth-stall causes, compute conservation and reuse,
latency/percentiles, future-length noninterference, deterministic replay, and
exhaustive small and randomized finite-workload termination. There are 40 tests
including the unchanged 23 Phase 1/2 tests. This is correctness validation, not
the preregistered experiment matrix or evidence of performance improvement.

No GPU, prefill compute, allocator runtime, bandwidth, batching, swapping, block
sharing, or contiguous fragmentation is modeled. Admission can occur early while
completion is delayed by stalls or compute deferrals. Larger active counts need
not mean more useful concurrency. The implementation favors explicit invariant
checks and readable traces over simulation speed. Workload manifests, experiment
runners, full-matrix controls, and statistical analysis remain separate future
milestones; this core cannot reproduce real vLLM GPU throughput.
