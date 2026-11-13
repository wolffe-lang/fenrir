#!/usr/bin/env python3
"""Map-containing interpolation is a named refusal, never output agreement."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
CASES=[('direct','',None,'m'),
       ('struct','struct Box { m: Map[str, int] }\n','Box { m: m }','value'),
       ('list','','[m]','value'),('tuple','','(m, true)','value')]

# Measured on the pinned releases; wolf-lang#1110 tracks the disagreement.
# These are tier-specific observations, never candidate output agreement.
SPANS={'direct':[74,75],'struct':[135,140],'list':[94,99],'tuple':[100,105]}
CHECKED={'struct':'Box { m: <value> }\n','list':'[<value>]\n','tuple':'(<value>, true)\n'}
LUPIN={'direct':'{x: 3}\n','struct':'Box { m: {x: 3} }\n','list':'[{x: 3}]\n','tuple':'({x: 3}, true)\n'}
DIRECT_REASON='string interpolation of a `Map` (iterate `pairs()`)'
NESTED_REASON='string interpolation of a value with no promised rendering (a channel, proc, region, scope, pointer or fn)'


def reference_matches(name,tier,record,tool_exit,site):
    if name not in SPANS or tier not in ('native','checked','lupin') or tool_exit!=0:
        return False
    expected=dict(protocol=1,impl='lupin' if tier=='lupin' else 'wolfgang',
                  impl_version='0.1.61' if tier=='lupin' else '0.2.39',
                  commit='a10cbe5' if tier=='lupin' else '3fc86f7',
                  seeded=False,diagnostics=[],warnings=[])
    rendered=LUPIN.get(name) if tier=='lupin' else CHECKED.get(name) if tier=='checked' else None
    if rendered is not None:
        expected.update(verdict='exit(0)',phase_reached='run',stdout_inline=rendered,
                        stdout_sha256=hashlib.sha256(rendered.encode()).hexdigest())
    else:
        expected.update(verdict='unsupported',phase_reached='resolve' if name=='direct' else 'mem',
                        stdout_inline=None,stdout_sha256=None,
                        **{'x-unsupported-construct':DIRECT_REASON if name=='direct' else NESTED_REASON,
                           'x-unsupported-line':site[0],'x-unsupported-col':site[1],
                           'x-unsupported-span':SPANS[name]})
    return all(key in record and record[key]==value for key,value in expected.items())


def cap():
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compiler',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--reference',action='store_true')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,WOLF_STD=str(ROOT/'.wolf-bin/std'),WOLF_RT_LIB=str(ROOT/'.wolf-bin/libwolf_rt.a'))
    rows=[];failed=False
    for name,prefix,initializer,expr in CASES:
        home=(args.out/name).resolve();home.mkdir(exist_ok=True)
        body='    var m = Map[str, int]()\n    m["x"] = 3\n'
        if initializer:body+='    let value = '+initializer+'\n'
        printing='    print("{'+expr+'}")'
        source_text=prefix+'fn main() -> int {\n'+body+printing+'\n    0\n}\n'
        source=home/'row.lu';source.write_text(source_text)
        expected_site=[source_text.splitlines().index(printing)+1,printing.index('{')+2]
        def run(label,command):
            p=subprocess.run(list(map(str,command)),cwd=home,env=env,capture_output=True,timeout=120,
                             preexec_fn=cap if sys.platform=='linux' else None)
            (home/(label+'.stdout')).write_bytes(p.stdout);(home/(label+'.stderr')).write_bytes(p.stderr)
            return p
        candidate=run('fenrir',[args.compiler.resolve(),'--emit=fir',source])
        match=re.search(r':(\d+):(\d+): error\[F0001\]',candidate.stderr.decode(errors='replace'))
        site=list(map(int,match.groups())) if match else None
        message=candidate.stderr.decode(errors='replace')
        ok=candidate.returncode==4 and candidate.stdout==b'' and site==expected_site and 'map' in message.lower() and 'pairs()' in message
        row=dict(name=name,source=source_text,verdict='fenrir-refuses',candidate_exit=candidate.returncode,candidate_site=site,expected_site=expected_site,reference={},reference_question='wolf-lang#1110')
        if args.reference:
            for tier,tool,flags in [('native','wolf',['--native']),('checked','wolf',['--checked']),('lupin','lupin',[])]:
                result=run(tier,[ROOT/'.wolf-bin'/tool,'conform-run',source,'--json',*flags])
                try:record=json.loads(result.stdout)
                except ValueError:record={}
                row['reference'][tier]=record
                ok &= reference_matches(name,tier,record,result.returncode,expected_site)
        row['passed']=bool(ok);rows.append(row);failed |= not ok
        print(('PASS' if ok else 'FAIL')+' map-refusal-'+name+' fenrir-refuses (not same; tier disagreement wolf-lang#1110)',flush=True)
    (args.out/'results.json').write_text(json.dumps(dict(rows=rows),indent=2,sort_keys=True)+'\n')
    return int(failed)

if __name__=='__main__':
    raise SystemExit(main())
