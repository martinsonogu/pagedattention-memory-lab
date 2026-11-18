"""Exact differential checks against the immutable Milestone 3 Git object."""
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import types
import unittest

import phase3_simulator as optimized
from phase3_workloads import GeneratorConfig, generate

REFERENCE_COMMIT = 'f7edb22819ba5ece5094327c321544c633c7b877'
REFERENCE_SHA256 = '602be794f3ed6c8197237ccb708fc9641440e7173d6c8f85fc1a2d4d695636fa'
ALLOCATORS = (('fixed',0),('paged',8),('paged',16),('paged',32))


@lru_cache(maxsize=1)
def reference():
    source=subprocess.check_output(['git','show',REFERENCE_COMMIT+':phase3_simulator.py'],cwd=Path(__file__).parent)
    if hashlib.sha256(source).hexdigest()!=REFERENCE_SHA256:
        raise RuntimeError('frozen reference checksum mismatch')
    module=types.ModuleType('phase3_frozen_reference')
    sys.modules[module.__name__]=module
    exec(compile(source,'<phase3_frozen_reference>','exec'),module.__dict__)
    return module


def execute(module, requests, kwargs, trace):
    return module.simulate(tuple(module.Request(*r) for r in requests),trace=trace,**kwargs)


def cases(group):
    if group=='smoke':
        config=json.loads((Path(__file__).parent/'phase3/configs/smoke.json').read_bytes())
        for fixture in config['fixtures']:
            requests=[(r['arrival'],r['prompt'],r['output']) for r in fixture['requests']]
            for (strategy,block),g in itertools.product(ALLOCATORS,config['compute_budgets']):
                yield fixture['name'],requests,dict(strategy=strategy,block_size=block,compute_budget=g,
                                                   maximum=fixture['maximum'],budget=fixture['budget'])
        return
    fixtures=[]
    if group=='edges':
        fixtures=[('empty',[],33,64),('prompt_only',[(3,1,0),(3,33,0),(20,8,0)],33,64),
                  ('exact_fit',[(0,1,32),(0,33,0),(1,1,1)],33,64),
                  ('actual_release',[(0,1,1),(0,1,32),(0,1,32)],33,128),
                  ('compute_reuse',[(0,8,24)]*2+[(0,1,31)]*3,32,64),
                  ('sparse',[(100,8,1),(0,1,0),(50,8,2)],32,64),
                  ('rounding',[(0,7,2),(0,8,1),(0,9,0)],9,32)]
    elif group=='generated':
        for seed in (20261117,20261118,20261119):
            w=generate(GeneratorConfig(seed=seed,length_regime='mixed',request_count=4))
            fixtures.append((f'seed-{seed}',[(r.arrival,r.prompt,r.output) for r in w.requests],2048,4096))
    elif group=='randomized':
        for seed in range(10):
            rng=random.Random(seed); requests=[]
            for _ in range(8):
                prompt=rng.randint(1,33)
                requests.append((rng.randint(0,6),prompt,rng.randint(0,33-prompt)))
            fixtures.append((f'pressure-{seed}',requests,33,64))
    else:
        raise ValueError(group)
    for name,requests,maximum,budget in fixtures:
        for (strategy,block),g in itertools.product(ALLOCATORS,(None,1,2,8)):
            yield name,requests,dict(strategy=strategy,block_size=block,compute_budget=g,maximum=maximum,budget=budget)


class OptimizationTests(unittest.TestCase):
    def compare_group(self,group):
        for name,requests,kwargs in cases(group):
            for trace in (False,True):
                with self.subTest(group=group,name=name,kwargs=kwargs,trace=trace):
                    self.assertEqual(execute(reference(),requests,kwargs,trace),
                                     execute(optimized,requests,kwargs,trace))

    def test_all_72_smoke_conditions(self):
        self.assertEqual(len(list(cases('smoke'))),72)
        self.compare_group('smoke')

    def test_edge_cases(self):
        self.compare_group('edges')

    def test_generated_multiple_seeds(self):
        self.compare_group('generated')

    def test_randomized_pressure(self):
        self.compare_group('randomized')

    def test_required_outcomes_are_exercised(self):
        events=set()
        for _,requests,kwargs in cases('smoke'):
            result=execute(optimized,requests,kwargs,True)
            for event in result['trace']:
                if event['event']=='tick_end': events.update(dict(event['outcomes']).values())
        self.assertEqual(events,{'generated','physical_capacity','protected_headroom','compute_deferred'})


if __name__=='__main__': unittest.main()
