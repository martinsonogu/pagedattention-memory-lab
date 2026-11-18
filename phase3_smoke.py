"""Correctness-only hand-built smoke matrix, independent of generator v1."""
import argparse
import hashlib
from pathlib import Path
import time

from phase3_experiment import canonical, read_json, replay, write_rows
from phase3_simulator import Request, rounded

DEFAULT_CONFIG = Path(__file__).parent / "phase3/configs/smoke.json"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_result(result, requests):
    """Recompute conservation and metrics from events, independent of counters."""
    m, c, records, events = (result[k] for k in ("metrics", "config", "requests", "trace"))
    n = len(requests)
    check(len(records) == m["admitted_requests"] == m["completed_requests"] == n, "request conservation")
    order = sorted(range(n), key=lambda i: (requests[i].arrival, i))
    check([e["request_id"] for e in events if e["event"] == "admit"] == order, "FIFO order")
    check(sorted(e["request_id"] for e in events if e["event"] == "complete") == list(range(n)), "completion IDs")
    reserve = c["maximum"] if c["strategy"] == "fixed" else rounded(c["maximum"], c["block_size"])
    for e in events:
        a, u, h = (e[k] for k in ("allocated_slots", "used_slots", "protected_headroom"))
        check(0 <= u <= a and 0 <= h and a + h <= c["budget"], "memory safety")
        check(a == sum(r[2] for r in e["residents"]), "allocation conservation")
        check(u == sum(r[1] for r in e["residents"]), "live-token conservation")
        check(h == (reserve - e["residents"][0][2] if e["residents"] else 0), "headroom transfer")
        for _, length, allocation in e["residents"]:
            check(allocation == (c["maximum"] if c["strategy"] == "fixed" else rounded(length, c["block_size"])), "rounding")
    ends = [e for e in events if e["event"] == "tick_end"]
    counts = dict(generated=0, physical_capacity=0, protected_headroom=0, compute_deferred=0)
    for e in ends:
        outcomes = dict(e["outcomes"])
        check(tuple(outcomes) == tuple(e["eligible_ids"]), "exhaustive population")
        check(outcomes[e["eligible_ids"][0]] == "generated", "oldest progress")
        generated = list(outcomes.values()).count("generated")
        check(c["compute_budget"] is None or generated <= c["compute_budget"], "compute conservation")
        for value in outcomes.values():
            check(value in counts, "unknown outcome")
            counts[value] += 1
    for outcome, metric in (("generated", "generated_tokens"), ("physical_capacity", "physical_capacity_stalls"),
                            ("protected_headroom", "protected_headroom_stalls"), ("compute_deferred", "compute_deferrals")):
        check(counts[outcome] == m[metric] == sum(r[metric] for r in records), metric)
    check(sum(counts.values()) == m["eligible_request_ticks"], "eligible accounting")
    check(m["growth_stall_request_ticks"] == counts["physical_capacity"] + counts["protected_headroom"], "stall sum")
    for event_key, metric in (("allocated_slots", "allocated_slot_ticks"), ("used_slots", "used_slot_ticks"),
                              ("protected_headroom", "protected_headroom_slot_ticks")):
        check(sum(e[event_key] for e in ends) == m[metric], metric)
    for key, metric in (("allocated_slots", "peak_allocated_slots"), ("used_slots", "peak_used_slots")):
        check(max((e[key] for e in events), default=0) == m[metric], metric)
    check(m["peak_occupancy"] == m["peak_allocated_slots"] / c["budget"], "allocated occupancy")
    check(m["peak_live_occupancy"] == m["peak_used_slots"] / c["budget"], "live occupancy")
    check(m["peak_active_requests"] == max((len(e["active_ids"]) for e in events), default=0), "peak active")
    check(m["unused_allocated_slot_ticks"] == m["allocated_slot_ticks"] - m["used_slot_ticks"], "unused slots")
    for i, (record, request) in enumerate(zip(records, requests)):
        check(record["request_id"] == i and record["arrival"] == request.arrival, "record identity")
        check(request.arrival <= record["admission"] <= record["completion"], "timestamps")
        check(record["generated_tokens"] == request.output, "output conservation")
        check(record["completion"] - record["admission"] == sum(record[k] for k in
              ("generated_tokens", "physical_capacity_stalls", "protected_headroom_stalls", "compute_deferrals")), "resident accounting")
    for field, start, mean, p95 in (("latency_ticks", "arrival", "mean_latency_ticks", "p95_latency_ticks"),
                                   ("waiting_ticks", "arrival", "mean_waiting_ticks", "p95_waiting_ticks")):
        end = "completion" if field == "latency_ticks" else "admission"
        values = [r[end] - r[start] for r in records]
        check(values == [r[field] for r in records], field)
        check(m[mean] == (sum(values) / n if n else 0), mean)
        check(m[p95] == (sorted(values)[(95*n+99)//100-1] if n else None), p95)
    check(m["total_waiting_ticks"] == m["queue_request_ticks"] == sum(r["waiting_ticks"] for r in records), "queue accounting")
    check(m["makespan"] == max((r["completion"] for r in records), default=0), "makespan")
    check(m["makespan"] <= max((r.arrival for r in requests), default=0) + sum(r.output for r in requests), "termination bound")
    check(m["mean_progressing_requests"] == (m["generated_tokens"] / m["makespan"] if m["makespan"] else 0), "progress denominator")
    check(all(m[k] == 0 for k in ("final_allocated_slots", "final_used_slots", "final_protected_headroom")), "release")


def check_expected(fixture, result):
    c, m, records = (result[k] for k in ("config", "metrics", "requests"))
    for rule in fixture["expected"]:
        if all(c.get(k) == v for k, v in rule["when"].items()):
            for key, value in rule.get("metrics", {}).items():
                check(m[key] == value, f"{fixture['name']}: expected {key}={value}")
            for key, value in rule.get("records", {}).items():
                check([r[key] for r in records] == value, f"{fixture['name']}: expected {key}")
            for key in rule.get("positive", []):
                check(m[key] > 0, f"{fixture['name']}: expected positive {key}")


def smoke(path=DEFAULT_CONFIG):
    config = read_json(path)
    check(config["schema_version"] == 1 and config["compute_budgets"] == [None, 1, 2], "smoke configuration")
    check(len(config["fixtures"]) == 6, "six fixtures required")
    check(len({f["name"] for f in config["fixtures"]}) == 6, "duplicate fixture names")
    identities = [canonical({k: f[k] for k in ("maximum", "budget", "requests")})
                  for f in config["fixtures"]]
    check(len(set(identities)) == 6, "duplicate fixture workloads")
    summaries = []
    for fixture in config["fixtures"]:
        requests = tuple(Request(**r) for r in fixture["requests"])
        kwargs = dict(maximum=fixture["maximum"], budgets=[fixture["budget"]],
                      compute_budgets=config["compute_budgets"], outcomes=True, trace=True)
        first = list(replay(requests, **kwargs))
        second = list(replay(requests, **kwargs))
        expected = {(strategy, block, fixture["budget"], compute)
                    for strategy, block in (("fixed", 0), ("paged", 8), ("paged", 16), ("paged", 32))
                    for compute in (None, 1, 2)}
        for results in (first, second):
            actual = [(r["config"]["strategy"], r["config"]["block_size"],
                       r["config"]["budget"], r["config"]["compute_budget"]) for r in results]
            check(len(actual) == 12 and set(actual) == expected, "missing or duplicate smoke conditions")
        check(canonical(first) == canonical(second), "deterministic replay")
        for result in first:
            validate_result(result, requests)
            check_expected(fixture, result)
        summaries.append(dict(fixture=fixture["name"], runs=len(first), replay_checks=len(second),
                              status="passed", fixture_sha256=hashlib.sha256(canonical(fixture)).hexdigest()))
    check(sum(s["runs"] for s in summaries) == 72, "72 distinct smoke cases")
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    start = time.perf_counter()
    summaries = smoke(args.config)
    write_rows(summaries, args.output)
    for row in summaries:
        print(f"{row['fixture']}: {row['runs']}/12 passed")
    print(f"72 distinct cases passed; 72 additional deterministic replays; 0 invariant failures; runtime={time.perf_counter()-start:.3f}s")


if __name__ == "__main__":
    main()
