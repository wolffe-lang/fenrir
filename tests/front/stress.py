#!/usr/bin/env python3
"""Linux-only, capped child fuzz and N/10N/100N scaling witnesses."""
import argparse
import json
from pathlib import Path
import random
import resource
import statistics
import subprocess
import sys
import time

CAP = 1024 * 1024 * 1024

def cap():
    resource.setrlimit(resource.RLIMIT_AS, (CAP, CAP))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))


def run(binary, source, mode="ast"):
    start = time.perf_counter()
    result = subprocess.run([str(binary), "--emit=" + mode, str(source)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=25, preexec_fn=cap)
    elapsed = time.perf_counter() - start
    assert result.returncode in (0, 2), ("front-crash", source.name, result.returncode, result.stderr[:400])
    if result.returncode == 2:
        assert b"error[E" in result.stderr and str(source).encode() in result.stderr, ("unnamed-refusal", source)
    return result, elapsed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("binary", type=Path)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--largest", type=int)
    a = p.parse_args()
    if a.largest is None:
        root = Path(__file__).resolve().parents[2]
        inputs = list((root / "src").rglob("*.lu")) + list((root / ".wolf-bin/reference/corpus").rglob("*.lu"))
        a.largest = max(path.stat().st_size for path in inputs)
    assert sys.platform.startswith("linux"), "fuzz and growing inputs require Linux hard caps"
    a.work.mkdir(parents=True, exist_ok=True)
    alphabet = ['fn', 'x', 'let', 'mut', 'return', 'if', 'then', 'else', 'match', 'type', 'impl', 'region', 'unsafe', 'c', 'r#"x"#', '"x"', '"{x:>{w}}"', "'x'", '0', '1.0', '(', ')', '[', ']', '{', '}', ';', '\n', '+', '-', '*', '=', '=>', '..', '..=', ',', ':', '|', '?', '#[', '#![', '...']
    source = a.work / "fuzz.lu"
    for seed in (7, 41, 2026):
        rng = random.Random(seed)
        for index in range(200):
            text = ' '.join(rng.choice(alphabet) for _ in range(rng.randrange(1, 200)))
            if index % 2:
                text = 'fn f() { ' + text + ' }\n'
            source.write_text(text)
            run(a.binary, source)
        print(f"PASS random-token-streams seed={seed} rows=200 cap={CAP}", flush=True)
    for kind in ("parentheses", "else-if", "prefix", "types", "patterns"):
        if kind == "parentheses": text = 'let x = ' + '(' * 600 + '0' + ')' * 600 + '\n'
        elif kind == "else-if": text = 'fn f() { ' + 'if x {} else ' * 600 + '{} }\n'
        elif kind == "prefix": text = 'let x = ' + '!' * 600 + 'true\n'
        elif kind == "types": text = 'type X = ' + 'shared ' * 600 + 'int\n'
        else: text = 'let ' + 'A(' * 600 + 'x' + ')' * 600 + ' = y\n'
        source.write_text(text)
        result, _ = run(a.binary, source)
        # The reference limits expressions to 256 levels (E0201) and nothing
        # else; fenrir's own rail refuses deeper syntax of any kind (F0002, 4).
        if kind in ("parentheses", "prefix"):
            assert result.returncode == 2 and b"E0201" in result.stderr, ("expression-limit", kind, result.stderr[:300])
        else:
            assert result.returncode == 0, ("reference-accepts", kind, result.stderr[:300])
            source.write_text(text.replace('if x {} else ' * 600, 'if x {} else ' * 20000).replace('shared ' * 600, 'shared ' * 20000)
                              .replace('A(' * 600, 'A(' * 20000).replace(')' * 600, ')' * 20000))
            result, _ = run(a.binary, source)
            assert result.returncode == 4 and b"F0002" in result.stderr, ("nesting-rail", kind, result.stderr[:300])
        print("PASS recursion-rail " + kind, flush=True)
    # The largest synthetic input exceeds ten times the largest real input.
    unit = 'let value = 123 + 456 * 789\n'
    base = max(256, (a.largest * 10 + len(unit) * 100 - 1) // (len(unit) * 100))
    all_results = {}
    for mode in ("tokens", "ast"):
        measurements = []
        for scale in (1, 10, 100):
            source = a.work / (mode + '-' + str(scale) + '.lu')
            source.write_text(unit * (base * scale))
            durations = []
            for _ in range(5):
                result, elapsed = run(a.binary, source, mode)
                assert result.returncode == 0, ("scaling-refusal", mode, scale, result.stderr[:300])
                durations.append(elapsed)
            median = statistics.median(durations)
            measurements.append(median)
            print(f"PASS scaling mode={mode} N={base * scale} bytes={source.stat().st_size} median={median:.6f}s child-cap={CAP}", flush=True)
        for index in (0, 1):
            assert measurements[index + 1] <= measurements[index] * 16, ("superlinear-scaling", mode, measurements)
        all_results[mode] = measurements
    (a.work / "measurements.json").write_text(json.dumps(dict(cap=CAP, largest=a.largest, base=base, seconds=all_results), indent=2) + "\n")
    print("PASS bounded-fuzz-and-linear-scaling", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, subprocess.TimeoutExpired) as exc:
        print("FAIL capped-front-stress: " + str(exc), flush=True)
        sys.exit(1)
