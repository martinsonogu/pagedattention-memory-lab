"""Deterministic, read-only analysis of the frozen Phase 3 experiment."""

import argparse
from collections import defaultdict
import csv
from fractions import Fraction
from html import escape
import itertools
import json
import math
from pathlib import Path
import random
import statistics
import sys

import numpy as np

import phase3_batch as batch
import phase3_research_batch as research
from phase3_workloads import loads

ROOT = Path(__file__).resolve().parent
PRIMARY = ROOT / 'phase3/research_batch/3e3/primary'
CONTROL = ROOT / 'phase3/research_batch/3e4b/ample_memory_control'
OUTPUT = ROOT / 'phase3/analysis/3e5'
ALLOCATORS = ('fixed', 'paged8', 'paged16', 'paged32')
OUTCOMES = ('mean_latency_ticks', 'p95_latency_ticks', 'makespan')
TITLES = ('Mean latency', 'P95 latency', 'Makespan')
SEEDS = tuple(range(20261117, 20261137))
DRAW_COUNT = 10000
DRAW_SEED = 20261118
HASHES = {
    PRIMARY: '17983e334c0980cbaabafa9da4fe2e9935977848475043de92db4906105a8b48',
    CONTROL: '6ca36528c01b1af6c6d95814d850ce68a2b034e5d4de3976b97c9e5049ee99fe',
}
PLAN_SHA = 'eff60269f9fa72efa552be796f432cce46ee231def9b3676999d2d565f860c93'
CONFIG_SHA = '3753af5cb496b4ba395a8f846b4871c0060407de75828e00d445206bad46d8fa'
FIELDS = ['length', 'split', 'arrival', 'budget', 'compute', 'allocator']
DIAGNOSTICS = (
    'mean_waiting_ticks', 'p95_waiting_ticks', 'peak_active_requests',
    'mean_progressing_requests', 'admission_blocked_physical_ticks',
    'admission_blocked_protection_ticks', 'physical_capacity_stalls',
    'protected_headroom_stalls', 'growth_stall_request_ticks', 'compute_deferrals', 'peak_occupancy',
    'peak_live_occupancy', 'allocated_slot_ticks', 'used_slot_ticks',
    'unused_allocated_slot_ticks', 'protected_headroom_slot_ticks',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nearest_p95(values):
    ordered = sorted(values)
    require(bool(ordered), 'empty p95 population')
    return ordered[(95 * len(ordered) + 99) // 100 - 1]


def outcomes(result):
    latencies = [q['latency_ticks'] for q in result['requests']]
    return (Fraction(sum(latencies), len(latencies)), Fraction(nearest_p95(latencies)),
            Fraction(result['metrics']['makespan']))


def paired(fixed, paged):
    require(fixed[0] == paged[0], 'paired workload hashes differ')
    delta = tuple(p - f for f, p in zip(fixed[1], paged[1], strict=True))
    relative = tuple(d / f if f else None for d, f in zip(delta, fixed[1], strict=True))
    return delta, relative


def draw_indices(n, count=DRAW_COUNT, seed=DRAW_SEED):
    rng = random.Random(seed)
    return [[rng.randrange(n) for _ in range(n)] for _ in range(count)]


def weight_matrix(indices, n):
    return np.array([np.bincount(row, minlength=n) for row in indices], dtype=float)


def linear_quantile(values, p):
    ordered = sorted(values)
    require(bool(ordered) and 0 <= p <= 1, 'invalid quantile')
    index = (len(ordered) - 1) * p
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def intervals(vectors, weights):
    """All vectors have the same ordered seed columns."""
    result = []
    for offset in range(0, len(vectors), 96):
        block = vectors[offset:offset + 96]
        values = np.array([[float(v) if v is not None else 0.0 for v in vec] for vec in block])
        valid = np.array([[v is not None for v in vec] for vec in block], dtype=float)
        count = weights @ valid.T
        sums = weights @ values.T
        for i in range(len(block)):
            present = count[:, i] > 0
            sample = sums[present, i] / count[present, i]
            endpoints = np.percentile(sample, [2.5, 97.5], method='linear') if len(sample) else (None, None)
            result.append((*endpoints, len(weights) - len(sample)))
    return result


def fixture_axes(frozen):
    return list(itertools.product(frozen['length_regimes'], frozen['split_regimes'],
                                  frozen['arrival_regimes']))


def validate_inventory(declared, expected, filenames):
    ids = {condition['run_id'] for condition in expected}
    require(declared == expected and len(expected) == len(ids),
            'incomplete, duplicate or noncanonical condition inventory')
    require(filenames == {f'condition-{run_id}.json' for run_id in ids},
            'missing or unexpected artifact')


def load_records(root, frozen, control=False):
    path = root / 'manifest.json'
    require(research.sha(path) == HASHES[root], f'{root}: manifest identity changed')
    manifest = research.read(path)
    identity = manifest['identity']
    plan = identity['plan']
    run_id = manifest['manifest_sha256']
    require(batch.digest({k:v for k,v in manifest.items() if k!='manifest_sha256'}) == run_id,
            'manifest checksum')
    for source, digest in {**identity['metadata']['source_sha256'], **identity['sha256']}.items():
        require(research.sha(ROOT / source) == digest, f'pinned scientific source changed: {source}')
    regimes = fixture_axes(frozen)[:1] if control else fixture_axes(frozen)
    budgets = [409600] if control else frozen['budgets']
    computes = [None] if control else frozen['compute_budgets']
    require(identity['scope'] == ('ample_memory_control' if control else 'primary')
            and plan['budgets'] == budgets and plan['compute_budgets'] == computes
            and plan['allocators'] == frozen['allocations'] and plan['seeds'] == list(SEEDS),
            'condition dimensions differ')
    if control:
        spec = root / 'specification.json'
        require(research.sha(spec) == plan['control_specification_sha256'], 'control specification hash')
        require(research.read(spec)['inventory_sha256'] == batch.digest(identity['expected']),
                'control specification inventory')
    work = {}
    for key, doc in identity['workloads'].items():
        workload = loads(research.runner.canonical(doc))
        cfg = workload.config
        cell = (cfg.length_regime,cfg.split_regime,cfg.arrival_regime,cfg.seed)
        require(key == workload.sha256 and cell not in work and cfg.maximum == 2048
                and cfg.request_count == 200, 'invalid or duplicate workload')
        for field in ('generator_version','distribution_definitions','rng'):
            require(doc['manifest'][field] == frozen[field], 'workload generator identity')
        work[cell] = (key, workload)
    dimensions = [(*axis,s) for axis in regimes for s in SEEDS]
    require(set(work) == set(dimensions), 'incomplete workload grid')
    expected = batch.conditions([work[k][1] for k in dimensions],plan)
    extras = {'.lock', 'manifest.json'} | ({'specification.json'} if control else set())
    validate_inventory(identity['expected'], expected, {p.name for p in root.iterdir()} - extras)
    by_hash = {h:(k,w) for k,(h,w) in work.items()}
    rows = {}
    for c in expected:
        h=c['workload_sha256']
        key,w=by_hash[h]
        cfg=c['config']
        allocator='fixed' if cfg['strategy']=='fixed' else f'paged{cfg["block_size"]}'
        record=research.read(root/f'condition-{c["run_id"]}.json')
        research.validate_record(record,run_id,w,c,identity)
        r=record['row']['result']
        row_key=(*key,cfg['budget'],cfg['compute_budget'],allocator)
        require(row_key not in rows, 'duplicate row key')
        rows[row_key]=(h,outcomes(r),r['metrics'],c['run_id'],r['requests'] if control else None)
    return rows, run_id


def contrast_vectors(primary, regimes, budgets, computes):
    labels=[]; absolute=[]; relative=[]; pairs=[]
    for cell in itertools.product(regimes,budgets,computes,ALLOCATORS[1:]):
        axis,budget,compute,allocator=cell
        deltas=[]; relatives=[]
        for seed in SEEDS:
            key=(*axis,seed,budget,compute)
            require((*key,'fixed') in primary and (*key,allocator) in primary, f'missing paired condition: {key}, {allocator}')
            fixed=primary[(*key,'fixed')]
            paged=primary[(*key,allocator)]
            delta,ratio=paired(fixed,paged)
            deltas.append(delta)
            relatives.append(ratio)
            pairs.append(((*axis,budget,compute,allocator),seed,fixed,paged,delta,ratio))
        for i,name in enumerate(OUTCOMES):
            labels.append((*axis,budget,compute,allocator,name))
            absolute.append([d[i] for d in deltas])
            relative.append([r[i] for r in relatives])
    return labels,absolute,relative,pairs


def tally(vector):
    return sum(v<0 for v in vector),sum(v==0 for v in vector),sum(v>0 for v in vector)


def describe(vector):
    present=[v for v in vector if v is not None]
    if not present:
        return [None]*6
    return [statistics.mean(present), min(present), linear_quantile(present,Fraction(1,4)),
            linear_quantile(present,Fraction(1,2)),linear_quantile(present,Fraction(3,4)),max(present)]


def decimal(value, factor=1):
    return '' if value is None else format(float(value)*factor,'.12g')


def csv_file(path, header, rows):
    with path.open('w',newline='') as output:
        writer=csv.writer(output,lineterminator='\n')
        writer.writerow(header)
        writer.writerows(rows)


def display_labels(label):
    length,split,arrival,budget,compute,allocator,*rest=label
    return [length,split,arrival,budget,'unlimited' if compute is None else 'G8',allocator,*rest]


def interval_values(endpoints, factor=1):
    low,high,missing=endpoints
    return [decimal(low,factor),decimal(high,factor),missing]


def primary_tables(output, primary, regimes, budgets, computes, weights):
    labels,absolute,relative,pairs=contrast_vectors(primary,regimes,budgets,computes)
    require(len(labels)==len(set(labels))==2160, 'primary comparison inventory')
    aci=intervals(absolute,weights)
    rci=intervals(relative,weights)
    distributions=('mean','min','q1','median','q3','max')
    csv_file(output/'primary_contrasts.csv',
             FIELDS+['outcome','paired_seeds','relative_defined','relative_undefined','wins','ties','losses']
             +[f'absolute_ticks_{x}' for x in distributions]+['absolute_ci_low_ticks','absolute_ci_high_ticks']
             +[f'relative_pct_{x}' for x in distributions]+['relative_ci_low_pct','relative_ci_high_pct','relative_undefined_draws'],
             [display_labels(label)+[20,sum(v is not None for v in rel),sum(v is None for v in rel),*tally(ab)]
              +[decimal(v) for v in describe(ab)]+interval_values(ai)[:2]
              +[decimal(v,100) for v in describe(rel)]+interval_values(ri,100)
              for label,ab,rel,ai,ri in zip(labels,absolute,relative,aci,rci,strict=True)])
    csv_file(output/'seed_pairs.csv',
             FIELDS+['seed','workload_sha256','fixed_run_id','paged_run_id','outcome',
                     'fixed_ticks_exact','paged_ticks_exact','delta_ticks_exact','relative_fraction_exact'],
             [display_labels(label)+[seed,fixed[0],fixed[3],paged[3],outcome,str(fixed[1][i]),
                                   str(paged[1][i]),str(diff[i]),'' if rel[i] is None else str(rel[i])]
              for label,seed,fixed,paged,diff,rel in pairs for i,outcome in enumerate(OUTCOMES)])
    overall=[]
    for allocator,outcome in itertools.product(ALLOCATORS[1:],OUTCOMES):
        indices=[i for i,key in enumerate(labels) if key[-2:]==(allocator,outcome)]
        ab=[statistics.mean(absolute[i][k] for i in indices) for k in range(20)]
        rel=[statistics.mean(relative[i][k] for i in indices) for k in range(20)] if all(
            value is not None for i in indices for value in relative[i]) else [None]*20
        ai,ri=intervals([ab,rel],weights)
        overall.append([allocator,outcome,len(indices),*tally([v for i in indices for v in absolute[i]]),
                       decimal(statistics.mean(ab)),*interval_values(ai)[:2],decimal(describe(rel)[0],100),
                       *interval_values(ri,100)[:2]])
    csv_file(output/'designed_grid_summary.csv',
             ['allocator','outcome','cells','wins','ties','losses','mean_delta_ticks','ci_low_ticks','ci_high_ticks',
              'mean_relative_pct','ci_low_pct','ci_high_pct'],overall)
    values={label: describe(vector)[0] for label,vector in zip(labels,relative,strict=True)}
    return values,overall,pairs


def diagnostics(output, primary, regimes, budgets, computes, pairs):
    rows=[]
    for axis,budget,compute,a in itertools.product(regimes,budgets,computes,ALLOCATORS):
        group=[primary[(*axis,s,budget,compute,a)][2] for s in SEEDS]
        allocated=sum(m['allocated_slot_ticks'] for m in group)
        unused=sum(m['unused_allocated_slot_ticks'] for m in group)
        rows.append(display_labels((*axis,budget,compute,a))+[20]+[
            decimal(statistics.mean(m[field] for m in group)) for field in DIAGNOSTICS]
            +[allocated, unused, decimal(Fraction(unused,allocated),100)])
    csv_file(output/'diagnostics.csv',FIELDS+['seeds']+[f'mean_{k}' for k in DIAGNOSTICS]
             +['allocated_slot_ticks_total', 'unused_slot_ticks_total', 'pooled_unused_pct'],rows)
    grouped=defaultdict(list)
    for label,seed,fixed,paged,_,_ in pairs:
        f=Fraction(fixed[2]['generated_tokens'],fixed[2]['makespan'])
        p=Fraction(paged[2]['generated_tokens'],paged[2]['makespan'])
        grouped[label].append((p-f,(p-f)/f if f else None))
    csv_file(output/'secondary_progressing.csv',FIELDS+['seeds','relative_undefined','higher','equal','lower',
             'mean_delta_requests','mean_relative_pct'],
             [display_labels(k)+[len(v),sum(r is None for _,r in v),
               sum(d>0 for d,_ in v),sum(d==0 for d,_ in v),sum(d<0 for d,_ in v),
               decimal(statistics.mean(d for d,_ in v)),decimal(describe([r for _,r in v])[0],100)]
              for k,v in grouped.items()])


def control_summary(output, rows, primary, regimes):
    blocking=('admission_blocked_physical_ticks','admission_blocked_protection_ticks',
              'physical_capacity_stalls','protected_headroom_stalls','growth_stall_request_ticks')
    timefields=('admission','first_token','completion','waiting_ticks','latency_ticks')
    comparisons=[]
    for s,a in itertools.product(SEEDS,ALLOCATORS):
        k=(*regimes[0],s)
        fixed=rows[(*k,409600,None,'fixed')]
        row=rows[(*k,409600,None,a)]
        require(row[0]==primary[(*k,2048,None,a)][0], 'control workload differs from primary reference')
        first=sorted(fixed[4],key=lambda q:q['request_id'])
        other=sorted(row[4],key=lambda q:q['request_id'])
        require([q['request_id'] for q in first] == [q['request_id'] for q in other], 'control request IDs differ')
        mismatch=sum(q[field]!=p[field] for q,p in zip(first,other,strict=True) for field in timefields)
        nonzero=sum(row[2][field]!=0 for field in blocking)
        aggregate=sum(row[2][field]!=fixed[2][field] for field in
                      ('makespan','mean_waiting_ticks','p95_waiting_ticks','mean_latency_ticks','p95_latency_ticks'))
        comparisons.append([s,a,row[3],nonzero,mismatch,aggregate])
    csv_file(output/'exploratory_control_checks.csv',
             ['seed','allocator','run_id','nonzero_blocking_fields','request_timing_differences','aggregate_timing_differences'],
             comparisons)
    pooled=[]
    for a in ALLOCATORS:
        group=[r[2] for k,r in rows.items() if k[-1]==a]
        allocated,used,unused=(sum(m[field] for m in group) for field in
                               ('allocated_slot_ticks','used_slot_ticks','unused_allocated_slot_ticks'))
        pooled.append([a,allocated,used,unused,decimal(Fraction(unused,allocated),100)])
    csv_file(output/'exploratory_control_memory.csv',
             ['allocator','allocated_slot_ticks','used_slot_ticks','unused_allocated_slot_ticks','pooled_unused_pct'],pooled)
    return len(rows),sum(int(any(x[3:])) for x in comparisons),pooled


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    output = parser.parse_args().output
    frozen_path = ROOT / 'phase3/configs/primary.json'
    require(research.sha(frozen_path) == CONFIG_SHA, 'primary configuration hash')
    require(research.sha(ROOT / 'PHASE3_ANALYSIS_PLAN.md') == PLAN_SHA, 'frozen analysis plan hash')
    frozen = json.loads(frozen_path.read_text())
    regimes = fixture_axes(frozen)
    budgets = frozen['budgets']
    computes = frozen['compute_budgets']
    primary, primary_identity = load_records(PRIMARY, frozen)
    control, control_identity = load_records(CONTROL, frozen, control=True)
    require(len(primary) == 19200 and len(control) == 80, 'dataset size')
    indices = draw_indices(len(SEEDS))
    output.mkdir(parents=True, exist_ok=True)
    values, overall, pairs = primary_tables(output, primary, regimes, budgets, computes,
                                             weight_matrix(indices, len(SEEDS)))
    diagnostics(output, primary, regimes, budgets, computes, pairs)
    count, mismatches, pooled = control_summary(output, control, primary, regimes)
    csv_file(output / 'bootstrap_seed_indices.csv', list(SEEDS), indices)
    metadata = {
        'scientific_head': 'df794b67e72740bffb6272248b9d609c8decfaea',
        'analysis_plan_sha256': PLAN_SHA, 'primary_config_sha256': CONFIG_SHA,
        'primary_manifest_file_sha256': HASHES[PRIMARY], 'primary_manifest_identity': primary_identity,
        'control_manifest_file_sha256': HASHES[CONTROL], 'control_manifest_identity': control_identity,
        'implementation_sha256': research.sha(Path(__file__)),
        'implementation_spec_sha256': research.sha(OUTPUT / 'IMPLEMENTATION_SPEC.md'),
        'python': sys.version.split()[0], 'numpy': np.__version__, 'seed_order': list(SEEDS),
        'rng': 'random.Random(20261118).randrange(20), row-major',
        'bootstrap_draws': DRAW_COUNT, 'draw_size': len(SEEDS),
        'bootstrap_matrix_csv_sha256': research.sha(output / 'bootstrap_seed_indices.csv'),
        'percentile': 'linear interpolation at zero-based index (n - 1) * p; p=0.025, 0.975',
        'condition_rows': len(primary), 'workloads': len(regimes) * len(SEEDS),
        'primary_cells': len(values), 'seed_outcome_pairs': len(pairs) * len(OUTCOMES),
        'exploratory_control_rows': count, 'control_rows_with_disagreement_or_blocking': mismatches,
    }
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2, sort_keys=True) + '\n')
    figures(output, values, overall, regimes, budgets, computes)
    summaries(output, overall, count, mismatches, pooled)
    print(f'{len(primary)} primary rows, {len(values)} cells, {count} separate control rows')


