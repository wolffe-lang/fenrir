"""Shared frame I/O. No compiler implementation is imported."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '.wolf-bin'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def twice(path, expected=None):
    a, b = sha(path), sha(path)
    if a != b or (expected is not None and a != expected):
        raise ValueError(f'digest mismatch: {Path(path).name}')
    return a


def download(url, dest):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with tempfile.TemporaryDirectory(dir=dest.parent, prefix='download-') as work:
            partial = Path(work) / 'archive'
            subprocess.run(['curl', '-fLsS', '--retry', '3', url, '-o', str(partial)], check=True)
            partial.replace(dest)
    return dest


def pins():
    return tomllib.loads((ROOT / 'wolf-toolchain.toml').read_text())


def oracle_identity(manifest):
    names = ('wolf-x86_64-unknown-linux-gnu', 'lupin-x86_64-unknown-linux-gnu', 'reference')
    selected = []
    for name in names:
        matches = [entry for entry in manifest['artifact'] if entry['name'] == name]
        if len(matches) != 1:
            raise ValueError('oracle pin must occur exactly once: ' + name)
        selected.append({'name': name, 'sha256': matches[0]['sha256']})
    digest = hashlib.sha256(json.dumps(selected, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    reference = next(entry for entry in manifest['artifact'] if entry['name'] == 'reference')
    return {'oracle_pins_sha256': digest, 'reference_rev': reference['rev']}


def extract(archive, dest, prefixes=None):
    """Extract only the sealed interface from reference source archives."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tf:
        for member in tf:
            parts = Path(member.name).parts
            if not parts or parts[0] in ('/', '..') or '..' in parts:
                raise ValueError('unsafe archive path')
            relative = Path(*parts[1:])
            if not relative.parts:
                continue
            if prefixes is not None and relative.parts[0] not in prefixes:
                continue
            # Source archives need no links. Binary release links are checked by data filter.
            if prefixes is not None and not (member.isfile() or member.isdir()):
                raise ValueError('link in source interface')
            member.name = str(relative)
            tf.extract(member, dest, filter='data')


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        name = stream.name
    os.replace(name, path)


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)
