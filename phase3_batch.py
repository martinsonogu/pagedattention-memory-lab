"""Bounded Phase 3 pilot execution and streaming completeness validation."""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import resource
import signal
import statistics
import sys
import time

from phase3_experiment import (ALLOCATORS, METRIC_SCHEMA_VERSION, POLICY_VERSION,
                               ROOT, canonical, code_metadata, read_json, run, write_rows)
from phase3_workloads import (ARRIVAL_REGIMES, GENERATOR_VERSION, LENGTH_REGIMES,
                              SPLIT_REGIMES, GeneratorConfig, generate, loads)

VERSION = 1
PILOT_PATH = ROOT / 'phase3/configs/pilot.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def pilot_plan():
    return dict(schema_version=VERSION, kind='phase3-pilot-v1', maximum=2048,
                request_count=200, seeds=[20261117], length_regimes=list(LENGTH_REGIMES),
                split_regimes=list(SPLIT_REGIMES), arrival_regimes=list(ARRIVAL_REGIMES),
                budgets=[2048,8192], compute_budgets=[None,8],
                allocators=[dict(strategy=s,block_size=b) for s,b in ALLOCATORS],
                expected_workloads=24, expected_runs=384,
                preflight=dict(length_regimes=['short','long'], split_regime='generation-heavy',
                               arrival_regime='dense', expected_workloads=2, expected_runs=32,
                               timeout_seconds=120),
                pilot_timeout_seconds=900,
                feasibility_rule='384 * slowest_preflight_workload_mean_run_seconds <= 900')


def validate_plan(plan):
    require(canonical(plan) == canonical(pilot_plan()), 'plan differs from frozen pilot v1')


def configs(plan, mode):
    validate_plan(plan)
    require(mode in ('pilot','preflight'), 'unsupported mode')
    result = [GeneratorConfig(seed=seed,length_regime=length,split_regime=split,arrival_regime=arrival,
                              request_count=plan['request_count'],maximum=plan['maximum'])
              for length,split,arrival,seed in itertools.product(plan['length_regimes'],plan['split_regimes'],
                                                               plan['arrival_regimes'],plan['seeds'])]
    if mode == 'preflight':
        p=plan['preflight']
        result=[c for c in result if c.length_regime in p['length_regimes'] and
                c.split_regime==p['split_regime'] and c.arrival_regime==p['arrival_regime']]
    return result


def conditions(workloads, plan):
    expected=[]
    for workload in workloads:
        for budget,compute,(strategy,block) in itertools.product(plan['budgets'],plan['compute_budgets'],ALLOCATORS):
            identity=dict(workload_sha256=workload.sha256, policy_version=POLICY_VERSION,
                          metric_schema_version=METRIC_SCHEMA_VERSION,
                          config=dict(strategy=strategy,block_size=block,budget=budget,
                                      compute_budget=compute,maximum=workload.config.maximum))
            expected.append(dict(run_id=digest(identity),**identity))
    return expected


def prepare(plan, mode):
    # This is the only generation site: one call per realized workload.
    workloads=[generate(c) for c in configs(plan,mode)]
    manifest=dict(kind='manifest',batch_schema_version=VERSION,mode=mode,plan=plan,
                  metadata=code_metadata(), batch_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  workloads=[json.loads(w.canonical_bytes()) for w in workloads],
                  expected=conditions(workloads,plan))
    manifest['manifest_sha256']=digest(manifest)
    validate_manifest(manifest)
    return manifest,workloads


