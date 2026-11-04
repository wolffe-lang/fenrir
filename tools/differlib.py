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
    entries = {}
    for row in rows:
        if not row['member']:
            entries.setdefault(str(Path(row['file']).parent), []).append(row)
    for row in rows:
        if row['member']:
            owners = entries.get(str(Path(row['file']).parent), [])
            row['module_entries'] = [owner['file'] for owner in owners]
            if len(owners) == 1:
                row['inherited_expectation'] = {'entry': owners[0]['file'], 'check': owners[0]['expected'], 'phase': owners[0]['phase']}
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


# Every oracle and program child inherits a 3 GiB address-space cap. A fenrir
# build links, and one ligature link of the 0.2.36 musl runtime peaks at about
# 7.4 GiB (tests/backend/linux.py), so a candidate build gets its own 10 GiB.
CHILD_ADDRESS_SPACE = 3221225472
BUILD_ADDRESS_SPACE = 10 << 30


def execute(args, cwd, env, timeout, address_space=CHILD_ADDRESS_SPACE):
    # The containing Linux job supplies cgroup memory and CPU limits. Per-child AS cap
    # is inherited by compiler/linker/program descendants, without preexec_fn in threads.
    proc = subprocess.Popen(['prlimit', f'--as={address_space}', '--', *map(str, args)], cwd=cwd,
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
    kind = TRAP.search(stderr) if code != 0 and not timedout else None
    site = SITE.search(stderr) if kind else None
    if timedout:
        verdict = 'timeout'
    elif kind:
        verdict = f'trap({kind.group(1)})'
    elif code < 0:
        verdict = 'crash'
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
                    trap_message=None, stderr=stderr, tool_exit=code,
                    tool_stdout=out.decode('utf-8', errors='replace'))
    record = json.loads(out)
    required = {'protocol', 'impl', 'impl_version', 'commit', 'file', 'phase_reached', 'seeded', 'diagnostics', 'verdict'}
    if not required <= record.keys() or record['protocol'] != 1:
        raise ValueError('malformed lupin observation record')
    verdict = record['verdict']
    match = re.fullmatch(r'exit\((\d+)\)', verdict)
    trap = re.fullmatch(r'trap\(([a-z-]+)\)', verdict)
    normalized_record = dict(record)
    # Normalize metadata paths only. Program output/message bytes must never be
    # rewritten inside the protocol envelope while retaining their original hash.
    for key in ('file', 'x-trap-file', 'x-unsupported-file'):
        if isinstance(normalized_record.get(key), str):
            normalized_record[key] = normalize(normalized_record[key], roots)
    if 'files' in normalized_record:
        normalized_record['files'] = [normalize(name, roots) for name in normalized_record['files']]
    observation = dict(verdict=verdict, exit=int(match.group(1)) if match else None,
                       stdout=record.get('stdout_inline'), stdout_sha256=record.get('stdout_sha256'),
                       trap_kind=trap.group(1) if trap else None,
                       trap_site=record.get('x-trap-span'), trap_message=record.get('trap_message'),
                       stderr=stderr, tool_exit=code, record=normalized_record)
    # An exiting protocol record with no output hash denotes no output: the
    # protocol requires a hash whenever an exiting program writes bytes. Traps
    # retain honest-absent metadata under the protocol's separate rule.
    if match and observation['stdout_sha256'] is None:
        observation['stdout'] = ''
        observation['stdout_sha256'] = hashlib.sha256(b'').hexdigest()
    return observation


def isolated_context(root, label, base_env):
    directory = Path(root) / label
    cwd, home, temp, cache = (directory / name for name in ('cwd', 'home', 'tmp', 'cache'))
    for path in (cwd, home, temp, cache):
        path.mkdir(parents=True)
    env = dict(base_env, HOME=str(home), TMPDIR=str(temp), XDG_CACHE_HOME=str(cache))
    return cwd, env


def freeze_package(root):
    root = Path(root)
    for path in [root, *root.rglob('*')]:
        path.chmod(path.stat().st_mode & ~0o222)


def remove_owned_scratch(root):
    import shutil
    # Undo only the read-only directories owned by this invocation before removal.
    for path in [Path(root), *Path(root).rglob('*')]:
        if not path.is_symlink() and path.is_dir():
            path.chmod(path.stat().st_mode | 0o700)
    shutil.rmtree(root)


