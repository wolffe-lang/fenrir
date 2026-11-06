#!/usr/bin/env python3
"""Pattern-analysis counters through `fenrir --emit=analysis` (docs/TYPED.md).

- The record format, in source function order, identical on a second run.
- Growth: five match families at 40, 400 and 4,000 arms. The counters are
  deterministic, so each tenfold step is held to the kernel's 18x ceiling on
  examined cells; a quadratic producer fails by name.
- The budget: an adversarial product match refuses with F0004 and status 4,
  twice identically, never E0801. Linux only, under a 2 GiB address-space
  limit; macOS never drives a cap-exhausting row (docs/COVERAGE.md).
- Headroom: every typed corpus row (census classes core, checked and
  oracle-refused) and every pattern fixture, against both caps. An ordinary
  function within ten times either cap fails; none is exempt.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pattern_rows import ROWS  # noqa: E402

CELLS, BYTES = 1000000, 67108864
RECORD = re.compile(r'^function (\d+) "((?:[^"\\]|\\.)*)" (\d+) (\d+) "(cells|storage|)"$')
ENV = dict(os.environ, WOLF_STD=str(ROOT / '.wolf-bin/std'), WOLF_RT_LIB=str(ROOT / '.wolf-bin/libwolf_rt.a'))


def capped():
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))


def analyse(fenrir, source, limit=False):
    r = subprocess.run([str(fenrir), '--emit=analysis', str(source)], capture_output=True, timeout=90,
                       preexec_fn=capped if limit else None)
    lines = r.stdout.decode().splitlines()
    if not lines or lines[0] != f'analysis/1 "{source}"':
        raise AssertionError(f'bad header {lines[:1]!r} status={r.returncode} {r.stderr[:300]!r}')
    records = []
    for line in lines[1:]:
        m = RECORD.match(line)
        if not m:
            raise AssertionError(f'bad record {line!r}')
        records.append(dict(decl=int(m[1]), name=m[2], cells=int(m[3]), bytes=int(m[4]), cap=m[5]))
    return r.returncode, records, r.stderr.decode(errors='replace'), r.stdout


def write(work, name, text):
    home = work / name
    home.mkdir(parents=True, exist_ok=True)
    path = home / 'row.lu'
    path.write_text(text)
    return path


def family(name, n):
    arms = []
    if name == 'str-literals':
        arms = [f'"k{i}" => {i % 7}' for i in range(n)] + ['_ => 0']
        return f'fn f(v: str) -> int {{ match v {{ {", ".join(arms)} }} }}\nfn main() -> int {{ f("k3") }}\n'
    if name == 'int-literals':
        arms = [f'{i} => {i % 7}' for i in range(n)] + ['_ => 0']
        return f'fn f(v: int) -> int {{ match v {{ {", ".join(arms)} }} }}\nfn main() -> int {{ f(3) }}\n'
    if name == 'int-ranges':
        arms = [f'{10 * i}..{10 * i + 10} => {i % 7}' for i in range(n)] + ['_ => 0']
        return f'fn f(v: int) -> int {{ match v {{ {", ".join(arms)} }} }}\nfn main() -> int {{ f(3) }}\n'
    if name == 'enum-variants':
        variants = ', '.join(f'V{i}' for i in range(n))
        arms = [f'V{i} => {i % 7}' for i in range(n)]
        return f'enum E {{ {variants} }}\nfn f(v: E) -> int {{ match v {{ {", ".join(arms)} }} }}\nfn main() -> int {{ f(E.V1) }}\n'
    if name == 'struct-fields':
        fields = ', '.join(f'f{i}: bool' for i in range(n))
        arms = [f'P {{ f{i}: true, .. }} => {i % 7}' for i in range(n)] + ['_ => 0']
        return f'struct P {{ {fields} }}\nfn f(v: P) -> int {{ match v {{ {", ".join(arms)} }} }}\nfn main() -> int {{ 0 }}\n'
    raise ValueError(name)


def adversarial(pairs):
    # Every `a` field before every `b` field in the first arm: the worst
    # variable order for the pair disjunction that follows.
    names = [f'a{i}' for i in range(pairs)] + [f'b{i}' for i in range(pairs)]
    first = 'P { ' + ', '.join(f'{x}: true' for x in names) + ' } => 0'
    arms = [first] + [f'P {{ a{i}: true, b{i}: true, .. }} => 1' for i in range(pairs)] + ['_ => 2']
    fields = ', '.join(f'{x}: bool' for x in names)
    return f'struct P {{ {fields} }}\nfn f(v: P) -> int {{ match v {{ {", ".join(arms)} }} }}\nfn main() -> int {{ 0 }}\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fenrir', type=Path, default=ROOT / 'target/fenrir')
    ap.add_argument('--work', type=Path, default=ROOT / 'target/analysis')
    a = ap.parse_args()
    fenrir, work = a.fenrir.resolve(), a.work.resolve()
    failures = []

    # The format, the source order, determinism and a match-free function.
    src = write(work, 'format', 'fn f(v: bool) -> int { match v { true => 1, false => 0 } }\n'
                                'fn main() -> int { f(true) }\n')
    status, records, err, out = analyse(fenrir, src)
    again = analyse(fenrir, src)[3]
    names = [r['name'] for r in records]
    if status != 0 or names != ['f', 'main'] or records[1]['cells'] != 0 or records[1]['bytes'] != 512 \
            or records[0]['cells'] <= 0 or records[0]['cap'] or out != again:
        failures.append(f'format status={status} records={records} same={out == again}')
    else:
        print(f'PASS analysis-format f={records[0]["cells"]}/{records[0]["bytes"]} main=0/512 deterministic')

    # Growth: examined cells at N, 10N, 100N.
    for name in ('str-literals', 'int-literals', 'int-ranges', 'enum-variants', 'struct-fields'):
        counts = []
        for n in (40, 400, 4000):
            path = write(work, f'{name}-{n}', family(name, n))
            status, records, err, _ = analyse(fenrir, path)
            f = next((r for r in records if r['name'] == 'f'), None)
            if status != 0 or f is None or f['cap']:
                failures.append(f'growth-{name} n={n} status={status} {err[:300]}')
                break
            counts.append((f['cells'], f['bytes']))
        else:
            ratios = [counts[i + 1][0] / counts[i][0] for i in range(2)]
            line = f'growth-{name} cells={[c for c, _ in counts]} bytes={[b for _, b in counts]} ratios={[round(x, 2) for x in ratios]}'
            if max(ratios) > 18:
                failures.append(line + ' exceeds 18x per tenfold')
            else:
                print('PASS ' + line)

    # The budget refusal, Linux only.
    if sys.platform == 'linux':
        path = write(work, 'adversarial', adversarial(32))
        seen = []
        for _ in range(2):
            r = subprocess.run([str(fenrir), '--emit=typed', str(path)], capture_output=True, timeout=90,
                               preexec_fn=capped)
            seen.append((r.returncode, r.stderr))
        status, records, _, _ = analyse(fenrir, path, limit=True)
        f = next((r for r in records if r['name'] == 'f'), None)
        text = seen[0][1].decode(errors='replace')
        if seen[0] != seen[1] or seen[0][0] != 4 or 'error[F0004]' not in text or 'E0801' in text \
                or status != 4 or f is None or f['cap'] not in ('cells', 'storage'):
            failures.append(f'budget-refusal status={seen[0][0]} same={seen[0] == seen[1]} record={f} {text[:300]}')
        else:
            print(f'PASS budget-refusal F0004 status=4 twice-identical cap={f["cap"]} cells={f["cells"]} bytes={f["bytes"]}')
    else:
        print('INFO budget-refusal runs on Linux only (no address-space limit on this host); the growth rows above ran here')

    # Headroom over the typed corpus rows and the pattern fixtures.
    table = json.loads((ROOT / 'tests/types/census.json').read_text())
    corpus = ROOT / '.wolf-bin/reference'
    sources = [(r['file'], corpus / r['file']) for r in table['rows'] if r['cls'] in ('core', 'checked', 'oracle-refused')]
    for row in ROWS:
        sources.append(('fixture:' + row['name'], write(work, 'fixture-' + row['name'], row['source'])))
    worst = []
    for label, path in sources:
        status, records, err, _ = analyse(fenrir, path)
        if status not in (0, 2, 4):
            failures.append(f'headroom {label} status={status} {err[:200]}')
        for rec in records:
            worst.append((rec['cells'], rec['bytes'], label, rec['name'], rec['cap']))
    top_cells = max(worst)
    top_bytes = max(worst, key=lambda w: (w[1], w[0]))
    print(f'INFO headroom {len(sources)} sources, {len(worst)} functions; largest cells {top_cells[0]} '
          f'({100 * top_cells[0] / CELLS:.3f}% of {CELLS}) in {top_cells[2]} `{top_cells[3]}`; largest storage '
          f'{top_bytes[1]} ({100 * top_bytes[1] / BYTES:.3f}% of {BYTES}) in {top_bytes[2]} `{top_bytes[3]}`')
    near = [w for w in worst if w[0] * 10 > CELLS or w[1] * 10 > BYTES or w[4]]
    for w in near:
        failures.append(f'headroom {w[2]} `{w[3]}` within ten times a cap: cells={w[0]} bytes={w[1]} cap={w[4]!r}')
    if not near:
        print('PASS headroom no ordinary function within ten times either cap')

    for f in failures:
        print('FAIL ' + f)
    print(f'analysis: {len(failures)} failures')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