def validate_manifest(manifest):
    require(type(manifest) is dict and set(manifest)=={'kind','batch_schema_version','mode','plan','metadata',
            'batch_source_sha256','workloads','expected','manifest_sha256'}, 'invalid manifest keys')
    require(manifest['kind']=='manifest' and type(manifest['batch_schema_version']) is int and
            manifest['batch_schema_version']==VERSION, 'invalid manifest version')
    require(manifest['manifest_sha256']==digest({k:v for k,v in manifest.items() if k!='manifest_sha256'}), 'manifest checksum')
    expected_configs=configs(manifest['plan'],manifest['mode'])
    workloads=[loads(canonical(doc)) for doc in manifest['workloads']]
    require([w.config for w in workloads]==expected_configs,'wrong workload enumeration')
    require(len({w.sha256 for w in workloads})==len(workloads),'duplicate workloads')
    require(canonical(manifest['expected'])==canonical(conditions(workloads,manifest['plan'])), 'wrong expected-run manifest')
    metadata=manifest['metadata']
    require(set(metadata)=={'code_revision','working_tree_dirty','source_sha256'}, 'metadata keys')
    require(type(metadata['working_tree_dirty']) is bool,'dirty flag')
    def hexstring(value,n):
        return type(value) is str and len(value)==n and all(c in '0123456789abcdef' for c in value)
    require(hexstring(metadata['code_revision'],40),'revision')
    require(set(metadata['source_sha256'])=={'phase3_simulator.py','phase3_workloads.py','phase3_experiment.py'},'source inventory')
    require(all(hexstring(v,64) for v in metadata['source_sha256'].values()) and
            hexstring(manifest['batch_source_sha256'],64),'source hashes')
    return {w.sha256:w for w in workloads}


def finite(value):
    if type(value) is float:
        require(math.isfinite(value),'nonfinite number')
    elif isinstance(value,dict):
        for v in value.values(): finite(v)
    elif isinstance(value,(list,tuple)):
        for v in value: finite(v)


METRICS = set('admitted_requests completed_requests makespan mean_latency_ticks p95_latency_ticks '
 'mean_progressing_requests total_waiting_ticks mean_waiting_ticks p95_waiting_ticks generated_tokens '
 'eligible_request_ticks physical_capacity_stalls protected_headroom_stalls growth_stall_request_ticks '
 'compute_deferrals admission_blocked_physical_ticks admission_blocked_protection_ticks queue_request_ticks '
 'peak_active_requests allocated_slot_ticks used_slot_ticks protected_headroom_slot_ticks '
 'unused_allocated_slot_ticks peak_allocated_slots peak_used_slots peak_occupancy peak_live_occupancy '
 'final_allocated_slots final_used_slots final_protected_headroom'.split())
FLOAT_METRICS={'mean_latency_ticks','mean_waiting_ticks','mean_progressing_requests','peak_occupancy','peak_live_occupancy'}
COUNTERS=('generated_tokens','physical_capacity_stalls','protected_headroom_stalls','compute_deferrals')


