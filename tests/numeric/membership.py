#!/usr/bin/env python3
"""Keep frozen predictions, F2 membership and every previous passing row honest."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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
    inside = {r['file'] for r in frozen.values() if r['placement'] == 'F2'}
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
        assert verdicts['identity'] == baseline['identity'], 'oracle identity changed'
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
                print('PASS numeric-membership-rejects-unruled-row')
            else:
                raise AssertionError('membership accepted an unruled row')
        print('PASS numeric-membership original=180 predicted=60 current=' + str(len(selected)) + ' beyond-prediction=' + str(len(selected - original - predicted)))
        return 0
    except AssertionError as exc:
        print('FAIL numeric-membership ' + str(exc), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
