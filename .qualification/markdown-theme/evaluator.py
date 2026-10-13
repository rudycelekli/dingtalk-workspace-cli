import json
PACKAGE_ROOT='github.com/DingTalk-Real-AI/dingtalk-workspace-cli/'
PACKAGES={PACKAGE_ROOT+'internal/helpers',PACKAGE_ROOT+'test/unit'}
PREFIX='TestCrossPlatformCoverageMarkdownThemeMultilineMetadata'
FAIL_NAMES={PREFIX,*[PREFIX+'/'+x for x in ['double-quoted-title','single-quoted-title','real-theme-before','real-theme-after','duplicate-real-keys','owned-literal','owned-folded','owned-multiline-quoted','quoted-crlf']], 'TestCrossPlatformCoverageMarkdownThemeMultilineUploadBytes'}
PASS_NAMES={PREFIX+'/'+x for x in ['other-literal','other-folded','ordinary-root','malformed-owned-fallback']}
EXPECTED_NEW={(PACKAGE_ROOT+'internal/helpers',x):('fail' if x in FAIL_NAMES else 'pass','') for x in FAIL_NAMES|PASS_NAMES}
def parse(raw):
 starts=set(); terms={}; package_starts=set(); packages={}; outputs={}
 for line in raw.splitlines():
  event=json.loads(line); action=event.get('Action'); package=event.get('Package'); test=event.get('Test')
  assert action!='build-fail' and '[build failed]' not in event.get('Output',''),'build failure'
  assert package in PACKAGES,('unexpected package',package)
  key=(package,test)
  if action=='start':
   assert test is None and package not in package_starts,'duplicate package start'
   package_starts.add(package)
  if action=='run':
   assert test is not None and key not in starts,'duplicate test start'
   starts.add(key)
  if action=='output' and test:
   output=event.get('Output','')
   # Keep the actual skip diagnostics, excluding runner timing/status markers.
   if not output.lstrip().startswith(('=== RUN','=== PAUSE','=== CONT','--- PASS','--- FAIL','--- SKIP')):
    outputs.setdefault(key,[]).append(output)
  if action in {'pass','fail','skip'}:
   if test:
    assert key not in terms,'duplicate test outcome'
    terms[key]=(action,''.join(outputs.get(key,[])) if action=='skip' else '')
   else:
    assert package not in packages,'duplicate package outcome'
    packages[package]=action
 assert package_starts==PACKAGES==set(packages),'missing package'
 assert starts==set(terms),'missing test run or outcome'
 assert starts,'empty suite'
 return terms,packages

def pristine(result):
 terms,packages=result
 assert all(v[0] in {'pass','skip'} for v in terms.values()),'original failure'
 assert all(v=='pass' for v in packages.values()),'original package failure'
 return result

def compare(original,negative,positive=None):
 old,old_packages=pristine(original); terms,packages=negative
 assert all(terms.get(k)==v for k,v in old.items()),'changed/missing original outcome or skip reason'
 assert {k:v for k,v in terms.items() if k not in old}==EXPECTED_NEW,'wrong new outcomes'
 assert packages=={PACKAGE_ROOT+'internal/helpers':'fail',PACKAGE_ROOT+'test/unit':'pass'},'unrelated/missing package failure'
 if positive is not None:
  fixed,fixed_packages=positive
  assert set(fixed)==set(terms),'changed fixed identities'
  assert all(fixed[k]==v for k,v in old.items()),'changed original fixed outcome/skip reason'
  assert all(fixed[k]==('pass','') for k in EXPECTED_NEW),'new fixed failure or skip'
  assert fixed_packages==old_packages,'fixed package failure'
 return True
