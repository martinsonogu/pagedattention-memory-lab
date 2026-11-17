"""Deterministic memory-aware replay; ticks are not GPU execution time."""

from collections import deque
from dataclasses import dataclass


def _integer(name, value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, excluding bool")


def rounded(length, block_size):
    _integer("length", length)
    _integer("block_size", block_size, 1)
    return (length + block_size - 1) // block_size * block_size


@dataclass(frozen=True)
class Request:
    arrival: int
    prompt: int
    output: int


@dataclass(frozen=True)
class _PublicRequest:
    request_id: int
    arrival: int
    prompt: int


@dataclass
class _Resident:
    length: int
    allocated: int


class _Execution:
    """Private completion oracle, consulted only AFTER admission or generation.

    The scheduling state and allocation predicates never receive output lengths.
    """

    def __init__(self, requests):
        self._remaining = [r.output for r in requests]

    def prefill(self, request_id):
        return self._remaining[request_id] == 0

    def generate(self, request_id):
        if self._remaining[request_id] <= 0:
            raise RuntimeError("generation after completion")
        self._remaining[request_id] -= 1
        return self._remaining[request_id] == 0


def _failure(allocated, headroom, budget):
    if allocated > budget:
        return "physical_capacity"
    if allocated + headroom > budget:
        return "protected_headroom"
    return None


def _p95(values):
    return sorted(values)[(95 * len(values) + 99) // 100 - 1] if values else None


def simulate(requests, strategy, budget=32768, maximum=2048,
             block_size=16, compute_budget=None, trace=False):
    """Replay requests under FIFO admission and oldest-request protection.

    Request IDs are input positions. Arrivals sort by (arrival, ID); all later
    priority is admission order. None means unlimited global generation budget.
    Returns config, metrics, per-request records, and optional event snapshots.
    No input is mutated; this module does not read or write files.
    """
    if strategy not in ("fixed", "paged"):
        raise ValueError("strategy must be fixed or paged")
    _integer("budget", budget, 1)
    _integer("maximum", maximum, 1)
    _integer("block_size", block_size)
    if strategy == "paged" and block_size not in (8, 16, 32):
        raise ValueError("paged block_size must be 8, 16, or 32")
    if compute_budget is not None:
        _integer("compute_budget", compute_budget, 1)
    if type(trace) is not bool:
        raise ValueError("trace must be bool")
    reserve = maximum if strategy == "fixed" else rounded(maximum, block_size)
    if budget < reserve:
        raise ValueError("budget cannot protect one worst-case request")
    requests = tuple(requests)
    for request in requests:
        if not isinstance(request, Request):
            raise ValueError("requests must contain Request instances")
        _integer("arrival", request.arrival)
        _integer("prompt", request.prompt, 1)
        _integer("output", request.output)
        if request.prompt + request.output > maximum:
            raise ValueError("request exceeds maximum")
    public = [_PublicRequest(i, r.arrival, r.prompt) for i, r in enumerate(requests)]
    return _replay(public, _Execution(requests), strategy, budget, maximum,
                   block_size, compute_budget, reserve, trace)


def _replay(public, execution, strategy, budget, maximum, block_size,
            compute_budget, reserve, tracing):
    pending = deque(sorted(public, key=lambda r: (r.arrival, r.request_id)))
    queue = deque()
    active = {}  # Insertion order is admission order, including arrival ties.
    records = [dict(request_id=r.request_id, arrival=r.arrival, prompt=r.prompt,
                    admission=None, completion=None, first_token=None,
                    generated_tokens=0, physical_capacity_stalls=0,
                    protected_headroom_stalls=0, compute_deferrals=0) for r in public]
    events = []
    tick = peak_allocated = peak_used = peak_active = 0
    allocated_ticks = used_ticks = headroom_ticks = eligible_ticks = queue_ticks = 0
    blocked = {"physical_capacity": 0, "protected_headroom": 0}

    def allocation(length):
        return maximum if strategy == "fixed" else rounded(length, block_size)

    def memory():
        allocated = sum(s.allocated for s in active.values())
        used = sum(s.length for s in active.values())
        oldest = next(iter(active), None)
        headroom = reserve - active[oldest].allocated if oldest is not None else 0
        return allocated, used, headroom, oldest

    def snapshot(event, request_id=None, **details):
        nonlocal peak_allocated, peak_used, peak_active
        allocated, used, headroom, oldest = memory()
        if not (0 <= used <= allocated and 0 <= headroom and allocated + headroom <= budget):
            raise RuntimeError("memory/protection invariant violated")
        if any(not 1 <= s.length <= maximum or s.allocated != allocation(s.length)
               for s in active.values()):
            raise RuntimeError("resident allocation invariant violated")
        peak_allocated = max(peak_allocated, allocated)
        peak_used = max(peak_used, used)
        peak_active = max(peak_active, len(active))
        if tracing:
            events.append(dict(tick=tick, event=event, request_id=request_id,
                               allocated_slots=allocated, used_slots=used,
                               protected_headroom=headroom, oldest_id=oldest,
                               active_ids=tuple(active), queued_ids=tuple(r.request_id for r in queue),
                               residents=tuple((i, s.length, s.allocated) for i, s in active.items()),
                               **details))

    def release(request_id, prompt_only=False):
        released = active.pop(request_id).allocated
        records[request_id]["completion"] = tick
        # Headroom is recomputed atomically from the new oldest before snapshot.
        snapshot("complete", request_id, released_slots=released, prompt_only=prompt_only)

    while pending or queue or active:
        if not active and not queue and pending:
            tick = max(tick, pending[0].arrival)  # Idle intervals have zero slot-ticks.
        while pending and pending[0].arrival <= tick:
            request = pending.popleft()
            queue.append(request)
            snapshot("arrival", request.request_id)
        while queue:
            candidate = queue[0]
            required = allocation(candidate.prompt)
            allocated, _, headroom, oldest = memory()
            prospective_headroom = headroom if oldest is not None else reserve - required
            reason = _failure(allocated + required, prospective_headroom, budget)
            if reason:
                blocked[reason] += 1
                snapshot("admission_blocked", candidate.request_id, reason=reason)
                break  # Strict FIFO: never bypass the queue head.
            queue.popleft()
            active[candidate.request_id] = _Resident(candidate.prompt, required)
            records[candidate.request_id]["admission"] = tick
            snapshot("admit", candidate.request_id)
            # EOS after prefill is observed only AFTER the same admission test.
            if execution.prefill(candidate.request_id):
                release(candidate.request_id, prompt_only=True)

        # Freeze the accounting population after ALL prompt-only releases.
        eligible = tuple(active)
        if not eligible:
            if queue:
                raise RuntimeError("feasible queue cannot remain blocked with no active request")
            continue
        snapshot("tick_begin", eligible_ids=eligible)
        queue_ticks += len(queue)
        eligible_ticks += len(eligible)
        generated = 0
        finished = []
        outcomes = {}
        for request_id in eligible:
            record = records[request_id]
            if compute_budget is not None and generated == compute_budget:
                record["compute_deferrals"] += 1
                outcomes[request_id] = "compute_deferred"
                snapshot("compute_deferred", request_id)
                continue  # Memory eligibility is intentionally not examined.
            state = active[request_id]
            required = allocation(state.length + 1)
            allocated, _, headroom, oldest = memory()
            delta = required - state.allocated
            prospective_headroom = reserve - required if request_id == oldest else headroom
            reason = _failure(allocated + delta, prospective_headroom, budget)
            if reason:
                record[f"{reason}_stalls"] += 1
                outcomes[request_id] = reason
                snapshot("growth_stalled", request_id, reason=reason)
                continue  # Failed attempts do not consume generation opportunities.
            state.length += 1
            state.allocated = required
            generated += 1
            record["generated_tokens"] += 1
            if record["first_token"] is None:
                record["first_token"] = tick + 1
            outcomes[request_id] = "generated"
            snapshot("generate", request_id)
            if execution.generate(request_id):
                finished.append(request_id)

        if outcomes[eligible[0]] != "generated" or len(outcomes) != len(eligible):
            raise RuntimeError("progress/accounting invariant violated")
        allocated, used, headroom, _ = memory()
        allocated_ticks += allocated
        used_ticks += used
        headroom_ticks += headroom
        snapshot("tick_end", eligible_ids=eligible, outcomes=tuple(outcomes.items()))
        tick += 1
        for request_id in finished:
            release(request_id)

    waits = []
    latencies = []
    for record in records:
        if record["admission"] is None or record["completion"] is None:
            raise RuntimeError("request was not drained")
        record["waiting_ticks"] = record["admission"] - record["arrival"]
        record["latency_ticks"] = record["completion"] - record["arrival"]
        waits.append(record["waiting_ticks"])
        latencies.append(record["latency_ticks"])
    total = lambda name: sum(r[name] for r in records)
    generated = total("generated_tokens")
    physical = total("physical_capacity_stalls")
    protected = total("protected_headroom_stalls")
    deferred = total("compute_deferrals")
    if eligible_ticks != generated + physical + protected + deferred or queue_ticks != sum(waits):
        raise RuntimeError("aggregate accounting invariant violated")
    metrics = dict(admitted_requests=len(records), completed_requests=len(records), makespan=tick,
                   mean_latency_ticks=sum(latencies) / len(records) if records else 0,
                   p95_latency_ticks=_p95(latencies),
                   mean_progressing_requests=generated / tick if tick else 0,
                   total_waiting_ticks=sum(waits),
                   mean_waiting_ticks=sum(waits) / len(records) if records else 0,
                   p95_waiting_ticks=_p95(waits), generated_tokens=generated,
                   eligible_request_ticks=eligible_ticks,
                   physical_capacity_stalls=physical, protected_headroom_stalls=protected,
                   growth_stall_request_ticks=physical + protected, compute_deferrals=deferred,
                   admission_blocked_physical_ticks=blocked["physical_capacity"],
                   admission_blocked_protection_ticks=blocked["protected_headroom"],
                   queue_request_ticks=queue_ticks, peak_active_requests=peak_active,
                   allocated_slot_ticks=allocated_ticks, used_slot_ticks=used_ticks,
                   protected_headroom_slot_ticks=headroom_ticks,
                   unused_allocated_slot_ticks=allocated_ticks - used_ticks,
                   peak_allocated_slots=peak_allocated, peak_used_slots=peak_used,
                   peak_occupancy=peak_allocated / budget, peak_live_occupancy=peak_used / budget,
                   final_allocated_slots=0, final_used_slots=0, final_protected_headroom=0)
    return dict(config=dict(strategy=strategy, budget=budget, maximum=maximum,
                            block_size=block_size if strategy == "paged" else 0,
                            compute_budget=compute_budget),
                metrics=metrics, requests=records, trace=events)
