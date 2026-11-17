"""Deterministic allocation simulation; ticks are not GPU execution time."""

import argparse
import csv
import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path


BLOCKS = (8, 16, 32)


def _integer(name, value, minimum=None):
    """Require built-in integers, excluding bool and implicit numeric coercion."""
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer (not bool)")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def rounded(length, block):
    _integer("length", length, 0)
    _integer("block", block, 1)
    return ((length + block - 1) // block) * block


def safe_capacity(budget, maximum):
    _integer("budget", budget, 1)
    _integer("maximum", maximum, 1)
    return budget // max(rounded(maximum, b) for b in BLOCKS)


@dataclass(frozen=True)
class Request:
    arrival: int
    prompt: int
    output: int


def workload(seed, requests=100, maximum=2048):
    _integer("seed", seed)
    _integer("requests", requests, 0)
    _integer("maximum", maximum, 2)
    rng = random.Random(seed)
    arrival = 0
    result = []
    for _ in range(requests):
        arrival += rng.randint(0, 8)
        prompt = rng.randint(1, min(256, maximum - 1))
        output = rng.randint(1, min(512, maximum - prompt))
        result.append(Request(arrival, prompt, output))
    return result


def simulate(requests, strategy, budget=32768, maximum=2048,
             block_size=16, concurrency=None, trace=None):
    """FIFO admission with a shared worst-case-safe concurrency limit.

    Optional trace is a list receiving event snapshots, useful for auditing.
    Invalid or unsafe configurations fail before any request is processed.
    """
    if strategy not in ("fixed", "paged"):
        raise ValueError("unknown strategy")
    _integer("block_size", block_size, 0)
    if strategy == "paged" and block_size not in BLOCKS:
        raise ValueError("supported block sizes are 8, 16, 32")
    cap = safe_capacity(budget, maximum)
    concurrency = cap if concurrency is None else concurrency
    _integer("concurrency", concurrency, 1)
    if not 1 <= concurrency <= cap:
        raise ValueError("budget/concurrency cannot guarantee worst-case growth")
    requests = list(requests)
    for r in requests:
        _integer("arrival", r.arrival, 0)
        _integer("prompt", r.prompt, 1)
        _integer("output", r.output, 0)
        if r.prompt + r.output > maximum:
            raise ValueError("request length exceeds maximum")
    pending = deque(sorted(enumerate(requests), key=lambda pair: pair[1].arrival))
    queue = deque()
    active = {}
    tick = completed = total_wait = allocated = used = 0
    peak_allocated = peak_used = allocated_ticks = used_ticks = queue_ticks = 0

    def snapshot(event, request_id=None):
        nonlocal peak_allocated, peak_used
        if not 0 <= used <= allocated <= budget:
            raise RuntimeError("memory-budget invariant violated")
        peak_allocated = max(peak_allocated, allocated)
        peak_used = max(peak_used, used)
        if trace is not None:
            trace.append(dict(tick=tick, event=event, request_id=request_id,
                              allocated_slots=allocated, used_slots=used,
                              active=len(active), queued=len(queue)))

    while pending or queue or active:
        while pending and pending[0][1].arrival <= tick:
            item = pending.popleft()
            queue.append(item)
            snapshot("arrival", item[0])
        while queue and len(active) < concurrency:
            request_id, r = queue.popleft()
            reservation = maximum if strategy == "fixed" else rounded(r.prompt, block_size)
            if allocated + reservation > budget:
                raise RuntimeError("safe admission bound violated")
            active[request_id] = [r, r.prompt, reservation]
            allocated += reservation
            used += r.prompt
            total_wait += tick - r.arrival
            snapshot("admit", request_id)
            if r.output == 0:
                allocated -= reservation
                used -= r.prompt
                del active[request_id]
                completed += 1
                snapshot("complete", request_id)
        queue_ticks += len(queue)
        for request_id, state in active.items():
            r, length, reservation = state
            new_length = length + 1
            required = maximum if strategy == "fixed" else rounded(new_length, block_size)
            if allocated + required - reservation > budget:
                raise RuntimeError("safe growth bound violated")
            allocated += required - reservation
            used += 1
            state[1:] = [new_length, required]
            snapshot("generate", request_id)
        # Charge the post-generation, pre-release occupancy to this tick.
        # A prompt-only request completes immediately and contributes no slot-ticks.
        allocated_ticks += allocated
        used_ticks += used
        if active or queue or pending:
            tick += 1
        for request_id, (r, length, reservation) in list(active.items()):
            if length == r.prompt + r.output:
                allocated -= reservation
                used -= length
                del active[request_id]
                completed += 1
                snapshot("complete", request_id)
    return dict(completed_requests=completed, makespan=tick,
                total_waiting_ticks=total_wait,
                mean_waiting_ticks=total_wait / completed if completed else 0,
                allocated_slot_ticks=allocated_ticks, used_slot_ticks=used_ticks,
                mean_allocated_slots=allocated_ticks / tick if tick else 0,
                mean_used_slots=used_ticks / tick if tick else 0,
                peak_allocated_slots=peak_allocated, peak_used_slots=peak_used,
                peak_occupancy=peak_allocated / budget,
                admission_stall_request_ticks=queue_ticks,
                allocation_failures=0, growth_stall_request_ticks=0,
                final_allocated_slots=allocated, final_used_slots=used,
                concurrency=concurrency)


def run(seed=20261117, trials=20, requests=100, budget=32768, maximum=2048,
        concurrency=None):
    _integer("seed", seed)
    _integer("trials", trials, 1)
    _integer("requests", requests, 0)
    _integer("budget", budget, 1)
    _integer("maximum", maximum, 2)
    if concurrency is not None:
        _integer("concurrency", concurrency, 1)
    rows = []
    for trial in range(trials):
        trial_seed = seed + trial
        arrivals = workload(trial_seed, requests, maximum)
        for strategy, block in [("fixed", 0)] + [("paged", b) for b in BLOCKS]:
            metrics = simulate(arrivals, strategy, budget, maximum, block, concurrency)
            rows.append(dict(trial=trial, seed=trial_seed, strategy=strategy,
                             block_size=block, requests=requests, budget=budget,
                             maximum=maximum, **metrics))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="phase2_results.csv")
    parser.add_argument("--seed", type=int, default=20261117)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--budget", type=int, default=32768)
    parser.add_argument("--maximum", type=int, default=2048)
    parser.add_argument("--concurrency", type=int)
    args = parser.parse_args()
    out = Path(args.output)
    if out.resolve() == Path(__file__).with_name("results.csv").resolve():
        parser.error("refusing to overwrite Phase 1 results.csv")
    try:
        rows = run(args.seed, args.trials, args.requests, args.budget,
                   args.maximum, args.concurrency)
    except ValueError as exc:
        parser.error(str(exc))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    for strategy, block in [("fixed", 0)] + [("paged", b) for b in BLOCKS]:
        group = [r for r in rows if (r["strategy"], r["block_size"]) == (strategy, block)]
        def mean(key):
            return sum(r[key] for r in group) / len(group)
        print(f'{strategy:5} block={block:2} completed={mean("completed_requests"):.2f} '
              f'makespan={mean("makespan"):.2f} wait={mean("mean_waiting_ticks"):.2f} '
              f'mean_allocated={mean("mean_allocated_slots"):.2f} '
              f'peak_occupancy={mean("peak_occupancy"):.3%} '
              f'failures={mean("allocation_failures"):.0f}')
    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