class Figure:
    def __init__(self, width, height, title, subtitle):
        self.path = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img">',
            f'<title>{escape(title)}</title>',
            '<style>text{font-family:Arial,sans-serif;fill:#172c3a}</style>',
        ]
        self.rect(0, 0, width, height, '#ffffff')
        self.text(20, 30, title, 23, bold=True)
        self.text(20, 53, subtitle, 13)

    def text(self, x, y, message, size=12, align='start', bold=False):
        weight = 'bold' if bold else 'normal'
        self.path.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{align}" '
                         f'font-weight="{weight}">{escape(str(message))}</text>')

    def rect(self, x, y, width, height, fill, title=''):
        self.path.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{width:.3f}" height="{height:.3f}" '
                         f'fill="{fill}"><title>{escape(title)}</title></rect>')

    def save(self, path):
        path.write_text('\n'.join([*self.path, '</svg>', '']))


def shade(value, scale, diverging=True):
    if value is None:
        return '#b5b5b5'
    saturation = min(1, abs(float(value)) / scale)
    end = (7, 103, 138) if value < 0 or not diverging else (173, 67, 29)
    return '#' + ''.join(f'{round(246+(c-246)*saturation):02x}' for c in end)


def color_key(fig, scale, x, y, diverging=True):
    values = [scale*i/20 for i in range(-20 if diverging else 0, 21)]
    for i,value in enumerate(values):
        fig.rect(x+7*i, y, 7, 13, shade(value, scale, diverging))
    fig.text(x, y+29, f'{values[0]:.3g}%')
    if diverging:
        fig.text(x+143, y+29, '0%', align='middle')
    fig.text(x+7*len(values), y+29, f'{scale:.3g}%', align='end')


