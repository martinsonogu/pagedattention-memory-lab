"""Sequential, resumable research batches with a Phase 3E-1-only CLI."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import tempfile
import time
import uuid

import phase3_batch as batch
import phase3_experiment as runner
from phase3_workloads import generate

PROTOCOL = runner.ROOT / 'PHASE3_RESEARCH_BATCH_PROTOCOL.md'
OUTPUT = runner.ROOT / 'phase3/research_batch/3e1'
SMOKE = (('short', 'fixed', 0), ('short', 'paged', 16),
         ('long', 'fixed', 0), ('long', 'paged', 16))
VERSION = 'phase3-research-batch-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_plan(mode):
    pilot = runner.read_json(batch.PILOT_PATH)
    configs = batch.configs(pilot, 'pilot')
    if mode == 'pilot':
        return pilot, configs
    batch.require(mode == 'primary', 'unknown frozen inventory')
    seeds = list(range(20261117, 20261137))
    plan = dict(pilot, kind='phase3-primary-v1', seeds=seeds,
                budgets=[2048, 4096, 8192, 16384, 32768],
                expected_workloads=480, expected_runs=19200)
    for key in ('preflight', 'pilot_timeout_seconds', 'feasibility_rule'):
        del plan[key]
    return plan, [replace(config, seed=seed) for config in configs for seed in seeds]


def inventory(workloads, plan):
    return batch.conditions(workloads, plan)


def smoke_inventory(scope):
    batch.require(scope in ('smoke', 'verification'), 'unknown 3E-1 scope')
    plan, configs = inventory_plan('pilot')
    selection = SMOKE if scope == 'smoke' else SMOKE[:1]
    lengths = {length for length, _, _ in selection}
    workloads = {c.length_regime: generate(c) for c in configs
                 if c.length_regime in lengths and c.split_regime == 'generation-heavy'
                 and c.arrival_regime == 'dense'}
    expected = inventory(workloads.values(), plan)
    items = []
    for length, strategy, block in selection:
        workload = workloads[length]
        config = dict(strategy=strategy, block_size=block, budget=8192,
                      compute_budget=None, maximum=2048)
        matches = [e for e in expected if e['workload_sha256'] == workload.sha256
                   and e['config'] == config]
        batch.require(len(matches) == 1 and workload.config.seed == 20261117
                      and len(workload.requests) == 200, 'frozen smoke condition mismatch')
        items.append((workload, matches[0]))
    return plan, items


def scientific_row(workload, expected, identity):
    """Use the existing runner's row format and the unchanged simulator once."""
    plan = identity['plan']
    config = expected['config']
    result = runner.simulate(workload.to_simulator_requests(), **config, trace=False)
    row = dict(identity['metadata'], policy_version=runner.POLICY_VERSION,
               metric_schema_version=runner.METRIC_SCHEMA_VERSION,
               workload_sha256=workload.sha256, workload_schema_version=1,
               generator_version=runner.GENERATOR_VERSION, seed=workload.config.seed,
               workload_config=asdict(workload.config),
               experiment_config=dict(budgets=plan['budgets'], compute_budgets=plan['compute_budgets'],
                                      allocators=plan['allocators'], outcomes=True, trace=False),
               **{key: result[key] for key in ('config', 'metrics', 'requests')})
    return dict(kind='result', run_id=expected['run_id'], result=row)


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def ensure_directory(path):
    if not path.parent.is_dir():
        ensure_directory(path.parent)
    path.mkdir(exist_ok=True)
    batch.require(path.is_dir() and not path.is_symlink(), 'invalid run directory')
    sync_directory(path.parent)


def publish(path, payload):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.partial-', delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(runner.canonical(payload))
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink()
    sync_directory(path.parent)


def read(path):
    batch.require(path.is_file() and not path.is_symlink(), f'invalid record path: {path}')
    return batch.parse_line(path.read_bytes())


def now():
    return datetime.now(timezone.utc).isoformat()


def run_identity(plan, items, scope):
    files = [Path(__file__), Path(batch.__file__), batch.PILOT_PATH, PROTOCOL]
    return dict(kind=VERSION, scope=scope, plan=plan, metadata=runner.code_metadata(),
                sha256={str(p.relative_to(runner.ROOT)): sha(p) for p in files},
                environment=dict(platform=platform.platform(), python=platform.python_version(),
                                 implementation=platform.python_implementation()),
                workloads={w.sha256: json.loads(w.canonical_bytes()) for w, _ in items},
                expected=[e for _, e in items])


