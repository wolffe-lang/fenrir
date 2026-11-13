#!/usr/bin/env python3
"""Validate every native/lowering fixture cheaply before Linux linking work."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def catalog():
    native=load('readiness_native',HERE/'linux.py')
    lower=load('readiness_lower',HERE.parent/'lower/rows.py')
    rows=[('backend',name,native.wolf_source(name)) for name,_,_ in native.rows.fixtures()]
    rows += [('lower',name,source) for name,source,_,_,_ in lower.rows()]
    return rows


def reference_accepted(status,record):
    return (status==0 and record.get('protocol')==1 and record.get('verdict')=='pass'
            and record.get('phase_reached')=='typecheck'
            and not any(d.get('severity')=='error' for d in record.get('diagnostics',[])))


def cap():
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    assert sys.platform=='linux','Linux readiness is not a platform skip'
    root=args.root.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,WOLF_STD=str(root/'.wolf-bin/std'),WOLF_RT_LIB=str(root/'.wolf-bin/libwolf_rt.a'),FENRIR_TOOLCHAIN=str(root/'.wolf-bin'))
    rows=catalog();assert len(rows)==len({(f,n) for f,n,_ in rows})
    results=[];failed=False
    for family,name,text in rows:
        home=out/family/name;home.mkdir(parents=True,exist_ok=True);source=home/'main.lu';source.write_text(text)
        reference=subprocess.run([str(root/'.wolf-bin/wolf'),'conform-run',str(source),'--native','--phase=typecheck','--json'],
                                 cwd=home,env=env,capture_output=True,timeout=90,preexec_fn=cap)
        (home/'reference.stdout').write_bytes(reference.stdout);(home/'reference.stderr').write_bytes(reference.stderr)
        try:record=json.loads(reference.stdout)
        except ValueError:record={}
        ok=reference_accepted(reference.returncode,record)
        row=dict(family=family,name=name,reference_exit=reference.returncode,reference=record)
        # Handwritten FIR's source twin is only the oracle, not a promise that
        # source lowering implements its constructs. Lowering fixtures are.
        if family=='lower':
            candidate=subprocess.run([str(root/'target/fenrir'),'--emit=fir',str(source)],cwd=home,env=env,
                                     capture_output=True,timeout=90,preexec_fn=cap)
            (home/'candidate.fir').write_bytes(candidate.stdout);(home/'candidate.stderr').write_bytes(candidate.stderr)
            row['candidate_exit']=candidate.returncode
            ok &= candidate.returncode==0
        row['passed']=bool(ok);results.append(row);failed |= not ok
        print(('PASS' if ok else 'FAIL')+' readiness-'+family+'-'+name+
              ('' if ok else ' '+json.dumps(dict(reference=record,candidate_exit=row.get('candidate_exit')),sort_keys=True)),flush=True)
    (out/'results.json').write_text(json.dumps(dict(rows=results),indent=1,sort_keys=True)+'\n')
    print(f'Linux readiness: {len(rows)} rows, {sum(not r["passed"] for r in results)} failed',flush=True)
    return int(failed)


if __name__=='__main__':raise SystemExit(main())
