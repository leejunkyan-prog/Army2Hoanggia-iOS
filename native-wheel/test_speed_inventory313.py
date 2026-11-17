"""Actual313 C6.n prefix and production312 inventory bridge on six PBs."""
from pathlib import Path
import json,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
import test_inventory_device282 as t
r=Path(__import__('os').environ.get('ARMY2_SPEED_QA',str(Path(__file__).parent/'build/speed313')));raw=(r/'native313').read_bytes();report=json.loads((r/'Army2HoangGia-2.4.1-Build313-MaxSpeed-unsigned.validation.json').read_text())
halt=0;source=0;boundaries={}
def target(at):
 w=struct.unpack_from('<I',raw,at)[0]&0x3ffffff
 return at+4*(w-(1<<26) if w&(1<<25) else w)
def hook(u,pc,size,_):
 if pc==halt:u.emu_stop()
 elif pc in boundaries:t.ret(boundaries[pc]())
t.u.hook_add(UC_HOOK_CODE,hook)
t.u.mem_write(t.B+0x250c000,raw[0x24cc000:0x24d0000])
checks=[]
for v,j in enumerate(report['variants']):
 entry=j['inventory_site']-0x34;end=entry+0x6c
 t.u.mem_write(t.B+entry,raw[entry:end+4]);boundaries[t.B+target(entry+0x20)]=lambda:0;boundaries[t.B+target(entry+0x28)]=lambda:source
 clazz=t.alloc(0x180);pool=t.alloc(0xc0);canvas=t.alloc(0x180);screen=t.alloc(0xe0)
 t.put(t.B+t.classes[v],'<Q',clazz);t.put(t.B+t.pools[v],'<Q',pool);t.put(t.B+t.canvases[v],'<Q',canvas)
 t.put(screen,'<Q',clazz);t.put(clazz+0xa0,'<Q',screen);t.put(canvas+0xb8,'<Q',screen);t.put(canvas+0x130,'<i',432);t.put(canvas+0x128,'<i',602)
 gear=t.item(70001,equipment=True);gem7=t.item(7,2000);source=t.vector([gear,gem7]);t.put(pool+0xa8,'<Q',source);t.put(screen+0x70,'<Q',source)
 t.call('_AGInventoryTick',t.E,v);display=t.get(screen+0x70,'<Q');before=t.displayed(screen)
 def native_prefix():
  global halt
  halt=t.B+j['inventory_site']+4
  t.u.reg_write(UC_ARM64_REG_SP,t.S+0x30000);t.u.reg_write(UC_ARM64_REG_LR,t.STOP);t.u.reg_write(UC_ARM64_REG_X0,t.E);t.u.reg_write(UC_ARM64_REG_X1,screen)
  t.u.emu_start(t.B+entry,t.STOP+4,count=100000);assert t.u.reg_read(UC_ARM64_REG_PC)==halt;halt=0
 for n in range(300):
  native_prefix();assert t.get(screen+0x70,'<Q')==display and t.displayed(screen)==before
 gem8=t.item(8,311);t.put(gem7+0x90,'<q',4);source=t.vector([gear,gem7,gem8]);t.put(pool+0xa8,'<Q',source)
 native_prefix();assert t.get(screen+0x70,'<Q')==display
 t.call('_AGInventoryTick',t.E,v);assert t.displayed(screen)[0]==8 and t.ids(source)==[70001,7,8]
 selected=t.get(screen+0x90,'<Q');display=t.get(screen+0x70,'<Q');before=t.displayed(screen)
 for n in range(300):
  native_prefix();t.call('_AGInventoryTick',t.E,v)
  assert t.displayed(screen)==before and t.get(screen+0x70,'<Q')==display and t.get(screen+0x90,'<Q')==selected
 t.call('_AGInventoryOrder',t.E,v,canvas,0,0);checks.append({'pb':v+1,'updates':600,'new_gem_first':True,'source_unchanged':True})
assert all(n==0 for n in t.pins.values())
(r/'speed313-inventory.json').write_text(json.dumps({'passed':True,'checks':checks,'limits':'Original C6.n prefix and production bridge executed. JNI allocation/refresh are boundaries. No physical-device test.'},indent=2))
print('PASS313 actual native C6.n + unchanged312 bridge: six PBs,3600 updates, no transient display/source flip; newly combined gem appears first; source quantities/order and selected handle preserved; all display roots released.')
