import json
PACKAGE_ROOT='github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/'
PACKAGES={PACKAGE_ROOT+'output',PACKAGE_ROOT+'tui'}
EXPECTED_NEW={('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/family'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/flag'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/skin-tone'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/ansi'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/ascii'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/cjk'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/combining'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/unsupported-escape'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/controls'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/zero-width'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/tui', 'TestCrossPlatformCoverageGraphemeColumns/empty'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTablePreservesFlagAndSkinToneClusters'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTablePreservesFlagAndSkinToneClusters/flag'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTablePreservesFlagAndSkinToneClusters/skin-tone'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes/flag-fits'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes/skin-tone-fits'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes/flag-prefix'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes/skin-tone-prefix'): ('fail', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes/combining'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes/ascii'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes/cjk'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes/one'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageTruncateUsesCompleteGraphemes/unbounded'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageGraphemeRawFormatsPreserveContent'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageGraphemeRawFormatsPreserveContent/json'): ('pass', ''), ('github.com/DingTalk-Real-AI/dingtalk-workspace-cli/internal/output', 'TestCrossPlatformCoverageGraphemeRawFormatsPreserveContent/csv'): ('pass', '')}
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
 assert packages=={p:'fail' for p in PACKAGES},'unrelated/missing package failure'
 if positive is not None:
  fixed,fixed_packages=positive
  assert set(fixed)==set(terms),'changed fixed identities'
  assert all(fixed[k]==v for k,v in old.items()),'changed original fixed outcome/skip reason'
  assert all(fixed[k]==('pass','') for k in EXPECTED_NEW),'new fixed failure or skip'
  assert fixed_packages==old_packages,'fixed package failure'
 return True


def listing(raw):
 import re
 starts=set();outcomes={};names=set()
 for line in raw.splitlines():
  e=json.loads(line);p=e.get('Package');a=e.get('Action')
  assert p in PACKAGES and a!='build-fail','unexpected listing/build failure'
  if a=='start':
   assert p not in starts,'duplicate listed package';starts.add(p)
  if a=='output':
   for item in e.get('Output','').splitlines():
    if re.fullmatch(r'(Test|Example|Fuzz)\S*',item):
     key=(p,item);assert key not in names,'duplicate listed method';names.add(key)
  if a in {'pass','fail','skip'}:
   assert not e.get('Test') and p not in outcomes,'duplicate listed outcome';outcomes[p]=a
 assert starts==PACKAGES==set(outcomes) and all(v=='pass' for v in outcomes.values()),'incomplete listed package'
 assert names,'empty method inventory'
 return names

def check_inventory(result,names):
 roots={k for k in result[0] if '/' not in k[1]}
 assert roots==names,'listed original method missing or unexpected'


def deployed_layout(root):
 import hashlib
 from pathlib import Path
 root=Path(root)
 helpers=root/'.qualification/table-graphemes'
 names={'qualify.py','evaluator.py','evaluator_controls.py'}
 assert {f.name for f in helpers.iterdir() if f.is_file()}==names,'deployed helper layout differs'
 workflow=root/'.github/workflows/table-graphemes-native.yml'
 assert workflow.is_file(),'canonical workflow missing'
 files={'.qualification/table-graphemes/'+n:helpers/n for n in names}
 files['.github/workflows/table-graphemes-native.yml']=workflow
 return {n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()}
