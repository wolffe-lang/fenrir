#!/usr/bin/env python3
"""Recompute the row-complete delta of the text, aggregate, attributes and control
tranches from sealed measured inputs, and check it against the committed table.

  fn09_delta.py [--self-test]
  fn09_delta.py --write --measurement-head SHA --record-sha256 DIGEST

The before inputs are the census and core verdict table at the base (the 0.2.40
pin move); the after inputs are the census and both engines' verdict tables
measured at the measurement head. Every frozen row of the four tranches must be
`same` on both engines, no row that was `same` may be lost, and no row outside
the frozen F2 membership may enter the core. Typing changes are listed row by
row. The sealed inputs, not the live tables, are the record, so later work on
the live census does not reopen this delta.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    'before_census': 'tests/types/fn09-baseline-census.json',
    'before_verdicts': 'tests/types/fn09-baseline-verdicts.json',
    'after_census': 'tests/types/fn09-measured-census.json',
    'native': 'tests/types/fn09-measured-native.json',
    'interpreter': 'tests/types/fn09-measured-interpreter.json',
    'membership': 'tests/types/fn08-membership.json',
    'oracle': 'tests/oracle.json',
}
TABLE = ROOT / 'tests/types/fn09-language-delta.json'
BASE = 'f49816523f9c610031cc5ef701a886803220a64f'
TRANCHES = ('text', 'aggregate', 'attributes', 'control')
# One delta's sealed inputs, its frozen tranches and their sizes; a later delta passes its own.
SPEC = dict(label='fn09-delta', files=FILES, table=TABLE, base=BASE, tranches=TRANCHES, baseline=242, frozen=35,
            predicted=33, scope='Complete typing/classification observations and native/interpreter execution gains of the four frozen tranches.')


def indexed(rows):
    result = {r['file']: r for r in rows}
    assert len(result) == len(rows), 'duplicate delta input row'
    return result


def derive(inputs, head, record_digest, spec=SPEC):
    TRANCHES, BASE = spec['tranches'], spec['base']
    before, after = inputs['before_census'], inputs['after_census']
    previous, native, interpreter = inputs['before_verdicts'], inputs['native'], inputs['interpreter']
    model, oracle = inputs['membership'], inputs['oracle']
    assert before['identity'] == after['identity'], 'census pin changed'
    assert previous['identity'] == native['identity'] == interpreter['identity'], 'execution pin changed'
    assert native == interpreter, 'engine tables disagree'
    old, new = indexed(before['rows']), indexed(after['rows'])
    assert set(old) == set(new) and len(old) == 1354, 'incomplete typing census'
    assert all(old[name]['sha256'] == new[name]['sha256'] for name in old), 'source pin changed'
    prior, measured = indexed(previous['rows']), indexed(native['rows'])
    assert len(prior) == spec['baseline'] and all(r['verdict'] == 'same' for r in prior.values()), 'incomplete baseline'
    selected = {name for name, row in new.items() if row['cls'] == 'core'}
    assert set(measured) == selected and set(prior) <= selected, 'missing execution row or lost baseline'
    assert all(row['verdict'] == 'same' for row in measured.values()), 'non-parity result'
    assert native['counts'] == dict(same=len(selected), differs=0, **{'fenrir-refuses': 0, 'fenrir-crashes': 0}), 'verdict counts disagree'
    tranches = {t['id']: set(t['rows']) for t in model['ordered_F2_tranches']}
    frozen = set().union(*(tranches[name] for name in TRANCHES))
    predicted = frozen - set(prior)
    assert len(frozen) == spec['frozen'] and len(predicted) == spec['predicted'], 'tranche membership changed'
    gains = selected - set(prior)
    assert gains == predicted, 'gains differ from the frozen tranches: ' + str(sorted(gains ^ predicted))
    run_names = {row['file'] for row in oracle['rows'] if str(row.get('expected', '')).startswith('run(')}
    assert len(run_names) == 814 and selected <= run_names, 'corpus denominator changed'
    remaining = {t['id']: sorted(set(t['rows']) - selected) for t in model['ordered_F2_tranches']}
    assert all(not remaining[name] for name in TRANCHES), 'a frozen tranche row is not core'
    typing = [dict(file=name, sha256=new[name]['sha256'],
                   before={k: v for k, v in old[name].items() if k not in ('file', 'sha256')},
                   after={k: v for k, v in new[name].items() if k not in ('file', 'sha256')})
              for name in sorted(old) if old[name] != new[name]]
    by_tranche = {name: sorted(tranches[name] - set(prior)) for name in TRANCHES}
    execution = [dict(file=name, sha256=new[name]['sha256'], before='unselected', after='same',
                      tranche=next(t for t in TRANCHES if name in tranches[t])) for name in sorted(gains)]
    assert re.fullmatch(r'[0-9a-f]{40}', head) and re.fullmatch(r'[0-9a-f]{64}', record_digest), 'invalid measurement provenance'
    return dict(format=1, base=BASE, measurement_head=head, measurement_record_sha256=record_digest,
                identity=native['identity'],
                scope=spec['scope'],
                counts=dict(corpus_files=len(old), run_rows=len(run_names), baseline_same=len(prior),
                            current_same=len(selected), execution_gains=len(gains), predicted_gains=len(predicted),
                            predicted_gains_realized=len(predicted & gains), regressions=0,
                            typing_changes=len(typing), unselected_run_rows=len(run_names - selected),
                            gains_by_tranche={name: len(rows) for name, rows in by_tranche.items()}),
                percentage=f'{len(selected) / len(run_names):.2%}', remaining_F2_by_tranche=remaining,
                gains_by_tranche=by_tranche, execution_changes=execution, typing_changes=typing)


def unfrozen_gain(inputs):
    """Damage for the self-test: a run row outside every frozen tranche turns core and `same` on both
    engines, so only the frozen-gain check can catch it."""
    frozen = set().union(*(set(t['rows']) for t in inputs['membership']['ordered_F2_tranches']))
    runs = {r['file']: r for r in inputs['oracle']['rows'] if str(r.get('expected', '')).startswith('run(')}
    row = next(r for r in inputs['after_census']['rows'] if r['cls'] != 'core' and r['file'] in runs and r['file'] not in frozen)
    row['cls'] = 'core'
    for engine in ('native', 'interpreter'):
        table = inputs[engine]
        table['rows'] = sorted(table['rows'] + [dict(expected=runs[row['file']]['expected'], file=row['file'], verdict='same')],
                               key=lambda r: r['file'])
        table['counts']['same'] += 1


def main(spec=SPEC, doc=__doc__):
    FILES, TABLE, label = spec['files'], spec['table'], spec['label']
    p = argparse.ArgumentParser(description=doc)
    p.add_argument('--write', action='store_true')
    p.add_argument('--measurement-head')
    p.add_argument('--record-sha256')
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args()
    try:
        inputs = {key: json.loads((ROOT / path).read_text()) for key, path in FILES.items()}
        if args.write:
            assert args.measurement_head and args.record_sha256, 'write requires head and record digest'
            head, digest = args.measurement_head, args.record_sha256
        else:
            saved = json.loads(TABLE.read_text())
            head, digest = saved['measurement_head'], saved['measurement_record_sha256']
        result = derive(inputs, head, digest, spec)
        result['inputs_sha256'] = {key: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for key, path in FILES.items()}
        if args.write:
            TABLE.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        else:
            assert result == saved, 'measured delta is stale'
        if args.self_test:
            for damage_label, damage in (
                    ('incomplete-engine', lambda b: (b['native']['rows'].pop(), b['interpreter']['rows'].pop())),
                    ('refusal', lambda b: [r.__setitem__('verdict', 'fenrir-refuses') for r in (b['native']['rows'][0], b['interpreter']['rows'][0])]),
                    ('lost-baseline', lambda b: b['after_census']['rows'][[r['file'] for r in b['after_census']['rows']].index(b['before_verdicts']['rows'][0]['file'])].__setitem__('cls', 'out-of-core')),
                    ('unfrozen-gain', unfrozen_gain)):
                broken = copy.deepcopy(inputs)
                damage(broken)
                try:
                    derive(broken, head, digest, spec)
                except AssertionError:
                    print(f'PASS {label}-rejects-{damage_label}', flush=True)
                else:
                    raise AssertionError('delta accepted ' + damage_label)
        print(f'PASS {label} ' + json.dumps(result['counts'], sort_keys=True) + ' percentage=' + result['percentage'], flush=True)
        return 0
    except (AssertionError, OSError, KeyError, ValueError) as exc:
        print(f'FAIL {label} ' + str(exc), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
