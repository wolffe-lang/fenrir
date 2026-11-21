#!/usr/bin/env python3
"""Keep frozen predictions, F2 membership and every previous passing row honest."""
import argparse
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def resolve_placements(model, placements):
    """Linear in the frozen rows and the resolution table; no baseline moves."""
    pending = {r['file'] for r in model['rows'] if r['placement'] == 'placement-needs-ruling'}
    changes = {r['file']: r for r in placements['placements']}
    assert len(changes) == len(placements['placements']) and set(changes) == pending, 'incomplete or duplicate placement resolution'
    assert all(r['milestone'] in ('F3', 'F4', 'F7') and r.get('rule') for r in changes.values()), 'placement imported a later feature into F2'
    effective = {r['file']: changes[r['file']]['milestone'] if r['file'] in pending else r['placement'] for r in model['rows']}
    assert dict(Counter(effective.values())) == placements['effective_remainder_counts'], 'resolved placement counts disagree'
    return effective


def recorded_move(start, target, ledgers=None):
    """Follow the committed pin ledgers from the frozen baseline's identity to the live table's.

    Each ledger records one pin move (`old_reference` to `new_reference`); a step may lose no core
    row and no `same` row. Linear in the ledgers; an identity no ledger reaches is a red.
    """
    if ledgers is None:
        ledgers = [json.loads(p.read_text()) for p in sorted((ROOT / 'tests/types').glob('fn*-pin-delta.json'))]
    by_old = {}
    for ledger in ledgers:
        key = json.dumps(ledger['old_reference'], sort_keys=True)
        assert key not in by_old, 'two pin ledgers leave one identity'
        by_old[key] = ledger
    seen, here = set(), start
    while here != target:
        key = json.dumps(here, sort_keys=True)
        assert key not in seen and key in by_old, 'oracle identity changed without a recorded pin move'
        seen.add(key)
        step = by_old[key]
        assert not step['same_lost'] and not step['core_removed'], 'a recorded pin move lost a row'
        here = step['new_reference']
    return len(seen)


