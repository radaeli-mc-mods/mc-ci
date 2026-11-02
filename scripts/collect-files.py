#!/usr/bin/env python3
import glob, json, os, shutil, sys
from pathlib import Path
patterns=json.loads(sys.argv[1]); dest=Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
seen=set(); selected=[]
for pattern in patterns:
    matches=[Path(x) for x in sorted(glob.glob(pattern,recursive=True)) if Path(x).is_file() and x.endswith('.jar') and not any(Path(x).name.endswith(s+'.jar') for s in ('-dev','-dev-shadow','-slim'))]
    if not matches: sys.exit('No eligible jars match: '+pattern)
    for path in matches:
        if path.resolve() in seen: continue
        if (dest/path.name).exists(): sys.exit('Duplicate jar filename: '+path.name)
        seen.add(path.resolve()); shutil.copy2(path,dest/path.name); selected.append(path.name)
primary=[x for x in selected if not x.endswith(('-sources.jar','-javadoc.jar'))]
if len(primary)!=1: sys.exit('Exactly one primary jar is required; narrow the file globs')
if os.getenv('GITHUB_OUTPUT'):
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f: f.write('primary='+primary[0]+'\n')
