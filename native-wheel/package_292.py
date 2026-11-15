"""Build292: replace only the framework/UI over the exact supplied Build290 IPA.
Only the enumerated spectator bridge edits may change the game executable.
All server initialization code and endpoint literals remain byte-identical.
"""
from pathlib import Path
from hashlib import sha256
from struct import unpack_from,pack_into
from copy import copy
from zipfile import ZipFile,ZIP_DEFLATED
import json,plistlib
BASE_IPA='097cca0d082dabdfca0b88039e32e25e9437b4f067ccadfe3e2bed942d149e7f'
BASE_NATIVE='889afdfc35bdbb47f7f3abcd2327c97f631702158d2670f6c79c37b6d2485a06'
def unsigned(raw):
 data=bytearray(raw);count,size=unpack_from('<II',data,16);pos=32;commands=[]
 for _ in range(count):
  command,length=unpack_from('<II',data,pos)
  if command!=0x1d:commands.append(data[pos:pos+length])
  pos+=length
 header=b''.join(commands);data[32:32+size]=header+bytes(size-len(header));pack_into('<II',data,16,len(commands),len(header));return bytes(data)
def assemble(source,overlay,target):
 source,overlay,target=map(Path,(source,overlay,target))
 baseline,previous,build=BASE_IPA,'290','292'
 assert sha256(source.read_bytes()).hexdigest()==baseline
 app='Payload/Army2Hoanggia.app/';framework=app+'Frameworks/';changed={}
 with ZipFile(source)as base,ZipFile(overlay)as patch:
  original_native=base.read(app+'Army2Hoanggia')
  assert sha256(original_native).hexdigest()==BASE_NATIVE
  manifest=json.loads(patch.read('framework-sha256.json'))
  assert set(manifest)=={'AGWheel.framework/AGWheel','AGWheel.framework/viewer/lobby.js','AGWheel.framework/viewer/lobby.html','AGWheel.framework/viewer/pixel-ui.js','AGWheel.framework/viewer/battlefield.js','AGWheel.framework/viewer/native-watch.js','AGWheel.framework/viewer/native-watch.html'}
  for name,digest in manifest.items():
   data=patch.read(name);assert sha256(data).hexdigest()==digest;changed[framework+name]=data
  for variant in range(1,7):
   resource=f'pb{variant}.png'
   changed[framework+'AGWheel.framework/viewer/art/'+resource]=base.read(app+'gameres/'+resource)
  name=framework+'AGWheel.framework/AGWheel';raw=changed[name];assert raw[:8]==bytes.fromhex('cffaedfe0c000001')
  symbols=['_AGRecipeDetail','_AGInventoryOrder','_AGInventoryResolve','_AGNativeWatchTryEnd','_AGNativeWatchPacket','_AGSceneHook']
  symbols+=['_AGNativeWatchFinishSnapshot','_AGNativeWatchToggleCamera']
  for symbol in symbols:assert symbol.encode()+b'\0'in raw,symbol
  from patch_spectator291 import framework_exports
  assert framework_exports(raw,b'_AGViewerStillWatching'), 'Spectator guard must be a dyld export, not a hidden symbol'
  assert framework_exports(raw,b'_AGNativeWatchTraceException'), 'Watch exception hook must be a dyld export'
  changed[name]=unsigned(raw)
  from patch_spectator292 import patch_native
  native,edits=patch_native(original_native,changed[name])
  assert len(native)==len(original_native) and edits
  restored=bytearray(native);covered=set()
  for edit in edits:
   offset=edit['offset'];before=bytes.fromhex(edit['before']);after=bytes.fromhex(edit['after'])
   assert len(before)==len(after)>0 and 0<=offset<=len(native)-len(after)
   region=set(range(offset,offset+len(after)));assert not region&covered;covered|=region
   assert original_native[offset:offset+len(before)]==before
   assert native[offset:offset+len(after)]==after
   restored[offset:offset+len(before)]=before
  assert bytes(restored)==original_native
  from package_290 import INITIALIZERS
  protected=[(at,at+0xd8) for at in INITIALIZERS]
  protected += [(0x5702f0,0x570394),(0x145f160,0x145f1c0)]
  for start,end in protected:assert native[start:end]==original_native[start:end]
  changed[app+'Army2Hoanggia']=native
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
   assert out.read(app+'Army2Hoanggia')==native
   b=out.read(framework+'AGWheel.framework/AGWheel');n=unpack_from('<I',b,16)[0];pos=32
   for _ in range(n):
    command,length=unpack_from('<II',b,pos);assert command!=0x1d
    if command==0x2c:assert unpack_from('<I',b,pos+16)[0]==0
    pos+=length
 report={'server_unchanged':True,'native_sha256':sha256(native).hexdigest(),'source_native_sha256':BASE_NATIVE,'native_edits':edits,'file':target.name,'sha256':sha256(target.read_bytes()).hexdigest(),'source_ipa_sha256':baseline,'game_executable_unchanged':False,'only_enumerated_native_edits':True,'changed':sorted(expected),'physical_device_tested':False}
 target.with_suffix('.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':
 import sys
 assemble(*sys.argv[1:])

