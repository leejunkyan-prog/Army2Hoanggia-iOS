"""Replay the native area -> room -> arena transition visible on iPhone.

Use the original ARM64 arena.show, Screen.show and GameCanvas screen setter.
JNI, allocation, terrain decoding and actor construction remain test fixtures.
"""
import base64,json
from pathlib import Path
import test_native_watch as t
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_SP,UC_ARM64_REG_LR

fixture=json.loads((Path(__file__).parent/'testdata/aot285.json').read_text())
for address in ('0x5ad9e8','0x50b910','0x542b58'):
 raw=base64.b64decode(fixture['chunks'][address]);at=t.MAIN+int(address,16)
 t.u.mem_write(at,raw);t.nativeRanges.append((at,at+len(raw)))
 t.u.ctl_remove_cache(at,at+len(raw))
def initialize():
 t.put(t.reg(1)+9,'<B',2);t.ret()
t.extraNative[t.MAIN+0x12e7330]=initialize
t.extraNative[t.MAIN+0x5acdf8]=lambda:t.ret()
def show_native(screen):
 t.u.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
 t.u.reg_write(t.UC_ARM64_REG_X0,t.ENV);t.u.reg_write(t.UC_ARM64_REG_X1,screen)
 try:t.u.emu_start(t.MAIN+0x5ad9e8,t.STOP+4,count=10000)
 except Exception:
  print('Screen transition PC',hex(t.u.reg_read(UC_ARM64_REG_PC)),'LR',hex(t.u.reg_read(UC_ARM64_REG_LR)))
  raise
 assert t.u.reg_read(UC_ARM64_REG_PC)==t.STOP

v=0;a,c,g,cam,back,oldMap,oldTiles=t.objects[v]
for attempt in range(3):
 t.stillWatching=True
 for cmd,encoded in t.trace:
  p=base64.b64decode(encoded)
  if cmd==-102 and p[3]in(3,4,5,7):
   assert t.packet(v,p)==1,('Native room transition prevents spectator presentation',attempt,p[3])
  elif cmd==8:
   t.observe(v,cmd,p)
   # Native cmd8 displays the room after SP3 saved the area list as back.
   # This mirrors the two characters/room thumbnail seen in the iPhone video.
   room=t.alloc(0x180);show_native(room)
   assert t.get(c+0xb8,'<Q')==room and room!=back
  elif cmd in(24,22):t.observe(v,cmd,p)
 assert t.call('_AGNativeWatchRunning',v)
 assert t.get(c+0xb8,'<Q')==t.get(a+0xe8,'<Q')
 assert t.get(t.get(a+0xe8,'<Q')+0x10,'<Q')==back
 t.call('_AGNativeWatchEnd',t.ENV,v)
 assert t.get(c+0xb8,'<Q')==back

# A canceled watch must never present over the destination chosen on exit.
for cmd,encoded in t.trace:
 p=base64.b64decode(encoded)
 if cmd==-102 and p[3]in(3,4):assert t.packet(v,p)==1
 elif cmd==8:t.observe(v,cmd,p)
other=t.alloc(0x180);show_native(other);t.stillWatching=False
assert t.packet(v,next(p for p in t.sp if p[3]==5))==0
assert t.get(c+0xb8,'<Q')==other
t.call('_AGNativeWatchEnd',t.ENV,v)
print('PASS original ARM64 screen methods: room activation between SP3/SP5, arena/map/actors presented, 3 leave/re-entry cycles, canceled watch cannot present')
