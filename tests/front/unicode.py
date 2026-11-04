#!/usr/bin/env python3
"""Generate identifier ranges from the digest-pinned Unicode data file."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
VERSION = "17.0.0"
URL = "https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt"
DIGEST = "24c7fed1195c482faaefd5c1e7eb821c5ee1fb6de07ecdbaa64b56a99da22c08"
SUFFIX = '''fn in_ranges(value: int, ranges: List[int]) -> bool {
    var lo = 0
    var hi = ranges.len / 2
    while lo < hi {
        let mid = lo + (hi - lo) / 2
        if value < ranges[mid * 2] { hi = mid }
        else if value > ranges[mid * 2 + 1] { lo = mid + 1 }
        else { return true }
    }
    false
}

fn xid_start(value: int, ranges: List[int]) -> bool {
    if value < 128 { return (value >= 65 && value <= 90) || (value >= 97 && value <= 122) }
    in_ranges(value, ranges)
}

fn xid_continue(value: int, ranges: List[int]) -> bool {
    if value < 128 { return (value >= 65 && value <= 90) || (value >= 97 && value <= 122) || value == 95 || digit(value) }
    in_ranges(value, ranges)
}
'''

def generate(data):
    text = '// Generated Unicode ' + VERSION + ' XID ranges; see docs/UNICODE-LICENSE.txt.\n'
    text += '// Source: ' + URL + '\n// SHA-256: ' + DIGEST + '\n'
    for prop, name in (("XID_Start", "unicode_starts"), ("XID_Continue", "unicode_continues")):
        ranges = data[prop]
        last = 127
        for lo, hi in ranges:
            assert 128 <= lo <= hi <= 0x10FFFF and lo > last
            last = hi
        values = [item for pair in ranges for item in pair]
        text += '\nfn ' + name + '() -> List[int] {\n    [\n'
        for index in range(0, len(values), 16):
            text += '        ' + ', '.join(map(str, values[index:index + 16])) + ',\n'
        text += '    ]\n}\n'
    return text + '\n' + SUFFIX


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path)
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    fixture = ROOT / 'tests/front/unicode-ranges.json'
    if a.input:
        raw = a.input.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == DIGEST, "Unicode input digest differs"
        data = dict(version=VERSION, url=URL, sha256=DIGEST, XID_Start=[], XID_Continue=[])
        for line in raw.decode().splitlines():
            match = re.match(r"^([0-9A-F]+)(?:\.\.([0-9A-F]+))?\s*;\s*(XID_Start|XID_Continue)\b", line)
            if match:
                lo, hi = int(match[1], 16), int(match[2] or match[1], 16)
                if hi >= 128:
                    target = data[match[3]]
                    lo = max(128, lo)
                    if target and target[-1][1] + 1 == lo:
                        target[-1][1] = hi
                    else:
                        target.append([lo, hi])
        if not a.check:
            fixture.write_text(json.dumps(data, indent=1) + '\n')
    else:
        data = json.loads(fixture.read_text())
    assert (data['version'], data['url'], data['sha256']) == (VERSION, URL, DIGEST)
    generated = generate(data)
    path = ROOT / 'src/front/unicode.lu'
    if a.check:
        assert path.read_text() == generated, "Unicode generated source differs"
        print('PASS unicode-pinned-ranges ' + VERSION)
    else:
        path.write_text(generated)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        sys.exit('FAIL unicode-pinned-ranges: ' + str(exc))
