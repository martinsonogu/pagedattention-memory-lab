import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import phase3_batch as batch
from phase3_experiment import canonical, run, write_rows
from phase3_workloads import GeneratorConfig


class BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only the test seam substitutes two requests; CLI plans always stay frozen.
        cls.small=[GeneratorConfig(length_regime='short',request_count=2)]
        with patch.object(batch,'configs',return_value=cls.small):
            cls.manifest,cls.workloads=batch.prepare(batch.pilot_plan(),'pilot')
            cls.rows=list(batch.execute_rows(cls.manifest,cls.workloads))

    def tiny(self):
        return patch.object(batch,'configs',return_value=self.small)

    def test_frozen_dimensions_and_enumeration(self):
        plan=batch.pilot_plan()
        self.assertEqual(batch.read_json(batch.PILOT_PATH),plan)
        a=batch.configs(plan,'pilot'); b=batch.configs(plan,'pilot')
        self.assertEqual(a,b); self.assertEqual(len(a),24)
        self.assertEqual(len(set(a)),24)
        self.assertTrue(all(c.request_count==200 and c.maximum==2048 and c.seed==20261117 for c in a))
        pre=batch.configs(plan,'preflight')
        self.assertEqual([(c.length_regime,c.split_regime,c.arrival_regime) for c in pre],
                         [('short','generation-heavy','dense'),('long','generation-heavy','dense')])
        self.assertEqual(24*2*2*4,384)
        for key,value in [('seeds',[20261118]),('budgets',[2048]),('request_count',True),('schema_version',1.0)]:
            wrong=copy.deepcopy(plan); wrong[key]=value
            with self.assertRaises(ValueError): batch.validate_plan(wrong)

    def test_deterministic_manifest_and_ids(self):
        with self.tiny():
            other,_=batch.prepare(batch.pilot_plan(),'pilot')
            self.assertEqual(canonical(other),canonical(self.manifest))
            ids=[x['run_id'] for x in other['expected']]
            self.assertEqual(len(ids),16); self.assertEqual(len(set(ids)),16)
            changed=copy.deepcopy(other['expected'][0]); old=changed.pop('run_id')
            changed['config']['budget']=4096
            self.assertNotEqual(batch.digest(changed),old)

    def test_generation_once_and_shared_pairing(self):
        with self.tiny(), patch.object(batch,'generate',wraps=batch.generate) as generated:
            manifest,workloads=batch.prepare(batch.pilot_plan(),'pilot')
            self.assertEqual(generated.call_count,1)
            with patch.object(batch,'run',wraps=run) as replay:
                rows=list(batch.execute_rows(manifest,workloads))
                self.assertEqual(replay.call_count,1)
                self.assertIs(replay.call_args.args[0],workloads[0])
                self.assertEqual({r['result']['workload_sha256'] for r in rows[1:-1]}, {workloads[0].sha256})

    def test_missing_duplicate_extra_and_order(self):
        with self.tiny():
            validator=batch.Validator(self.manifest)
            with self.assertRaisesRegex(ValueError,'missing'): validator.complete()
            validator.accept(self.rows[1])
            with self.assertRaisesRegex(ValueError,'duplicate'): validator.accept(self.rows[1])
            validator=batch.Validator(self.manifest)
            with self.assertRaises(ValueError): validator.accept(self.rows[2])
            for row in self.rows[1:-1]: validator.accept(row)
            self.assertEqual(validator.complete()['observed_runs'],16)
            with self.assertRaises(ValueError): validator.accept(self.rows[1])

    def test_manifest_tampering_even_when_resigned(self):
        with self.tiny():
            for mutate in (lambda m:m['expected'].pop(),lambda m:m['workloads'][0]['requests'][0].update(output=1),
                           lambda m:m['metadata'].update(code_revision='x'),lambda m:m['expected'].reverse()):
                bad=copy.deepcopy(self.manifest); mutate(bad)
                bad['manifest_sha256']=batch.digest({k:v for k,v in bad.items() if k!='manifest_sha256'})
                with self.assertRaises(ValueError): batch.validate_manifest(bad)

    def test_integrity_rejects_corrupted_results(self):
        mutations=[lambda r:r.update(run_id='x'),lambda r:r['result'].update(workload_sha256='0'*64),
                   lambda r:r['result']['config'].update(budget=4096),lambda r:r['result'].update(working_tree_dirty=False),
                   lambda r:r['result']['requests'][0].update(first_token=0)]
        for key,value in [('admitted_requests',199),('completed_requests',0),('generated_tokens',0),
                          ('mean_latency_ticks',-1),('p95_latency_ticks',None),('compute_deferrals',-1),
                          ('used_slot_ticks',-1),('peak_occupancy',2),('makespan',0),
                          ('mean_progressing_requests',float('nan')),('peak_live_occupancy',float('inf')),
                          ('allocated_slot_ticks',True)]:
            mutations.append(lambda r,k=key,v=value:r['result']['metrics'].update({k:v}))
        with self.tiny():
            for mutate in mutations:
                bad=copy.deepcopy(self.rows[1]); mutate(bad)
                with self.assertRaises(ValueError): batch.Validator(self.manifest).accept(bad)

    def test_complete_file_revalidation_and_truncation(self):
        with self.tiny(), tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'complete.jsonl'
            write_rows(self.rows,path)
            self.assertEqual(batch.validate_dataset(path)['completion']['observed_runs'],16)
            for rows in (self.rows[:-1],self.rows[:-2]+self.rows[-1:],self.rows+[self.rows[1]],
                         self.rows[:-1]+[dict(self.rows[-1],results_sha256='0'*64)]):
                path.write_bytes(b''.join(canonical(r) for r in rows))
                with self.assertRaises(ValueError): batch.validate_dataset(path)

    def test_impossible_memory_accounting_rejected(self):
        with self.tiny():
            for index in (1,2):  # Fixed and paged-8.
                bad=copy.deepcopy(self.rows[index])
                for key in ('used_slot_ticks','allocated_slot_ticks','protected_headroom_slot_ticks',
                            'unused_allocated_slot_ticks','peak_allocated_slots','peak_used_slots',
                            'peak_occupancy','peak_live_occupancy','peak_active_requests'):
                    bad['result']['metrics'][key]=0
                expected=self.manifest['expected'][index-1]
                with self.assertRaisesRegex(ValueError,'live slot-time lower bound'):
                    batch.validate_result(bad,expected,self.workloads[0],self.manifest)
            bad=copy.deepcopy(self.rows[1])
            bad['result']['metrics']['allocated_slot_ticks']-=1
            bad['result']['metrics']['unused_allocated_slot_ticks']-=1
            with self.assertRaisesRegex(ValueError,'fixed reservation slot-time identity'):
                batch.validate_result(bad,self.manifest['expected'][0],self.workloads[0],self.manifest)

    def test_atomic_interruption_and_no_overwrite(self):
        with self.tiny(), tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'dataset.jsonl'
            def interrupted():
                yield self.manifest
                yield self.rows[1]
                self.assertFalse(path.exists())
                raise TimeoutError('bounded interruption')
            with self.assertRaises(TimeoutError): write_rows(interrupted(),path)
            self.assertFalse(path.exists()); self.assertEqual(list(Path(temp).iterdir()),[])
            write_rows(self.rows,path); original=path.read_bytes()
            with self.assertRaises(FileExistsError): write_rows(self.rows,path)
            self.assertEqual(path.read_bytes(),original)

    def test_deadline_interrupts_before_publication(self):
        import time
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'deadline.jsonl'
            def slow():
                yield self.manifest
                time.sleep(1)
            with self.assertRaises(TimeoutError):
                with batch.deadline(.02): write_rows(slow(),path)
            self.assertFalse(path.exists())

    def test_json_strictness(self):
        for line in (b'{"a":1,"a":2}\n',b'{"a":NaN}\n',b'{"a": Infinity}\n',b'{}',b'{ }\n'):
            with self.assertRaises(ValueError): batch.parse_line(line)


if __name__=='__main__': unittest.main()
