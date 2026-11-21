"""Frozen-plan checks using hand-built analysis fixtures."""

from fractions import Fraction as F
import random
import unittest

import phase3_primary_analysis as analysis


class PrimaryAnalysisTests(unittest.TestCase):
    def test_paired_signs_exact_tie_and_undefined_denominator(self):
        delta, ratios = analysis.paired(('a', (F(4), F(4), F(0))), ('a', (F(3), F(4), F(1))))
        self.assertEqual(delta, (F(-1), F(0), F(1)))
        self.assertEqual(ratios, (F(-1, 4), F(0), None))
        self.assertEqual(analysis.tally(delta), (1, 1, 1))
        self.assertIsNone(analysis.paired(('a', (F(0),)), ('a', (F(0),)))[1][0])
        with self.assertRaisesRegex(ValueError, 'workload hashes'):
            analysis.paired(('a', (F(4),)), ('b', (F(4),)))

    def test_exact_latency_mean_and_nearest_rank(self):
        result = {'requests': [{'latency_ticks': i} for i in range(1, 21)],
                  'metrics': {'makespan': 23}}
        self.assertEqual(analysis.outcomes(result), (F(21, 2), F(19), F(23)))
        self.assertEqual(analysis.nearest_p95(list(range(19))), 18)
        with self.assertRaisesRegex(ValueError, 'empty'):
            analysis.nearest_p95([])

    def test_shared_rng_matches_stdlib_row_major(self):
        rng = random.Random(20261118)
        expected = [[rng.randrange(20) for _ in range(20)] for _ in range(10)]
        self.assertEqual(analysis.draw_indices(20, 10), expected)
        self.assertEqual(analysis.draw_indices(20, 10), expected)

    def test_intervals_and_undefined_draws(self):
        weights = analysis.weight_matrix([[0, 0], [0, 1], [1, 1]], 2)
        result = analysis.intervals([[F(0), F(20)], [F(4), None], [None, None]], weights)
        self.assertEqual(result[0], (0.5, 19.5, 0))
        self.assertEqual(result[1], (4.0, 4.0, 1))
        self.assertEqual(result[2], (None, None, 3))
        self.assertEqual(analysis.linear_quantile([0, 10, 20], F(1, 40)), F(1, 2))

    def test_seed_weighting_and_no_request_pseudoreplication(self):
        axis = ('short', 'prompt-heavy', 'dense')
        records = {}
        for i, seed in enumerate(analysis.SEEDS):
            for allocator in analysis.ALLOCATORS:
                ticks = [5] * (100 if i == 0 else 1)
                if i == 0 and allocator != 'fixed':
                    ticks = [25] * 100
                row = {'requests': [{'latency_ticks': t} for t in ticks], 'metrics': {'makespan': 25}}
                records[(*axis, seed, 2048, None, allocator)] = (str(seed), analysis.outcomes(row))
        _, absolute, _, pairs = analysis.contrast_vectors(records, [axis], [2048], [None])
        self.assertEqual(len(pairs), 20 * 3)
        self.assertEqual(analysis.describe(absolute[0])[0], F(1))
        del records[(*axis, analysis.SEEDS[-1], 2048, None, 'paged8')]
        with self.assertRaisesRegex(ValueError, 'missing paired condition'):
            analysis.contrast_vectors(records, [axis], [2048], [None])

    def test_inventory_rejects_missing_duplicate_and_incompatible_rows(self):
        first = {'run_id': 'a', 'config': {'budget': 2048}}
        second = {'run_id': 'b', 'config': {'budget': 4096}}
        expected = [first, second]
        filenames = {'condition-a.json', 'condition-b.json'}
        analysis.validate_inventory(expected, expected, filenames)
        with self.assertRaisesRegex(ValueError, 'artifact'):
            analysis.validate_inventory(expected, expected, {'condition-a.json'})
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            analysis.validate_inventory([first, first], [first, first], filenames)
        incompatible = {'run_id': 'b', 'config': {'budget': 8192}}
        with self.assertRaisesRegex(ValueError, 'noncanonical'):
            analysis.validate_inventory([first, incompatible], expected, filenames)


if __name__ == '__main__':
    unittest.main()
