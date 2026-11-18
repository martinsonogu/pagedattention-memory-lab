"""Single-workload deterministic experiment runner; no primary-matrix execution."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from phase3_simulator import rounded, simulate
from phase3_workloads import (GeneratorConfig, Workload, generate, load,
                              distribution_definitions, rng_definition, GENERATOR_VERSION)

ALLOCATORS = (("fixed", 0), ("paged", 8), ("paged", 16), ("paged", 32))
POLICY_VERSION = "phase3-fifo-oldest-protection-v1"
METRIC_SCHEMA_VERSION = 1
ROOT = Path(__file__).resolve().parent


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f"invalid JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=unique, parse_constant=invalid)


def from_manifest(path):
    """Explicit generation from the complete M2 manifest (not a matrix plan)."""
    manifest = read_json(path)
    if type(manifest) is not dict or set(manifest) != {
            "generator_version", "config", "distribution_definitions", "rng"}:
        raise ValueError("expected a complete single-workload manifest")
    if manifest["generator_version"] != GENERATOR_VERSION:
        raise ValueError("unsupported generator version")
    for key, expected in (("distribution_definitions", distribution_definitions()),
                          ("rng", rng_definition())):
        if canonical(manifest[key]) != canonical(expected):
            raise ValueError(f"invalid {key}")
    config = manifest["config"]
    if type(config) is not dict or set(config) != set(GeneratorConfig.__dataclass_fields__):
        raise ValueError("manifest must specify every generator configuration field")
    return generate(GeneratorConfig(**config))


def validate_conditions(maximum, budgets, compute_budgets):
    if type(maximum) is not int or maximum < 1:
        raise ValueError("maximum must be a positive integer")
    for name, values in (("budgets", budgets), ("compute_budgets", compute_budgets)):
        if not isinstance(values, (tuple, list)) or not values:
            raise ValueError(f"{name} must be a nonempty sequence")
        for value in values:
            if name == "compute_budgets" and value is None:
                continue
            if type(value) is not int or value < 1:
                raise ValueError(f"invalid {name} value")
        if len(set(values)) != len(values):
            raise ValueError(f"duplicate {name}")
    if any(budget < max(maximum, *(rounded(maximum, b) for b in (8, 16, 32)))
           for budget in budgets):
        raise ValueError("every budget must fit every allocator's maximum reservation")
    return sorted(budgets), sorted(compute_budgets, key=lambda x: -1 if x is None else x)


def code_metadata():
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT))
    # HEAD alone does not identify uncommitted runner code.
    sources = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
               for name in ("phase3_simulator.py", "phase3_workloads.py", "phase3_experiment.py")}
    return dict(code_revision=revision, working_tree_dirty=dirty, source_sha256=sources)


def replay(requests, maximum, budgets, compute_budgets, *, outcomes=False, trace=False):
    """Shared low-level replay used by the runner and separate hand-built fixtures."""
    budgets, compute_budgets = validate_conditions(maximum, budgets, compute_budgets)
    if type(outcomes) is not bool or type(trace) is not bool:
        raise ValueError("outcomes and trace must be booleans")
    requests = tuple(requests)
    # Validate all conditions before the first simulation; request validation is
    # also performed by the unchanged simulator before each replay.
    for budget in budgets:
        for compute in compute_budgets:
            for strategy, block in ALLOCATORS:
                result = simulate(requests, strategy, budget=budget, maximum=maximum,
                                  block_size=block, compute_budget=compute, trace=trace)
                row = {"config": result["config"], "metrics": result["metrics"]}
                if outcomes:
                    row["requests"] = result["requests"]
                if trace:
                    row["trace"] = result["trace"]
                yield row


def run(workload, budgets=(32768,), compute_budgets=(None, 8), *, outcomes=False, trace=False):
    if type(workload) is not Workload:
        raise ValueError("workload must be a validated Workload")
    budgets, compute_budgets = validate_conditions(workload.config.maximum, budgets, compute_budgets)
    metadata = dict(code_metadata(), policy_version=POLICY_VERSION,
                    metric_schema_version=METRIC_SCHEMA_VERSION,
                    workload_sha256=workload.sha256, workload_schema_version=1,
                    generator_version=GENERATOR_VERSION, seed=workload.config.seed,
                    workload_config=asdict(workload.config),
                    experiment_config=dict(budgets=budgets, compute_budgets=compute_budgets,
                                           allocators=[dict(strategy=s, block_size=b) for s, b in ALLOCATORS],
                                           outcomes=outcomes, trace=trace))
    requests = workload.to_simulator_requests()  # Exactly once; no per-strategy RNG.
    for result in replay(requests, workload.config.maximum, budgets, compute_budgets,
                         outcomes=outcomes, trace=trace):
        yield dict(metadata, **result)


def write_rows(rows, path):
    """Publish complete JSONL atomically, without overwriting an artifact."""
    target = Path(path).resolve()
    if target == ROOT or ROOT in target.parents:
        raise ValueError("scratch outputs must be outside the repository")
    if target.exists():
        raise FileExistsError(target)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent,
                                         prefix=f".{target.name}.", suffix=".partial",
                                         delete=False) as output:
            temporary = Path(output.name)
            for row in rows:
                output.write(canonical(row))
            output.flush()
            os.fsync(output.fileno())
        # A same-filesystem hard link publishes the closed file atomically and
        # fails if another writer created the destination in the meantime.
        os.link(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--workload")
    source.add_argument("--manifest")
    parser.add_argument("--budgets", nargs="+", type=int, default=[32768])
    parser.add_argument("--compute", nargs="+", default=["unlimited", "8"])
    parser.add_argument("--outcomes", action="store_true")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        computes = [None if value == "unlimited" else int(value) for value in args.compute]
        workload = load(args.workload) if args.workload else from_manifest(args.manifest)
        validate_conditions(workload.config.maximum, args.budgets, computes)
        write_rows(run(workload, args.budgets, computes, outcomes=args.outcomes, trace=args.trace), args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
