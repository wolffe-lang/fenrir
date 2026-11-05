#!/usr/bin/env python3
"""Link hello under 2 GiB, measuring the linker child rather than the runner.

Prediction: the former linker pin fails this row; the replacement fits the cap
and produces the same hello executable. RLIMIT_AS is enforced by the kernel.
wait4 reports this child's exact peak RSS; /proc supplies a sampled VmPeak.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import tomllib

BUDGET = 2 << 30
TIMEOUT = 180


def cap():
    resource.setrlimit(resource.RLIMIT_AS, (BUDGET, BUDGET))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def measured(argv, env, prefix):
    """Reap one direct child with wait4, never accumulated RUSAGE_CHILDREN."""
    started = time.monotonic()
    sampled_virtual = 0
    timed_out = False
    with prefix.with_suffix('.stdout').open('wb') as out, prefix.with_suffix('.stderr').open('wb') as err:
        child = subprocess.Popen([str(arg) for arg in argv], env=env, stdout=out,
                                 stderr=err, preexec_fn=cap)
        while True:
            try:
                status = Path(f'/proc/{child.pid}/status').read_text()
                for line in status.splitlines():
                    if line.startswith('VmPeak:'):
                        sampled_virtual = max(sampled_virtual, int(line.split()[1]) * 1024)
            except FileNotFoundError:
                pass
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                break
            if time.monotonic() - started >= TIMEOUT:
                timed_out = True
                child.kill()  # This invocation's own child, by its pid only.
                _, status, usage = os.wait4(child.pid, 0)
                break
            time.sleep(0.01)
        child.returncode = os.waitstatus_to_exitcode(status)
    observation = dict(argv=[str(arg) for arg in argv], exit=child.returncode,
                       timeout=timed_out, seconds=time.monotonic() - started,
                       address_space_bytes=BUDGET,
                       child_peak_rss_bytes=usage.ru_maxrss * 1024,
                       child_sampled_peak_virtual_bytes=sampled_virtual)
    prefix.with_suffix('.json').write_text(json.dumps(observation, indent=2) + '\n')
    return observation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('Linux child accounting required; this is not a skip')
    root = args.root.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Retain each take, but never accept an executable from a previous one.
    out = Path(tempfile.mkdtemp(prefix='take-', dir=out))
    stage = root / '.wolf-bin'
    env = dict(os.environ, FENRIR_TOOLCHAIN=str(stage),
               LIGATURE_SYSROOT=str(stage / 'bundle/sysroot'))
    pin = next(p for p in tomllib.loads((root / 'wolf-toolchain.toml').read_text())['artifact']
               if p['name'] == 'ligature')
    assembly, obj, binary = out / 'hello.s', out / 'hello.o', out / 'hello'
    commands = ([root / 'target/fenrir', 'asm', root / 'examples/hello.fir', '-o', assembly],
                [stage / 'bin/clef', '--64', '-o', obj, assembly])
    for index, argv in enumerate(commands):
        result = subprocess.run([str(arg) for arg in argv], env=env, capture_output=True,
                                timeout=TIMEOUT, preexec_fn=cap)
        (out / f'prepare-{index}.stdout').write_bytes(result.stdout)
        (out / f'prepare-{index}.stderr').write_bytes(result.stderr)
        if result.returncode:
            print(f'FAIL link-budget-prepare-{index} exit={result.returncode}', flush=True)
            return 1
    argv = [stage / 'bin/ligature', '-o', binary, obj, stage / 'musl/libwolf_rt.a',
            '-lpthread', '-ldl', '-lm', '-Wl,--gc-sections']
    link = measured(argv, env, out / 'link')
    observations = dict(ligature_rev=pin['rev'], link=link)
    passed = link['exit'] == 0 and not link['timeout'] and binary.is_file()
    if passed:
        verify = measured([stage / 'bin/ligature', 'verify', binary], env, out / 'verify')
        observations['verify'] = verify
        passed = verify['exit'] == 0 and not verify['timeout']
    if passed:
        result = subprocess.run([str(binary)], env=env, capture_output=True,
                                timeout=TIMEOUT, preexec_fn=cap)
        (out / 'program.stdout').write_bytes(result.stdout)
        (out / 'program.stderr').write_bytes(result.stderr)
        observations['program_exit'] = result.returncode
        passed = (result.returncode, result.stdout, result.stderr) == (0, b'hello, wolf\n', b'')
    (out / 'result.json').write_text(json.dumps(observations, indent=2) + '\n')
    print(f'{"PASS" if passed else "FAIL"} link-two-gib pin={pin["rev"]} '
          f'exit={link["exit"]} child_peak_rss_bytes={link["child_peak_rss_bytes"]} '
          f'child_sampled_peak_virtual_bytes={link["child_sampled_peak_virtual_bytes"]} '
          f'address_space_bytes={BUDGET}', flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
