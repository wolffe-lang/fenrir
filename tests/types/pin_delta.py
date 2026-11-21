#!/usr/bin/env python3
"""Derive a pin-only ledger (fn07-pin-delta.json's shape) from the tables before and after a pin move.

  pin_delta.py --old-oracle OLD --old-census OLD --old-verdicts OLD --head SHA --reasons REASONS.json \
               --placements PLACEMENTS.json --output tests/types/fn09-pin-delta.json

The new tables are the committed ones (tests/oracle.json, tests/types/census.json,
tests/lower/core-verdicts.json). Every changed native observation needs a reason, either the
unstable-row reason (both captures disagree on it already) or an entry in REASONS; a missing reason
stops the derivation rather than writing a ledger that hides a change. Linear in the rows.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ('stdout', 'stdout_sha256', 'trap_kind', 'trap_message', 'trap_site', 'verdict')
UNSTABLE = 'Both capture sets identify this race/UB row as unstable; this observed change is not attributed to the pin.'


def native(row):
    obs = row.get('native_run') or row.get('wolf') or {}
    return {k: obs.get(k) for k in FIELDS} if obs else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('old-oracle', 'old-census', 'old-verdicts', 'reasons', 'placements', 'output'):
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--head', required=True)
    a = ap.parse_args()
    load = lambda p: json.loads(Path(p).read_text())
    old_o, new_o = load(a.old_oracle), load(ROOT / 'tests/oracle.json')
    old_c, new_c = load(a.old_census), load(ROOT / 'tests/types/census.json')
    old_v, new_v = load(a.old_verdicts), load(ROOT / 'tests/lower/core-verdicts.json')
    reasons, placements = load(a.reasons), load(a.placements)
    oi, ni = {r['file']: r for r in old_o['rows']}, {r['file']: r for r in new_o['rows']}
    unstable = set(old_o.get('repeat_changes', [])) | set(new_o.get('repeat_changes', []))
    changes, relation_changes, missing = [], [], []
    for name in sorted(set(oi) & set(ni)):
        o, n = oi[name], ni[name]
        if o['relation'] != n['relation']:
            relation_changes.append(dict(file=name, old=o['relation'], new=n['relation']))
        if native(o) != native(n):
            reason = UNSTABLE if name in unstable else reasons.get(name)
            if reason is None:
                missing.append(name)
            changes.append(dict(file=name, old=native(o), new=native(n), reason=reason,
                                source_changed=o['sha256'] != n['sha256'], unstable=name in unstable))
    if missing:
        raise SystemExit('pin-delta: changed native observation without a reason: ' + ', '.join(missing))
    oc, nc = {r['file']: r for r in old_c['rows']}, {r['file']: r for r in new_c['rows']}
    added = sorted(set(nc) - set(oc))
    assert set(placements) == set(added), 'every added source needs a placement, and only those'
    old_core = {f for f, r in oc.items() if r['cls'] == 'core'}
    new_core = {f for f, r in nc.items() if r['cls'] == 'core'}
    old_same = {r['file'] for r in old_v['rows'] if r['verdict'] == 'same'}
    new_same = {r['file'] for r in new_v['rows'] if r['verdict'] == 'same'}
    data = dict(
        format=1, scope='pin-only observations; no language implementation change', head=a.head,
        old_reference=old_v['identity'], new_reference=new_v['identity'],
        old_rows=len(oi), new_rows_total=len(ni),
        new_rows=[dict(file=f, cls=nc[f]['cls'], expected=ni[f].get('expected'), native=native(ni[f]),
                       relation=ni[f]['relation'], placement=placements[f]['milestone'], rule=placements[f]['rule'])
                  for f in added],
        removed_rows=sorted(set(oc) - set(nc)),
        relation_changes=relation_changes, native_changes=changes,
        census_class_changes=[dict(file=f, old=oc[f]['cls'], new=nc[f]['cls'])
                              for f in sorted(set(oc) & set(nc)) if oc[f]['cls'] != nc[f]['cls']],
        census_counts=dict(old=old_c['counts'], new=new_c['counts']),
        core_added=sorted(new_core - old_core), core_removed=sorted(old_core - new_core),
        same_added=sorted(new_same - old_same), same_lost=sorted(old_same - new_same),
        candidate_counts=new_v['counts'])
    a.output.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    print('pin-delta: ' + json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in data.items()
                                      if k in ('new_rows', 'removed_rows', 'relation_changes', 'native_changes',
                                               'census_class_changes', 'core_added', 'core_removed',
                                               'same_added', 'same_lost')}, sort_keys=True))


if __name__ == '__main__':
    main()