def figures(output, values, overall, regimes, budgets, computes):
    scenario_names = {None:'Unlimited', 8:'G8'}
    columns = list(itertools.product(computes, ALLOCATORS[1:]))
    for outcome, title in zip(OUTCOMES, TITLES, strict=True):
        scale = max(float(abs(v)*100) for k,v in values.items() if k[-1]==outcome and v is not None) or 1
        fig = Figure(1130, 640, f'{title} by workload and budget',
                     'Mean paired change versus fixed (%) · Blue favors paged · Orange favors fixed · Gray is undefined')
        for i,(compute,allocator) in enumerate(columns):
            x=231+i*148
            fig.text(x+67, 83, f'{scenario_names[compute]} · {allocator}', align='middle', bold=True)
            for j,budget in enumerate(budgets):
                fig.text(x+26*j+12, 104, budget, 9, 'middle')
            for row,axis in enumerate(regimes):
                if i==0:
                    fig.text(20, 125+18*row, ' · '.join(axis), 11)
                for j,budget in enumerate(budgets):
                    ratio=values[(*axis,budget,compute,allocator,outcome)]
                    value=ratio*100 if ratio is not None else None
                    fig.rect(x+26*j,113+18*row,25,17,shade(value,scale),
                             f'{" / ".join(axis)}, {budget} slots, {scenario_names[compute]}, {allocator} — {decimal(value)}%')
        fig.text(20, 104, 'Length · split · arrival')
        fig.text(20, 580, 'Memory budgets are in token slots. Each tile averages 20 paired seed differences.', 13)
        color_key(fig, scale, 780, 569)
        fig.save(output/f'{outcome}.svg')

    fig=Figure(840, 410, 'Seed-level improvements, ties and regressions',
               'All 4,800 paired seed–grid observations per outcome and allocator')
    colors=('#07678a','#aeb6be','#ad431d')
    for i,row in enumerate(overall):
        allocator,outcome,_,wins,ties,losses,*_=row
        y=84+i*30
        fig.text(20,y+13,f'{allocator} · {TITLES[OUTCOMES.index(outcome)]}')
        left=181
        for count,color in zip((wins,ties,losses),colors,strict=True):
            width=470*count/4800
            fig.rect(left,y,width,18,color,str(count))
            left+=width
        fig.text(670,y+13,f'{wins} / {ties} / {losses}')
    for i,(label,color) in enumerate(zip(('Improvement','Tie','Regression'),colors,strict=True)):
        fig.rect(181+i*145, 365, 15, 15, color)
        fig.text(202+i*145, 377, label)
    fig.save(output/'win_tie_loss.svg')

    with (output/'diagnostics.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    fig=Figure(730, 380, 'Unused share of allocated memory',
               'Pooled over matching primary workloads, seeds and compute scenarios within each tile')
    for i,allocator in enumerate(ALLOCATORS):
        fig.text(26,137+i*42,allocator,bold=True)
        for j,budget in enumerate(budgets):
            selected=[r for r in rows if r['allocator']==allocator and int(r['budget'])==budget]
            allocated=sum(int(r['allocated_slot_ticks_total']) for r in selected)
            unused=sum(int(r['unused_slot_ticks_total']) for r in selected)
            v=100*unused/allocated
            x=130+j*105
            if i==0:
                fig.text(x+48,100,budget,align='middle')
            fig.rect(x,110+i*42,98,38,shade(v,100,False),f'{float(v):.2f}%')
            fig.path.append(f'<text x="{x+49}" y="{134+i*42}" text-anchor="middle" font-size="13" '
                            f'style="fill:{"white" if v>65 else "#172c3a"}">{float(v):.2f}%</text>')
    fig.text(130,82,'Memory budget (token slots)',bold=True)
    fig.text(26,310,'Unused allocated slot-ticks ÷ allocated slot-ticks. Protected headroom is separate.')
    color_key(fig,100,130,325,False)
    fig.save(output/'memory_fragmentation.svg')

    fig=Figure(1030, 480, 'Relative effects by compute scenario',
               'Exploratory marginal means over the 24 observed workload definitions at each budget')
    scale=max(float(abs(v)*100) for v in values.values() if v is not None) or 1
    for i,(compute,allocator,outcome) in enumerate(itertools.product(computes,ALLOCATORS[1:],OUTCOMES)):
        if i==0:
            for j,budget in enumerate(budgets):
                fig.text(312+j*96,84,budget,align='middle')
            fig.text(780,84,'Memory budget (token slots)')
        y=98+i*17
        fig.text(20,y+12,f'{scenario_names[compute]} · {allocator} · {TITLES[OUTCOMES.index(outcome)]}',11)
        for j,budget in enumerate(budgets):
            group=[values[(*axis,budget,compute,allocator,outcome)] for axis in regimes]
            value=100*statistics.mean(group) if all(v is not None for v in group) else None
            x=266+j*96
            fig.rect(x,y,92,16,shade(value,scale),f'{decimal(value)}%')
            ink='white' if value is not None and abs(value)>scale*.7 else '#172c3a'
            content='undefined' if value is None else f'{float(value):+.2f}%'
            fig.path.append(f'<text x="{x+46}" y="{y+12}" text-anchor="middle" '
                            f'font-size="11" style="fill:{ink}">{content}</text>')
    fig.text(20,430,'Negative favors paged. Compute-scenario comparisons are descriptive.')
    color_key(fig,scale,630,420)
    fig.save(output/'compute_variation.svg')


