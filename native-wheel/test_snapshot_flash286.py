"""Replay the actual native HP-flash routine between SP5 and SP7."""
import base64,json
from pathlib import Path
import test_native_watch as t
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_SP,UC_ARM64_REG_LR

fixture=json.loads((Path(__file__).parent/'testdata/aot285.json').read_text())
flash=base64.b64decode(fixture['chunks']['0x541c50'])
t.u.mem_write(t.MAIN+0x541c50,flash)
t.nativeRanges.append((t.MAIN+0x541c50,t.MAIN+0x541c50+len(flash)))
shim=base64.b64decode(fixture['chunks']['0x24f90f0'])
t.u.mem_write(t.MAIN+0x24f90f0,shim)
t.nativeRanges.append((t.MAIN+0x24f90f0,t.MAIN+0x24f90f0+len(shim)))
t.u.mem_write(t.MAIN+0x24ff8bc,base64.b64decode(fixture['chunks']['0x24ff8bc']))
v=0;a,c,g,cam,back,oldMap,oldTiles=t.objects[v]
for cmd,encoded in t.trace:
 p=base64.b64decode(encoded)
 if cmd==-102 and p[3] in (3,4,5):assert t.packet(v,p)==1
 elif cmd==8:t.observe(v,cmd,p)
assert not t.call('_AGNativeWatchRunning',v)
assert t.get(c+0xb8,'<Q')==t.get(a+0xe8,'<Q')
monitor=t.alloc(0x20);thread=t.alloc(0x20);t.put(thread,'<I',1);t.put(t.ENV+0x18,'<Q',thread)
def set_busy():t.put(c+0x13c,'<B',t.reg(1));t.ret()
def cas():
 assert t.get(t.reg(2),'<I')==t.reg(0)
 t.put(t.reg(2),'<I',t.reg(1));t.ret(1)
def lookup():
 assert bytes(t.u.mem_read(t.reg(1),14))==b'AGBattleAwait\0'
 t.ret(t.symbols['_AGBattleAwait'])
t.extraNative.update({
 t.MAIN+0x1300d54:lambda:t.ret(),t.MAIN+0x12e76d8:lambda:t.ret(),
 t.MAIN+0x50ba44:lambda:t.ret(),t.MAIN+0x50ba04:set_busy,
 t.MAIN+0x50b8d4:lambda:t.ret(t.get(c+0xb8,'<Q')),
 t.MAIN+0x51803c:lambda:t.ret(monitor),t.MAIN+0x131cb08:cas,
 t.MAIN+0x131cf70:lookup})
t.snapshotSync=True;waits=t.waitCalls;clock=t.get(a+0x110,'<Q');seconds=t.get(clock+0x18,'<i')
t.u.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
t.u.reg_write(t.UC_ARM64_REG_X0,t.ENV)
t.u.emu_start(t.MAIN+0x541c50,t.STOP+4,count=100000)
assert t.u.reg_read(UC_ARM64_REG_PC)==t.STOP
assert t.waitCalls==waits and t.get(c+0x13c,'<B')==1
assert t.get(clock+0x18,'<i')==seconds+2
t.snapshotSync=False
assert t.packet(v,next(p for p in t.sp if p[3]==7))==1
assert t.call('_AGNativeWatchRunning',v)
t.call('_AGNativeWatchEnd',t.ENV,v)
assert t.get(c+0x13c,'<B')==0,'Snapshot flash leaked into the room after leaving'
print('PASS actual B285 ARM64 HP flash: SP5 scene presented, native clock/flash state applied, receive thread does not wait during snapshot, SP7 completes, leave restores room')