def validate_result(row, expected, workload, manifest):
    finite(row)
    require(set(row)=={'kind','run_id','result'},'result envelope')
    require(row['kind']=='result' and row['run_id']==expected['run_id'],'unexpected condition or ordering')
    r=row['result']; m=r['metrics']; records=r['requests']
    require(set(r)=={'code_revision','working_tree_dirty','source_sha256','policy_version','metric_schema_version',
                    'workload_sha256','workload_schema_version','generator_version','seed','workload_config',
                    'experiment_config','config','metrics','requests'}, 'runner schema changed')
    for k in ('config','workload_sha256','policy_version','metric_schema_version'):
        require(canonical(r[k])==canonical(expected[k]),'wrong '+k)
    require(r['workload_schema_version']==1 and type(r['workload_schema_version']) is int and
            r['generator_version']==GENERATOR_VERSION, 'workload version')
    require(canonical(r['workload_config'])==canonical(asdict(workload.config)) and
            type(r['seed']) is int and r['seed']==workload.config.seed,'wrong generator config')
    for key,value in manifest['metadata'].items():
        require(canonical(r[key])==canonical(value),'source metadata changed: '+key)
    plan=manifest['plan']
    require(canonical(r['experiment_config'])==canonical(dict(budgets=plan['budgets'],compute_budgets=plan['compute_budgets'],
            allocators=plan['allocators'],outcomes=True,trace=False)), 'runner conditions mismatch')
    require(set(m)==METRICS,'missing or unknown metrics')
    for key,value in m.items():
        if key in ('p95_latency_ticks','p95_waiting_ticks') and not workload.requests:
            require(value is None,'empty percentile'); continue
        require(type(value) in ((int,float) if key in FLOAT_METRICS else (int,)) and value>=0, 'invalid metric '+key)
    n=len(workload.requests); total=sum(q.output for q in workload.requests)
    require(m['admitted_requests']==m['completed_requests']==len(records)==n,'request conservation')
    require(m['generated_tokens']==total,'token conservation')
    record_keys=set('request_id arrival prompt admission completion first_token generated_tokens physical_capacity_stalls '
                    'protected_headroom_stalls compute_deferrals waiting_ticks latency_ticks'.split())
    for i,(record,q) in enumerate(zip(records,workload.requests)):
        require(set(record)==record_keys,'record schema')
        for key,value in record.items():
            if key=='first_token' and value is None: continue
            require(type(value) is int and value>=0,'invalid record '+key)
        require((record['request_id'],record['arrival'],record['prompt'])==(i,q.arrival,q.prompt),'request identity')
        a,c=record['admission'],record['completion']
        require(q.arrival<=a<=c,'timestamps')
        require(record['generated_tokens']==q.output and c-a==sum(record[k] for k in COUNTERS),'resident accounting')
        require(record['waiting_ticks']==a-q.arrival and record['latency_ticks']==c-q.arrival,'latency/waiting')
        require((a < record['first_token'] <= c) if q.output else (record['first_token'] is None and a==c), 'first token')
    require([r['admission'] for r in records]==sorted(r['admission'] for r in records),'FIFO admissions')
    for key in COUNTERS: require(m[key]==sum(r[key] for r in records),'counter sum '+key)
    for field,mean,p95 in (('latency_ticks','mean_latency_ticks','p95_latency_ticks'),('waiting_ticks','mean_waiting_ticks','p95_waiting_ticks')):
        values=[r[field] for r in records]
        require(m[mean]==(sum(values)/n if n else 0),'mean denominator')
        require(m[p95]==(sorted(values)[(95*n+99)//100-1] if n else None),'nearest rank')
    t=m['makespan']; b=r['config']['budget']; g=r['config']['compute_budget']
    require(t==max((x['completion'] for x in records),default=0),'makespan identity')
    require(t<=max((q.arrival for q in workload.requests),default=0)+total,'termination bound')
    require(m['mean_progressing_requests']==(total/t if t else 0),'progress identity')
    require(g is None or total<=g*t,'compute bound')
    require(m['eligible_request_ticks']==sum(m[k] for k in COUNTERS),'eligible accounting')
    require(m['growth_stall_request_ticks']==m['physical_capacity_stalls']+m['protected_headroom_stalls'],'growth sum')
    require(m['queue_request_ticks']==m['total_waiting_ticks']==sum(x['waiting_ticks'] for x in records),'queue accounting')
    require(0<=m['peak_used_slots']<=m['peak_allocated_slots']<=b,'peak capacity')
    require(m['peak_occupancy']==m['peak_allocated_slots']/b and m['peak_live_occupancy']==m['peak_used_slots']/b,'occupancy denominators')
    require(m['used_slot_ticks']<=m['allocated_slot_ticks'] and
            m['allocated_slot_ticks']+m['protected_headroom_slot_ticks']<=b*t,'slot-time bounds')
    # Every successful token contributes its post-generation resident length.
    # Stalled/deferred intervals retain at least the prompt's live slots.
    minimum_used=sum(q.prompt*q.output + q.output*(q.output+1)//2 +
                     q.prompt*(record['completion']-record['admission']-q.output)
                     for q,record in zip(workload.requests,records))
    require(m['used_slot_ticks']>=minimum_used,'live slot-time lower bound')
    require(m['peak_used_slots']>=max((q.prompt+q.output for q in workload.requests),default=0),
            'live peak lower bound')
    require(m['peak_active_requests']>0 or n==0,'nonempty resident population')
    if r['config']['strategy']=='fixed':
        resident_ticks=sum(record['completion']-record['admission'] for record in records)
        require(m['allocated_slot_ticks']==workload.config.maximum*resident_ticks,
                'fixed reservation slot-time identity')
        require(m['protected_headroom_slot_ticks']==0,'fixed headroom must be zero')
        require(m['peak_allocated_slots']==workload.config.maximum*m['peak_active_requests'],
                'fixed reservation peak identity')
    require(m['unused_allocated_slot_ticks']==m['allocated_slot_ticks']-m['used_slot_ticks'],'unused slots')
    require(m['peak_active_requests']<=n,'peak population')
    require(all(m[k]==0 for k in ('final_allocated_slots','final_used_slots','final_protected_headroom')),'final release')


class Validator:
    def __init__(self,manifest):
        self.manifest=manifest
        self.workloads=validate_manifest(manifest)
        self.index=0; self.seen=set(); self.hasher=hashlib.sha256()

    def accept(self,row):
        require(self.index<len(self.manifest['expected']),'extra run')
        require(row.get('run_id') not in self.seen,'duplicate run')
        expected=self.manifest['expected'][self.index]
        validate_result(row,expected,self.workloads[expected['workload_sha256']],self.manifest)
        self.seen.add(row['run_id']); self.index+=1; self.hasher.update(canonical(row))

    def complete(self):
        require(self.index==len(self.manifest['expected']),'missing runs')
        return dict(kind='completion',batch_schema_version=VERSION,status='complete',
                    manifest_sha256=self.manifest['manifest_sha256'],expected_runs=len(self.manifest['expected']),
                    observed_runs=self.index,workload_count=len(self.workloads),results_sha256=self.hasher.hexdigest())


def peak_rss_bytes():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform=='darwin' else value*1024)


def execute_rows(manifest,workloads):
    validator=Validator(manifest)
    timings=[]; started=time.perf_counter()
    yield manifest
    for workload in workloads:
        iterator=iter(run(workload,manifest['plan']['budgets'],manifest['plan']['compute_budgets'],outcomes=True,trace=False))
        while True:
            start=time.perf_counter()
            try: result=next(iterator)
            except StopIteration: break
            elapsed=time.perf_counter()-start
            identity={k:result[k] for k in ('config','workload_sha256','policy_version','metric_schema_version')}
            row=dict(kind='result',run_id=digest(identity),result=result)
            validator.accept(row)
            timings.append(dict(run_id=row['run_id'],seconds=elapsed,workload_sha256=workload.sha256))
            yield row
        print(f"validated {validator.index}/{len(manifest['expected'])} runs",file=sys.stderr,flush=True)
    require(code_metadata()==manifest['metadata'],'execution sources or Git state changed')
    require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==manifest['batch_source_sha256'],'batch source changed')
    complete=validator.complete()
    values=[x['seconds'] for x in timings]
    complete['measurements']=dict(elapsed_seconds=time.perf_counter()-started,
        mean_run_seconds=statistics.mean(values),median_run_seconds=statistics.median(values),
        peak_rss_bytes=peak_rss_bytes(),run_timings=timings)
    yield complete


@contextmanager
def deadline(seconds):
    require(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,'invalid deadline')
    def expired(signum,frame): raise TimeoutError('execution wall-clock limit exceeded; final dataset not published')
    old=signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old)


