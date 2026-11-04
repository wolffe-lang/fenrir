"""Corpus enumeration, black-box observations and differential verdicts."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

PHASES = {'none', 'lex', 'parse', 'resolve', 'typecheck', 'mem', 'wir', 'run'}
TRAP = re.compile(r'^wolf-trap: ([a-z-]+)$', re.M)
SITE = re.compile(r'^  at (.+):(\d+):(\d+)$', re.M)


def directives(path):
    result = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        if not line.startswith('//!'):
            break
        match = re.match(r'//!\s*([a-z.]+):\s*(.*)', line)
        if match:
            key, value = match.groups()
            if key in result:
                raise ValueError(f'duplicate directive: {path.name}: {key}')
            result[key] = value
    if result.get('member') == 'true' and ('check' in result or 'phase' in result):
        raise ValueError('member carries entry directives')
    if 'phase' in result and result['phase'] not in PHASES:
        raise ValueError('unknown corpus phase')
    return result


def corpus_rows(root):
    rows = []
    for source in sorted(root.rglob('*.lu')):
        header = directives(source)
        member = header.get('member') == 'true' or (header.get('member') != 'false' and not ('check' in header and 'phase' in header))
        rows.append({'file': source.relative_to(root.parent).as_posix(),
                     'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                     'directives': header, 'member': member,
                     'expected': header.get('check'), 'phase': header.get('phase')})
    return rows


def normalize(text, roots):
    for root, label in roots:
        text = text.replace(str(root), label)
    return text


def descendants(pid):
    """Snapshot only descendants of a process started by this harness."""
    children = {}
    for status in Path('/proc').glob('[0-9]*/status'):
        try:
            text = status.read_text()
            parent = int(re.search(r'^PPid:\s*(\d+)', text, re.M).group(1))
            children.setdefault(parent, []).append(int(status.parent.name))
        except (OSError, AttributeError):
            pass
    found = []
    todo = [pid]
    while todo:
        current = todo.pop()
        found.append(current)
        todo.extend(children.get(current, []))
    return found


def execute(args, cwd, env, timeout):
    # The containing Linux job supplies cgroup memory and CPU limits. Per-child AS cap
    # is inherited by compiler/linker/program descendants, without preexec_fn in threads.
    proc = subprocess.Popen(['prlimit', '--as=3221225472', '--', *map(str, args)], cwd=cwd,
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err, False
    except subprocess.TimeoutExpired:
        # Never signal a group. Kill recorded descendants by individual pid, leaf first.
        for pid in reversed(descendants(proc.pid)):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        out, err = proc.communicate()
        return proc.returncode, out, err, True


def stream_fields(out):
    return {'stdout': out.decode('utf-8', errors='replace'),
            'stdout_base64': base64.b64encode(out).decode(),
            'stdout_sha256': hashlib.sha256(out).hexdigest()}


def native_observation(result, source, roots):
    code, out, err, timedout = result
    stderr = normalize(err.decode('utf-8', errors='replace'), roots)
    kind = TRAP.search(stderr)
    site = SITE.search(stderr)
    diagnostic = re.search(r'\b(?:error\[|error\s+|\[)([EIF][0-9]{4})\]?', stderr)
    if timedout:
        verdict = 'timeout'
    elif kind:
        verdict = f'trap({kind.group(1)})'
    elif code < 0:
        verdict = 'crash'
    elif diagnostic:
        verdict = f'fail({diagnostic.group(1)})'
    elif code == 4 and ('unsupported' in stderr.lower() or 'not supported' in stderr.lower()):
        verdict = 'unsupported'
    elif code == 2 and stderr:
        verdict = 'tool-error'
    else:
        verdict = f'exit({code})'
    return dict(stream_fields(out), verdict=verdict, exit=code, stderr=stderr,
                trap_kind=kind.group(1) if kind else None,
                trap_site={'file': site.group(1), 'line': int(site.group(2)), 'column': int(site.group(3))} if site else None,
                trap_message=None)


def lupin_observation(result, source, roots):
    code, out, err, timedout = result
    stderr = normalize(err.decode('utf-8', errors='replace'), roots)
    if code or timedout:
        return dict(verdict='timeout' if timedout else 'tool-error', exit=code,
                    stdout=None, stdout_sha256=None, trap_kind=None, trap_site=None,
                    trap_message=None, stderr=stderr)
    record = json.loads(out)
    required = {'protocol', 'impl', 'impl_version', 'commit', 'file', 'phase_reached', 'seeded', 'diagnostics', 'verdict'}
    if not required <= record.keys() or record['protocol'] != 1:
        raise ValueError('malformed lupin observation record')
    verdict = record['verdict']
    match = re.fullmatch(r'exit\((\d+)\)', verdict)
    trap = re.fullmatch(r'trap\(([a-z-]+)\)', verdict)
    observation = dict(verdict=verdict, exit=int(match.group(1)) if match else None,
                       stdout=record.get('stdout_inline'), stdout_sha256=record.get('stdout_sha256'),
                       trap_kind=trap.group(1) if trap else None,
                       trap_site=record.get('x-trap-span'), trap_message=record.get('trap_message'),
                       stderr=stderr, record=json.loads(normalize(json.dumps(record), roots)))
    # An exiting protocol record with no output hash denotes no output: the
    # protocol requires a hash whenever an exiting program writes bytes. Traps
    # retain honest-absent metadata under the protocol's separate rule.
    if match and observation['stdout_sha256'] is None:
        observation['stdout'] = ''
        observation['stdout_sha256'] = hashlib.sha256(b'').hexdigest()
    return observation


def observe_native(wolf, source, cwd, env, timeout, roots, runner=execute):
    # Pinned 0.2.36's `run` is native by default and rejects --native. Keep
    # the exact argv in the observation so command drift can be audited.
    args = [wolf, 'run', source]
    observed = native_observation(runner(args, cwd, env, timeout), source, roots)
    observed['argv'] = [normalize(str(arg), roots) for arg in args]
    if observed['exit'] in (2, 4) and observed['trap_kind'] is None:
        classified = lupin_observation(runner([wolf, 'conform-run', source, '--native', '--json'], cwd, env, timeout), source, roots)
        verdict = classified['verdict']
        expected_exit = 2 if verdict.startswith('fail(') else (4 if verdict == 'unsupported' else None)
        match = re.fullmatch(r'exit\((\d+)\)', verdict)
        if match:
            expected_exit = int(match.group(1))
        observed['classification_record'] = classified.get('record')
        if expected_exit == observed['exit'] and 'unknown flag' not in observed['stderr']:
            observed['verdict'] = verdict
        else:
            observed['verdict'] = 'tool-error'
            observed['classification_error'] = 'native invocation did not produce the outcome of its classification record'
    return observed


def oracle_relation(a, b):
    va, vb = a['verdict'], b['verdict']
    if va == 'module-member' and vb == va:
        return 'module-member'
    if va in ('timeout', 'crash', 'tool-error') or vb in ('timeout', 'crash', 'tool-error'):
        return 'oracle-error'
    if va == 'unsupported' or vb == 'unsupported':
        return 'scope-gap'
    if va != vb:
        if 'pass' in (va, vb) and any(v.startswith(('exit(', 'trap(', 'ub(')) for v in (va, vb)):
            return 'not-dynamically-comparable'
        return 'differs'
    if va.startswith('fail(') and a.get('record') and b.get('record'):
        def first(record):
            errors = [d for d in record['diagnostics'] if d.get('severity') == 'error']
            if not errors:
                return None
            diag = min(errors, key=lambda d: d['span'][0])
            file = record.get('files', ['<entry>'])[diag.get('file', 0)] if 'files' in record else '<entry>'
            return diag['code'], diag['span'], file
        if first(a['record']) != first(b['record']):
            return 'differs'
    if va.startswith(('exit(', 'trap(')):
        ha, hb = a.get('stdout_sha256'), b.get('stdout_sha256')
        if ha is not None and hb is not None and ha != hb:
            return 'differs'
    # The native run front door provides no rejection byte span. Record this
    # comparison limitation explicitly rather than claiming protocol span parity.
    return 'same-observed'


def fenrir_verdict(oracle, candidate):
    verdict = candidate['verdict']
    if candidate.get('build_exit') == 70:
        return 'fenrir-crashes'
    if verdict == 'refused' or candidate.get('build_exit') == 2:
        return 'fenrir-refuses'
    if verdict in ('crash', 'timeout', 'tool-error'):
        return 'fenrir-crashes'
    if oracle['verdict'] in ('unsupported', 'pass', 'module-member'):
        return 'differs'
    if oracle['verdict'] != verdict:
        return 'differs'
    for field in ('stdout_sha256', 'trap_kind', 'trap_site', 'trap_message'):
        if oracle.get(field) != candidate.get(field):
            return 'differs'
    # Fixtures may carry literal stdout without a digest; still compare it.
    if oracle.get('stdout_sha256') is None and oracle.get('stdout') != candidate.get('stdout'):
        return 'differs'
    return 'same'


def reconcile(first, second):
    if first.get('format') != 2 or second.get('format') != 2:
        raise ValueError('oracle recordings use an obsolete invocation schema')
    if first['identity'] != second['identity'] or first['complete'] != second['complete']:
        raise ValueError('oracle recordings have different identities or completeness')
    if len(first['rows']) != len(second['rows']):
        raise ValueError('oracle recordings have different row counts')
    data = dict(first)
    rows = []
    changes = []
    for a, b in zip(first['rows'], second['rows']):
        if any(a.get(key) != b.get(key) for key in ('file', 'sha256', 'member', 'directives', 'expected', 'phase')):
            raise ValueError('oracle recordings have different source rows')
        row = dict(a, repeat_wolf=b['wolf'], repeat_lupin=b['lupin'], repeat_relation=b['relation'],
                   repeat_native_run=b.get('native_run'), repeat_declared_phase=b.get('declared_phase'))
        fields = ('verdict', 'stdout_sha256', 'trap_kind', 'trap_site', 'trap_message')
        row['repeat_stable'] = all(a[side].get(key) == b[side].get(key) for side in ('wolf', 'lupin') for key in fields)
        if not row['repeat_stable']:
            changes.append(row['file'])
        rows.append(row)
    data.update(rows=rows, recordings=2, repeat_changes=changes)
    return data


def comparison(data):
    rows = []
    same = total = 0
    for source in data['rows']:
        row = dict(source)
        if row.get('member'):
            continue
        verdict = fenrir_verdict(row['wolf'], row['fenrir'])
        row['verdict'] = verdict
        dynamic = (row.get('expected') or '').startswith('run(')
        total += dynamic
        same += dynamic and verdict == 'same'
        rows.append(row)
    return {'rows': rows, 'coverage': {'same': same, 'run_rows': total,
                                      'fraction': same / total if total else 0.0},
            'counts': {name: sum(row['verdict'] == name for row in rows) for name in
                       ('same', 'differs', 'fenrir-refuses', 'fenrir-crashes')}}
