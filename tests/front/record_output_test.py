#!/usr/bin/env python3
"""Exercise output adaptation, optionally against an external record writer."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ADAPTOR = ROOT / 'tests/front/record_output.py'


def command(text, status):
    return [sys.executable, '-I', str(ADAPTOR), '--', sys.executable, '-I', '-c',
            'import sys; sys.stdout.write(' + repr(text) + '); sys.exit(' + str(status) + ')']


def unit():
    for name, text, status, markers in (
        ('record-output-no-fail', 'ordinary diagnostic\n', 7, []),
        ('record-output-indented-fail', '  FAIL fixture demonstrated\n', 9, ['FAIL fixture demonstrated']),
        ('record-output-zero-exit', 'FAIL fixture literal\n', 0, ['FAIL fixture literal']),
    ):
        result = subprocess.run(command(text, status), capture_output=True, text=True)
        observed = [line for line in result.stdout.splitlines() if line.startswith('FAIL ')]
        assert result.returncode == status and observed == markers, (name, result, observed)
        print('PASS ' + name)


def canonical(writer):
    (ROOT / 'target').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='record-output-', dir=ROOT / 'target') as directory:
        repo = Path(directory)
        def git(*args):
            return subprocess.check_output(['git', '-c', 'commit.gpgsign=false', '-C', str(repo), *args], text=True).strip()
        git('init', '-b', 'trunk')
        git('config', 'user.name', 'Fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        git('remote', 'add', 'origin', 'https://example.invalid/record-test.git')
        (repo / 'fixture').write_text('base\n')
        git('add', 'fixture'); git('commit', '-m', 'Add fixture')
        base = git('rev-parse', 'HEAD')
        git('switch', '-c', 'plant')
        (repo / 'fixture').write_text('break\n')
        git('add', 'fixture'); git('commit', '-m', 'Plant fixture')
        for label, text, status, accepted in (
            ('no-fail', 'ordinary diagnostic\n', 7, False),
            ('indented-fail', '  FAIL fixture demonstrated\n', 9, True),
        ):
            script = repo / (label + '.py')
            script.write_text('import subprocess,sys\nprint("START adapter",flush=True)\nr=subprocess.run(' + repr(command(text, status)) + ')\nprint("END adapter exit=%s secs=0"%r.returncode,flush=True)\nsys.exit(r.returncode)\n')
            result = subprocess.run(['bash', str(writer), '--output', str(repo / (label + '.log')), '--base', base, '--plant', 'fixture', '--', sys.executable, '-I', str(script)], cwd=repo, capture_output=True, text=True)
            combined = result.stdout + result.stderr
            if accepted:
                assert result.returncode == status and 'plant record verified' in combined, combined
            else:
                assert result.returncode != status and 'missing FAIL line for fixture' in combined and 'plant record verified' not in combined, combined
            print('PASS canonical-record-' + label)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--writer', type=Path)
    a = p.parse_args()
    try:
        unit()
        if a.writer:
            canonical(a.writer.resolve())
    except (AssertionError, OSError, subprocess.CalledProcessError) as exc:
        print('FAIL record-output-adaptor: ' + str(exc), flush=True)
        sys.exit(1)