def summaries(output, overall, count, mismatches, pooled):
    lines=['# Primary contrasts', '',
           'The nine designed-grid summaries weight each of 240 workload–budget–compute cells and all 20 seeds equally.',
           'Negative changes favor paged. Brackets show pointwise 95% seed-bootstrap intervals.', '',
           '| Allocator | Outcome | Mean ticks [95% interval] | Mean % [95% interval] | Wins / ties / losses |',
           '|---|---|---:|---:|---:|']
    for a,o,_,w,t,l,ab,al,ah,re,rl,rh in overall:
        absolute=f'{float(ab):+.3f} [{float(al):+.3f}, {float(ah):+.3f}]'
        relative=f'{float(re):+.3f} [{float(rl):+.3f}, {float(rh):+.3f}]' if re else 'Undefined'
        lines.append(f'| {a} | {o} | {absolute} | {relative} | {w:,} / {t:,} / {l:,} |')
    lines.extend(['','[All 2,160 primary cells](primary_contrasts.csv) · [Exact matched pairs](seed_pairs.csv) · '
                  '[Designed-grid data](designed_grid_summary.csv) · [Bootstrap metadata](metadata.json)',
                  '', '## Exploratory secondary measures', '',
                  'Diagnostics retain the six design dimensions. They report seed-average waiting in ticks, '
                  'peak active concurrency, occupancy, blocking, stalls, deferrals, allocated/used/unused slot-ticks '
                  'and protected headroom. Occupancy ratios use budget as denominator. The pooled unused share divides '
                  'summed unused slot-ticks by summed allocation slot-ticks. Protected headroom is recorded separately.',
                  '', 'Mean progressing requests equals generated tokens divided by makespan. Matched comparisons '
                  'of this secondary measure share the same seed-level makespan information.',
                  '', '[Full diagnostics](diagnostics.csv) · [Matched progressing comparisons](secondary_progressing.csv)'])
    (output/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    lines=['# Exploratory ample-memory control','',
           f'Validated {count} saved conditions across all four allocators and 20 matched seeds. '
           f'{mismatches} records had a nonzero blocking/stall field or a timing difference from fixed within seed.',
           '', '| Allocator | Allocated slot-ticks | Used slot-ticks | Unused slot-ticks | Pooled unused % |',
           '|---|---:|---:|---:|---:|']
    for a,allocated,used,unused,pct in pooled:
        lines.append(f'| {a} | {allocated:,} | {used:,} | {unused:,} | {pct} |')
    lines.extend(['', 'The pooled share uses the exact integer ratio unused over allocated slot-ticks. '
                  'The historical 640-condition planning count did not define an executable suite and was never run. '
                  'This check applies to the saved ample-memory fixture.',
                  '', '[Record-level verification](exploratory_control_checks.csv) · '
                  '[Allocation accounting](exploratory_control_memory.csv)'])
    (output/'EXPLORATORY_CONTROL.md').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    main()
