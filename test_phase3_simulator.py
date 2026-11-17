import itertools
import random
import unittest

from phase3_simulator import Request, rounded, simulate


STRATEGIES = [("fixed", 0), ("paged", 8), ("paged", 16), ("paged", 32)]


class Phase3Tests(unittest.TestCase):
    def replay(self, requests, strategy="paged", block=8, **kwargs):
        return simulate(requests, strategy, block_size=block, trace=True, **kwargs)

    def assert_conservation(self, result, requests):
        metrics, config = result["metrics"], result["config"]
        maximum = config["maximum"]
        reserve = maximum if config["strategy"] == "fixed" else rounded(maximum, config["block_size"])
        for event in result["trace"]:
            a, u, h = (event[k] for k in ("allocated_slots", "used_slots", "protected_headroom"))
            self.assertTrue(0 <= u <= a <= config["budget"])
            self.assertTrue(0 <= h and a + h <= config["budget"])
            self.assertEqual(a, sum(row[2] for row in event["residents"]))
            self.assertEqual(u, sum(row[1] for row in event["residents"]))
            self.assertEqual(h, reserve - event["residents"][0][2] if event["residents"] else 0)
            self.assertEqual(set(event["active_ids"]) & set(event["queued_ids"]), set())
            if event["event"] == "tick_end":
                outcomes = dict(event["outcomes"])
                self.assertEqual(tuple(outcomes), event["eligible_ids"])
                self.assertEqual(outcomes[event["eligible_ids"][0]], "generated")
                generated = sum(v == "generated" for v in outcomes.values())
                if config["compute_budget"] is not None:
                    self.assertLessEqual(generated, config["compute_budget"])
        self.assertEqual(metrics["admitted_requests"], len(requests))
        self.assertEqual(metrics["completed_requests"], len(requests))
        self.assertEqual(metrics["generated_tokens"], sum(r.output for r in requests))
        self.assertEqual(metrics["eligible_request_ticks"], metrics["generated_tokens"] +
                         metrics["growth_stall_request_ticks"] + metrics["compute_deferrals"])
        self.assertEqual(metrics["queue_request_ticks"], metrics["total_waiting_ticks"])
        self.assertEqual(metrics["final_allocated_slots"], 0)
        self.assertEqual(metrics["final_used_slots"], 0)
        self.assertEqual(metrics["final_protected_headroom"], 0)
        for record, request in zip(result["requests"], requests):
            self.assertEqual(record["generated_tokens"], request.output)
            self.assertGreaterEqual(record["admission"], request.arrival)
            self.assertGreaterEqual(record["completion"], record["admission"])
            # Each resident generating interval has precisely one accounting outcome.
            self.assertEqual(record["completion"] - record["admission"],
                             record["generated_tokens"] + record["physical_capacity_stalls"] +
                             record["protected_headroom_stalls"] + record["compute_deferrals"])

    def test_rounding_and_invalid_inputs(self):
        for block in (8, 16, 32):
            for length in range(70):
                allocation = rounded(length, block)
                self.assertEqual(allocation % block, 0)
                self.assertTrue(length <= allocation < length + block)
        for field in ("budget", "maximum", "block_size", "compute_budget"):
            for value in (True, False, 1.5, 16.0, "8", -1):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        simulate([], "fixed", **{field: value})
        for field in ("arrival", "prompt", "output"):
            for value in (True, False, 1.0, "1", None, -1):
                fields = dict(arrival=0, prompt=1, output=1)
                fields[field] = value
                with self.assertRaises(ValueError):
                    self.replay([Request(**fields)])
        for kwargs in (dict(compute_budget=0), dict(maximum=0), dict(budget=0),
                       dict(maximum=33, budget=33, block=32), dict(block=7)):
            with self.assertRaises(ValueError):
                self.replay([], **kwargs)
        with self.assertRaises(ValueError):
            self.replay([Request(0, 0, 1)])
        with self.assertRaises(ValueError):
            self.replay([Request(0, 32, 1)], maximum=32)
        with self.assertRaises(ValueError):
            simulate([], "unknown")

    def test_empty_and_prompt_only(self):
        empty = self.replay([])["metrics"]
        self.assertEqual(empty["makespan"], 0)
        self.assertIsNone(empty["p95_latency_ticks"])
        self.assertIsNone(empty["p95_waiting_ticks"])
        requests = [Request(3, 1, 0)] * 3
        result = self.replay(requests, maximum=33, budget=64, block=32, compute_budget=1)
        self.assert_conservation(result, requests)
        self.assertEqual(result["metrics"]["makespan"], 3)
        self.assertEqual(result["metrics"]["allocated_slot_ticks"], 0)
        self.assertFalse(any(e["event"] == "tick_begin" for e in result["trace"]))
        for event in result["trace"]:
            if event["event"] == "complete":
                self.assertEqual(event["protected_headroom"], 0)

    def test_hand_calculated_metrics(self):
        result = self.replay([Request(2, 8, 2)], maximum=32, budget=32)
        expected = dict(makespan=4, mean_latency_ticks=2, p95_latency_ticks=2,
                        mean_progressing_requests=0.5, total_waiting_ticks=0,
                        allocated_slot_ticks=32, used_slot_ticks=19,
                        protected_headroom_slot_ticks=32, peak_allocated_slots=16,
                        peak_used_slots=10, peak_occupancy=0.5, peak_live_occupancy=10 / 32)
        for name, value in expected.items():
            self.assertEqual(result["metrics"][name], value, name)
        self.assertEqual(result["requests"][0]["first_token"], 3)

    def test_early_completion_non_aligned_headroom_transfer(self):
        requests = [Request(0, 1, 1), Request(0, 1, 32), Request(0, 1, 32)]
        result = self.replay(requests, maximum=33, budget=128, block=32)
        self.assert_conservation(result, requests)
        release = next(e for e in result["trace"] if e["event"] == "complete")
        self.assertEqual(release["request_id"], 0)
        self.assertEqual(release["released_slots"], 32)  # Strictly less than R=64.
        self.assertEqual(release["allocated_slots"], 64)
        self.assertEqual(release["protected_headroom"], 32)
        self.assertEqual(release["oldest_id"], 1)
        self.assertGreaterEqual(128 - release["allocated_slots"], 64)

    def test_exact_fit_and_simultaneous_completions(self):
        requests = [Request(0, 31, 1), Request(0, 31, 1)]
        for strategy, block in STRATEGIES:
            result = self.replay(requests, strategy, block, maximum=32, budget=64)
            self.assert_conservation(result, requests)
            self.assertEqual(result["metrics"]["makespan"], 1)
            self.assertEqual(result["metrics"]["peak_occupancy"], 1)
            self.assertEqual([r["completion"] for r in result["requests"]], [1, 1])
        single = self.replay([Request(0, 1, 31)], maximum=32, budget=32)
        self.assertEqual(single["metrics"]["makespan"], 31)
        self.assertEqual(single["metrics"]["growth_stall_request_ticks"], 0)

    def test_fifo_no_bypass_even_for_prompt_only(self):
        requests = [Request(0, 1, 2), Request(0, 32, 0), Request(0, 1, 1)]
        result = self.replay(requests, maximum=32, budget=48)
        self.assert_conservation(result, requests)
        self.assertEqual([r["admission"] for r in result["requests"]], [0, 2, 2])
        self.assertEqual([r["completion"] for r in result["requests"]], [2, 2, 3])
        blocked = [e for e in result["trace"] if e["event"] == "admission_blocked"]
        self.assertTrue(all(e["request_id"] == 1 for e in blocked))
        self.assertEqual(blocked[0]["reason"], "protected_headroom")

    def test_boundary_arrivals_and_stable_ties(self):
        requests = [Request(1, 31, 1)] + [Request(0, 31, 1)] * 3
        for strategy, block in STRATEGIES:
            result = self.replay(requests, strategy, block, maximum=32, budget=64)
            admitted = [(e["request_id"], e["tick"]) for e in result["trace"] if e["event"] == "admit"]
            self.assertEqual(admitted, [(1, 0), (2, 0), (3, 1), (0, 1)])
            self.assert_conservation(result, requests)

    def test_prompt_only_released_before_population_is_frozen(self):
        requests = [Request(0, 1, 0), Request(0, 1, 2), Request(0, 1, 0), Request(0, 1, 1)]
        for strategy, block in STRATEGIES:
            result = self.replay(requests, strategy, block, maximum=32, budget=128, compute_budget=1)
            self.assert_conservation(result, requests)
            begin = next(e for e in result["trace"] if e["event"] == "tick_begin")
            self.assertEqual(begin["eligible_ids"], (1, 3))
            self.assertEqual(begin["oldest_id"], 1)
            for request_id in (0, 2):
                record = result["requests"][request_id]
                self.assertEqual(record["admission"], record["completion"])
                self.assertEqual(record["compute_deferrals"], 0)
                self.assertIsNone(record["first_token"])

    def test_physical_and_protected_stalls_are_observed(self):
        requests = [Request(0, 1, 31)] * 5
        result = self.replay(requests, maximum=32, budget=64)
        self.assert_conservation(result, requests)
        self.assertGreater(result["metrics"]["physical_capacity_stalls"], 0)
        self.assertGreater(result["metrics"]["protected_headroom_stalls"], 0)
        self.assertGreater(result["metrics"]["peak_active_requests"], 64 // 32)
        self.assertLessEqual(result["metrics"]["makespan"], 155)

    def test_stalled_attempt_does_not_consume_compute(self):
        requests = [Request(0, 8, 24), Request(0, 8, 24)] + [Request(0, 1, 31)] * 3
        result = self.replay(requests, maximum=32, budget=64, compute_budget=2)
        self.assert_conservation(result, requests)
        first = next(e for e in result["trace"] if e["event"] == "tick_end")
        self.assertEqual(dict(first["outcomes"]), {0: "generated", 1: "protected_headroom",
                                                  2: "generated", 3: "compute_deferred",
                                                  4: "compute_deferred"})

    def test_compute_deferral_precedes_memory_check(self):
        requests = [Request(0, 8, 24), Request(0, 8, 24)]
        result = self.replay(requests, maximum=32, budget=40, compute_budget=1)
        first = next(e for e in result["trace"] if e["event"] == "tick_end")
        self.assertEqual(dict(first["outcomes"]), {0: "generated", 1: "compute_deferred"})
        self.assertEqual(result["metrics"]["growth_stall_request_ticks"], 0)
        self.assertGreater(result["metrics"]["compute_deferrals"], 0)
        self.assert_conservation(result, requests)

    def test_compute_limited_control_and_latency(self):
        requests = [Request(0, 1, 2)] * 3
        for strategy, block in STRATEGIES:
            result = self.replay(requests, strategy, block, maximum=32, budget=128, compute_budget=1)
            self.assert_conservation(result, requests)
            self.assertEqual([r["completion"] for r in result["requests"]], [2, 4, 6])
            self.assertEqual(result["metrics"]["mean_latency_ticks"], 4)
            self.assertEqual(result["metrics"]["p95_latency_ticks"], 6)
            self.assertEqual(result["metrics"]["mean_progressing_requests"], 1)
            self.assertEqual(result["metrics"]["total_waiting_ticks"], 0)

    def test_nearest_rank_percentile(self):
        requests = [Request(0, 1, output) for output in range(1, 21)]
        result = self.replay(requests, maximum=32, budget=1024)
        self.assertEqual(result["metrics"]["p95_latency_ticks"], 19)

    def test_no_future_length_in_admission_or_growth(self):
        short = [Request(0, 1, 3), Request(0, 8, 20), Request(0, 1, 20)]
        longer = [Request(0, 1, 5), Request(0, 8, 22), Request(0, 1, 24)]
        for strategy, block in STRATEGIES:
            for compute in (None, 1, 2):
                a = self.replay(short, strategy, block, maximum=32, budget=64, compute_budget=compute)
                b = self.replay(longer, strategy, block, maximum=32, budget=64, compute_budget=compute)
                self.assertEqual([e for e in a["trace"] if e["tick"] < 3],
                                 [e for e in b["trace"] if e["tick"] < 3])

    def test_deterministic_replay_does_not_mutate_input(self):
        requests = [Request(2, 1, 3), Request(0, 8, 0), Request(2, 8, 10)]
        before = list(requests)
        self.assertEqual(self.replay(requests), self.replay(requests))
        self.assertEqual(requests, before)
        self.assertEqual(simulate(requests, "paged")["trace"], [])

    def test_small_exhaustive_termination_and_accounting(self):
        choices = [Request(0, 1, 0), Request(1, 1, 2), Request(0, 8, 1)]
        for size in range(4):
            for requests in itertools.product(choices, repeat=size):
                for strategy, block in STRATEGIES:
                    for compute in (None, 1, 2):
                        result = self.replay(requests, strategy, block, maximum=9,
                                             budget=64, compute_budget=compute)
                        self.assert_conservation(result, requests)
                        bound = max((r.arrival for r in requests), default=0) + sum(r.output for r in requests)
                        self.assertLessEqual(result["metrics"]["makespan"], bound)

    def test_randomized_pressure_and_termination(self):
        for seed in range(10):
            rng = random.Random(seed)
            requests = []
            for _ in range(8):
                prompt = rng.randint(1, 32)
                requests.append(Request(rng.randint(0, 6), prompt, rng.randint(0, 33 - prompt)))
            for strategy, block in STRATEGIES:
                for compute in (None, 1, 2):
                    result = self.replay(requests, strategy, block, maximum=33,
                                         budget=64, compute_budget=compute)
                    self.assert_conservation(result, requests)
                    self.assertLessEqual(result["metrics"]["makespan"],
                                         max(r.arrival for r in requests) + sum(r.output for r in requests))


if __name__ == "__main__":
    unittest.main()
