import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dynamic_experiment import BLOCKS, Request, rounded, run, safe_capacity, simulate, workload


class DynamicTests(unittest.TestCase):
    def test_rounding(self):
        for block in BLOCKS:
            for length in range(130):
                allocation = rounded(length, block)
                self.assertEqual(allocation % block, 0)
                self.assertLessEqual(length, allocation)
                self.assertLess(allocation - length, block)
        self.assertEqual(rounded(0, 16), 0)
        with self.assertRaises(ValueError):
            rounded(1, 0)

    def test_determinism_and_seed(self):
        self.assertEqual(run(trials=2, requests=12), run(trials=2, requests=12))
        self.assertEqual(workload(1), workload(1))
        self.assertNotEqual(workload(1), workload(2))
        for r in workload(1):
            self.assertLessEqual(r.prompt + r.output, 2048)

    def test_arrival_growth_release_and_metrics(self):
        trace = []
        result = simulate([Request(2, 8, 2)], "paged", 32, 32, 8, trace=trace)
        self.assertEqual(result["makespan"], 4)
        self.assertEqual(result["total_waiting_ticks"], 0)
        self.assertEqual(result["allocated_slot_ticks"], 32)
        self.assertEqual(result["used_slot_ticks"], 19)
        self.assertEqual(result["mean_allocated_slots"], 8)
        self.assertEqual(result["peak_allocated_slots"], 16)
        self.assertEqual(result["peak_used_slots"], 10)
        self.assertEqual(result["peak_occupancy"], 0.5)
        self.assertEqual([(e["tick"], e["used_slots"]) for e in trace
                          if e["event"] == "generate"], [(2, 9), (3, 10)])
        self.assertEqual(trace[-1]["event"], "complete")
        self.assertEqual(trace[-1]["tick"], 4)
        self.assertEqual(trace[-1]["allocated_slots"], 0)

    def test_fifo_arrival_order_and_memory_reuse(self):
        trace = []
        result = simulate([Request(1, 1, 1), Request(0, 1, 3), Request(1, 1, 1)],
                          "fixed", 32, 32, trace=trace)
        admitted = [(e["request_id"], e["tick"]) for e in trace if e["event"] == "admit"]
        self.assertEqual(admitted, [(1, 0), (0, 3), (2, 4)])
        self.assertEqual(result["makespan"], 5)
        self.assertEqual(result["total_waiting_ticks"], 5)
        self.assertEqual(result["admission_stall_request_ticks"], 5)
        self.assertEqual(result["completed_requests"], 3)
        self.assertEqual(result["final_allocated_slots"], 0)

    def test_pressure_terminates_and_common_scheduler(self):
        requests = [Request(0, 1, 31)] * 7
        results = []
        for strategy, block in [("fixed", 0)] + [("paged", b) for b in BLOCKS]:
            trace = []
            result = simulate(requests, strategy, 64, 32, block, trace=trace)
            results.append(result)
            self.assertEqual(result["completed_requests"], 7)
            self.assertEqual(result["makespan"], 124)
            self.assertEqual(result["allocation_failures"], 0)
            self.assertEqual(result["growth_stall_request_ticks"], 0)
            self.assertEqual(result["final_used_slots"], 0)
            for event in trace:
                self.assertLessEqual(event["used_slots"], event["allocated_slots"])
                self.assertLessEqual(event["allocated_slots"], 64)
                self.assertLessEqual(event["active"], 2)
        self.assertEqual(len({r["total_waiting_ticks"] for r in results}), 1)

    def test_randomized_budget_invariants_and_bound(self):
        for seed in range(10):
            requests = workload(seed, 15, 33)
            for strategy, block in [("fixed", 0)] + [("paged", b) for b in BLOCKS]:
                trace = []
                result = simulate(requests, strategy, 128, 33, block, trace=trace)
                self.assertEqual(result["completed_requests"], len(requests))
                self.assertLessEqual(result["makespan"],
                                     max(r.arrival for r in requests) + sum(r.output for r in requests))
                for event in trace:
                    self.assertTrue(0 <= event["used_slots"] <= event["allocated_slots"] <= 128)

    def test_non_aligned_maximum_can_cost_paging_more(self):
        self.assertEqual(safe_capacity(128, 33), 2)
        requests = [Request(0, 32, 1)] * 2
        fixed = simulate(requests, "fixed", 128, 33)
        paged = simulate(requests, "paged", 128, 33, 32)
        self.assertGreater(paged["allocated_slot_ticks"], fixed["allocated_slot_ticks"])
        self.assertEqual(paged["makespan"], fixed["makespan"])

    def test_invalid_or_unsafe_inputs_rejected(self):
        for kwargs in [dict(budget=31, maximum=32), dict(concurrency=0),
                       dict(concurrency=17), dict(strategy="unknown"),
                       dict(strategy="paged", block_size=7)]:
            params = dict(strategy="fixed")
            params.update(kwargs)
            with self.assertRaises(ValueError):
                simulate([], **params)
        for r in [Request(-1, 1, 1), Request(0, 0, 1), Request(0, 32, 1),
                  Request(0, 1, -1), Request(0.5, 1, 1)]:
            with self.assertRaises(ValueError):
                simulate([r], "fixed", 32, 32)
        with self.assertRaises(ValueError):
            run(trials=0)

    def test_empty_prompt_only_and_custom_cap(self):
        self.assertEqual(simulate([], "fixed")["makespan"], 0)
        trace = []
        result = simulate([Request(3, 4, 0)] * 3, "paged", 32, 32, 8, trace=trace)
        self.assertEqual(result["makespan"], 3)
        self.assertEqual(result["completed_requests"], 3)
        self.assertEqual(result["allocated_slot_ticks"], 0)
        self.assertEqual(result["peak_allocated_slots"], 8)
        result = simulate([Request(0, 1, 1)] * 2, "fixed", concurrency=1)
        self.assertEqual(result["makespan"], 2)

    def test_identical_workloads_and_timing(self):
        rows = run(trials=2, requests=20)
        for trial in range(2):
            group = [r for r in rows if r["trial"] == trial]
            for metric in ("seed", "completed_requests", "makespan", "total_waiting_ticks",
                           "used_slot_ticks", "concurrency", "admission_stall_request_ticks"):
                self.assertEqual(len({r[metric] for r in group}), 1)

    def test_cli(self):
        script = Path(__file__).with_name("dynamic_experiment.py")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.csv"
            result = subprocess.run([sys.executable, "-B", str(script), "--output", str(output),
                                     "--trials", "1", "--seed", "7", "--requests", "3"],
                                    capture_output=True, text=True, check=True)
            self.assertIn("Wrote 4 rows", result.stdout)
            with output.open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(r["completed_requests"] == "3" for r in rows))
        result = subprocess.run([sys.executable, "-B", str(script), "--output",
                                 str(script.with_name("results.csv"))], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite", result.stderr)

    def test_integer_configuration_types(self):
        cases = [
            (rounded, dict(length=1, block=8), ("length", "block")),
            (safe_capacity, dict(budget=64, maximum=32), ("budget", "maximum")),
            (workload, dict(seed=1, requests=0, maximum=32), ("seed", "requests", "maximum")),
            (simulate, dict(requests=[], strategy="fixed", budget=64, maximum=32,
                            block_size=0, concurrency=1),
             ("budget", "maximum", "block_size", "concurrency")),
            (simulate, dict(requests=[], strategy="paged", budget=64, maximum=32,
                            block_size=16, concurrency=1),
             ("budget", "maximum", "block_size", "concurrency")),
            (run, dict(seed=1, trials=1, requests=0, budget=64, maximum=32, concurrency=1),
             ("seed", "trials", "requests", "budget", "maximum", "concurrency")),
        ]
        for function, defaults, names in cases:
            for name in names:
                for value in (1.5, 1.0, 16.0, True, False, "1", None, float("nan"), float("inf")):
                    if name == "concurrency" and value is None:
                        continue  # None explicitly selects the automatic cap.
                    with self.subTest(function=function.__name__, name=name, value=value):
                        params = dict(defaults, **{name: value})
                        with self.assertRaisesRegex(ValueError, name):
                            function(**params)

    def test_request_integer_types(self):
        for name in ("arrival", "prompt", "output"):
            for value in (1.5, 1.0, True, False, "1", None):
                with self.subTest(name=name, value=value):
                    fields = dict(arrival=0, prompt=1, output=1)
                    fields[name] = value
                    with self.assertRaisesRegex(ValueError, name):
                        simulate([Request(**fields)], "fixed")

    def test_integer_boundaries(self):
        self.assertEqual(rounded(0, 1), 0)
        self.assertEqual(safe_capacity(32, 1), 1)
        self.assertEqual(workload(-1, requests=0, maximum=2), [])
        self.assertEqual(len(run(seed=-1, trials=1, requests=0, budget=32, maximum=2)), 4)
        self.assertEqual(simulate([Request(0, 1, 0)], "fixed", budget=32, maximum=1,
                                  block_size=0)["completed_requests"], 1)
        cases = [(rounded, dict(length=-1, block=8)),
                 (rounded, dict(length=1, block=0)),
                 (safe_capacity, dict(budget=0, maximum=32)),
                 (safe_capacity, dict(budget=32, maximum=0)),
                 (workload, dict(seed=0, requests=-1)),
                 (workload, dict(seed=0, maximum=1)),
                 (run, dict(trials=0)), (run, dict(requests=-1)),
                 (run, dict(budget=0)), (run, dict(maximum=1)),
                 (run, dict(concurrency=0)),
                 (simulate, dict(requests=[], strategy="fixed", block_size=-1))]
        for function, params in cases:
            with self.subTest(function=function.__name__, params=params):
                with self.assertRaises(ValueError):
                    function(**params)

    def test_arrivals_at_simultaneous_completion_boundary(self):
        requests = [Request(0, 1, 2), Request(0, 1, 2), Request(1, 1, 1), Request(2, 1, 1)]
        for strategy, block in [("fixed", 0)] + [("paged", b) for b in BLOCKS]:
            with self.subTest(strategy=strategy, block=block):
                trace = []
                result = simulate(requests, strategy, 64, 32, block, trace=trace)
                admissions = [(e["request_id"], e["tick"]) for e in trace if e["event"] == "admit"]
                completions = [(e["request_id"], e["tick"]) for e in trace if e["event"] == "complete"]
                self.assertEqual(admissions, [(0, 0), (1, 0), (2, 2), (3, 2)])
                self.assertEqual(completions, [(0, 2), (1, 2), (2, 3), (3, 3)])
                self.assertEqual(result["total_waiting_ticks"], 1)
                self.assertEqual(result["admission_stall_request_ticks"], 1)
                self.assertEqual(result["makespan"], 3)
                self.assertEqual(result["completed_requests"], 4)

    def test_mixed_prompt_only_and_generating_requests(self):
        requests = [Request(0, 8, 2), Request(0, 8, 0), Request(1, 8, 1), Request(3, 8, 0)]
        for strategy, block in [("fixed", 0)] + [("paged", b) for b in BLOCKS]:
            with self.subTest(strategy=strategy, block=block):
                trace = []
                result = simulate(requests, strategy, 32, 32, block, trace=trace)
                admissions = [(e["request_id"], e["tick"]) for e in trace if e["event"] == "admit"]
                completions = [(e["request_id"], e["tick"]) for e in trace if e["event"] == "complete"]
                self.assertEqual(admissions, [(0, 0), (1, 2), (2, 2), (3, 3)])
                self.assertEqual(completions, [(0, 2), (1, 2), (2, 3), (3, 3)])
                self.assertEqual(result["completed_requests"], 4)
                self.assertEqual(result["makespan"], 3)
                self.assertEqual(result["total_waiting_ticks"], 3)
                self.assertEqual(result["used_slot_ticks"], 28)
                self.assertEqual(result["allocated_slot_ticks"], 96 if strategy == "fixed" or block == 32 else 48)
                self.assertEqual(result["final_allocated_slots"], 0)
                self.assertEqual(result["final_used_slots"], 0)

    def test_nonbinding_limits(self):
        sparse = [Request(0, 1, 2), Request(3, 1, 1), Request(5, 1, 2)]
        for strategy, block in [("fixed", 0)] + [("paged", b) for b in BLOCKS]:
            reference = None
            for cap in (1, 2, 4):
                trace = []
                result = simulate(sparse, strategy, 128, 32, block, cap, trace)
                schedule = [(e["event"], e["request_id"], e["tick"]) for e in trace
                            if e["event"] in ("admit", "complete")]
                if reference is None:
                    reference = schedule
                self.assertEqual(schedule, reference)
                self.assertEqual(result["makespan"], 7)
                self.assertEqual(result["total_waiting_ticks"], 0)
                self.assertEqual(result["completed_requests"], 3)
            # Additional memory cannot change scheduling under the same smaller cap.
            loaded = [Request(0, 1, 3)] * 6
            small = simulate(loaded, strategy, 256, 32, block, 4)
            large = simulate(loaded, strategy, 512, 32, block, 4)
            self.assertEqual(small["makespan"], 6)
            self.assertEqual(small["total_waiting_ticks"], 6)
            self.assertEqual(small["peak_occupancy"], large["peak_occupancy"] * 2)
            for key in small:
                if key != "peak_occupancy":
                    self.assertEqual(small[key], large[key], key)


if __name__ == "__main__":
    unittest.main()
