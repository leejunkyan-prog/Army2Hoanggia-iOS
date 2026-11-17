"""Audited native-only overlay on the exact user-supplied312 IPA.

Eight original arena steps per Max update owner; UI loops sleep33ms. Never
accelerate input, mutate packet payloads, or bypass the existing spectator
owner. Keep the private inventory vector through original C6.n updates.
"""
from pathlib import Path
from struct import unpack_from,pack_into,pack
from hashlib import sha256
from zipfile import ZipFile,ZIP_DEFLATED
from copy import copy
import plistlib,json
from keystone import Ks,KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN
BASE_IPA='8a39193b9843365fd81b863fc8aa03db066d27d6da6e1f184771602d21fe55c2'
CAVE=0x250c000;EXTRA=0x4000;STEPS=8
CANVAS=(0x207dac0,0x20ad740,0x20db440,0x2109130,0x2136e20,0x2164b10)
ARENA=(0x2082e30,0x20b23a0,0x20e0090,0x210dd80,0x213ba70,0x2169760)
INVENTORY=(0x591cdc,0x67b2c0,0x75ff84,0x844c48,0x92990c,0xa0e5d0)
ks=Ks(KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN)
def asm(s,at):return bytes(ks.asm(s,addr=at)[0])
def branch_target(raw,off,pc):
 w=unpack_from('<I',raw,off)[0];n=w&0x3ffffff
 assert w&0x7c000000==0x14000000
 return pc+4*(n-(1<<26) if n&(1<<25) else n)
def extend(raw):
 """Grow existing RX segment. Move only LINKEDIT and its file-offset fields."""
 d=bytearray(raw);pos=32;commands=[];cut=None
 for _ in range(unpack_from('<I',d,16)[0]):
  cmd,n=unpack_from('<II',d,pos);commands.append((pos,cmd,n))
  if cmd==0x19 and bytes(d[pos+8:pos+24]).split(b'\0')[0]==b'__LINKEDIT':cut=unpack_from('<Q',d,pos+40)[0]
  pos+=n
 assert cut==0x24cc000 and len(d)>cut
 for p,cmd,n in commands:
  if cmd==0x19:
   name=bytes(d[p+8:p+24]).split(b'\0')[0]
   if name==b'__AGSCENE':
    assert unpack_from('<QQQQ',d,p+24)==(0x102508000,0x4000,0x24c8000,0x4000)
    pack_into('<Q',d,p+32,0x8000);pack_into('<Q',d,p+48,0x8000)
   elif name==b'__LINKEDIT':
    pack_into('<Q',d,p+24,unpack_from('<Q',d,p+24)[0]+EXTRA);pack_into('<Q',d,p+40,cut+EXTRA)
  elif cmd==0x2: # symtab
   for q in (p+8,p+16):
    v=unpack_from('<I',d,q)[0]
    if v>=cut:pack_into('<I',d,q,v+EXTRA)
  elif cmd==0xb: # dysymtab: file offsets, not symbol indices
   for q in (32,40,48,56,64,72):
    v=unpack_from('<I',d,p+q)[0]
    if v>=cut:pack_into('<I',d,p+q,v+EXTRA)
  elif cmd in (0x22,0x80000022):
   for q in (8,16,24,32,40):
    v=unpack_from('<I',d,p+q)[0]
    if v>=cut:pack_into('<I',d,p+q,v+EXTRA)
  elif cmd in (0x26,0x29,0x2b,0x2e,0x80000033,0x80000034):
   v=unpack_from('<I',d,p+8)[0]
   if v>=cut:pack_into('<I',d,p+8,v+EXTRA)
  assert cmd!=0x1d,'Input must be unsigned'
 return d[:cut]+bytearray(EXTRA)+d[cut:],pos