def validate_record(record, run_id, workload, expected, identity):
    fields = {'manifest_sha256', 'row', 'row_sha256', 'elapsed_seconds', 'completed_utc', 'checksum'}
    batch.require(set(record) == fields and record['manifest_sha256'] == run_id,
                  'completed-record identity mismatch')
    batch.require(record['checksum'] == batch.digest({k: v for k, v in record.items() if k != 'checksum'})
                  and record['row_sha256'] == batch.digest(record['row']), 'completed-record checksum mismatch')
    seconds = record['elapsed_seconds']
    batch.require(type(seconds) in (float, int) and math.isfinite(seconds) and seconds >= 0,
                  'invalid elapsed time')
    batch.require(datetime.fromisoformat(record['completed_utc']).utcoffset() is not None,
                  'invalid completion timestamp')
    batch.validate_result(record['row'], expected, workload, identity)


def run_batch(root, plan, items, scope):
    started = time.perf_counter()
    root = Path(root)
    ensure_directory(root)
    with (root / '.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        identity = run_identity(plan, items, scope)
        manifest_path = root / 'manifest.json'
        if manifest_path.exists():
            manifest = read(manifest_path)
            batch.require(set(manifest) == {'identity', 'created_utc', 'manifest_sha256'}
                          and runner.canonical(manifest['identity']) == runner.canonical(identity),
                          'incompatible code/config or run identity')
            batch.require(manifest['manifest_sha256'] == batch.digest({
                k: v for k, v in manifest.items() if k != 'manifest_sha256'}), 'manifest checksum mismatch')
        else:
            batch.require(not list(root.glob('condition-*.json')), 'completed records without manifest')
            manifest = dict(identity=identity, created_utc=now())
            manifest['manifest_sha256'] = batch.digest(manifest)
            publish(manifest_path, manifest)
        sync_directory(root)
        run_id = manifest['manifest_sha256']
        allowed = {f'condition-{e["run_id"]}.json' for _, e in items}
        batch.require(len(allowed) == len(items), 'duplicate condition identity')
        batch.require({p.name for p in root.glob('condition-*.json')} <= allowed, 'unexpected condition record')
        pending = []
        for workload, expected in items:
            key = expected['run_id']
            path = root / f'condition-{key}.json'
            if path.exists() or path.is_symlink():
                record = read(path)
                validate_record(record, run_id, workload, expected, identity)
                with path.open('rb') as file:
                    os.fsync(file.fileno())
                sync_directory(root)
                print(f'skipped {key} (validated)', flush=True)
            else:
                pending.append((workload, expected, path))
        for workload, expected, path in pending:
            key = expected['run_id']
            attempt = time.perf_counter()
            print(f'dispatched {key}', flush=True)
            try:
                row = scientific_row(workload, expected, identity)
                elapsed = time.perf_counter() - attempt
                record = dict(manifest_sha256=run_id, row=row, row_sha256=batch.digest(row),
                              elapsed_seconds=elapsed, completed_utc=now())
                record['checksum'] = batch.digest(record)
                validate_record(record, run_id, workload, expected, identity)
                publish(path, record)
                batch.require(path.read_bytes() == runner.canonical(record),
                              'completed-record readback mismatch')
                print(f'completed {key} {elapsed:.6f}s', flush=True)
            except BaseException as error:
                try:
                    publish(root / f'failure-{uuid.uuid4().hex}.json',
                            dict(run_id=key, manifest_sha256=run_id, utc=now(),
                                 elapsed_seconds=time.perf_counter() - attempt,
                                 error_type=type(error).__name__, error=str(error)))
                except OSError as save_error:
                    print(f'Unable to persist failure: {save_error}', flush=True)
                raise
        print(f'{scope}: dispatched={len(pending)} skipped={len(items)-len(pending)} '
              f'wall={time.perf_counter()-started:.6f}s', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scope', choices=['smoke', 'verification'])
    parser.add_argument('--list', action='store_true', help='resolve identities without simulating')
    args = parser.parse_args()
    plan, items = smoke_inventory(args.scope)
    if args.list:
        for workload, expected in items:
            print(runner.canonical(dict(workload=asdict(workload.config), **expected)).decode(), end='')
        return
    run_batch(OUTPUT / args.scope, plan, items, args.scope)


if __name__ == '__main__':
    main()
