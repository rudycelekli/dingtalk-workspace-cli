import copy,json
from evaluator import PACKAGES,PACKAGE_ROOT,EXPECTED_NEW,parse,compare,pristine,listing,check_inventory,deployed_layout
R=PACKAGE_ROOT+'output';O=PACKAGE_ROOT+'tui'
def events(added=False,fixed=False):
 out=[{'Action':'start','Package':p} for p in sorted(PACKAGES)]
 cases={(R,'Original'):('pass',''),(O,'ExistingSkip'):('skip','    fixture.go:7: external runtime unavailable\n')}
 if added:cases.update({k:('pass','') if fixed else v for k,v in EXPECTED_NEW.items()})
 for (p,t),(a,reason) in sorted(cases.items()):
  out.append({'Action':'run','Package':p,'Test':t})
  if reason:out.append({'Action':'output','Package':p,'Test':t,'Output':reason})
  out.append({'Action':a,'Package':p,'Test':t})
 out.extend({'Action':'fail' if added and not fixed else 'pass','Package':p} for p in sorted(PACKAGES))
 return out

def parsed(es):return parse('\n'.join(json.dumps(x) for x in es))
old,negative,fixed=events(),events(True),events(True,True)
assert compare(parsed(old),parsed(negative),parsed(fixed))
def reject(name,which,mutate):
 data=[copy.deepcopy(x) for x in [old,negative,fixed]];mutate(data[which])
 try:compare(*[parsed(x) for x in data])
 except (AssertionError,KeyError):return name
 raise AssertionError('evaluator accepted '+name)
results=[]
results.append(reject('pristine-unrelated-package-failure',0,lambda e:next(x for x in e if x.get('Package')==O and not x.get('Test') and x['Action']=='pass').update(Action='fail')))
results.append(reject('missing-identity',1,lambda e:e.__setitem__(slice(None),[x for x in e if x.get('Test')!='Original'])))
results.append(reject('duplicate-start',1,lambda e:e.append(next(copy.deepcopy(x) for x in e if x['Action']=='run'))))
results.append(reject('duplicate-outcome',1,lambda e:e.append(next(copy.deepcopy(x) for x in e if x.get('Test') and x['Action']=='fail'))))
results.append(reject('duplicate-package-outcome',1,lambda e:e.append(copy.deepcopy(e[-1]))))
results.append(reject('fixed-failure',2,lambda e:next(x for x in e if x.get('Test')=='Original' and x['Action']=='pass').update(Action='fail')))
results.append(reject('wrong-new-failure',1,lambda e:next(x for x in e if x.get('Test','').endswith('/unbounded') and x['Action']=='pass').update(Action='fail')))
results.append(reject('new-skip',2,lambda e:next(x for x in e if x.get('Test','').endswith('/unbounded') and x['Action']=='pass').update(Action='skip')))
results.append(reject('changed-original-skip',1,lambda e:next(x for x in e if x.get('Test')=='ExistingSkip' and x['Action']=='skip').update(Action='pass')))
results.append(reject('changed-skip-reason',1,lambda e:next(x for x in e if x.get('Test')=='ExistingSkip' and x['Action']=='output').update(Output='different reason\n')))
results.append(reject('missing-outcome',1,lambda e:e.remove(next(x for x in e if x.get('Test')=='Original' and x['Action']=='pass'))))
results.append(reject('missing-package',1,lambda e:e.pop()))
results.append(reject('build-fail',1,lambda e:e.append({'Action':'build-fail','Package':R})))
try:pristine(parsed(negative))
except AssertionError:results.append('pristine-failure')
else:raise AssertionError('accepted failed pristine suite')

# An original root omitted from every execution still must match pristine --list.
roots={(R,'Original'),(O,'ExistingSkip')}
check_inventory(parsed(old),roots)
try:
 check_inventory(parsed([e for e in old if e.get('Test')!='Original']),roots)
except AssertionError:results.append('same-omitted-original-listed-method')
else:raise AssertionError('accepted original omitted from all execution logs')
listdata=[{'Action':'start','Package':p} for p in sorted(PACKAGES)]
listdata+=[{'Action':'output','Package':p,'Output':'Test'+t+'\n'} for p,t in sorted(roots)]
listdata+=[{'Action':'pass','Package':p} for p in sorted(PACKAGES)]
assert listing('\n'.join(json.dumps(e) for e in listdata))=={(p,'Test'+t) for p,t in roots}
for name,events in [('duplicate-listed-method',listdata+[{'Action':'output','Package':R,'Output':'TestOriginal\n'}]),('missing-listed-package',listdata[:-1])]:
 # Use Test-prefixed roots to exercise actual Go method-line recognition.
 if name=='duplicate-listed-method':
  data=[dict(e,Output='TestOriginal\n') if e.get('Output')=='Original\n' else e for e in events]
 else:data=events
 try:listing('\n'.join(json.dumps(e) for e in data))
 except AssertionError:results.append(name)
 else:raise AssertionError('accepted '+name)

import tempfile,pathlib,shutil
here=pathlib.Path(__file__).parent
wf=here/'table-graphemes-native.yml'
if not wf.exists():wf=here.parents[1]/'.github/workflows/table-graphemes-native.yml'
with tempfile.TemporaryDirectory() as temp:
 root=pathlib.Path(temp);helpers=root/'.qualification/table-graphemes';helpers.mkdir(parents=True)
 for n in ['qualify.py','evaluator.py','evaluator_controls.py']:shutil.copy2(here/n,helpers/n)
 canonical=root/'.github/workflows/table-graphemes-native.yml';canonical.parent.mkdir(parents=True);shutil.copy2(wf,canonical)
 assert set(deployed_layout(root))=={'.qualification/table-graphemes/'+n for n in ['qualify.py','evaluator.py','evaluator_controls.py']}|{'.github/workflows/table-graphemes-native.yml'}
 shutil.copy2(wf,helpers/'table-graphemes-native.yml')
 try:deployed_layout(root)
 except AssertionError:results.append('flat-authoring-workflow-not-deployed-layout')
 else:raise AssertionError('accepted same-layout trap')
 (helpers/'table-graphemes-native.yml').unlink();canonical.unlink()
 try:deployed_layout(root)
 except AssertionError:results.append('missing-canonical-deployed-workflow')
 else:raise AssertionError('accepted missing canonical workflow')
print(json.dumps({'status':'PASS','kind':'synthetic evaluator interventions; not native source qualification','rejected':results},indent=2))
