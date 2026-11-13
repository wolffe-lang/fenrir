#!/usr/bin/env python3
"""Finite F2 trap catalogue audit: exact bytes, streams, status and site."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 2 << 30
CATALOGUE = {
    'overflow': ('finite core', 'mem.ub.defined'),
    'div-zero': ('finite core', 'mem.ub.defined'),
    'bounds': ('finite core', 'mem.ub.defined'),
    'assert': ('finite core', 'conf.trap.assert'),
    'stack-overflow': ('native platform resource; bounded FIR exhaustion is a tool refusal', 'conf.trap.stack'),
    'use-after-move': ('outside core: ownership checking', 'mem.tier0.move'),
    'exclusivity': ('outside core: dynamic borrowing/modes', 'mem.iter.excl'),
    'region-fault': ('outside core: regions', 'mem.region'),
    'stale-handle': ('outside core: shared handles', 'mem.shared.handle.2'),
    'alloc-contract': ('outside core: noalloc/region allocation contracts', 'mem.region.cap.1'),
    'race': ('outside core: concurrency', 'conc.mm.race.3'),
    'ub': ('outside core: unsafe UB oracle', 'proto.record.ub'),
    'deadlock': ('outside core: concurrency', 'conc.deadlock.trap'),
    'argument-utf8': ('outside core: text argv readers', 'os.env.argv'),
}


def case(name, body, kind=None, output='before\n', fault=None, prefix=''):
    return dict(name=name, source=prefix + 'fn main() -> int {\n' + '\n'.join('    '+line for line in body.splitlines()) + '\n    0\n}\n',
                kind=kind, output=output, fault=fault)


def arithmetic(name, ty, initial, expression, kind='overflow', extra=''):
    fault='let _ = ' + expression
    body=f'var x: {ty} = {initial}\n' + (extra+'\n' if extra else '') + 'print("before")\n' + fault
    return case(name, body, kind, fault=fault)


def fixtures():
    for ty, maximum in [('int','9223372036854775807'), ('i64','9223372036854775807'),
                        ('i32','2147483647'), ('uint','18446744073709551615'),
                        ('u64','18446744073709551615'), ('u8','255')]:
        yield arithmetic('add-'+ty, ty, maximum, 'x + 1')
    yield arithmetic('sub-i32','i32','-2147483648','x - 1')
    yield arithmetic('sub-u64','u64','0','x - 1')
    yield arithmetic('mul-i64','i64','4294967296','x * x')
    for op, name in [('/','division'),('%','remainder')]:
        yield arithmetic(name+'-zero','int','10','x '+op+' d','div-zero','var d: int = 0')
        yield arithmetic(name+'-signed-edge','int','0 - 9223372036854775807 - 1','x '+op+' d','overflow','var d: int = 0 - 1')
    for name, setup, expression in [
        ('list', 'let xs = [1]\nvar i: int = 2', 'xs[i]'),
        ('list-negative', 'let xs = [1]\nvar i: int = 0 - 1', 'xs[i]'),
        ('bytes', 'let s = "é"\nvar i: int = 2', 's.bytes()[i]'),
        ('chars', 'let s = "é"\nvar i: int = 1', 's.chars()[i]'),
        ('str-boundary', 'let s = "éx"\nvar i: int = 1', 's[i..2]'),
        ('list-slice', 'let xs = [1, 2]', 'xs[2..1]')]:
        fault='let _ = '+expression
        yield case('bounds-'+name, setup+'\nprint("before")\n'+fault, 'bounds', fault=fault)
    yield case('assert', 'print("before")\nassert(false)', 'assert', fault='assert(false)')
    prefix='fn message() -> str { print("message")\n "payload" }\n'
    yield case('assert-message', 'print("before")\nassert(false, message())', 'assert',
               output='before\nmessage\n', fault='assert(false, message())', prefix=prefix)
    yield case('assert-message-lazy', 'print("before")\nassert(true, message())\nprint("after")',
               output='before\nafter\n', prefix=prefix)
    yield case('repeat-negative', 'let s = "x"\nvar n: int = 0 - 1\nprint("before")\nlet _ = s.repeat(n)',
               'assert', fault='let _ = s.repeat(n)')
    yield case('map-absence-is-row', 'let m = Map[str, int]()\nprint("before")\nlet n = m["missing"] else 9\nassert(n == 9)')
    yield case('list-absence-is-row', 'var xs = List[int]()\nprint("before")\nlet n = (mut xs).pop() else 9\nassert(n == 9)')
    yield case('str-get-is-row', 'let s = "éx"\nprint("before")\nlet text = s.get(1..2) else "none"\nassert(text == "none")')


def cap():
    resource.setrlimit(resource.RLIMIT_AS,(LIMIT,LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compiler',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--native',action='store_true')
    parser.add_argument('--reference',action='store_true')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    spec=(ROOT/'.wolf-bin/reference/spec/05-conformance.md').read_text()
    section=spec.split('- `[conf.trap.set]`',1)[1].split('- `[conf.trap.map]`',1)[0]
    names=set(re.findall(r'`([a-z][a-z0-9]*(?:-[a-z0-9]+)*)`',section))-{'trap','nonzero'}
    assert names==set(CATALOGUE),(names-set(CATALOGUE),set(CATALOGUE)-names)
    prelude=json.loads((ROOT/'.wolf-bin/reference/spec/prelude.json').read_text())
    assert not {'panic','unwrap'} & {row['name'] for row in prelude['names']}, 'new trap surface needs an audit'
    env=dict(os.environ,WOLF_STD=str(ROOT/'.wolf-bin/std'),WOLF_RT_LIB=str(ROOT/'.wolf-bin/libwolf_rt.a'))
    records=[];failed=False
    for row in fixtures():
        home=(args.out/row['name']).resolve();home.mkdir(exist_ok=True)
        source=home/'row.lu';source.write_text(row['source'])
        status=134 if row['kind'] else 0
        wanted_error=b''
        if row['kind']:
            line=next(i+1 for i,s in enumerate(row['source'].splitlines()) if s.strip()==row['fault'])
            wanted_error=f'wolf-trap: {row["kind"]}\n  at {source}:{line}:5\n'.encode()
        def run(label,command):
            p=subprocess.run(list(map(str,command)),capture_output=True,timeout=180,env=env,cwd=home,
                             preexec_fn=cap if sys.platform=='linux' else None)
            (home/(label+'.stdout')).write_bytes(p.stdout);(home/(label+'.stderr')).write_bytes(p.stderr)
            record=dict(exit=p.returncode,stdout_base64=base64.b64encode(p.stdout).decode(),stderr_base64=base64.b64encode(p.stderr).decode())
            return p,record
        result=dict(name=row['name'],kind=row['kind'],expected_exit=status,source=row['source'])
        lowered,result['lower']=run('lower',[args.compiler.resolve(),'--emit=fir',source])
        fir=home/'row.fir';fir.unlink(missing_ok=True)
        report=home/'outcome';report.unlink(missing_ok=True)
        ok=lowered.returncode==0
        if ok:
            fir.write_bytes(lowered.stdout)
            executed,result['interpreter']=run('interpreter',[args.compiler.resolve(),'interpret',fir,'--steps','100000','--bytes','4194304','--report',report])
            expected_outcome=f'trap {row["kind"]}\n' if row['kind'] else 'exit 0\n'
            ok=(executed.returncode,executed.stdout,executed.stderr,report.read_text() if report.exists() else '')==(status,row['output'].encode(),wanted_error,expected_outcome)
            if args.native:
                exe=home/'program';exe.unlink(missing_ok=True)
                built,result['build']=run('build',[args.compiler.resolve(),'build',source,'-o',exe])
                ok &= built.returncode==0
                if built.returncode==0:
                    native,result['native']=run('native',[exe])
                    ok &= (native.returncode,native.stdout,native.stderr)==(status,row['output'].encode(),wanted_error)
        if args.reference:
            exe=home/'wolf-program';exe.unlink(missing_ok=True)
            reference,result['reference']=run('reference',[ROOT/'.wolf-bin/wolf','run','--no-cache','-o',exe,source])
            ok &= (reference.returncode,reference.stdout,reference.stderr)==(status,row['output'].encode(),wanted_error)
        print(('PASS' if ok else 'FAIL')+' trap-'+row['name'],flush=True)
        result['passed']=bool(ok);records.append(result);failed |= not ok
    (args.out/'results.json').write_text(json.dumps(dict(catalogue=CATALOGUE,rows=records),indent=2,sort_keys=True)+'\n')
    return int(failed)


if __name__=='__main__':
    raise SystemExit(main())