def validate(census, verdicts=None):
    model = json.loads((ROOT / 'tests/types/fn08-membership.json').read_text())
    baseline_path = ROOT / 'tests/numeric/baseline.json'
    assert hashlib.sha256(baseline_path.read_bytes()).hexdigest() == model['inputs_sha256']['tests/lower/core-verdicts.json'], 'frozen baseline digest changed'
    baseline = json.loads(baseline_path.read_text())
    original = {r['file'] for r in baseline['rows'] if r['verdict'] == 'same'}
    assert len(original) == 180 and len(baseline['rows']) == 180, 'incomplete original baseline'
    frozen = {r['file']: r for r in model['rows']}
    assert len(frozen) == len(model['rows']) == 223, 'incomplete former ceiling remainder'
    assert sum(model['placement_counts'].values()) == 223, 'membership counts changed'
    assert {bucket: sum(r['placement'] == bucket for r in frozen.values()) for bucket in model['placement_counts']} == model['placement_counts'], 'membership partition does not match rows'
    placements = json.loads((ROOT / 'tests/types/fn08-membership-placements.json').read_text())
    effective = resolve_placements(model, placements)
    inside = {name for name, milestone in effective.items() if milestone == 'F2'}
    assert len(original | inside) == model['corrected_F2']['confirmed_members'] == 290, 'confirmed membership changed'
    tranche, = [t for t in model['ordered_F2_tranches'] if t['id'] == 'integer']
    predicted = set(tranche['rows'])
    assert len(predicted) == len(tranche['rows']) == tranche['additional_same_predicted'] == 60, 'integer prediction changed'
    current = {r['file']: r for r in census['rows']}
    assert len(current) == len(census['rows']), 'duplicate census row'
    selected = {name for name, row in current.items() if row['cls'] == 'core'}
    assert original <= selected, 'lost original core row: ' + str(sorted(original - selected))
    assert predicted <= selected, 'missing frozen integer row: ' + str(sorted(predicted - selected))
    assert selected <= original | inside, 'unruled or later-milestone row entered F2: ' + str(sorted(selected - original - inside))
    for name in selected - original:
        assert current[name]['sha256'] == frozen[name]['sha256'], 'changed frozen corpus source: ' + name
    if verdicts is not None:
        observed = {r['file']: r for r in verdicts['rows']}
        assert len(observed) == len(verdicts['rows']) and set(observed) == selected, 'incomplete execution selection'
        recorded_move(baseline['identity'], verdicts['identity'])
        bad = [name for name, row in observed.items() if row['verdict'] != 'same']
        assert not bad, 'non-parity execution rows: ' + str(sorted(bad))
        assert verdicts['counts']['same'] == len(selected), 'execution count disagrees'
    return selected, original, predicted


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--census', type=Path, default=ROOT / 'tests/types/census.json')
    p.add_argument('--verdicts', type=Path)
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args()
    census = json.loads(args.census.read_text())
    verdicts = json.loads(args.verdicts.read_text()) if args.verdicts else None
    try:
        selected, original, predicted = validate(census, verdicts)
        if args.self_test:
            model = json.loads((ROOT / 'tests/types/fn08-membership.json').read_text())
            placements = json.loads((ROOT / 'tests/types/fn08-membership-placements.json').read_text())
            for label in ('missing-resolution', 'F2-smuggling'):
                broken = copy.deepcopy(placements)
                if label == 'missing-resolution': broken['placements'].pop()
                else: broken['placements'][0]['milestone'] = 'F2'
                try: resolve_placements(model, broken)
                except AssertionError: print('PASS numeric-membership-rejects-' + label)
                else: raise AssertionError('membership accepted ' + label)
            for label, name in [('original', sorted(original)[0]), ('predicted', sorted(predicted)[0])]:
                broken = copy.deepcopy(census)
                next(r for r in broken['rows'] if r['file'] == name)['cls'] = 'out-of-core'
                try:
                    validate(broken)
                except AssertionError:
                    print('PASS numeric-membership-rejects-lost-' + label)
                else:
                    raise AssertionError('membership accepted a lost ' + label + ' row')
            broken = copy.deepcopy(census)
            pending = next(r['file'] for r in json.loads((ROOT / 'tests/types/fn08-membership.json').read_text())['rows'] if r['placement'] == 'placement-needs-ruling')
            next(r for r in broken['rows'] if r['file'] == pending)['cls'] = 'core'
            try:
                validate(broken)
            except AssertionError:
                print('PASS numeric-membership-rejects-later-row')
            else:
                raise AssertionError('membership accepted a later-milestone row')
            if verdicts is not None and verdicts['identity'] != json.loads((ROOT / 'tests/numeric/baseline.json').read_text())['identity']:
                ledgers = [json.loads(p.read_text()) for p in sorted((ROOT / 'tests/types').glob('fn*-pin-delta.json'))]
                for label in ('unrecorded-pin-move', 'pin-move-losing-a-row'):
                    broken = copy.deepcopy(ledgers)
                    last = next(l for l in broken if l['new_reference'] == verdicts['identity'])
                    if label == 'unrecorded-pin-move':
                        digest = last['new_reference']['oracle_pins_sha256']
                        last['new_reference'] = dict(last['new_reference'], oracle_pins_sha256=('0' if digest[0] != '0' else '1') + digest[1:])
                    else:
                        last['same_lost'] = [sorted(original)[0]]
                    try:
                        recorded_move(json.loads((ROOT / 'tests/numeric/baseline.json').read_text())['identity'], verdicts['identity'], broken)
                    except AssertionError:
                        print('PASS numeric-membership-rejects-' + label)
                    else:
                        raise AssertionError('membership accepted an ' + label)
        print('PASS numeric-membership original=180 predicted=60 current=' + str(len(selected)) + ' beyond-prediction=' + str(len(selected - original - predicted)))
        return 0
    except AssertionError as exc:
        print('FAIL numeric-membership ' + str(exc), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
