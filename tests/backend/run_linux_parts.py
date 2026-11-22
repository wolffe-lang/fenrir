#!/usr/bin/env python3
"""Every step of the Linux gate runs in exactly one hosted job.

`tests/backend/run-linux PART` runs the shared steps (the whole `preflight` part:
fetch, builds and readiness) and that part's own steps; the backend workflow runs
parts as parallel jobs. This check lists each part's steps through run-linux's list
mode (FENRIR_RUN_LINUX_LIST=1, which runs nothing) and reads which part each
workflow job runs. It fails, by name, on a step of `run-linux` that no job runs, a
step two jobs run, a job that runs an unknown part or skips a shared step, and a
part that lists a step `run-linux` with no part would not run. It also holds the
selection every other caller uses (FENRIR_RUN_LINUX_ONLY=NAMES: the shared steps,
then exactly the named ones, and exit 2 for a name no part runs), so a record's chain
runs a gate step through run-linux's own line, never a copy of it. A step can then
leave hosted CI only by being deleted, never by a part moving out from under the
jobs.

  run_linux_parts.py [--run-linux PATH] [--workflow PATH]
  run_linux_parts.py --self-test   fixtures that must be red by name, then the live tree

Cost: one list-mode run of run-linux per part, linear in the script and workflow.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RUN_LINUX = ROOT / 'tests/backend/run-linux'
WORKFLOW = ROOT / '.github/workflows/backend.yml'
INVOCATION = re.compile(r'tests/backend/run-linux(?:[ \t]+([A-Za-z0-9_-]+))?')


def steps(run_linux, part):
    """The steps `run-linux PART` would run, in order, or None for an unknown part."""
    env = dict(os.environ, FENRIR_RUN_LINUX_LIST='1')
    p = subprocess.run(['bash', str(run_linux), part], capture_output=True, text=True, env=env, timeout=60)
    if p.returncode == 2 and 'unknown part' in p.stderr:
        return None
    if p.returncode != 0:
        raise RuntimeError(f'run-linux {part} list mode exited {p.returncode}: {p.stderr.strip()}')
    return [line[5:] for line in p.stdout.splitlines() if line.startswith('STEP ')]


def jobs(workflow):
    """(job, part) for each run-linux invocation, in file order; part 'all' when none is named."""
    found, job, in_jobs = [], None, False
    for line in Path(workflow).read_text().splitlines():
        if re.match(r'^jobs:\s*$', line):
            in_jobs = True
            continue
        heading = re.match(r'^  ([A-Za-z0-9_-]+):\s*$', line)
        if in_jobs and heading:
            job = heading.group(1)
            continue
        if line.lstrip().startswith('#'):
            continue
        for match in INVOCATION.finditer(line):
            found.append((job, match.group(1) or 'all'))
    return found


def problems(run_linux, workflow):
    """Every failed condition as a line that begins with the step or job it names,
    and a summary for the pass line."""
    shared = steps(run_linux, 'preflight')
    every = steps(run_linux, 'all')
    out = []
    if len(every) != len(set(every)):
        out.append('all names a step twice')
    own = [s for s in every if s not in shared]
    runners = {s: [] for s in own}
    invocations = jobs(workflow)
    for job, part in invocations:
        listed = steps(run_linux, part)
        if listed is None:
            out.append(f'job-{job} runs unknown part {part}')
            continue
        missing = [s for s in shared if s not in listed]
        if missing:
            out.append(f'job-{job} part {part} skips the shared steps {", ".join(missing)}')
        for step in listed:
            if step in shared:
                continue
            if step in runners:
                runners[step].append(job)
            else:
                out.append(f'job-{job} part {part} lists {step}, which run-linux all does not run')
    for step in own:
        if not runners[step]:
            out.append(f'{step} runs in no hosted job')
        elif len(runners[step]) > 1:
            out.append(f'{step} runs in {len(runners[step])} hosted jobs: {", ".join(runners[step])}')
    summary = f'{len(own)} steps, each in one of {len(invocations)} hosted jobs; {len(shared)} shared steps in every job'
    return out, summary


def selection(run_linux):
    """FENRIR_RUN_LINUX_ONLY: each own step alone, after the shared steps; an unknown name is exit 2."""
    shared = steps(run_linux, 'preflight')
    every = steps(run_linux, 'all')
    own = [s for s in every if s not in shared]
    out = []
    for name in own:
        env = dict(os.environ, FENRIR_RUN_LINUX_LIST='1', FENRIR_RUN_LINUX_ONLY=name)
        p = subprocess.run(['bash', str(run_linux), 'all'], capture_output=True, text=True, env=env, timeout=60)
        listed = [line[5:] for line in p.stdout.splitlines() if line.startswith('STEP ')]
        if p.returncode != 0 or [s for s in listed if s in own] != [name] or not set(shared) <= set(listed):
            out.append(f'only-{name} lists {[s for s in listed if s in own]} (exit {p.returncode})')
    env = dict(os.environ, FENRIR_RUN_LINUX_LIST='1', FENRIR_RUN_LINUX_ONLY='no-such-step')
    p = subprocess.run(['bash', str(run_linux), 'all'], capture_output=True, text=True, env=env, timeout=60)
    if p.returncode != 2 or 'no-such-step' not in p.stderr:
        out.append(f'only-unknown-name exits {p.returncode}, not 2 naming it')
    return out


def check(run_linux, workflow):
    found, summary = problems(run_linux, workflow)
    if Path(run_linux) == RUN_LINUX:
        found += selection(run_linux)
    for line in found:
        print(f'FAIL run-linux-parts-{line}', flush=True)
    if not found:
        print(f'PASS run-linux-parts {summary}', flush=True)
    return int(bool(found))


FIXTURE = '''#!/usr/bin/env bash
set -euo pipefail
part=${1:-all}
case $part in
    all|preflight|one|two) ;;
    *) echo "run-linux: unknown part '$part'" >&2; exit 2 ;;
esac
want() { [[ $part == all || $part == "$1" ]]; }
step() { if [[ -n ${FENRIR_RUN_LINUX_LIST:-} ]]; then echo "STEP $1"; return 0; fi; exit 9; }
step fetch true
step build true
if [[ $part == preflight ]]; then exit 0; fi
if want one; then step alpha true; fi
if want two; then step beta true; fi
EXTRA
'''
WORKFLOW_FIXTURE = 'name: fixture\non:\n  workflow_dispatch:\njobs:\n' + ''.join(
    f'  {job}:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: bash tests/backend/run-linux {part}\n'
    for job, part in (('j1', 'one'), ('j2', 'two')))
CASES = [
    # name, extra run-linux line, extra workflow jobs, the exact failures expected
    ('clean', '', [], []),
    ('neither', 'if [[ $part == all ]]; then step gamma true; fi', [], ['gamma runs in no hosted job']),
    ('both', '', [('j3', 'two')], ['beta runs in 2 hosted jobs: j2, j3']),
    ('unknown-part', '', [('j4', 'three')], ['job-j4 runs unknown part three']),
    ('whole-gate-job', '', [('j5', '')], ['alpha runs in 2 hosted jobs: j1, j5', 'beta runs in 2 hosted jobs: j2, j5']),
]


def self_test():
    status = 0
    with tempfile.TemporaryDirectory(prefix='run-linux-parts-') as work:
        for name, extra, more, expected in CASES:
            root = Path(work) / name
            (root / 'tests/backend').mkdir(parents=True)
            script = root / 'tests/backend/run-linux'
            script.write_text(FIXTURE.replace('EXTRA', extra))
            workflow = root / 'backend.yml'
            workflow.write_text(WORKFLOW_FIXTURE + ''.join(
                f'  {job}:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: bash tests/backend/run-linux {part}\n'
                for job, part in more))
            found, _ = problems(script, workflow)
            for line in found:
                print(f'EXPECTED-RED fixture-{name}: FAIL run-linux-parts-{line}', flush=True)
            if found != expected:
                print(f'FAIL run-linux-parts-self-test fixture-{name} found {found}, expected {expected}', flush=True)
                status = 1
            else:
                print(f'PASS run-linux-parts-self-test fixture-{name} ({len(expected)} named failures)', flush=True)
    return status


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run-linux', type=Path, default=RUN_LINUX)
    ap.add_argument('--workflow', type=Path, default=WORKFLOW)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    status = self_test() if a.self_test else 0
    return check(a.run_linux, a.workflow) or status


if __name__ == '__main__':
    sys.exit(main())
