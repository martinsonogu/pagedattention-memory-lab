import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import phase3_batch as batch
import phase3_experiment as runner
import phase3_research_batch as research
from phase3_workloads import GeneratorConfig, generate


class ResearchBatchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'fixture'
        self.workload = generate(GeneratorConfig(request_count=2))
        self.plan, _ = research.inventory_plan('pilot')
        self.items = [(self.workload, item) for item in research.inventory([self.workload], self.plan)[:2]]

    def run_fixture(self, scope='test'):
        with redirect_stdout(io.StringIO()):
            research.run_batch(self.root, self.plan, self.items, scope)

    def test_inventory_counts_and_stable_smoke_ids(self):
        pilot, configs = research.inventory_plan('pilot')
        primary, primary_configs = research.inventory_plan('primary')
        self.assertEqual(len(configs) * len(pilot['budgets']) * 2 * 4, 384)
        self.assertEqual(len(set(primary_configs)), 480)
        self.assertEqual(len(primary_configs) * len(primary['budgets']) * 2 * 4, 19200)
        with patch.object(runner, 'simulate', side_effect=AssertionError('inventory simulated')):
            _, smoke = research.smoke_inventory('smoke')
        self.assertEqual(len({condition['run_id'] for _, condition in smoke}), 4)
        for workload, item in smoke:
            self.assertIn(item, batch.conditions([workload], pilot))
            self.assertEqual(len(workload.requests), 200)
        self.assertEqual([(w.config.length_regime, e['config']['strategy'], e['config']['block_size'])
                          for w, e in smoke], list(research.SMOKE))

    def test_single_dispatch_canonical_row_equivalence(self):
        identity = research.run_identity(self.plan, self.items, 'test')
        reference = next(runner.run(self.workload, self.plan['budgets'], self.plan['compute_budgets'],
                                    outcomes=True))
        with patch.object(runner, 'simulate', wraps=runner.simulate) as simulate:
            actual = research.scientific_row(self.workload, self.items[0][1], identity)
        self.assertEqual(simulate.call_count, 1)
        self.assertEqual(runner.canonical(actual['result']), runner.canonical(reference))

    def test_valid_resume_validates_and_skips(self):
        self.run_fixture()
        before = {p: p.read_bytes() for p in self.root.glob('*.json')}
        with patch.object(runner, 'simulate', side_effect=AssertionError('unexpected rerun')):
            self.run_fixture()
        self.assertEqual({p: p.read_bytes() for p in self.root.glob('*.json')}, before)

    def test_corrupt_record_stops_before_dispatch(self):
        self.run_fixture()
        items = sorted(self.root.glob('condition-*.json'))
        items[0].unlink()
        items[1].write_bytes(b'{"truncated":')
        with patch.object(runner, 'simulate', side_effect=AssertionError('unexpected dispatch')):
            with self.assertRaises(ValueError):
                self.run_fixture()

    def test_changed_config_or_source_stops_resume(self):
        self.run_fixture()
        with patch.object(runner, 'simulate', side_effect=AssertionError('unexpected dispatch')):
            with self.assertRaisesRegex(ValueError, 'incompatible code/config'):
                self.run_fixture(scope='other')
            actual = research.sha
            with patch.object(research, 'sha', side_effect=lambda p: '0' * 64
                              if p == batch.PILOT_PATH else actual(p)):
                with self.assertRaisesRegex(ValueError, 'incompatible code/config'):
                    self.run_fixture()

    def test_publication_no_overwrite_and_failed_file_sync(self):
        self.root.mkdir()
        path = self.root / 'record.json'
        with patch.object(research.os, 'fsync', side_effect=OSError('injected fsync')):
            with self.assertRaisesRegex(OSError, 'injected fsync'):
                research.publish(path, {'first': 1})
        self.assertFalse(path.exists())
        research.publish(path, {'first': 1})
        original = path.read_bytes()
        with self.assertRaises(FileExistsError):
            research.publish(path, {'different': 2})
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(list(self.root.glob('.partial-*')))

    def test_caught_failure_is_not_completed(self):
        with patch.object(runner, 'simulate', side_effect=RuntimeError('injected')):
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                self.run_fixture()
        self.assertFalse(list(self.root.glob('condition-*.json')))
        self.assertEqual(len(list(self.root.glob('failure-*.json'))), 1)