def execute(plan,mode,path):
    start=time.perf_counter()
    limit=plan['preflight']['timeout_seconds'] if mode=='preflight' else plan['pilot_timeout_seconds']
    with deadline(limit):
        manifest,workloads=prepare(plan,mode)
        write_rows(execute_rows(manifest,workloads),path)
    report=validate_dataset(path)
    return dict(report,output_bytes=Path(path).stat().st_size,total_elapsed_seconds=time.perf_counter()-start)


def parse_line(line):
    def unique(pairs):
        d={}
        for k,v in pairs:
            require(k not in d,'duplicate JSON key'); d[k]=v
        return d
    def invalid(value): raise ValueError('nonfinite JSON')
    doc=json.loads(line,object_pairs_hook=unique,parse_constant=invalid)
    require(canonical(doc)==line,'noncanonical dataset line')
    return doc


def validate_dataset(path):
    with Path(path).open('rb') as stream:
        manifest=parse_line(next(stream,b''))
        validator=Validator(manifest)
        completion=None
        for line in stream:
            row=parse_line(line)
            if row.get('kind')=='completion':
                require(completion is None,'duplicate completion')
                completion=row
                expected=validator.complete()
                require(set(row)==set(expected)|{'measurements'},'completion schema')
                require(all(canonical(row[k])==canonical(v) for k,v in expected.items()),'completion mismatch')
                finite(row['measurements'])
            else:
                require(completion is None,'rows after completion')
                validator.accept(row)
        require(completion is not None,'missing completion record')
        measurements=completion['measurements']
        require(set(measurements)=={'elapsed_seconds','mean_run_seconds','median_run_seconds','peak_rss_bytes','run_timings'},'measurement schema')
        for key in ('elapsed_seconds','mean_run_seconds','median_run_seconds'):
            require(type(measurements[key]) in (int,float) and measurements[key]>=0,'invalid measurement '+key)
        require(type(measurements['peak_rss_bytes']) is int and measurements['peak_rss_bytes']>=0,'invalid RSS')
        timings=measurements['run_timings']
        require([t['run_id'] for t in timings]==[e['run_id'] for e in manifest['expected']],'timing inventory')
        for timing,e in zip(timings,manifest['expected']):
            require(set(timing)=={'run_id','seconds','workload_sha256'},'timing schema')
            require(timing['workload_sha256']==e['workload_sha256'] and type(timing['seconds']) in (int,float) and timing['seconds']>=0,'invalid timing')
        values=[t['seconds'] for t in timings]
        require(measurements['mean_run_seconds']==statistics.mean(values) and
                measurements['median_run_seconds']==statistics.median(values),'timing statistics')
        require(measurements['elapsed_seconds']>=sum(values),'elapsed excludes run time')
        return dict(mode=manifest['mode'],completion=completion,metadata=manifest['metadata'],
                    batch_source_sha256=manifest['batch_source_sha256'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['preflight','pilot','validate'])
    parser.add_argument('--config',default=str(PILOT_PATH))
    parser.add_argument('--output',required=True)
    parser.add_argument('--preflight-report')
    args=parser.parse_args()
    try:
        if args.command=='validate': report=validate_dataset(args.output)
        else:
            plan=read_json(args.config); validate_plan(plan)
            if args.command=='pilot':
                require(args.preflight_report is not None,'pilot requires completed preflight dataset')
                prior=validate_dataset(args.preflight_report)
                require(prior['mode']=='preflight','not a preflight dataset')
                require(prior['metadata']==code_metadata() and prior['batch_source_sha256']==
                        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'preflight execution code or Git state differs')
                timings=prior['completion']['measurements']['run_timings']
                groups={t['workload_sha256'] for t in timings}
                estimate=384*max(statistics.mean(t['seconds'] for t in timings if t['workload_sha256']==w) for w in groups)
                require(estimate<=plan['pilot_timeout_seconds'],'preflight estimate exceeds pilot wall-clock limit')
            report=execute(plan,args.command,args.output)
        print(json.dumps(report,sort_keys=True,allow_nan=False))
    except (ValueError,OSError,TimeoutError) as exc:
        parser.error(str(exc))


if __name__=='__main__': main()
