"""Fresh-login spectator startup, executing original ARM64 actor allocation.

Run the real arena-start prefix, roster-capacity getter and array setter.
Native image resources, object allocators and actor field construction are
fixtures; no live session or iPhone is represented by this test.
"""
import base64,json
from pathlib import Path
import test_native_watch as t
from unicorn.arm64_const import UC_ARM64_REG_PC

fixture=json.loads((Path(__file__).parent/'testdata/aot285.json').read_text())
for address in ('0x547f84','0x5122f0','0x5123e8','0x5483a4'):
 raw=base64.b64decode(fixture['chunks'][address]);at=t.MAIN+int(address,16)
 t.u.mem_write(at,raw);t.u.ctl_remove_cache(at,at+len(raw))
 t.nativeRanges.append((at,at+len(raw)))
entered=[];args=[]
def initialize():t.put(t.reg(1)+9,'<B',2);t.ret()
def enter():
 global args
 args=[t.reg(i)for i in range(7)];entered.append(args)
 # Keep PC unchanged: execute the native prologue and initialization.
def player_array():
 n=t.reg(1);assert n==100
 p=t.alloc(0x18+n*8);t.put(p+0x10,'<i',n);t.ret(p)
def shorts():
 n=t.reg(1);p=t.alloc(0x14+n*2);t.put(p+0x10,'<i',n);t.ret(p)
def finish_prefix():
 a,c,g,cam,back,oldMap,oldTiles=t.objects[0]
 players=t.get(t.MAIN+t.actors[0],'<Q');array=t.get(players+0xa0,'<Q')
 assert array and t.get(array+0x10,'<i')==100,'Original start did not allocate the actor array'
 values=[list(__import__('struct').unpack('<100q',t.u.mem_read(args[i]+0x18,800)))for i in (3,4,5)]
 clock=t.alloc(0x30);t.put(a+0x110,'<Q',clock);t.put(a+0xd8,'<Q',t.alloc(0x30))
 for slot,x in enumerate(values[0]):
  if x==-1:continue
  player=t.alloc(0x200);t.put(array+0x18+slot*8,'<Q',player)
  t.put(player+0x114,'<ii',x,values[1][slot]);t.put(player+0x68,'<q',values[2][slot]);t.put(player+0xa4,'<i',85)
 t.u.reg_write(UC_ARM64_REG_PC,t.MAIN+0x5483a4)
t.extraNative.update({
 t.MAIN+0x547f84:enter,t.MAIN+0x5480c0:finish_prefix,
 t.MAIN+0x12e7330:initialize,
 t.MAIN+0x1f64a4:lambda:t.ret(t.alloc(0x30)),
 t.MAIN+0x4f83cc:lambda:t.ret(),
 t.MAIN+0x5122a4:lambda:t.ret(t.alloc(0x30)),t.MAIN+0x512980:lambda:t.ret(),
 t.MAIN+0x548758:player_array,t.MAIN+0x512464:lambda:t.ret(),
 t.MAIN+0x12e7cc8:shorts,t.MAIN+0x5124e0:lambda:t.ret(),t.MAIN+0x512520:lambda:t.ret()})
for attempt in range(3):
 a,c,g,cam,back,oldMap,oldTiles=t.objects[0]
 players=t.get(t.MAIN+t.actors[0],'<Q');t.put(players+0xa0,'<Q',0)
 t.stillWatching=True
 for cmd,encoded in t.trace:
  p=base64.b64decode(encoded)
  if cmd==-102 and p[3]in(3,4,5,7):
   assert t.packet(0,p)==1,('Fresh login cannot reach native actor initialization',attempt,p[3],len(entered))
  elif cmd in(8,24,22):t.observe(0,cmd,p)
 assert t.call('_AGNativeWatchRunning',0)
 t.call('_AGNativeWatchEnd',t.ENV,0)
 assert t.get(players+0xa0,'<Q')==0
assert len(entered)==3
print('PASS original ARM64 initialization: no actor array before SP5, native start allocates its own roster, 3 cold-start/re-entry snapshots complete')
