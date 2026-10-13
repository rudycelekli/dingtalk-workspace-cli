import datetime, hashlib, json, os, pathlib, subprocess, xml.etree.ElementTree as ET
from evaluator import parse, pristine, compare, EXPECTED_NEW
BASE='59d1da576c6983582d5be11401e7efe07aaaa238'
HEAD='1e94487bbca6b96e09a21bd09fd3df3359caf4c2'
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
command(['python3',str(root/'.qualification/rotation/evaluator_controls.py')],root,'evaluator-controls')
for directory,sha in [(base,BASE),(fixed,HEAD)]:
 assert command(['git','rev-parse','HEAD'],directory,directory.name+'-head').decode().strip()==sha
 command(['git','diff','--exit-code'],directory,directory.name+'-clean')
tracked=['.changes/whiteboard-rotated-preview-bounds.md','internal/whiteboard/render/renderer.go','internal/whiteboard/render/renderer_rotation_test.go','skills/mono/references/products/whiteboard/render.md','skills/multi/dingtalk-misc/references/whiteboard/render.md']
hashes={'.changes/whiteboard-rotated-preview-bounds.md': 'ce777f6e9329ae6c5a3c7ad4a26667eb35d44a55818d8472c298e39b6eb2382f', 'internal/whiteboard/render/renderer.go': '8e26e57d434596f1c59d73368f48e45180c877de7d6bd02c4fce1c4ab21e8a35', 'internal/whiteboard/render/renderer_rotation_test.go': '4583995a8976910b47ffebe1b0a3088be6b3ff87349f0b79dbeb2816f0af83e6', 'skills/mono/references/products/whiteboard/render.md': '198490cd92f7607a9bc358e58900b4c97e5a2beff4e28941f6fe2ee00540db2e', 'skills/multi/dingtalk-misc/references/whiteboard/render.md': '198490cd92f7607a9bc358e58900b4c97e5a2beff4e28941f6fe2ee00540db2e'}
assert hashes=={p:hashlib.sha256((fixed/p).read_bytes()).hexdigest() for p in tracked}
assert command(['git','rev-parse','HEAD^'],fixed,'candidate-parent').decode().strip()==BASE
assert set(command(['git','diff','--name-only',BASE,HEAD],fixed,'changed-paths').decode().splitlines())==set(tracked)
version=command(['go','version'],fixed,'go-version').decode().strip()
assert version=='go version go1.26.7 linux/amd64',version
command(['uname','-a'],fixed,'native-uname')
packages=['./internal/whiteboard/render','./internal/whiteboard/opennodes']
def suite(directory,label,expected=0,race=False):
 args=['go','test','-json','-count=1']+(['-race'] if race else [])+packages
 raw=command(args,directory,label,expected)
 result=parse(raw)
 (proof/(label+'-outcomes.json')).write_text(json.dumps({'tests':[{'package':k[0],'test':k[1],'action':v[0],'skipReason':v[1]} for k,v in sorted(result[0].items())],'packages':result[1]},indent=2))
 return result
original=pristine(suite(base,'baseline-original'))
(base/tracked[2]).write_bytes((fixed/tracked[2]).read_bytes())
negative=suite(base,'baseline-regression',1)
compare(original,negative)
positive=suite(fixed,'candidate-regression');raced=suite(fixed,'candidate-race',race=True)
compare(original,negative,positive);compare(original,negative,raced)
# Remove transplanted test before validating the immutable baseline CLI.
(base/tracked[2]).unlink()
for directory in [base,fixed]:
 command(['make','build'],directory,directory.name+'-shipping-build')
 cli_env=dict(env,DWS_CONFIG_DIR=str(proof/(directory.name+'-config')))
 cli_env.update({k:'http://127.0.0.1:9' for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']})
 for angle in [90,0]:
  fixture=proof/(directory.name+'-'+str(angle)+'.json');svg=fixture.with_suffix('.svg')
  fixture.write_text(json.dumps({'schemaVersion':'1.0','catalogVersion':'dml-v1','nodes':[{'id':'card','type':'shape','x':0,'y':0,'width':300,'height':40,'angle':angle,'geometry':'dml:rect'}]}))
  raw=command([str(directory/'dws'),'whiteboard','render','--source','@'+str(fixture),'--output',str(svg),'--format','json','--yes'],directory,directory.name+'-cli-'+str(angle),extra=cli_env)
  data=json.loads(raw)['data'];assert data['remoteReads'] is False and data['exactCount']==1
  want=[-24,-154,348,348] if directory==fixed and angle==90 else [-24,-24,348,88]
  view=[float(x) for x in ET.parse(svg).getroot().attrib['viewBox'].split()]
  assert view==want,(directory,angle,view)
for directory,sha in [(base,BASE),(fixed,HEAD)]:
 command(['git','diff','--exit-code'],directory,directory.name+'-final-clean')
 assert initial[directory.name]==checkout_bytes(directory,sha,directory.name+'-final')
assert hashes=={p:hashlib.sha256((fixed/p).read_bytes()).hexdigest() for p in tracked}
(proof/'receipt.json').write_text(json.dumps({'status':'PASS','base':BASE,'head':HEAD,'sourceHashes':hashes,'originalTests':len(original[0]),'originalSkips':[{'package':k[0],'test':k[1],'reason':v[1]} for k,v in original[0].items() if v[0]=='skip'],'newOutcomes':[{'package':k[0],'test':k[1],'action':v[0]} for k,v in EXPECTED_NEW.items()],'runtime':command(['go','version'],fixed,'go-version-final').decode().strip(),'scope':'complete renderer and opennodes packages, race, shipping CLI controls; not full repository suite'},indent=2))
