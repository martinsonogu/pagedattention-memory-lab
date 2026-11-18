import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import phase3_experiment as runner
from phase3_simulator import Request, simulate
from phase3_smoke import DEFAULT_CONFIG, check_expected, validate_result, smoke
from phase3_workloads import GeneratorConfig, generate, save


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.workload = generate(GeneratorConfig(length_regime='short', request_count=2))

    def test_same_tuple_reused_and_no_generation(self):
        real = runner.simulate
        with patch.object(runner, 'simulate', wraps=real) as simulated, \
             patch.object(runner, 'generate', side_effect=AssertionError('regeneration')):
            rows = list(runner.run(self.workload, [4096,2048], [8,None]))
        self.assertEqual(len(rows),16)
        args = [call.args[0] for call in simulated.call_args_list]
        self.assertTrue(all(requests is args[0] for requests in args))
        self.assertEqual(args[0],self.workload.to_simulator_requests())
        self.assertEqual([row['config']['budget'] for row in rows], [2048]*8+[4096]*8)
        self.assertTrue(all(row['workload_sha256']==self.workload.sha256 for row in rows))
        self.assertNotIn('requests',rows[0])
        self.assertNotIn('trace',rows[0])

    def test_metrics_passthrough_and_optional_details(self):
        row = next(runner.run(self.workload,[2048],[None],outcomes=True,trace=True))
        direct = simulate(self.workload.to_simulator_requests(),'fixed',budget=2048,maximum=2048,block_size=0,trace=True)
        for key in ('config','metrics','requests','trace'):
            self.assertEqual(row[key],direct[key])
        for key in ('code_revision','source_sha256','working_tree_dirty','policy_version','metric_schema_version',
                    'seed','workload_schema_version','generator_version','experiment_config'):
            self.assertIn(key,row)

    def test_invalid_conditions_before_any_simulation(self):
        invalid=[([2048,2047],[None]),([], [None]),([2048],[]),([2048,2048],[None]),
                 ([2048],[None,None]),([True],[None]),([2048.0],[None]),([2048],[True]),
                 ([2048],[0]),([2048],[1.5]),([2048],[-1])]
        with patch.object(runner,'simulate',side_effect=AssertionError('must not execute')):
            for budgets,computes in invalid:
                with self.subTest(budgets=budgets,computes=computes), self.assertRaises(ValueError):
                    list(runner.run(self.workload,budgets,computes))
        with self.assertRaises(ValueError):
            runner.validate_conditions(33,[63],[None])
        self.assertEqual(runner.validate_conditions(33,[64],[None]),([64],[None]))

    def test_empty_contract(self):
        rows=list(runner.run(generate(GeneratorConfig(request_count=0)),[2048],[None]))
        for row in rows:
            m=row['metrics']
            for key in ('makespan','mean_progressing_requests','mean_latency_ticks','mean_waiting_ticks','completed_requests'):
                self.assertEqual(m[key],0)
            self.assertIsNone(m['p95_latency_ticks'])
            self.assertIsNone(m['p95_waiting_ticks'])

    def test_stable_serialization_and_output_guards(self):
        first=list(runner.run(self.workload,[2048],[None]))
        second=list(runner.run(self.workload,[2048],[None]))
        self.assertEqual(runner.canonical(first),runner.canonical(second))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'rows.jsonl'
            runner.write_rows(first,path)
            self.assertEqual([json.loads(line) for line in path.read_bytes().splitlines()],first)
            with self.assertRaises(FileExistsError): runner.write_rows(second,path)
        with self.assertRaises(ValueError): runner.write_rows([],runner.ROOT/'results.csv')

    def test_manifest_generation_once_and_strict_validation(self):
        manifest=json.loads(self.workload.canonical_bytes())['manifest']
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'manifest.json'
            path.write_bytes(runner.canonical(manifest))
            with patch.object(runner,'generate',wraps=generate) as generated:
                self.assertEqual(runner.from_manifest(path),self.workload)
                self.assertEqual(generated.call_count,1)
            for key in manifest:
                broken=copy.deepcopy(manifest); del broken[key]
                path.write_bytes(runner.canonical(broken))
                with self.assertRaises(ValueError): runner.from_manifest(path)
            broken=copy.deepcopy(manifest); broken['config']['request_count']=True
            path.write_bytes(runner.canonical(broken))
            with self.assertRaises(ValueError): runner.from_manifest(path)
            for bad in ('{"x":1,"x":2}','{"x":NaN}'):
                path.write_text(bad)
                with self.assertRaises(ValueError): runner.read_json(path)

    def test_failed_output_never_publishes_partial_file(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'output.jsonl'
            def interrupted():
                yield {'row': 1}
                self.assertFalse(target.exists())
                raise KeyboardInterrupt('interrupted')
            with self.assertRaises(KeyboardInterrupt):
                runner.write_rows(interrupted(), target)
            self.assertEqual(list(Path(temp).iterdir()), [])
            with self.assertRaises(ValueError):
                runner.write_rows([{'row': 1}, {'invalid': float('nan')}], target)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_output_publication_cannot_overwrite_concurrent_writer(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'output.jsonl'
            def raced():
                yield {'row': 1}
                target.write_bytes(b'other writer\n')
            with self.assertRaises(FileExistsError):
                runner.write_rows(raced(), target)
            self.assertEqual(target.read_bytes(), b'other writer\n')
            self.assertEqual(list(Path(temp).iterdir()), [target])

    def test_smoke_rejects_duplicate_fixture_identity(self):
        config = runner.read_json(DEFAULT_CONFIG)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'smoke.json'
            for distinct_names in (False, True):
                invalid = copy.deepcopy(config)
                invalid['fixtures'] = [copy.deepcopy(config['fixtures'][0]) for _ in range(6)]
                if distinct_names:
                    for i, fixture in enumerate(invalid['fixtures']):
                        fixture['name'] = str(i)
                path.write_bytes(runner.canonical(invalid))
                with patch('phase3_smoke.replay', side_effect=AssertionError('must reject before replay')):
                    with self.assertRaisesRegex(AssertionError, 'duplicate fixture'):
                        smoke(path)

    def test_smoke_rejects_duplicate_condition_rows(self):
        fixture = runner.read_json(DEFAULT_CONFIG)['fixtures'][0]
        requests = tuple(Request(**r) for r in fixture['requests'])
        result = simulate(requests, 'fixed', maximum=32, budget=64, trace=True)
        with patch('phase3_smoke.replay', return_value=[result] * 12):
            with self.assertRaisesRegex(AssertionError, 'missing or duplicate smoke conditions'):
                smoke()

    def test_cli_saved_workload_replay_across_processes(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'workload.json'; save(self.workload,source)
            outputs=[Path(temp)/name for name in ('a.jsonl','b.jsonl')]
            for target in outputs:
                subprocess.run([sys.executable,'-B',str(runner.ROOT/'phase3_experiment.py'),
                                '--workload',str(source),'--budgets','2048','--compute','1','--output',str(target)],check=True,capture_output=True)
            self.assertEqual(outputs[0].read_bytes(),outputs[1].read_bytes())
            self.assertEqual(len(outputs[0].read_bytes().splitlines()),4)
            invalid=subprocess.run([sys.executable,'-B',str(runner.ROOT/'phase3_experiment.py'),
                                    '--workload',str(source),'--budgets','1','--output',str(Path(temp)/'invalid')],capture_output=True)
            self.assertNotEqual(invalid.returncode,0)
            self.assertFalse((Path(temp)/'invalid').exists())

    def test_smoke_definition_not_full_matrix_execution(self):
        config=runner.read_json(DEFAULT_CONFIG)
        self.assertEqual(len(config['fixtures']),6)
        self.assertEqual(config['compute_budgets'],[None,1,2])
        self.assertEqual(len({f['name'] for f in config['fixtures']}),6)
        for fixture in config['fixtures']:
            runner.validate_conditions(fixture['maximum'],[fixture['budget']],config['compute_budgets'])
        # One hand-calculated case exercises the harness before the separate matrix.
        fixture=config['fixtures'][0]
        requests=tuple(Request(**r) for r in fixture['requests'])
        result=simulate(requests,'fixed',maximum=32,budget=64,trace=True)
        validate_result(result,requests)
        check_expected(fixture,result)
        corrupted=copy.deepcopy(result); corrupted['metrics']['used_slot_ticks']+=1
        with self.assertRaises(AssertionError): validate_result(corrupted,requests)


if __name__=='__main__':
    unittest.main()