def patch(raw):
 d,header_end=extend(raw);edits=[];maps=[]
 def offset(a):return a-0x40000 if a>=0x24f8000 else a
 def put(a,code,purpose):
  p=offset(a);old=bytes(d[p:p+len(code)]);d[p:p+len(code)]=code
  edits.append({'address':a,'offset':p,'purpose':purpose,'before':old.hex(),'after':code.hex()})
 def load_global(reg,slot):return f'adrp x{reg}, {slot&~4095};ldr x{reg}, [x{reg}, #{slot&4095}]'
 def active(v,fail):
  return f'''{load_global(9,CANVAS[v])};cbz x9,{fail};{load_global(10,ARENA[v])};cbz x10,{fail};ldr x10,[x10,#0xe8];cbz x10,{fail};ldr x11,[x9,#0xb8];cmp x10,x11;b.ne {fail};ldr x11,[x9,#0x108];cbnz x11,{fail};ldr x11,[x9,#0xe0];cbz x11,no_menu;ldrb w12,[x11,#0x2c];cbnz w12,{fail};no_menu:'''
 for v in range(6):
  base=CAVE+v*0x600;batch=base;original=base+0x200;pace=base+0x240;inventory=base+0x380
  old_update=0x24f91d0+v*0x12e0;old_pace=0x24f92a0+v*0x12e0
  op=offset(old_pace);getter=branch_target(raw,op+0x48,old_pace+0x48);loop=branch_target(raw,op+0x60,old_pace+0x60)
  old=raw[offset(old_update):offset(old_update)+8]
  assert old[:4]==bytes.fromhex('fc6fbaa9')
  original_return=branch_target(raw,offset(old_update)+4,old_update+4)
  put(original,old[:4]+asm(f'b {original_return}',original+4),f'PB{v+1} preserve original arena prologue')
  code=f'''stp x29,x30,[sp,#-64]!;stp x19,x20,[sp,#16];stp x21,x22,[sp,#32];mov x29,sp;mov x19,x0;mov x20,x1;mov w21,#1;bl {getter};cmp w0,#10;b.ne run;{active(v,'run')};cmp x10,x20;b.ne run;mov w21,#{STEPS};run:mov x0,x19;mov x1,x20;bl {original};subs w21,w21,#1;b.eq done;{load_global(9,CANVAS[v])};cbz x9,done;ldr x10,[x9,#0xb8];cmp x10,x20;b.ne done;ldr x10,[x9,#0x108];cbnz x10,done;ldr x10,[x9,#0xe0];cbz x10,next;ldrb w10,[x10,#0x2c];cbnz w10,done;next:b run;done:ldp x21,x22,[sp,#32];ldp x19,x20,[sp,#16];ldp x29,x30,[sp],#64;ret'''
  b=asm(code,batch);assert len(b)<=0x200;put(batch,b,f'PB{v+1} bounded original simulation batch, same update owner')
  put(old_update,asm(f'b {batch}',old_update),f'PB{v+1} attach batch to existing simulation entry')
  code=f'''ldr x0,[sp,#16];mov x1,#33;{active(v,'sleep')};mov x1,#1;ldrb w10,[x9,#0x13c];cbz w10,sleep;mov w10,#19;str w10,[x9,#0x118];sleep:bl {0xac30dc};ldp x29,x30,[sp],#32;b {loop}'''
  p=asm(code,pace);assert len(p)<=0x140;put(pace,p,f'PB{v+1} Max UI33ms / active arena1ms and original next-frame HP notify')
  assert raw[op+0x5c:op+0x60]==bytes.fromhex('fd7bc2a8')
  put(old_pace+0x5c,asm(f'b {pace}',old_pace+0x5c),f'PB{v+1} pace only Max; lower levels unchanged')
  site=INVENTORY[v];assert raw[site:site+4]==bytes.fromhex('283900f9')
  code=f'''str x10,[sp,#-16]!;ldr x10,[x9,#0x70];cbz x10,initial;mov x8,x10;b ready;initial:str x8,[x9,#0x70];ready:ldr x10,[sp],#16;b {site+4}'''
  put(inventory,asm(code,inventory),f'PB{v+1} keep stable private chest vector and coherent native length')
  put(site,asm(f'b {inventory}',site),f'PB{v+1} avoid transient source/display vector flip')
  maps.append({'v':v,'batch':batch,'original':original,'pace':pace,'inventory':inventory,'old_update':old_update,'old_pace':old_pace,'getter':getter,'loop':loop,'inventory_site':site,'original_return':original_return})
 # Except audited hooks/header, all previous code/resources remain exact.
 expected=bytearray(raw[:0x24cc000])+bytearray(EXTRA)+bytearray(raw[0x24cc000:])
 permitted=bytearray(len(d));permitted[:header_end]=b'\1'*header_end
 for e in edits:permitted[e['offset']:e['offset']+len(bytes.fromhex(e['after']))]=b'\1'*len(bytes.fromhex(e['after']))
 assert all(a==b or permitted[i] for i,(a,b) in enumerate(zip(expected,d)))
 return bytes(d),{'header_end':header_end,'steps':STEPS,'variants':maps,'edits':edits,'base_native_sha256':sha256(raw).hexdigest(),'native_sha256':sha256(d).hexdigest()}

def package(source,target):
 source,target=Path(source),Path(target);data=source.read_bytes();assert sha256(data).hexdigest()==BASE_IPA
 with ZipFile(source) as z:
  app='Payload/Army2Hoanggia.app/';native,report=patch(z.read(app+'Army2Hoanggia'));info=plistlib.loads(z.read(app+'Info.plist'));assert info['CFBundleVersion']=='312';info['CFBundleVersion']='313'
  changes={app+'Army2Hoanggia':native,app+'Info.plist':plistlib.dumps(info,fmt=plistlib.FMT_BINARY)}
  with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=6) as out:
   for entry in z.infolist():out.writestr(copy(entry),changes.get(entry.filename,z.read(entry.filename)))
 with ZipFile(source) as old,ZipFile(target) as new:
  assert old.namelist()==new.namelist() and new.testzip() is None
  for n in old.namelist():
   if n not in changes:assert old.read(n)==new.read(n),n
 report.update(build=313,source_ipa_sha256=BASE_IPA,ipa_sha256=sha256(target.read_bytes()).hexdigest(),changed_files=list(changes),physical_device_tested=False)
 target.with_suffix('.validation.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
 import sys
 r=package(*sys.argv[1:]);print(json.dumps({k:r[k] for k in ('build','steps','ipa_sha256','changed_files')},indent=2))
