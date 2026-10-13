import datetime, hashlib, json, os, pathlib, subprocess, xml.etree.ElementTree as ET
from evaluator import parse, pristine, compare, EXPECTED_NEW
BASE='59d1da576c6983582d5be11401e7efe07aaaa238'
HEAD='f966df8bb00d4538b02dca2b46c647d5c4f28990'
root=pathlib.Path.cwd(); proof=root/'proof'; proof.mkdir()
base=root/'baseline'; fixed=root/'candidate'
env=dict(os.environ,DWS_PACKAGE_VERSION='0.0.0-test',DWS_NO_UPDATE_CHECK='1',DO_NOT_TRACK='1')
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

initial={directory.name:checkout_bytes(directory,sha,directory.name+'-initial') for directory,sha in [(base,BASE),(fixed,HEAD)]}
command(['python3',str(root/'.qualification/markdown-theme/evaluator_controls.py')],root,'evaluator-controls')
for directory,sha in [(base,BASE),(fixed,HEAD)]:
 assert command(['git','rev-parse','HEAD'],directory,directory.name+'-head').decode().strip()==sha
 command(['git','diff','--exit-code'],directory,directory.name+'-clean')
tracked=['.changes/markdown-theme-multiline-metadata.md', 'internal/helpers/markdown_theme.go', 'internal/helpers/markdown_theme_multiline_test.go', 'skills/mono/references/products/markdown.md', 'skills/multi/dingtalk-misc/references/markdown.md']
hashes={'.changes/markdown-theme-multiline-metadata.md': '87705348f8b2ffea3173358599e2e6103f8885fad0354e11620e2198c83ef057', 'internal/helpers/markdown_theme.go': '4b19223c46c54411f1010aac8d0d037183ddbff80c58e4a221f3b67095b35e88', 'internal/helpers/markdown_theme_multiline_test.go': 'f7db8d30e5448b65135172c4a67654fe785b8a2b75adf6f3d48dc081169f8516', 'skills/mono/references/products/markdown.md': '38e017585830dae22d5533cf2b2ff4e2a7e8ea573ec6d963e38d29f1ce2e1aea', 'skills/multi/dingtalk-misc/references/markdown.md': 'f05340410b3b51135cb6a9b31225ea540721b951a16ee412750e7fd8997f095e'}
assert hashes=={p:hashlib.sha256((fixed/p).read_bytes()).hexdigest() for p in tracked}
assert command(['git','rev-parse','HEAD^'],fixed,'candidate-parent').decode().strip()==BASE
assert set(command(['git','diff','--name-only',BASE,HEAD],fixed,'changed-paths').decode().splitlines())==set(tracked)
version=command(['go','version'],fixed,'go-version').decode().strip()
assert version=='go version go1.26.7 linux/amd64',version
command(['uname','-a'],fixed,'native-uname')
packages=['./internal/helpers','./test/unit']
pattern='^Test.*(Markdown.*Theme|ApplyMarkdownTheme|MarkdownBoundedLine|MonoMultiSkillContent)'
regressionPath='internal/helpers/markdown_theme_multiline_test.go'
def suite(directory,label,expected=0,race=False):
 args=['go','test','-json','-count=1','-covermode=atomic','-coverprofile='+str(proof/(label+'.coverage')),'-run',pattern]+(['-race'] if race else [])+packages
 raw=command(args,directory,label,expected)
 result=parse(raw)
 (proof/(label+'-outcomes.json')).write_text(json.dumps({'tests':[{'package':k[0],'test':k[1],'action':v[0],'skipReason':v[1]} for k,v in sorted(result[0].items())],'packages':result[1]},indent=2))
 return result
original=pristine(suite(base,'baseline-original'))
(base/regressionPath).write_bytes((fixed/regressionPath).read_bytes())
negative=suite(base,'baseline-regression',1)
compare(original,negative)
positive=suite(fixed,'candidate-regression');raced=suite(fixed,'candidate-race',race=True)
compare(original,negative,positive);compare(original,negative,raced)
coverage_env=dict(env,COVERAGE_TARGET='100',COVERAGE_OVERALL_TOLERANCE='0',COVERAGE_ENFORCE_OVERALL='false')
coverage=command(['./scripts/policy/check-coverage-gate.sh','--base-ref',BASE,'--overall-profile',str(proof/'candidate-regression.coverage'),'--baseline-profile',str(proof/'baseline-original.coverage'),'--diff-profile',str(proof/'candidate-regression.coverage')],fixed,'canonical-coverage-gate',extra=coverage_env)
assert b'changed code coverage: 100.0000%' in coverage,coverage

# Remove transplanted test before validating the immutable baseline CLI.
(base/regressionPath).unlink()
for directory in [base,fixed]:
 command(['make','build'],directory,directory.name+'-shipping-build')
 cli_env=dict(env,DWS_CONFIG_DIR=str(proof/(directory.name+'-config')))
 cli_env.update({k:'http://127.0.0.1:9' for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']})
 cases={
  'multiline-title':('---\ntitle: "first\nx-we-markdown-theme: songyan\nlast"\nother: keep\n---\n# Body\n',75,104),
  'real-theme-after':('---\ntitle: "first\nx-we-markdown-theme: songyan\nlast"\nx-we-markdown-theme: default\nother: keep\n---\n# Body\n',75,104),
  'ordinary':('---\ntitle: first\nx-we-markdown-theme: songyan\nother: keep\n---\n# Body\n',68,68),
  'quoted-control':('---\ntitle: "x-we-markdown-theme: songyan"\nother: keep\n---\n# Body\n',93,93),
 }
 for name,(content,baseline_size,fixed_size) in cases.items():
  fixture=proof/(directory.name+'-'+name+'.md');fixture.write_text(content)
  raw=command([str(directory/'dws'),'--dry-run','markdown','create','--file',str(fixture),'--space-id','test-space','--theme','qingya','--format','json'],directory,directory.name+'-cli-'+name,extra=cli_env)
  data=json.loads(raw);assert data['dry_run'] is True and data['executed'] is False and data['theme']=='qingya'
  assert data['file_size']==(fixed_size if directory==fixed else baseline_size),(directory,name,data)
  assert fixture.read_text()==content,'user source mutated'
for directory,sha in [(base,BASE),(fixed,HEAD)]:
 command(['git','diff','--exit-code'],directory,directory.name+'-final-clean')
 assert initial[directory.name]==checkout_bytes(directory,sha,directory.name+'-final')
assert hashes=={p:hashlib.sha256((fixed/p).read_bytes()).hexdigest() for p in tracked}
(proof/'receipt.json').write_text(json.dumps({'status':'PASS','base':BASE,'head':HEAD,'sourceHashes':hashes,'originalTests':len(original[0]),'originalSkips':[{'package':k[0],'test':k[1],'reason':v[1]} for k,v in original[0].items() if v[0]=='skip'],'newOutcomes':[{'package':k[0],'test':k[1],'action':v[0]} for k,v in EXPECTED_NEW.items()],'runtime':command(['go','version'],fixed,'go-version-final').decode().strip(),'scope':'complete targeted Markdown-theme/helper and mono-multi content identities, race, shipping CLI controls; not full helpers or repository suite'},indent=2))
