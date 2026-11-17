import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from phase3_simulator import Request, simulate
from phase3_workloads import (
    ARRIVAL_REGIMES, GENERATOR_VERSION, LENGTH_BOUNDS, LENGTH_REGIMES,
    SPLIT_REGIMES, STREAMS, GeneratorConfig, Workload, WorkloadRequest,
    _sample_total, distribution_definitions, generate, load, loads,
    primary_plan, save, stream_seed,
)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def signed(document):
    """Re-sign malformed test documents to exercise validation beyond the hash."""
    document = copy.deepcopy(document)
    document.pop("sha256", None)
    document["sha256"] = hashlib.sha256(canonical(document)).hexdigest()
    return canonical(document)


class EndpointRNG:
    def __init__(self, upper=False, choice=0):
        self.upper = upper
        self.choice = choice
        self.calls = []

    def randint(self, low, high):
        self.calls.append((low, high))
        return high if self.upper else low

    def randrange(self, stop):
        if stop != 100:
            raise AssertionError(stop)
        return self.choice


class WorkloadTests(unittest.TestCase):
    def setUp(self):
        self.config = GeneratorConfig(request_count=5)
        self.workload = generate(self.config)
        self.document = json.loads(self.workload.canonical_bytes())

    def test_reproducibility_and_immutability(self):
        self.assertEqual(self.workload, generate(self.config))
        self.assertEqual(self.workload.canonical_bytes(), generate(self.config).canonical_bytes())
        self.assertNotEqual(self.workload.requests, generate(replace(self.config, seed=1)).requests)
        with self.assertRaises(FrozenInstanceError):
            self.workload.requests[0].arrival = 2
        with self.assertRaises(FrozenInstanceError):
            self.workload.config.seed = 2
        before = distribution_definitions()
        changed = distribution_definitions()
        changed["total_lengths"]["bounds"]["short"][0] = 0
        self.assertEqual(distribution_definitions(), before)

    def test_seed_derivation_and_process_independence(self):
        derived = []
        for stream in STREAMS:
            expected = int.from_bytes(hashlib.sha256(canonical([GENERATOR_VERSION, 7, stream])).digest(), "big")
            self.assertEqual(stream_seed(7, stream), expected)
            derived.append(expected)
        self.assertEqual(len(set(derived)), 3)
        script = ("import sys; from phase3_workloads import generate, GeneratorConfig; "
                  "sys.stdout.buffer.write(generate(GeneratorConfig(request_count=5)).canonical_bytes())")
        for hash_seed in ("1", "999"):
            result = subprocess.run([sys.executable, "-B", "-c", script],
                                    cwd=Path(__file__).parent, env=dict(os.environ, PYTHONHASHSEED=hash_seed),
                                    capture_output=True, check=True)
            self.assertEqual(result.stdout, self.workload.canonical_bytes())

    def test_independent_streams(self):
        for length in LENGTH_REGIMES:
            for split in SPLIT_REGIMES:
                workloads = [generate(GeneratorConfig(length_regime=length, split_regime=split,
                                                     arrival_regime=arrival, request_count=35))
                             for arrival in ARRIVAL_REGIMES]
                shapes = [tuple((r.prompt, r.output) for r in w.requests) for w in workloads]
                self.assertTrue(all(shape == shapes[0] for shape in shapes))
        reference_arrivals = None
        for length in LENGTH_REGIMES:
            generation = generate(GeneratorConfig(length_regime=length, request_count=35))
            prompt = generate(replace(generation.config, split_regime="prompt-heavy"))
            self.assertEqual([(r.prompt, r.output) for r in generation.requests],
                             [(r.output, r.prompt) for r in prompt.requests])
            arrivals = [r.arrival for r in generation.requests]
            if reference_arrivals is None:
                reference_arrivals = arrivals
            self.assertEqual(arrivals, reference_arrivals)

    def test_exact_inclusive_length_boundaries(self):
        for name, (low, high) in LENGTH_BOUNDS.items():
            for upper, expected in ((False, low), (True, high)):
                rng = EndpointRNG(upper=upper)
                self.assertEqual(_sample_total(rng, name), expected)
                self.assertEqual(rng.calls, [(low, high)])

    def test_mixed_probability_definition_and_thresholds(self):
        mixed = distribution_definitions()["total_lengths"]["mixed"]
        self.assertEqual(mixed["probabilities"],
                         {"short": [60, 100], "medium": [30, 100], "long": [10, 100]})
        for choice, regime in ((0, "short"), (59, "short"), (60, "medium"),
                               (89, "medium"), (90, "long"), (99, "long")):
            rng = EndpointRNG(choice=choice)
            self.assertEqual(_sample_total(rng, "mixed"), LENGTH_BOUNDS[regime][0])
            self.assertEqual(rng.calls, [LENGTH_BOUNDS[regime]])

    def test_generation_endpoints_and_first_arrival_draw(self):
        for regime in LENGTH_BOUNDS:
            for split in SPLIT_REGIMES:
                for arrival, gap_max in (("dense", 8), ("moderate", 64)):
                    for upper in (False, True):
                        rngs = [EndpointRNG(upper) for _ in STREAMS]
                        config = GeneratorConfig(length_regime=regime, split_regime=split,
                                                 arrival_regime=arrival, request_count=2)
                        with patch("phase3_workloads.random.Random", side_effect=rngs):
                            workload = generate(config)
                        length = LENGTH_BOUNDS[regime][int(upper)]
                        small = min(128, length - 1) if upper else 1
                        self.assertEqual(rngs[0].calls, [(0, gap_max)])  # No first-arrival draw.
                        self.assertEqual([r.arrival for r in workload.requests], [0, gap_max if upper else 0])
                        for request in workload.requests:
                            self.assertEqual(request.prompt + request.output, length)
                            self.assertEqual(request.prompt if split == "generation-heavy" else request.output, small)

    def test_regime_membership_ids_and_splits(self):
        for length in LENGTH_REGIMES:
            for split in SPLIT_REGIMES:
                workload = generate(GeneratorConfig(length_regime=length, split_regime=split))
                low, high = LENGTH_BOUNDS.get(length, (32, 2048))
                self.assertEqual([r.request_id for r in workload.requests], list(range(200)))
                arrivals = [r.arrival for r in workload.requests]
                self.assertEqual(arrivals, sorted(arrivals))
                self.assertEqual(arrivals[0], 0)
                for request in workload.requests:
                    total = request.prompt + request.output
                    self.assertTrue(low <= total <= high <= 2048)
                    self.assertGreaterEqual(request.prompt, 1)
                    self.assertGreaterEqual(request.output, 1)
                    small = request.prompt if split == "generation-heavy" else request.output
                    self.assertTrue(1 <= small <= min(128, total - 1))

    def test_bursty_partial_final_group(self):
        workload = generate(GeneratorConfig(arrival_regime="bursty", request_count=65))
        self.assertEqual([r.arrival for r in workload.requests], [0] * 32 + [128] * 32 + [256])
        for count in (0, 1, 31, 32, 33, 64):
            workload = generate(GeneratorConfig(arrival_regime="bursty", request_count=count))
            self.assertEqual([r.arrival for r in workload.requests], [(i // 32) * 128 for i in range(count)])

    def test_round_trip_and_hash_boundary(self):
        payload = {key: value for key, value in self.document.items() if key != "sha256"}
        self.assertEqual(self.workload.sha256, hashlib.sha256(canonical(payload)).hexdigest())
        self.assertEqual(self.document["sha256"], self.workload.sha256)
        self.assertNotEqual(hashlib.sha256(self.workload.canonical_bytes()).hexdigest(), self.workload.sha256)
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "first.json", Path(directory) / "second.json"
            save(self.workload, first)
            restored = load(first)
            self.assertEqual(restored, self.workload)
            save(restored, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with self.assertRaises(FileExistsError):
                save(self.workload, first)
        pretty = json.dumps(self.document, indent=2).encode("utf-8")
        self.assertEqual(loads(pretty).canonical_bytes(), self.workload.canonical_bytes())

    def test_loading_never_regenerates(self):
        with patch("phase3_workloads.generate", side_effect=AssertionError("regeneration")), \
             patch("phase3_workloads.random.Random", side_effect=AssertionError("RNG on load")):
            self.assertEqual(loads(self.workload.canonical_bytes()), self.workload)
        # Valid saved realizations need not reproduce the seed: loading is not a provenance audit.
        changed = copy.deepcopy(self.document)
        changed["manifest"]["config"]["seed"] += 1
        restored = loads(signed(changed))
        self.assertEqual(restored.requests, self.workload.requests)

    def test_tampering_detected(self):
        workload = generate(GeneratorConfig(length_regime="short", request_count=2))
        original = json.loads(workload.canonical_bytes())
        modified = copy.deepcopy(original)
        modified["manifest"]["config"]["seed"] += 1
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            loads(canonical(modified))
        modified = copy.deepcopy(original)
        request = modified["requests"][0]
        total = request["prompt"] + request["output"]
        request["output"] += 1 if total < 256 else -1
        with self.assertRaises(ValueError):
            loads(canonical(modified))
        self.assertNotEqual(loads(signed(modified)).sha256, workload.sha256)
        for checksum in ("0" * 64, "X" * 64, "abc", 1, True, None):
            modified = copy.deepcopy(original)
            modified["sha256"] = checksum
            with self.assertRaises(ValueError):
                loads(canonical(modified))

    def test_config_type_and_range_rejections(self):
        for field in ("seed", "maximum", "request_count"):
            for value in (True, False, 1.0, 1.5, -1, None, "1"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        GeneratorConfig(**{field: value})
        for field in ("length_regime", "split_regime", "arrival_regime"):
            for value in (None, True, 1, [], "unknown"):
                with self.assertRaises(ValueError):
                    GeneratorConfig(**{field: value})
        for value in (0, 1, 2047, 2049):
            with self.assertRaises(ValueError):
                GeneratorConfig(maximum=value)
        self.assertEqual(generate(GeneratorConfig(seed=0, request_count=0)).requests, ())

    def test_loading_rejects_bad_request_types(self):
        for field in ("request_id", "arrival", "prompt", "output"):
            for value in (True, False, 1.0, 1.5, -1, None, "1"):
                with self.subTest(field=field, value=value):
                    modified = copy.deepcopy(self.document)
                    modified["requests"][0][field] = value
                    with self.assertRaises(ValueError):
                        loads(signed(modified))
        for field in ("seed", "maximum", "request_count"):
            for value in (True, 200.0, -1):
                modified = copy.deepcopy(self.document)
                modified["manifest"]["config"][field] = value
                with self.assertRaises(ValueError):
                    loads(signed(modified))

    def test_loading_rejects_bad_ids_order_and_lengths(self):
        mutations = [
            lambda d: d["requests"][1].update(request_id=0),
            lambda d: d["requests"][0].update(request_id=99),
            lambda d: d["requests"].reverse(),
            lambda d: d["requests"][0].update(arrival=1),
            lambda d: d["requests"][1].update(arrival=100),
            lambda d: d["requests"][0].update(prompt=0),
            lambda d: d["requests"][0].update(prompt=1, output=2048),
            lambda d: d["requests"][0].update(prompt=1, output=0),
            lambda d: d["requests"][0].update(prompt=129, output=200),
            lambda d: d["requests"].pop(),
        ]
        for mutate in mutations:
            modified = copy.deepcopy(self.document)
            mutate(modified)
            with self.assertRaises(ValueError):
                loads(signed(modified))
        bursty = json.loads(generate(GeneratorConfig(arrival_regime="bursty", request_count=33)).canonical_bytes())
        bursty["requests"][32]["arrival"] = 127
        with self.assertRaises(ValueError):
            loads(signed(bursty))
        short = json.loads(generate(GeneratorConfig(length_regime="short", request_count=1)).canonical_bytes())
        short["requests"][0].update(prompt=1, output=256)
        with self.assertRaises(ValueError):
            loads(signed(short))

    def test_loading_rejects_malformed_manifests_and_versions(self):
        for value in (True, 1.0, 0, -1, 2, "1", None):
            modified = copy.deepcopy(self.document)
            modified["schema_version"] = value
            with self.assertRaises(ValueError):
                loads(signed(modified))
        mutations = [
            lambda d: d.update(extra=1),
            lambda d: d.pop("manifest"),
            lambda d: d.update(manifest=[]),
            lambda d: d["manifest"].update(generator_version="unknown"),
            lambda d: d["manifest"].update(extra=1),
            lambda d: d["manifest"]["config"].pop("seed"),
            lambda d: d["manifest"]["config"].update(extra=1),
            lambda d: d["manifest"]["config"].update(arrival_regime="unknown"),
            lambda d: d["manifest"]["distribution_definitions"]["arrivals"].update(first_tick=False),
            lambda d: d["manifest"]["distribution_definitions"]["total_lengths"]["bounds"].update(short=[32.0, 256]),
            lambda d: d["manifest"].update(rng={}),
            lambda d: d.update(requests={}),
            lambda d: d["requests"][0].update(extra=1),
        ]
        for mutate in mutations:
            modified = copy.deepcopy(self.document)
            mutate(modified)
            with self.assertRaises(ValueError):
                loads(signed(modified))

    def test_rejects_ambiguous_or_invalid_json(self):
        for data in (b"", b"{", b"[]", b"null", b"\xff", b'{"x":1,"x":2}',
                     b'{"nested":{"x":1,"x":2}}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.assertRaises(ValueError):
                loads(data)
        with self.assertRaises(ValueError):
            loads(self.workload.canonical_bytes().decode("utf-8"))

    def test_adapter_matches_simulator_ids_and_round_trip_replay(self):
        workload = generate(GeneratorConfig(length_regime="short", request_count=3))
        restored = loads(workload.canonical_bytes())
        adapted = restored.to_simulator_requests()
        self.assertIsInstance(adapted, tuple)
        self.assertTrue(all(type(r) is Request for r in adapted))
        self.assertEqual([(r.arrival, r.prompt, r.output) for r in adapted],
                         [(r.arrival, r.prompt, r.output) for r in workload.requests])
        before = workload.canonical_bytes()
        # Tiny API compatibility checks only; no comparative metrics are reported.
        for strategy, block, budget, compute in (("fixed", 0, 4096, None), ("paged", 8, 2048, 1)):
            kwargs = dict(strategy=strategy, block_size=block, budget=budget,
                          maximum=workload.config.maximum, compute_budget=compute)
            first = simulate(workload.to_simulator_requests(), **kwargs)
            second = simulate(adapted, **kwargs)
            self.assertEqual(canonical(first), canonical(second))
            self.assertEqual([r["request_id"] for r in second["requests"]], [0, 1, 2])
        self.assertEqual(before, workload.canonical_bytes())

    def test_empty_round_trip_and_replay(self):
        workload = generate(GeneratorConfig(request_count=0))
        restored = loads(workload.canonical_bytes())
        self.assertEqual(restored, workload)
        self.assertEqual(restored.to_simulator_requests(), ())
        result = simulate(restored.to_simulator_requests(), "fixed", maximum=2048)
        self.assertEqual(result["metrics"]["completed_requests"], 0)

    def test_primary_plan_matches_frozen_dimensions(self):
        path = Path(__file__).parent / "phase3" / "configs" / "primary.json"
        plan = json.loads(path.read_bytes())
        self.assertEqual(canonical(plan), canonical(primary_plan()))
        self.assertEqual(plan["seeds"], list(range(20261117, 20261137)))
        self.assertEqual(plan["maximum"], 2048)
        self.assertEqual(plan["request_count"], 200)
        workloads = len(plan["seeds"]) * len(plan["length_regimes"]) * len(plan["split_regimes"]) * len(plan["arrival_regimes"])
        self.assertEqual(workloads, 480)
        self.assertEqual(workloads * len(plan["budgets"]) * len(plan["allocations"]) * len(plan["compute_budgets"]), 19200)

    def test_cli_generate_verify_and_no_overwrite(self):
        script = Path(__file__).with_name("phase3_workloads.py")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "example.json"
            command = [sys.executable, "-B", str(script), "generate", "--request-count", "3", "--output", str(output)]
            created = subprocess.run(command, capture_output=True, text=True, check=True)
            verified = subprocess.run([sys.executable, "-B", str(script), "verify", str(output)],
                                      capture_output=True, text=True, check=True)
            self.assertEqual(created.stdout, verified.stdout)
            self.assertIn("requests=3 sha256=", created.stdout)
            original = output.read_bytes()
            refused = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            invalid = subprocess.run([sys.executable, "-B", str(script), "generate", "--seed", "-1",
                                      "--output", str(Path(directory) / "invalid.json")], capture_output=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertFalse((Path(directory) / "invalid.json").exists())


if __name__ == "__main__":
    unittest.main()
