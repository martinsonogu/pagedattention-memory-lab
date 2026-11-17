"""Versioned deterministic workloads; no experiment runner or scheduling policy."""

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import random
import re

from phase3_simulator import Request


SCHEMA_VERSION = 1
GENERATOR_VERSION = "phase3-workloads-v1"
LENGTH_REGIMES = ("short", "medium", "long", "mixed")
SPLIT_REGIMES = ("generation-heavy", "prompt-heavy")
ARRIVAL_REGIMES = ("dense", "moderate", "bursty")
STREAMS = ("arrivals", "lengths", "splits")
LENGTH_BOUNDS = {"short": (32, 256), "medium": (257, 1024), "long": (1025, 2048)}


def _integer(name, value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, excluding bool")


def _keys(value, names, name):
    if type(value) is not dict or set(value) != set(names):
        raise ValueError(f"{name} must contain exactly {sorted(names)}")


def _choice(name, value, choices):
    if type(value) is not str or value not in choices:
        raise ValueError(f"unsupported {name}: {value!r}")


def _canonical(value):
    """UTF-8, sorted keys, compact separators, ASCII escaping, one final LF."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def distribution_definitions():
    """Fresh data each time so callers cannot mutate the frozen definitions."""
    return {
        "total_lengths": {
            "sampling": "uniform_integer_inclusive",
            "bounds": {name: list(bounds) for name, bounds in LENGTH_BOUNDS.items()},
            "mixed": {"choice": "uniform_integer_0_to_99",
                      "intervals": {"short": [0, 59], "medium": [60, 89], "long": [90, 99]},
                      "probabilities": {"short": [60, 100], "medium": [30, 100], "long": [10, 100]}},
        },
        "splits": {"sampling": "uniform_integer_inclusive",
                   "sampled_min": 1, "sampled_max": "min(128,total_length-1)",
                   "generation-heavy": "sample_prompt_output_is_remainder",
                   "prompt-heavy": "sample_output_prompt_is_remainder"},
        "arrivals": {"first_tick": 0, "gap_sampling": "uniform_integer_inclusive",
                     "dense_gap": [0, 8], "moderate_gap": [0, 64],
                     "bursty_group_size": 32, "bursty_period": 128},
    }


def rng_definition():
    return {"algorithm": "python.random.Random",
            "seed_derivation": "sha256(canonical_json([generator_version,seed,stream]))_big_endian",
            "streams": list(STREAMS)}


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 20261117
    length_regime: str = "mixed"
    split_regime: str = "generation-heavy"
    arrival_regime: str = "dense"
    request_count: int = 200
    maximum: int = 2048

    def __post_init__(self):
        _integer("seed", self.seed)
        _integer("request_count", self.request_count)
        _integer("maximum", self.maximum, 1)
        if self.maximum != 2048:
            raise ValueError("generator v1 freezes maximum at 2048")
        _choice("length_regime", self.length_regime, LENGTH_REGIMES)
        _choice("split_regime", self.split_regime, SPLIT_REGIMES)
        _choice("arrival_regime", self.arrival_regime, ARRIVAL_REGIMES)


@dataclass(frozen=True)
class WorkloadRequest:
    request_id: int
    arrival: int
    prompt: int
    output: int


@dataclass(frozen=True)
class Workload:
    config: GeneratorConfig
    requests: tuple[WorkloadRequest, ...]

    def __post_init__(self):
        if type(self.config) is not GeneratorConfig:
            raise ValueError("config must be GeneratorConfig")
        if type(self.requests) is not tuple or len(self.requests) != self.config.request_count:
            raise ValueError("requests must be a tuple matching request_count")
        previous_arrival = 0
        for index, request in enumerate(self.requests):
            if type(request) is not WorkloadRequest:
                raise ValueError("requests must contain WorkloadRequest instances")
            for name in ("request_id", "arrival", "prompt", "output"):
                _integer(name, getattr(request, name), 1 if name == "prompt" else 0)
            if request.request_id != index:
                raise ValueError("request IDs must be unique contiguous input positions starting at 0")
            if request.arrival < previous_arrival:
                raise ValueError("arrival order must be nondecreasing")
            if index == 0 and request.arrival != 0:
                raise ValueError("first arrival must be tick zero")
            if self.config.arrival_regime == "bursty":
                if request.arrival != (index // 32) * 128:
                    raise ValueError("arrival violates bursty group boundaries")
            elif index and request.arrival - previous_arrival > (
                    8 if self.config.arrival_regime == "dense" else 64):
                raise ValueError("arrival gap outside declared distribution")
            previous_arrival = request.arrival
            total = request.prompt + request.output
            if total > self.config.maximum:
                raise ValueError("request exceeds public maximum")
            low, high = LENGTH_BOUNDS.get(self.config.length_regime, (32, 2048))
            if not low <= total <= high:
                raise ValueError("total length outside declared regime")
            sampled = request.prompt if self.config.split_regime == "generation-heavy" else request.output
            if not 1 <= sampled <= min(128, total - 1):
                raise ValueError("request violates declared prompt/output split")

    def _payload(self):
        return {"schema_version": SCHEMA_VERSION,
                "manifest": {"generator_version": GENERATOR_VERSION,
                             "config": asdict(self.config),
                             "distribution_definitions": distribution_definitions(),
                             "rng": rng_definition()},
                "requests": [asdict(request) for request in self.requests]}

    @property
    def sha256(self):
        return hashlib.sha256(_canonical(self._payload())).hexdigest()

    def canonical_bytes(self):
        payload = self._payload()
        return _canonical(dict(payload, sha256=hashlib.sha256(_canonical(payload)).hexdigest()))

    def to_simulator_requests(self):
        """IDs remain input positions; output lengths enter only execution replay."""
        return tuple(Request(r.arrival, r.prompt, r.output) for r in self.requests)


def stream_seed(seed, stream):
    _integer("seed", seed)
    _choice("stream", stream, STREAMS)
    return int.from_bytes(hashlib.sha256(_canonical([GENERATOR_VERSION, seed, stream])).digest(), "big")


def _sample_total(rng, regime):
    if regime == "mixed":
        choice = rng.randrange(100)
        regime = "short" if choice < 60 else "medium" if choice < 90 else "long"
    return rng.randint(*LENGTH_BOUNDS[regime])


def generate(config=GeneratorConfig()):
    if type(config) is not GeneratorConfig:
        raise ValueError("config must be GeneratorConfig")
    arrivals_rng, lengths_rng, splits_rng = (
        random.Random(stream_seed(config.seed, stream)) for stream in STREAMS)
    arrival = 0
    requests = []
    for index in range(config.request_count):
        if config.arrival_regime == "bursty":
            arrival = (index // 32) * 128
        elif index:
            arrival += arrivals_rng.randint(0, 8 if config.arrival_regime == "dense" else 64)
        total = _sample_total(lengths_rng, config.length_regime)
        sampled = splits_rng.randint(1, min(128, total - 1))
        prompt, output = (sampled, total - sampled) if config.split_regime == "generation-heavy" else (total - sampled, sampled)
        requests.append(WorkloadRequest(index, arrival, prompt, output))
    return Workload(config, tuple(requests))


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _invalid_constant(value):
    raise ValueError(f"non-finite JSON number: {value}")


def loads(data):
    """Validate stored realizations and checksum; never call RNG or regenerate."""
    if type(data) is not bytes:
        raise ValueError("workload input must be UTF-8 bytes")
    try:
        document = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=_invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 JSON workload") from exc
    _keys(document, ("schema_version", "manifest", "requests", "sha256"), "workload")
    _integer("schema_version", document["schema_version"], 1)
    if document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported workload schema_version")
    manifest = document["manifest"]
    _keys(manifest, ("generator_version", "config", "distribution_definitions", "rng"), "manifest")
    if manifest["generator_version"] != GENERATOR_VERSION:
        raise ValueError("unsupported generator_version")
    _keys(manifest["config"], GeneratorConfig.__dataclass_fields__, "config")
    config = GeneratorConfig(**manifest["config"])
    # Byte comparison also rejects bool/int and float/int equivalence in Python.
    if _canonical(manifest["distribution_definitions"]) != _canonical(distribution_definitions()):
        raise ValueError("distribution definitions differ from generator v1")
    if _canonical(manifest["rng"]) != _canonical(rng_definition()):
        raise ValueError("RNG definition differs from generator v1")
    if type(document["requests"]) is not list:
        raise ValueError("requests must be an array")
    requests = []
    for record in document["requests"]:
        _keys(record, WorkloadRequest.__dataclass_fields__, "request")
        requests.append(WorkloadRequest(**record))
    workload = Workload(config, tuple(requests))
    checksum = document["sha256"]
    if type(checksum) is not str or re.fullmatch(r"[0-9a-f]{64}", checksum) is None:
        raise ValueError("sha256 must contain 64 lowercase hexadecimal characters")
    if checksum != workload.sha256:
        raise ValueError("workload SHA-256 mismatch")
    return workload


def load(path):
    return loads(Path(path).read_bytes())


def save(workload, path):
    """Create a new canonical file; refuse to overwrite any existing artifact."""
    if type(workload) is not Workload:
        raise ValueError("workload must be Workload")
    data = workload.canonical_bytes()
    with Path(path).open("xb") as output:
        output.write(data)


def primary_plan():
    """Declarative dimensions only: this function never generates or runs cases."""
    return {"schema_version": 1, "kind": "phase3-primary-plan",
            "generator_version": GENERATOR_VERSION, "maximum": 2048,
            "request_count": 200, "seeds": list(range(20261117, 20261137)),
            "length_regimes": list(LENGTH_REGIMES), "split_regimes": list(SPLIT_REGIMES),
            "arrival_regimes": list(ARRIVAL_REGIMES),
            "distribution_definitions": distribution_definitions(), "rng": rng_definition(),
            "budgets": [2048, 4096, 8192, 16384, 32768],
            "allocations": [{"strategy": "fixed", "block_size": 0}] +
                           [{"strategy": "paged", "block_size": b} for b in (8, 16, 32)],
            "compute_budgets": [None, 8], "concurrency_cap": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("generate", help="save one workload, without running a simulation")
    create.add_argument("--seed", type=int, default=20261117)
    create.add_argument("--length-regime", choices=LENGTH_REGIMES, default="mixed")
    create.add_argument("--split-regime", choices=SPLIT_REGIMES, default="generation-heavy")
    create.add_argument("--arrival-regime", choices=ARRIVAL_REGIMES, default="dense")
    create.add_argument("--request-count", type=int, default=200)
    create.add_argument("--output", required=True)
    verify = subparsers.add_parser("verify", help="validate a saved workload, without regeneration")
    verify.add_argument("path")
    args = parser.parse_args()
    try:
        if args.command == "generate":
            workload = generate(GeneratorConfig(args.seed, args.length_regime, args.split_regime,
                                                args.arrival_regime, args.request_count))
            save(workload, args.output)
        else:
            workload = load(args.path)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"requests={workload.config.request_count} sha256={workload.sha256}")


if __name__ == "__main__":
    main()
