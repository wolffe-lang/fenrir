#!/usr/bin/env python3
"""Pin the measured tier disagreement without awarding Map output parity."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('map_refusals',HERE/'map_refusals.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
ROWS=json.loads((HERE/'map-tier-observations.json').read_text())['rows']


class MapTierObservations(unittest.TestCase):
    def matches(self,row):
        return module.reference_matches(row['name'],row['tier'],row['record'],row['tool_exit'],row['site'])

    def test_all_twelve_measured_answers_are_pinned(self):
        self.assertEqual(len(ROWS),12)
        for row in ROWS:
            with self.subTest(name=row['name'],tier=row['tier']):
                self.assertTrue(self.matches(row))

    def test_tool_failure_or_protocol_drift_is_not_a_tier_answer(self):
        for row in ROWS:
            for field,value in [('tool_exit',2),('protocol',2),('impl_version','unrecorded')]:
                bad=copy.deepcopy(row)
                if field=='tool_exit':bad[field]=value
                else:bad['record'][field]=value
                with self.subTest(name=row['name'],tier=row['tier'],field=field):
                    self.assertFalse(self.matches(bad))

    def test_refusal_phase_reason_span_and_outer_site_are_exact(self):
        for row in ROWS:
            if row['record']['verdict']!='unsupported':continue
            for field,value in [('phase_reached','run'),('x-unsupported-construct','another refusal'),
                                ('x-unsupported-span',[0,1]),('x-unsupported-line',1),('x-unsupported-col',1)]:
                bad=copy.deepcopy(row);bad['record'][field]=value
                with self.subTest(name=row['name'],tier=row['tier'],field=field):
                    self.assertFalse(self.matches(bad))

    def test_rendered_bytes_hash_status_and_diagnostics_are_exact(self):
        for row in ROWS:
            if row['record']['verdict']!='exit(0)':continue
            for field,value in [('stdout_inline','wrong\n'),('stdout_sha256','0'*64),('verdict','exit(1)'),
                                ('diagnostics',[{'code':'E0401','severity':'error','span':[0,1]}]),
                                ('warnings',[{'code':'W0001'}])]:
                bad=copy.deepcopy(row);bad['record'][field]=value
                with self.subTest(name=row['name'],tier=row['tier'],field=field):
                    self.assertFalse(self.matches(bad))


if __name__=='__main__':unittest.main()
