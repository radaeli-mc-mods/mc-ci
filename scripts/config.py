#!/usr/bin/env python3
import json, os, re, sys, uuid
from pathlib import Path

def validate(c):
    def require(condition, message):
        if not condition: raise ValueError(message)
    def keys(o, required, optional=()):
        require(isinstance(o, dict) and not (set(o)-set(required)-set(optional)) and not (set(required)-set(o)), 'invalid or missing keys')
    def string(x): return isinstance(x, str) and bool(x.strip()) and not any(ch in x for ch in '\r\n')
    def strings(x): return isinstance(x, list) and all(string(i) for i in x)
    keys(c, ['displayName','java','checks','curseforge','targets'], ['$schema'])
    require(string(c['displayName']), 'invalid displayName')
    require(isinstance(c['java'],list) and c['java'] and all(type(x)==int and x in (17,21,25) for x in c['java']) and len(set(c['java']))==len(c['java']), 'invalid java')
    require(strings(c['checks']) and all(re.fullmatch(r'[A-Za-z0-9_:.-]+',x) for x in c['checks']), 'invalid checks')
    cf=c['curseforge']; keys(cf,['projectId','releaseType'])
    require(isinstance(cf['projectId'],str) and re.fullmatch(r'[0-9]+',cf['projectId']) and cf['releaseType'] in ('auto','alpha','beta','release'), 'invalid curseforge')
    require(isinstance(c['targets'],list) and c['targets'], 'targets must not be empty')
    ids=set()
    for t in c['targets']:
        keys(t,['id','task','files','loaders','gameVersions','java','dependencies'])
        require(isinstance(t['id'],str) and re.fullmatch(r'[a-z0-9][a-z0-9_.-]*',t['id']) and t['id'] not in ids, 'invalid or duplicate id'); ids.add(t['id'])
        require(isinstance(t['task'],str) and re.fullmatch(r'[A-Za-z0-9_:.-]+',t['task']), 'invalid task')
        for k in ('files','loaders','gameVersions','dependencies'):
            require(strings(t[k]) and (k=='dependencies' or t[k]), 'invalid '+k)
        require(all(not x.startswith(('/', '!')) and '..' not in x.split('/') and '\\' not in x for x in t['files']), 'invalid glob')
        require(type(t['java'])==int and t['java'] in c['java'], 'target java must be in java')
    return c

def main():
    c=validate(json.loads(Path(sys.argv[1] if len(sys.argv)>1 else '.github/mod-pipeline.json').read_text(encoding='utf-8')))
    compact=lambda x:json.dumps(x,separators=(',',':'),ensure_ascii=True)
    outputs={'matrix':compact({'include':c['targets']}),'java':'\n'.join(map(str,c['java'])),'checks':compact(c['checks']),'display-name':c['displayName'],'project-id':c['curseforge']['projectId'],'release-type':c['curseforge']['releaseType']}
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:
            for k,v in outputs.items():
                delimiter=uuid.uuid4().hex
                f.write(f'{k}<<{delimiter}\n{v}\n{delimiter}\n')
    else: print(compact(outputs))
if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,TypeError) as e: print(f'Invalid pipeline config: {e}',file=sys.stderr); sys.exit(1)
