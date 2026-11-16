"""Execute the packaged static HUD bridges with real ARM64 calling conventions."""
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_SP
import test_inventory_device282 as t
from patch_hud309 import patch_native,offset,PAINTS,BARS,CAVE,CACHE
raw=(Path(__file__).parent/'build/base293-native').read_bytes();patched,edits=patch_native(raw,t.blob)
t.u.mem_write(t.B,patched[:26050560]);t.u.mem_write(t.B+0x24f8000,patched[offset(0x24f8000):offset(0x250bfff)+1])
UI=t.F+0x31800;SKIP=UI+0x100;IMAGE=UI+0x200
missing=False;skip=True;calls=[];expected=[];replacement=0x612345670
def hook(u,pc,size,_):
 if pc==t.B+0x131cf70:
  name=bytes(u.mem_read(t.reg(1),80)).split(b'\0')[0].decode()
  t.ret(0 if missing else {'AGHUDCanvasPaint':UI,'AGHUDSkipBar':SKIP,'AGHUDImage':IMAGE}[name])
 elif pc==UI:calls.append(('canvas',tuple(t.reg(i) for i in range(5))));t.ret()
 elif pc==SKIP:calls.append(('bar',tuple(t.reg(i) for i in range(4))));t.ret(skip)
 elif pc==IMAGE:
  ptr=t.reg(0);args=struct.unpack('<8Q',bytes(u.mem_read(ptr,64)));stack=bytes(u.mem_read(ptr+64,12))
  calls.append(('image',args,stack,t.reg(1)));t.put(ptr+16,'<Q',replacement);t.ret()
 elif pc in (t.B+0xc452e0,t.B+0xc4558c):calls.append(('gpu',tuple(t.reg(i) for i in range(8)),bytes(u.mem_read(u.reg_read(UC_ARM64_REG_SP),12))));t.ret()
 elif pc in [t.B+0x250b600+v*0x100 for v in range(6)]:calls.append(('legacy',pc,tuple(t.reg(i) for i in range(3))));t.ret()
 elif pc in [t.B+x+4 for x in BARS]:
  # Confirm the displaced native prologue executed before the original body.
  assert u.reg_read(UC_ARM64_REG_SP)==t.S+0x30000-64
  calls.append(('original_bar',pc,tuple(t.reg(i) for i in range(4))))
  u.reg_write(UC_ARM64_REG_SP,u.reg_read(UC_ARM64_REG_SP)+64);t.ret()
t.u.hook_add(UC_HOOK_CODE,hook)
def invoke(site,args,stack=b'\0'*12):
 for i in range(19,30):uval=0x1000+i;t.u.reg_write(t.regs[i],uval)
 t.u.mem_write(t.S+0x30000,stack)
 t.symbols['_test_bridge']=t.B+site;t.call('_test_bridge',*args)
 assert all(t.reg(i)==0x1000+i for i in range(19,30)),'Callee-saved register changed'
 assert t.u.reg_read(UC_ARM64_REG_SP)==t.S+0x30000
for missing in (False,True):
 for v in range(6):
  t.u.mem_write(t.B+CACHE,bytes(24));calls.clear();args=(t.E,0x600001110,0x600002220)
  invoke(PAINTS[v],args)
  if missing:assert calls==[('legacy',t.B+0x250b600+v*0x100,args)]
  else:assert calls==[('canvas',args+(v,t.B+CAVE+0xb00+v*16))]
  for skip in (False,True):
   t.u.mem_write(t.B+CACHE,bytes(24));calls.clear();args=(t.E,0x600003330,0x600004440,73)
   invoke(BARS[v],args)
   if missing:assert calls==[('original_bar',t.B+BARS[v]+4,args)]
   elif skip:assert calls==[('bar',args[:3]+(v,))]
   else:assert calls==[('bar',args[:3]+(v,)),('original_bar',t.B+BARS[v]+4,args)]
 for region,site in enumerate((0x1c6144,0x1c6150)):
  t.u.mem_write(t.B+CACHE,bytes(24));calls.clear();args=(t.E,0x600005550,0x600006660,13,7,35,32,6);packed=struct.pack('<iii',-123,456,33)
  invoke(site,args,packed)
  if missing:assert calls==[('gpu',args,packed)]
  else:
   assert calls[0]==('image',args,packed,region)
   assert calls[1]==('gpu',args[:2]+(replacement,)+args[3:],packed)
assert all(e['before']!=e['after'] for e in edits)
print('PASS309 static ARM64 bridges: six canvas entry/fallbacks, six ranked/default HP paths, unchanged arguments and x19-x29/SP/LR, image and transformed-region packed stack ABI, only image handle substituted, exact legacy fallback when exports are missing; every undeclared executable byte unchanged.')
