"""Extract exact user312/313 artifacts and run the installed ARM64 checks."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import json,plistlib,os,subprocess,sys,lief
import patch_speed313 as p
source,target=map(Path,sys.argv[1:3]);folder=target.parent.resolve();app='Payload/Army2Hoanggia.app/'
assert sha256(source.read_bytes()).hexdigest()==p.BASE_IPA
with ZipFile(source) as a,ZipFile(target) as b:
 assert a.testzip() is b.testzip() is None and a.namelist()==b.namelist()
 changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
 assert set(changed)=={app+'Army2Hoanggia',app+'Info.plist'}
 old=plistlib.loads(a.read(app+'Info.plist'));new=plistlib.loads(b.read(app+'Info.plist'));assert old.pop('CFBundleVersion')=='312' and new.pop('CFBundleVersion')=='313' and old==new
 oldraw=a.read(app+'Army2Hoanggia');newraw=b.read(app+'Army2Hoanggia')
 (folder/'native312').write_bytes(oldraw);(folder/'native313').write_bytes(newraw)
 fw=a.read(app+'Frameworks/AGWheel.framework/AGWheel');(folder/'AGWheel312').write_bytes(fw)
for label,raw in [('312',oldraw),('313',newraw)]:
 m=lief.MachO.parse(raw).at(0)
 assert not m.has_code_signature
 if label=='312':oldm=m
 else:
  assert [x.name for x in oldm.libraries]==[x.name for x in m.libraries]
  assert sorted((x.name,x.value) for x in oldm.symbols)==sorted((x.name,x.value) for x in m.symbols)
  assert [(x.symbol.name,x.address,x.addend) for x in oldm.dyld_info.bindings]==[(x.symbol.name,x.address,x.addend) for x in m.dyld_info.bindings]
  for name in ('__DATA','__AGDATA','__LINKEDIT'):
   s=next(s for s in oldm.segments if s.name==name);t=next(s for s in m.segments if s.name==name)
   assert oldraw[s.file_offset:s.file_offset+s.file_size]==newraw[t.file_offset:t.file_offset+t.file_size],name
root=Path(__file__).parent;env={**os.environ,'ARMY2_SPEED_QA':str(folder)}
for test in ('test_speed313','test_speed_inventory313','test_speed_projectiles313'):
 result=subprocess.run([sys.executable,str(root/(test+'.py')),str(folder/'AGWheel312')],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (folder/(test+'.txt')).write_text(result.stdout);print(result.stdout,end='');assert result.returncode==0,test
result=subprocess.run([sys.executable,str(root/'verify_endpoint290.py'),str(target),'--report',str(folder/'endpoint313-check.json')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(folder/'endpoint313-check.txt').write_text(result.stdout);assert result.returncode==0,result.stdout
report={'passed':True,'build':313,'base_sha256':p.BASE_IPA,'ipa_sha256':sha256(target.read_bytes()).hexdigest(),'changed_files':changed,'framework312_sha256':sha256(fw).hexdigest(),'all_other_entries_identical':True,'linkedit_symbols_bindings_preserved':True,'native_hook_cases':151,'inventory_interleavings':12000,'inventory_production_updates':3600,'original_projectile_updates':43,'native_initializers_checked':6,'physical_device_tested':False}
(folder/'Build313-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