def package_snapshot(root):
    root = Path(root)
    rows = [('.', 'directory', root.lstat().st_mode & 0o777)]
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode & 0o777
        if path.is_symlink():
            rows.append((name, 'link', mode, os.readlink(path)))
        elif path.is_dir():
            rows.append((name, 'directory', mode))
        else:
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            rows.append((name, 'file', mode, digest))
    return rows


def package_guard(root, runner=execute):
    baseline = package_snapshot(root)
    def checked(args, cwd, env, timeout):
        result = runner(args, cwd, env, timeout)
        current = package_snapshot(root)
        checked.after_digest = hashlib.sha256(json.dumps(current).encode()).hexdigest()
        if current != baseline:
            raise ValueError('oracle invocation changed the read-only package')
        checked.invocations += 1
        return result
    checked.invocations = 0
    checked.digest = hashlib.sha256(json.dumps(baseline).encode()).hexdigest()
    checked.after_digest = checked.digest
    return checked


def classify_native(observed, classified):
    observed = dict(observed)
    verdict = classified['verdict']
    expected_exit = 2 if verdict.startswith('fail(') else (4 if verdict == 'unsupported' else None)
    match = re.fullmatch(r'exit\((\d+)\)', verdict)
    if match:
        expected_exit = int(match.group(1))
    observed['classification_record'] = classified.get('record')
    observed['classification_observation'] = classified
    consistent = expected_exit == observed['exit']
    if match and classified.get('stdout_sha256') != observed['stdout_sha256']:
        consistent = False
    if consistent:
        observed['verdict'] = verdict
    else:
        observed['verdict'] = 'tool-error'
        observed['classification_error'] = 'native invocation did not produce the outcome of its classification record'
    return observed


def observe_native(wolf, source, cwd, env, timeout, roots, runner=execute, classification_context=None):

    # Pinned 0.2.36's `run` is native by default and rejects --native. Disable
    # package-local caches and name an invocation-owned output before the input.
    output = str(Path(cwd) / 'native-program')
    args = [wolf, 'run', '--no-cache', '-o', output, source]
    observed = native_observation(runner(args, cwd, env, timeout), source, roots)
    observed['argv'] = [normalize(str(arg), roots) for arg in args]
    if observed['exit'] in (2, 4) and observed['trap_kind'] is None:
        classify_cwd, classify_env = classification_context or (cwd, env)
        classified = lupin_observation(runner([wolf, 'conform-run', source, '--native', '--json'], classify_cwd, classify_env, timeout), source, roots)
        observed = classify_native(observed, classified)
        observed['classification_argv'] = [normalize(str(arg), roots) for arg in (wolf, 'conform-run', source, '--native', '--json')]
    return observed


def root_nonzero(row):
    if not row:
        return False
    anchors = {tag.strip() for tag in row.get('directives', {}).get('conforms', '').split(',')}
    return 'conc.proc.root' in anchors and bool(re.match(r'run\(\s*exit\s*=\s*nonzero(?:\s*[,)]|$)', row.get('expected') or ''))


def nonzero_exits(a, b, row):
    if not root_nonzero(row):
        return False
    left = re.fullmatch(r'exit\((\d+)\)', a)
    right = re.fullmatch(r'exit\((\d+)\)', b)
    return bool(left and right and int(left.group(1)) != 0 and int(right.group(1)) != 0)


def oracle_relation(a, b, row=None):
    va, vb = a['verdict'], b['verdict']
    if va == 'module-member' and vb == va:
        return 'module-member'
    if va in ('timeout', 'crash', 'tool-error') or vb in ('timeout', 'crash', 'tool-error'):
        return 'oracle-error'
    if va == 'unsupported' or vb == 'unsupported':
        return 'scope-gap'
    if va != vb and not nonzero_exits(va, vb, row):
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


def fenrir_verdict(oracle, candidate, row=None):
    verdict = candidate['verdict']
    if candidate.get('build_exit') == 70:
        return 'fenrir-crashes'
    # A rejection is 2 and a refusal (outside fenrir's scope) is 4, as
    # [conf.exit.static] and [conf.exit.refused] number them; both refuse.
    if verdict == 'refused' or candidate.get('build_exit') in (2, 4):
        return 'fenrir-refuses'
    if verdict in ('crash', 'timeout', 'tool-error'):
        return 'fenrir-crashes'
    if oracle['verdict'] in ('unsupported', 'pass', 'module-member'):
        return 'differs'
    if oracle['verdict'] != verdict and not nonzero_exits(oracle['verdict'], verdict, row):
        return 'differs'
    for field in ('stdout_sha256', 'trap_kind', 'trap_site', 'trap_message'):
        if oracle.get(field) != candidate.get(field):
            return 'differs'
    # Fixtures may carry literal stdout without a digest; still compare it.
    if oracle.get('stdout_sha256') is None and oracle.get('stdout') != candidate.get('stdout'):
        return 'differs'
    return 'same'


