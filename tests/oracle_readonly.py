#!/usr/bin/env -S python3 -I
"""Black-box cache/output integration against an actually read-only package."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from frame import ROOT, STAGE
from differlib import (freeze_package, isolated_context, lupin_observation,
                       observe_native, oracle_relation, package_guard, remove_owned_scratch)

(ROOT / 'target').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='oracle-readonly-', dir=ROOT / 'target') as work:
    root = Path(work)
    package = root / 'package'
    package.mkdir()
    source = package / 'hello.lu'
    shutil.copyfile(STAGE / 'reference/corpus/hello.lu', source)
    freeze_package(package)
    env = dict(os.environ, WOLF_STD=str(STAGE / 'std'), WOLF_RT_LIB=str(STAGE / 'libwolf_rt.a'))
    def execute(args, cwd, env, timeout):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env, capture_output=True)
        return result.returncode, result.stdout, result.stderr, False
    checked = package_guard(package, execute)
    native_cwd, native_env = isolated_context(root, 'native-run', env)
    classification = isolated_context(root, 'classification', env)
    native = observe_native(STAGE / 'wolf', source, native_cwd, native_env, 30, [],
                            runner=checked, classification_context=classification)
    if native['verdict'] != 'exit(0)' or native['stdout'] != 'hello, wolf\n':
        raise SystemExit('FAIL oracle-readonly native invocation: ' + repr(native))
    observations = {}
    for name in ('wolf', 'lupin'):
        cwd, invocation_env = isolated_context(root, name, env)
        command = [STAGE / name, 'conform-run', source, '--phase=run', '--json']
        if name == 'wolf':
            command.append('--native')
        observation = lupin_observation(checked(command, cwd, invocation_env, 30), source, [])
        observations[name] = observation
        if oracle_relation(native, observation) != 'same-observed':
            raise SystemExit('FAIL oracle-readonly ' + name + ' observation: ' + repr(observation))
    if checked.invocations != 3 or checked.digest != checked.after_digest:
        raise SystemExit('FAIL oracle-readonly package listing changed')
    print('oracle-readonly: native, native protocol and lupin agree byte-for-byte; 3 private invocations; package tree unchanged')
    remove_owned_scratch(package)
