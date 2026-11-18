"""Exact M4F equivalence against the independently loaded M4D Git source."""
import hashlib
import subprocess
import sys
import types
import unittest
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch

import phase3_simulator as optimized
import phase3_experiment as runner
import phase3_batch as batch
from phase3_workloads import GeneratorConfig
from test_phase3_optimization import cases

COMMIT='393658751c71af88980f8443f80dba7d815800b0'
SHA256='7a20f2ea4529347864b0d51f36a9b5cd51d7fb428b040a48e6a05bb2675644b0'

@lru_cache(maxsize=1)
def reference():
    source=subprocess.check_output(['git','show',COMMIT+':phase3_simulator.py'],cwd=Path(__file__).parent)
    if hashlib.sha256(source).hexdigest()!=SHA256:
        raise RuntimeError('reference checksum mismatch')
    module=types.ModuleType('allocation_frozen_reference')
    sys.modules[module.__name__]=module
    exec(compile(source,'<allocation_frozen_reference>','exec'),module.__dict__)
    return module

class AllocationTests(unittest.TestCase):
    def compare(self,requests,kwargs):
        for trace in (False,True):
            with self.subTest(kwargs=kwargs,trace=trace):
                a=reference().simulate([reference().Request(*r) for r in requests],trace=trace,**kwargs)
                b=optimized.simulate([optimized.Request(*r) for r in requests],trace=trace,**kwargs)
                self.assertEqual(a,b)
                self.assertEqual(runner.canonical(a),runner.canonical(b))

    def test_existing_coverage_against_new_reference(self):
        count=0
        for group in ('smoke','edges','generated','randomized'):
            for name,requests,kwargs in cases(group):
                with self.subTest(group=group,name=name):self.compare(requests,kwargs)
                count+=2
        self.assertEqual(count,784)

    def test_pressure_and_consecutive_releases(self):
        fixtures=[([(0,1,127)]*24,128,512),
                  ([(0,8,8),(0,8,8),(0,8,8),(8,1,0)],16,32),
                  ([(0,1,1)]*12+[(1,33,0),(1,1,32)],33,512)]
        for requests,maximum,budget in fixtures:
            for strategy,block in runner.ALLOCATORS:
                for g in (None,1,2,8):
                    self.compare(requests,dict(strategy=strategy,block_size=block,maximum=maximum,budget=budget,compute_budget=g))

    def test_stall_classification_transition(self):
        result=optimized.simulate([optimized.Request(0,1,31)]*5,'paged',maximum=32,budget=64,block_size=8,trace=True)
        histories={}
        for e in result['trace']:
            if e['event']=='growth_stalled':histories.setdefault(e['request_id'],[]).append(e['reason'])
        self.assertTrue(any('protected_headroom' in h and 'physical_capacity' in h[h.index('protected_headroom')+1:] for h in histories.values()))

    def test_runner_and_batch_compatibility(self):
        configs=[GeneratorConfig(request_count=2,length_regime='short',seed=20261118)]
        with patch.object(batch,'configs',return_value=configs):
            manifest,workloads=batch.prepare(batch.pilot_plan(),'pilot')
            expected=list(runner.run(workloads[0],manifest['plan']['budgets'],manifest['plan']['compute_budgets'],outcomes=True))
            def adapter(requests,*args,**kwargs):
                return reference().simulate([reference().Request(r.arrival,r.prompt,r.output) for r in requests],*args,**kwargs)
            with patch.object(runner,'simulate',side_effect=adapter):
                actual=list(runner.run(workloads[0],manifest['plan']['budgets'],manifest['plan']['compute_budgets'],outcomes=True))
            self.assertEqual(runner.canonical(actual),runner.canonical(expected))
            validator=batch.Validator(manifest)
            for result in actual:
                identity={k:result[k] for k in ('config','workload_sha256','policy_version','metric_schema_version')}
                validator.accept(dict(kind='result',run_id=batch.digest(identity),result=result))
            self.assertEqual(validator.complete()['observed_runs'],16)

    def test_boundaries_and_completion_at_maximum(self):
        for strategy,block in runner.ALLOCATORS:
            requests=[(0,p,33-p) for p in (1,7,8,15,16,31,32,33)]
            for g in (None,1,2,8):
                self.compare(requests,dict(strategy=strategy,block_size=block,maximum=33,budget=256,compute_budget=g))

    def test_invalid_public_inputs_remain_rejected(self):
        for module in (reference(),optimized):
            for kw in (dict(budget=True),dict(maximum=2.5),dict(block_size=3),
                       dict(compute_budget=False),dict(trace=1)):
                with self.subTest(module=module.__name__,kw=kw):
                    with self.assertRaises(ValueError):module.simulate([],"paged",**kw)
            for request in ((0,True,0),(0,1,1.5),(-1,1,0),(0,33,1)):
                with self.assertRaises(ValueError):module.simulate([module.Request(*request)],"paged",maximum=33,budget=64)
            for length,block in ((True,8),(1,False),(-1,8),(1.5,8),(1,0)):
                with self.assertRaises(ValueError):module.rounded(length,block)

if __name__=='__main__':unittest.main()
