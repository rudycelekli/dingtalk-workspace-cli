import copy,json
from evaluator import PACKAGES,PACKAGE_ROOT,EXPECTED_NEW,parse,compare,pristine
R=PACKAGE_ROOT+'internal/helpers';O=PACKAGE_ROOT+'test/unit'
def events(added=False,fixed=False):
 out=[{'Action':'start','Package':p} for p in sorted(PACKAGES)]
 cases={(R,'Original'):('pass',''),(O,'ExistingSkip'):('skip','    fixture.go:7: external runtime unavailable\n')}
 if added:cases.update({k:('pass','') if fixed else v for k,v in EXPECTED_NEW.items()})
 for (p,t),(a,reason) in sorted(cases.items()):
  out.append({'Action':'run','Package':p,'Test':t})
  if reason:out.append({'Action':'output','Package':p,'Test':t,'Output':reason})
  out.append({'Action':a,'Package':p,'Test':t})
 out.extend({'Action':'fail' if p==R and added and not fixed else 'pass','Package':p} for p in sorted(PACKAGES))
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
results.append(reject('same-unrelated-unit-package-failure',1,lambda e:next(x for x in e if x.get('Package')==O and not x.get('Test') and x['Action']=='pass').update(Action='fail')))
results.append(reject('missing-identity',1,lambda e:e.__setitem__(slice(None),[x for x in e if x.get('Test')!='Original'])))
results.append(reject('duplicate-start',1,lambda e:e.append(next(copy.deepcopy(x) for x in e if x['Action']=='run'))))
results.append(reject('duplicate-outcome',1,lambda e:e.append(next(copy.deepcopy(x) for x in e if x.get('Test') and x['Action']=='fail'))))
results.append(reject('duplicate-package-outcome',1,lambda e:e.append(copy.deepcopy(e[-1]))))
results.append(reject('fixed-failure',2,lambda e:next(x for x in e if x.get('Test')=='Original' and x['Action']=='pass').update(Action='fail')))
results.append(reject('wrong-new-failure',1,lambda e:next(x for x in e if x.get('Test','').endswith('/ordinary-root') and x['Action']=='pass').update(Action='fail')))
results.append(reject('new-skip',2,lambda e:next(x for x in e if x.get('Test','').endswith('/ordinary-root') and x['Action']=='pass').update(Action='skip')))
results.append(reject('changed-original-skip',1,lambda e:next(x for x in e if x.get('Test')=='ExistingSkip' and x['Action']=='skip').update(Action='pass')))
results.append(reject('changed-skip-reason',1,lambda e:next(x for x in e if x.get('Test')=='ExistingSkip' and x['Action']=='output').update(Output='different reason\n')))
results.append(reject('missing-outcome',1,lambda e:e.remove(next(x for x in e if x.get('Test')=='Original' and x['Action']=='pass'))))
results.append(reject('missing-package',1,lambda e:e.pop()))
results.append(reject('build-fail',1,lambda e:e.append({'Action':'build-fail','Package':R})))
try:pristine(parsed(negative))
except AssertionError:results.append('pristine-failure')
else:raise AssertionError('accepted failed pristine suite')
print(json.dumps({'status':'PASS','kind':'synthetic evaluator interventions; not native source qualification','rejected':results},indent=2))
