import datetime, hashlib, json, os, pathlib, subprocess, xml.etree.ElementTree as ET
from evaluator import parse, pristine, compare, EXPECTED_NEW, listing, check_inventory, deployed_layout
BASE='59d1da576c6983582d5be11401e7efe07aaaa238'
HEAD='e664fbc2ef6380bc521576dd235369126b6cefc6'
root=pathlib.Path.cwd(); proof=root/'proof'; proof.mkdir()
base=root/'baseline'; fixed=root/'candidate'
env=dict(os.environ,DWS_PACKAGE_VERSION='0.0.0-test',DWS_NO_UPDATE_CHECK='1',DO_NOT_TRACK='1',GOMAXPROCS='2',GOFLAGS='-p=2 -mod=readonly',GOTOOLCHAIN='local')
def command(args,cwd,label,expected=0,extra=None,timeout=600):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 try:
  p=subprocess.run(args,cwd=cwd,env=extra or env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
  stdout,stderr,actual,timed_out=p.stdout,p.stderr,p.returncode,False
 except subprocess.TimeoutExpired as error:
  stdout,stderr,actual,timed_out=error.stdout or b'',error.stderr or b'',None,True
 except OSError as error:
  stdout,stderr,actual,timed_out=b'',str(error).encode(),None,False
 end=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (proof/(label+'.stdout')).write_bytes(stdout);(proof/(label+'.stderr')).write_bytes(stderr)
 (proof/(label+'.command.json')).write_text(json.dumps({'argv':args,'cwd':str(cwd),'start':start,'end':end,'actualExit':actual,'expectedExit':expected,'timeoutSeconds':timeout,'timedOut':timed_out,'stdoutSHA256':hashlib.sha256(stdout).hexdigest(),'stderrSHA256':hashlib.sha256(stderr).hexdigest()},indent=2))
 assert not timed_out and actual==expected,(label,actual,timed_out)
 return stdout

def checkout_bytes(directory,sha,label):
 assert command(['git','rev-parse','HEAD'],directory,label+'-head').decode().strip()==sha
 entries=command(['git','ls-tree','-r','-z',sha],directory,label+'-tree').split(b'\0')
 manifest={}
 for entry in entries:
  if not entry:continue
  metadata,name=entry.split(b'\t',1);mode,kind,oid=metadata.split();assert kind==b'blob','unexpected submodule'
  path=directory/os.fsdecode(name)
  data=os.fsencode(os.readlink(path)) if mode==b'120000' else path.read_bytes()
  actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  assert actual==oid.decode(),('checkout blob mismatch',str(path))
  manifest[os.fsdecode(name)]={'gitBlob':actual,'sha256':hashlib.sha256(data).hexdigest()}
 (proof/(label+'-tracked-hashes.json')).write_text(json.dumps(manifest,indent=2))
 return manifest

harnessHead=command(['git','rev-parse','HEAD'],root,'harness-head-initial').decode().strip()
assert harnessHead==os.environ['GITHUB_SHA'],'deployed harness HEAD differs from actual workflow run'
harnessTree=command(['git','rev-parse','HEAD^{tree}'],root,'harness-tree-initial').decode().strip()
assert command(['git','rev-parse','HEAD^'],root,'harness-parent').decode().strip()==BASE
harnessFiles=deployed_layout(root)
assert pathlib.Path(__file__).resolve()==root/'.qualification/table-graphemes/qualify.py','wrong qualifier deployment'
assert set(command(['git','diff','--name-only',BASE,harnessHead],root,'harness-changed-paths').decode().splitlines())==set(harnessFiles)
for name,digest in harnessFiles.items():
 raw=command(['git','show',harnessHead+':'+name],root,'harness-blob-'+pathlib.Path(name).name)
 assert hashlib.sha256(raw).hexdigest()==digest,'harness deployed bytes differ from immutable Git blob'
(proof/'harness-binding.json').write_text(json.dumps({'head':harnessHead,'githubSha':os.environ['GITHUB_SHA'],'tree':harnessTree,'parent':BASE,'canonicalWorkflowSHA256':harnessFiles['.github/workflows/table-graphemes-native.yml'],'deployedHashes':harnessFiles},indent=2))
initial={directory.name:checkout_bytes(directory,sha,directory.name+'-initial') for directory,sha in [(base,BASE),(fixed,HEAD)]}
command(['python3',str(root/'.qualification/table-graphemes/evaluator_controls.py')],root,'evaluator-controls')
for directory,sha in [(base,BASE),(fixed,HEAD)]:
 assert command(['git','rev-parse','HEAD'],directory,directory.name+'-head').decode().strip()==sha
 command(['git','diff','--exit-code'],directory,directory.name+'-clean')
tracked=['go.mod', 'internal/tui/theme.go', 'internal/output/formatter.go', 'internal/tui/grapheme_columns_test.go', 'internal/output/grapheme_columns_test.go', '.changes/table-grapheme-columns.md']
hashes={'go.mod': '57572f31a8d109e2d7ae28803f16e86efa17d8acf37b22b56095efb182883f40', 'internal/tui/theme.go': '914158d5946a5d0c4c5953d14e6093575278bb7cf27dd81d8347a5391e82a612', 'internal/output/formatter.go': '1cda33c8f02b0c1bf53dc7a9ad2c217b4b971aca1511857ca3d76e08dd1e77e7', 'internal/tui/grapheme_columns_test.go': '485321ce0cd6bd2cdf89717d65bc4485346530989f6108413a2cf2e1b55d6d0a', 'internal/output/grapheme_columns_test.go': '8feb9d950507aa2ec979f8ed832c81d83532110b94c81acc35feffc6abe3c4ed', '.changes/table-grapheme-columns.md': 'a8ee2ca62bbaa6b5628653016ad6951dc6370c107464f28652b065b50173f2e1'}
assert hashes=={p:hashlib.sha256((fixed/p).read_bytes()).hexdigest() for p in tracked}
assert command(['git','rev-parse','HEAD^'],fixed,'candidate-parent').decode().strip()==BASE
assert set(command(['git','diff','--name-only',BASE,HEAD],fixed,'changed-paths').decode().splitlines())==set(tracked)
version=command(['go','version'],fixed,'go-version').decode().strip()
assert version=='go version go1.26.7 linux/amd64',version
command(['uname','-a'],fixed,'native-uname')
runtimeEnv=json.loads(command(['go','env','-json','GOOS','GOARCH','GOVERSION','CGO_ENABLED','GOFLAGS'],fixed,'native-go-env'))
assert {k:runtimeEnv[k] for k in ['GOOS','GOARCH','GOVERSION','GOFLAGS']}=={'GOOS':'linux','GOARCH':'amd64','GOVERSION':'go1.26.7','GOFLAGS':'-p=2 -mod=readonly'},runtimeEnv
packages=['./internal/output','./internal/tui']
def suite(directory,label,expected=0,race=False):
 args=['go','test','-json','-count=1','-covermode=atomic','-coverprofile='+str(proof/(label+'.coverage'))]+(['-race'] if race else [])+packages
 raw=command(args,directory,label,expected)
 result=parse(raw)
 (proof/(label+'-outcomes.json')).write_text(json.dumps({'tests':[{'package':k[0],'test':k[1],'action':v[0],'skipReason':v[1]} for k,v in sorted(result[0].items())],'packages':result[1]},indent=2))
 return result
original_methods=listing(command(['go','test','-json','-list','^(Test|Example|Fuzz)',*packages],base,'baseline-pristine-methods'))
fixed_methods=listing(command(['go','test','-json','-list','^(Test|Example|Fuzz)',*packages],fixed,'candidate-pristine-methods'))
new_methods={k for k in EXPECTED_NEW if '/' not in k[1]}
assert fixed_methods==original_methods|new_methods,'candidate method inventory changed'
original=pristine(suite(base,'baseline-original'))
check_inventory(original,original_methods)
regressionPaths=['internal/tui/grapheme_columns_test.go','internal/output/grapheme_columns_test.go']
for path in regressionPaths:
 assert not (base/path).exists()
 (base/path).write_bytes((fixed/path).read_bytes())
for directory in [base,fixed]:
 command(['go','test','-run','^$','-bench','^BenchmarkTableGraphemeColumns$','-benchmem','-benchtime=200ms','-count=3','./internal/output'],directory,directory.name+'-table-benchmark')
negative=suite(base,'baseline-regression',1)
compare(original,negative)
check_inventory(negative,fixed_methods)
positive=suite(fixed,'candidate-regression');raced=suite(fixed,'candidate-race',race=True)
compare(original,negative,positive);compare(original,negative,raced)
check_inventory(positive,fixed_methods);check_inventory(raced,fixed_methods)
coverage_env=dict(env,COVERAGE_TARGET='100',COVERAGE_OVERALL_TOLERANCE='0',COVERAGE_ENFORCE_OVERALL='false')
coverage=command(['./scripts/policy/check-coverage-gate.sh','--base-ref',BASE,'--overall-profile',str(proof/'candidate-regression.coverage'),'--baseline-profile',str(proof/'baseline-original.coverage'),'--diff-profile',str(proof/'candidate-regression.coverage')],fixed,'canonical-coverage-gate',extra=coverage_env)
assert b'changed code coverage: 100.0000%' in coverage,coverage
# Remove transplanted test before validating the immutable baseline CLI.
for path in regressionPaths:(base/path).unlink()
for directory in [base,fixed]:
 command(['make','build'],directory,directory.name+'-shipping-build')
 cli_env=dict(env,DWS_CONFIG_DIR=str(proof/(directory.name+'-config')))
 cli_env.update({k:'http://127.0.0.1:9' for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']})
 for cluster in ['🇨🇳','👍🏽']:
  content=cluster*40
  prefix=directory.name+'-cli-'+('flag' if cluster=='🇨🇳' else 'skin')
  args=[str(directory/'dws'),'mcp','published','invoke','fixture',content,'--params','{}','--dry-run']
  raw=command(args+['--format','json'],directory,prefix+'-json',extra=cli_env)
  data=json.loads(raw);assert data['dry_run'] is True and data['executed'] is False and data['tool']==content
  text=command(args+['--format','table'],directory,prefix+'-table',extra=cli_env)
  assert content.encode() in text,'unchanged key-value CLI content changed'
for directory,sha in [(base,BASE),(fixed,HEAD)]:
 command(['git','diff','--exit-code'],directory,directory.name+'-final-clean')
 assert initial[directory.name]==checkout_bytes(directory,sha,directory.name+'-final')
assert hashes=={p:hashlib.sha256((fixed/p).read_bytes()).hexdigest() for p in tracked}
assert command(['git','rev-parse','HEAD'],root,'harness-head-final').decode().strip()==harnessHead
assert command(['git','rev-parse','HEAD^{tree}'],root,'harness-tree-final').decode().strip()==harnessTree
assert deployed_layout(root)==harnessFiles,'harness changed during qualification'
command(['git','diff','--exit-code'],root,'harness-final-clean')
(proof/'receipt.json').write_text(json.dumps({'status':'PASS','base':BASE,'head':HEAD,'sourceHashes':hashes,'originalTests':len(original[0]),'originalSkips':[{'package':k[0],'test':k[1],'reason':v[1]} for k,v in original[0].items() if v[0]=='skip'],'newOutcomes':[{'package':k[0],'test':k[1],'action':v[0]} for k,v in EXPECTED_NEW.items()],'harnessHead':harnessHead,'harnessTree':harnessTree,'harnessHashes':harnessFiles,'runtimeEnv':runtimeEnv,'runtime':command(['go','version'],fixed,'go-version-final').decode().strip(),'coverage':'canonical repository gate100% changedstatements PASS; overall/scoped nonregression not enforced or claimed; not full repository coverage','scope':'complete output and tui packages, race, real shipping build and unchanged dryrun key-value content controls; not full repository suite'},indent=2))