def observation_signature(row):
    fields = ('verdict', 'exit', 'stdout_sha256', 'trap_kind', 'trap_site', 'trap_message')
    observations = [row.get('wolf'), row.get('lupin'), row.get('native_run')]
    declared = row.get('declared_phase') or {}
    observations.extend(declared.get(side) for side in ('wolf', 'lupin'))
    return [[observation.get(key) for key in fields] if observation is not None else None for observation in observations]


def derive_protocol(capture):
    """Re-parse a saved protocol record without invoking an implementation."""
    code = capture.get('tool_exit', 0)
    output = json.dumps(capture['record']).encode() if 'record' in capture else capture.get('tool_stdout', '').encode()
    result = lupin_observation((code, output, capture.get('stderr', '').encode(), capture.get('verdict') == 'timeout'), None, [])
    if 'argv' in capture:
        result['argv'] = capture['argv']
    return result


def derive_native(capture):
    result = native_observation((capture['exit'], base64.b64decode(capture['stdout_base64'], validate=True),
                                 capture['stderr'].encode(), capture['verdict'] == 'timeout'), None, [])
    result['argv'] = capture['argv']
    if result['exit'] in (2, 4) and result['trap_kind'] is None:
        result = classify_native(result, derive_protocol(capture['classification_observation']))
        result['classification_argv'] = capture['classification_argv']
    return result


def derive_row(capture):
    """Pure derivation from saved process bytes, protocol objects and headers."""
    row = dict(capture)
    if row.get('member'):
        row.update(wolf={'verdict': 'module-member'}, lupin={'verdict': 'module-member'}, relation='module-member')
        return row
    if row.get('native_run') and row.get('declared_phase'):
        native = derive_native(row['native_run'])
        declared = dict(row['declared_phase'])
        for side in ('wolf', 'lupin'):
            declared[side] = derive_protocol(declared[side])
        declared['relation'] = oracle_relation(declared['wolf'], declared['lupin'], row)
        if (row.get('expected') or '').startswith('run('):
            wolf, lupin = native, derive_protocol(row['lupin'])
        else:
            wolf, lupin = declared['wolf'], declared['lupin']
        row.update(native_run=native, declared_phase=declared, wolf=wolf, lupin=lupin)
    row['relation'] = oracle_relation(row['wolf'], row['lupin'], row)
    return row


def reconcile(first, second):
    if first.get('format') != 4 or second.get('format') != 4:
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
        a, b = derive_row(a), derive_row(b)
        row = dict(a, repeat_wolf=b['wolf'], repeat_lupin=b['lupin'], repeat_relation=b['relation'],
                   repeat_native_run=b.get('native_run'), repeat_declared_phase=b.get('declared_phase'),
                   repeat_package_before=b.get('package_before'), repeat_package_after=b.get('package_after'),
                   repeat_checked_invocations=b.get('checked_invocations'))
        row['repeat_stable'] = observation_signature(a) == observation_signature(b)
        if not row['repeat_stable']:
            changes.append(row['file'])
        rows.append(row)
    names = ('same-observed', 'differs', 'scope-gap', 'not-dynamically-comparable', 'oracle-error', 'module-member')
    counts = {name: sum(row['relation'] == name for row in rows) for name in names}
    disagreements = [row['file'] for row in rows if row['relation'] in ('differs', 'oracle-error')]
    data.update(rows=rows, counts=counts, disagreements=disagreements, recordings=2, repeat_changes=changes)
    return data


def comparison(data):
    rows = []
    same = total = 0
    for source in data['rows']:
        row = dict(source)
        if row.get('member'):
            continue
        verdict = fenrir_verdict(row['wolf'], row['fenrir'], row)
        row['verdict'] = verdict
        dynamic = (row.get('expected') or '').startswith('run(')
        total += dynamic
        same += dynamic and verdict == 'same'
        rows.append(row)
    return {'rows': rows, 'coverage': {'same': same, 'run_rows': total,
                                      'fraction': same / total if total else 0.0},
            'counts': {name: sum(row['verdict'] == name for row in rows) for name in
                       ('same', 'differs', 'fenrir-refuses', 'fenrir-crashes')}}
