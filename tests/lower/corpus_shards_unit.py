#!/usr/bin/env python3
"""The corpus differential's shards: each core row in exactly one shard, and a shard's
table checked row by row against the committed table. Runs anywhere; no compiler."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('corpus_differential', ROOT / 'tests/lower/corpus.py')
corpus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus)
CENSUS = ROOT / 'tests/types/census.json'
TABLE = ROOT / 'tests/lower/core-verdicts.json'


def core():
    return sorted(r['file'] for r in json.loads(CENSUS.read_text())['rows'] if r['cls'] == 'core')


class Shards(unittest.TestCase):
    def test_shards_partition_the_live_core(self):
        names = core()
        for count in (1, 2, 3, 4):
            with self.subTest(count=count):
                shards = [corpus.shard_rows(CENSUS, k, count) for k in range(1, count + 1)]
                flat = [n for s in shards for n in s]
                self.assertEqual(sorted(flat), names)
                self.assertEqual(len(flat), len(set(flat)))
                self.assertLessEqual(max(map(len, shards)) - min(map(len, shards)), 1)

    def test_the_committed_core_splits_97_97_96(self):
        self.assertEqual([len(corpus.shard_rows(CENSUS, k, 3)) for k in (1, 2, 3)], [97, 97, 96])

    def test_a_shard_spec_names_one_of_its_shards(self):
        self.assertEqual(corpus.parse_shard('2/3'), (2, 3))
        for bad in ('0/3', '4/3', '1/0', '3', 'a/b', '-1/2'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                corpus.parse_shard(bad)

    def test_a_shard_table_is_checked_row_by_row(self):
        expected = json.loads(TABLE.read_text())
        names = corpus.shard_rows(CENSUS, 2, 3)
        rows = [r for r in expected['rows'] if r['file'] in set(names)]
        table = dict(expected, rows=rows)
        self.assertEqual(corpus.shard_problems(table, expected, names), [])
        changed = copy.deepcopy(table)
        changed['rows'][3]['verdict'] = 'differs'
        self.assertEqual(corpus.shard_problems(changed, expected, names),
                         [f'{rows[3]["file"]} differs from the committed row'])
        missing = dict(table, rows=rows[1:])
        self.assertEqual(corpus.shard_problems(missing, expected, names), [f'{rows[0]["file"]} missing from the shard table'])
        extra = dict(table, rows=rows + [r for r in expected['rows'] if r['file'] not in set(names)][:1])
        self.assertEqual(len(corpus.shard_problems(extra, expected, names)), 1)
        self.assertIn('outside the shard', corpus.shard_problems(extra, expected, names)[0])
        other = copy.deepcopy(table)
        other['identity']['reference_rev'] = '0' * 40
        self.assertEqual(corpus.shard_problems(other, expected, names), ['identity differs from the committed table'])


if __name__ == '__main__':
    unittest.main()
