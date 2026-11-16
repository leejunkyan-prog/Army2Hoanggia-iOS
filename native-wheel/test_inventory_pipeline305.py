"""Run original C6.n between the global tick and existing grid callbacks."""
from pathlib import Path
import re,struct
import test_inventory_device282 as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
raw=(Path(__file__).parent/'build/base293-native').read_bytes()
grid=(Path(__file__).parent/'GridMap.h').read_text()
sites=[int(x,16) for x in re.findall(r'\{(0x[0-9a-f]+),0x[0-9a-f]+,GM_INV_SCROLL,\d,0\}',grid)]
paint=[int(x,16) for x in re.findall(r'\{(0x[0-9a-f]+),0x[0-9a-f]+,GM_HALF_INNER,\d,0\}',grid)]
fixed='_AGProfileAvatarRead' in t.symbols
halt_at=0;source_vec=0;native_calls={}
def target(a):
 x=struct.unpack_from('<I',raw,a)[0]&0x3ffffff
 if x&(1<<25):x-=1<<26
 return a+4*x
def hook(u,pc,size,_):
 if pc==halt_at:u.emu_stop()
 elif pc in native_calls:t.ret(native_calls[pc]())
 elif pc==t.B+0x1dfce8:t.ret(t.get(t.reg(1)+0x24,'<i'))
 elif pc in [t.B+0x1c6190,t.B+0x1c619c]:t.ret()
t.u.hook_add(UC_HOOK_CODE,hook)
for v,site in enumerate(sites):
 entry=site-0x6c
 t.u.mem_write(t.B+entry,raw[entry:site+4])
 native_calls[t.B+target(entry+0x20)]=lambda:0
 native_calls[t.B+target(entry+0x28)]=lambda:source_vec
 clazz=t.alloc(0x180);pool=t.alloc(0xc0);canvas=t.alloc(0x180);screen=t.alloc(0xe0)
 t.put(t.B+t.classes[v],'<Q',clazz);t.put(t.B+t.pools[v],'<Q',pool);t.put(t.B+t.canvases[v],'<Q',canvas)
 t.put(screen,'<Q',clazz);t.put(clazz+0xa0,'<Q',screen);t.put(canvas+0xb8,'<Q',screen)
 t.put(canvas+0x130,'<i',432);t.put(canvas+0x128,'<i',602)
 gear=t.item(70001,equipment=True);gem7=t.item(7,2000)
 source_vec=t.vector([gear,gem7]);t.put(pool+0xa8,'<Q',source_vec);t.put(screen+0x70,'<Q',source_vec)
 t.call('_AGInventoryTick',t.E,v)
 gem8=t.item(8,305);t.put(gem7+0x90,'<q',3)
 source_vec=t.vector([gear,gem7,gem8]);t.put(pool+0xa8,'<Q',source_vec)
 t.call('_AGInventoryTick',t.E,v);assert t.displayed(screen)[0]==8
 # Original native update overwrites the bridge's order after the global tick.
 halt_at=t.B+site;t.u.reg_write(UC_ARM64_REG_SP,t.S+0x30000);t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
 t.u.reg_write(UC_ARM64_REG_X0,t.E);t.u.reg_write(UC_ARM64_REG_X1,screen)
 t.u.emu_start(t.B+entry,t.STOP+4,count=100000)
 assert t.u.reg_read(UC_ARM64_REG_PC)==halt_at
 assert t.displayed(screen)==[70001,7,8]
 frame=t.alloc(31*8)
 t.u.mem_write(frame,struct.pack('<31Q',*[t.reg(i)&((1<<64)-1) for i in range(31)]))
 halt_at=0;t.call('_AGGridAdjust',frame,t.B+site)
 assert t.displayed(screen)==([8,70001,7] if fixed else [70001,7,8])
 if fixed:
  # A final paint callback also repairs any intervening native rebind.
  t.put(screen+0x70,'<Q',source_vec);g=t.alloc(0x60);t.put(frame+19*8,'<Q',t.E);t.put(frame+20*8,'<Q',g)
  t.call('_AGGridAdjust',frame,t.B+paint[v]);assert t.displayed(screen)[0]==8
  assert t.get(screen+0xc8,'<i')==0 and t.get(screen+0x90,'<Q')==gem8
 assert t.ids(source_vec)==[70001,7,8]
 t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
print('PASS305 original C6.n: all six PBs reproduce tick order overwrite, repair inside native scroll update and before paint, new gem first/selected, server vector untouched' if fixed else 'CONTROL304: original C6.n overwrites the sorted chest in all six PBs; existing native grid callbacks do not restore it')
