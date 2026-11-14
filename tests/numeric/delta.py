#!/usr/bin/env python3
"""Recompute the row-complete integer delta from sealed measured gate inputs."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    'before_census': 'tests/numeric/baseline-census.json',
    'before_verdicts': 'tests/numeric/baseline.json',
    'after_census': 'tests/numeric/measured-census.json',
    'native': 'tests/numeric/measured-native.json',
    'interpreter': 'tests/numeric/measured-interpreter.json',
    'prediction': 'tests/types/fn08-membership.json',
    'needs': 'tests/types/fn07-needs.json',
}
TABLE = ROOT / 'tests/types/fn08-language-delta.json'
BASE = 'c9b3189dc582b9d14aae2b43254bda07e4da5820'
EXTRA = {'corpus/strings/boundary_battery.lu', 'corpus/strings/chars_walk.lu'}


def indexed(rows):
    result = {r['file']: r for r in rows}
    assert len(result) == len(rows), 'duplicate delta input row'
    return result


def derive(inputs, head, record_digest):
    before, after = inputs['before_census'], inputs['after_census']
    previous, native, interpreter = inputs['before_verdicts'], inputs['native'], inputs['interpreter']
    model, needs = inputs['prediction'], inputs['needs']
    assert before['identity'] == after['identity'], 'census pin changed'
    assert previous['identity'] == native['identity'] == interpreter['identity'], 'execution pin changed'
    assert native == interpreter, 'engine tables disagree'
    old, new = indexed(before['rows']), indexed(after['rows'])
    assert set(old) == set(new) and len(old) == 1353, 'incomplete typing census'
    assert all(old[name]['sha256'] == new[name]['sha256'] for name in old), 'source pin changed'
    prior, measured = indexed(previous['rows']), indexed(native['rows'])
    assert len(prior) == 180 and all(r['verdict'] == 'same' for r in prior.values()), 'incomplete baseline'
    selected = {name for name, row in new.items() if row['cls'] == 'core'}
    assert set(measured) == selected and set(prior) <= selected, 'missing execution row or lost baseline'
    assert all(row['verdict'] == 'same' for row in measured.values()), 'non-parity result'
    assert native['counts'] == dict(same=len(selected), differs=0, **{'fenrir-refuses': 0, 'fenrir-crashes': 0}), 'verdict counts disagree'
    tranche, = [t for t in model['ordered_F2_tranches'] if t['id'] == 'integer']
    predicted = set(tranche['rows'])
    assert len(predicted) == 60 and not predicted & set(prior), 'prediction changed'
    gains = selected - set(prior)
    assert predicted <= gains, 'lost predicted gain'
    assert gains - predicted == EXTRA, 'unexpected unlisted extra gain'
    inside = set(prior) | {row['file'] for row in model['rows'] if row['placement'] == 'F2'}
    assert len(inside) == 290 and selected <= inside, 'later or unruled language entered F2'
    remaining = {t['id']: sorted(set(t['rows']) - selected) for t in model['ordered_F2_tranches']}
    run_names = {row['file'] for row in needs['rows']}
    assert len(run_names) == 813 and selected <= run_names, 'corpus denominator changed'
    typing = [dict(file=name, sha256=new[name]['sha256'],
                   before={k: v for k, v in old[name].items() if k not in ('file', 'sha256')},
                   after={k: v for k, v in new[name].items() if k not in ('file', 'sha256')})
              for name in sorted(old) if old[name] != new[name]]
    execution = [dict(file=name, sha256=new[name]['sha256'], before='unselected', after='same',
                      in_frozen_integer_prediction=name in predicted) for name in sorted(gains)]
    assert re.fullmatch(r'[0-9a-f]{40}', head) and re.fullmatch(r'[0-9a-f]{64}', record_digest), 'invalid measurement provenance'
    return dict(format=1, base=BASE, measurement_head=head, measurement_record_sha256=record_digest,
                identity=native['identity'],
                scope='Complete typing/classification observations and native/interpreter execution gains; candidate-only fixtures are not corpus parity.',
                counts=dict(corpus_files=len(old), run_rows=len(run_names), baseline_same=len(prior),
                            current_same=len(selected), execution_gains=len(gains), predicted_gains=len(predicted),
                            predicted_gains_realized=len(predicted & gains), beyond_prediction=len(gains-predicted),
                            regressions=0, typing_changes=len(typing), unselected_run_rows=len(run_names-selected),
                            confirmed_F2=len(inside), remaining_F2=len(inside-selected)),
                percentage=f'{len(selected)/len(run_names):.2%}', remaining_F2_by_tranche=remaining,
                beyond_frozen_prediction=sorted(gains-predicted),
                extra_gain_reason='Both text rows already had byte/scalar materialization and contextual string get ranges. Byte/char-to-int casts complete their requirements; the frozen integer prediction conservatively left their range labels in the later text group.',
                execution_changes=execution, typing_changes=typing,
                unselected_run_rows=sorted(run_names-selected))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write', action='store_true')
    p.add_argument('--measurement-head')
    p.add_argument('--record-sha256')
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args()
    try:
        inputs = {key: json.loads((ROOT/path).read_text()) for key, path in FILES.items()}
        if args.write:
            assert args.measurement_head and args.record_sha256, 'write requires head and record digest'
            head, digest = args.measurement_head, args.record_sha256
        else:
            saved = json.loads(TABLE.read_text())
            head, digest = saved['measurement_head'], saved['measurement_record_sha256']
        result = derive(inputs, head, digest)
        result['inputs_sha256'] = {key: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for key,path in FILES.items()}
        assert result['inputs_sha256']['before_verdicts'] == inputs['prediction']['inputs_sha256']['tests/lower/core-verdicts.json'], 'frozen baseline digest changed'
        if args.write:
            TABLE.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
        else:
            assert result == saved, 'measured delta is stale'
        if args.self_test:
            broken = copy.deepcopy(inputs)
            broken['native']['rows'].pop()
            broken['interpreter']['rows'].pop()
            try: derive(broken, head, digest)
            except AssertionError: print('PASS numeric-delta-rejects-incomplete-engine')
            else: raise AssertionError('delta accepted an incomplete engine table')
            broken = copy.deepcopy(inputs)
            broken['interpreter']['rows'][0]['verdict'] = 'fenrir-refuses'
            broken['native']['rows'][0]['verdict'] = 'fenrir-refuses'
            try: derive(broken, head, digest)
            except AssertionError: print('PASS numeric-delta-rejects-refusal')
            else: raise AssertionError('delta accepted an interpreter refusal')
        print('PASS numeric-delta '+json.dumps(result['counts'],sort_keys=True)+' percentage='+result['percentage'],flush=True)
        return 0
    except (AssertionError, OSError, KeyError, ValueError) as exc:
        print('FAIL numeric-delta '+str(exc),flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
