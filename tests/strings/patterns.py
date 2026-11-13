#!/usr/bin/env python3
"""Binding alternatives join their selected values before guards and bodies."""
import importlib.util
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tests/types'))
from or_rows import PROGRAMS
spec=importlib.util.spec_from_file_location('or_execution_runner',Path(__file__).with_name('format.py'))
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
runner.__doc__=__doc__;runner.SUITE='pattern'
runner.CASES=[(name,'print("{'+call+'}")',str(answer)+'\n') for name,(_,call,answer) in PROGRAMS.items()]
runner.PREFIXES={name:prefix for name,(prefix,_,_) in PROGRAMS.items()}
runner.REFERENCE_REFUSALS={name:'or-patterns with payload bindings (join params)'
                          for name in PROGRAMS if name.startswith('or-')}
runner.REFERENCE_REFUSALS['or-at']='or-patterns over product patterns (join params)'

if __name__=='__main__':
    raise SystemExit(runner.main())
