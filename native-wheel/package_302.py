"""Build302: bind native recipe replies to the attached inventory screen.
Patch only audited recipe callback/shim sites. Server initializers, protocol
methods and endpoint literals remain unchanged.
"""
from pathlib import Path
from hashlib import sha256
from struct import unpack_from,pack_into
from copy import copy
from zipfile import ZipFile,ZIP_DEFLATED
import json,plistlib
from patch_recipe301 import patch_native
BASE_IPA='3d307b2951c6a8540052d4d259d9307b56bcf9103cd5989e39bbf3301e136378'
BASE_NATIVE='93e9c074725e3e5d087192cf29b498df8f71bbf542e9d09d7f20c4bc17a6f6c0'
def unsigned(raw):
 data=bytearray(raw);count,size=unpack_from('<II',data,16);pos=32;commands=[]
 for _ in range(count):
  command,length=unpack_from('<II',data,pos)
  if command!=0x1d:commands.append(data[pos:pos+length])
  pos+=length
 header=b''.join(commands);data[32:32+size]=header+bytes(size-len(header));pack_into('<II',data,16,len(commands),len(header));return bytes(data)
def assemble(source,overlay,target):
 source,overlay,target=map(Path,(source,overlay,target))
 baseline,previous,build=BASE_IPA,'293','302'
 assert sha256(source.read_bytes()).hexdigest()==baseline
 app='Payload/Army2Hoanggia.app/';framework=app+'Frameworks/';changed={}
 with ZipFile(source)as base,ZipFile(overlay)as patch:
  assert sha256(base.read(app+'Army2Hoanggia')).hexdigest()==BASE_NATIVE
  manifest=json.loads(patch.read('framework-sha256.json'))
  assert set(manifest)=={'AGWheel.framework/AGWheel','AGWheel.framework/viewer/lobby.js','AGWheel.framework/viewer/lobby.html','AGWheel.framework/viewer/pixel-ui.js','AGWheel.framework/viewer/battlefield.js','AGWheel.framework/viewer/native-watch.js','AGWheel.framework/viewer/native-watch.html'}
  for name,digest in manifest.items():
   data=patch.read(name);assert sha256(data).hexdigest()==digest;changed[framework+name]=data
  for variant in range(1,7):
   resource=f'pb{variant}.png'
   changed[framework+'AGWheel.framework/viewer/art/'+resource]=base.read(app+'gameres/'+resource)
  name=framework+'AGWheel.framework/AGWheel';raw=changed[name];assert raw[:8]==bytes.fromhex('cffaedfe0c000001')
  symbols=['_AGInventoryPrepareRecipe','_AGRecipeDetail','_AGRecipeDetailObject','_AGInventoryOrder','_AGInventoryResolve','_AGNativeWatchTryEnd','_AGNativeWatchPacket','_AGSceneHook']
  symbols+=['_AGNativeWatchFinishSnapshot','_AGNativeWatchToggleCamera','_AGThreadPulse','_AGThreadDiagnosticsSample','_AGCanvasRecoveryTrack','_AGCanvasRecoveryFrame','_AGCanvasRecoveryCopy','_AGCraftSample','_AGCraftDiagnosticCopy','_AGCraftEventsCopy']
  for symbol in symbols:assert symbol.encode()+b'\0'in raw,symbol
  patched_native,native_edits=patch_native(base.read(app+'Army2Hoanggia'),raw)
  changed[app+'Army2Hoanggia']=patched_native
  native_digest=sha256(patched_native).hexdigest()
  assert native_digest!=BASE_NATIVE
  changed[name]=unsigned(raw)
  info=plistlib.loads(base.read(app+'Info.plist'))
  assert info['CFBundleVersion']==previous and info['CFBundleShortVersionString']=='2.4.1'
  info['CFBundleVersion']=build
  changed[app+'Info.plist']=plistlib.dumps(info,fmt=plistlib.FMT_BINARY)
  expected=set(changed);target.parent.mkdir(parents=True,exist_ok=True)
  assert not target.exists()
  original=set(base.namelist())
  with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=6)as out:
   for entry in base.infolist():
    if '/_CodeSignature/'in entry.filename:continue
    out.writestr(copy(entry),changed.get(entry.filename,base.read(entry.filename)))
   for name in sorted(expected-original):out.writestr(name,changed[name])
  with ZipFile(target)as out:
   assert out.testzip()is None and len(out.namelist())==len(set(out.namelist()))
   assert plistlib.loads(out.read(app+'Info.plist'))['CFBundleVersion']==build
   for name in out.namelist():
    if name not in expected:assert out.read(name)==base.read(name),name
   assert sha256(out.read(app+'Army2Hoanggia')).hexdigest()==native_digest
   b=out.read(framework+'AGWheel.framework/AGWheel');n=unpack_from('<I',b,16)[0];pos=32
   for _ in range(n):
    command,length=unpack_from('<II',b,pos);assert command!=0x1d
    if command==0x2c:assert unpack_from('<I',b,pos+16)[0]==0
    pos+=length
 report={'server_unchanged':True,'native_sha256':native_digest,'source_native_sha256':BASE_NATIVE,'native_patch_sites':len(native_edits),'file':target.name,'sha256':sha256(target.read_bytes()).hexdigest(),'source_ipa_sha256':baseline,'game_executable_unchanged':False,'only_recipe_sites_changed':True,'changed':sorted(expected),'physical_device_tested':False}
 target.with_suffix('.native-patch.json').write_text(json.dumps({'source_sha256':BASE_NATIVE,'patched_sha256':native_digest,'edits':native_edits},indent=2))
 target.with_suffix('.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':
 import sys
 assemble(*sys.argv[1:])




