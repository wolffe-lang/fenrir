#!/usr/bin/env -S python3 -I
"""N/10N/100N scaling witness for the lexical subset inventory."""
from pathlib import Path
import statistics
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from frame import ROOT
from constructs import lex

largest = max(path.stat().st_size for path in (ROOT / 'src').rglob('*.lu'))
pattern = 'fn sample() -> int { let value = 42; if value > 0 { return value } 0 }\n'
base = pattern * ((max(4096, largest) + len(pattern) - 1) // len(pattern))
times = {}
counts = {}
for factor in (1, 10, 100):
    text = base * factor
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        tokens = lex(text)
        samples.append(time.perf_counter() - start)
    times[factor] = statistics.median(samples)
    counts[factor] = len(tokens)
    print(f'scaling N={factor} bytes={len(text)} tokens={len(tokens)} seconds={times[factor]:.6f}')
if counts[10] != 10 * counts[1] or counts[100] != 100 * counts[1]:
    raise SystemExit('FAIL inventory-scaling non-linear token census')
# A generous scheduling allowance, but not enough to hide quadratic (100x) growth.
if times[100] > times[10] * 25 + 0.05:
    raise SystemExit('FAIL inventory-scaling superlinear 10N-to-100N growth')
print(f'inventory scaling: linear token counts; largest real file={largest}; 100N exceeds 10x that size')
