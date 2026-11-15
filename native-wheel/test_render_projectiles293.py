"""Render-clock integration with original AOT arena/projectile/clock bodies.

The preceding fixture verifies native packet decoding and two complete shots.
Here two more shots can advance only through the compiled render scheduler
and original arena.update. Actor updates, camera, terrain effects, graphics,
audio, JVM and transport remain fixture boundaries; no live iPhone is used.
"""
import test_projectile_progress292 as shots
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_INVALID, UcError
from unicorn.arm64_const import UC_ARM64_REG_PC

t=shots.t
live=shots.live
v=0
arena=live.arena
canvas=live.c
def invalid_memory(uc,access,address,size,value,data):
    raise AssertionError(('Uninitialized native fixture memory',hex(uc.reg_read(UC_ARM64_REG_PC)-t.MAIN),hex(address),size))
t.u.hook_add(UC_HOOK_MEM_INVALID,invalid_memory)

# Execute the displaced update prologue and the full original arena body.
t.nativeRanges.extend((t.MAIN+a,t.MAIN+b)for a,b in (
    (0x24f91d0,0x24f91e0),(0x546624,0x547cdc),
    (0x57f8c0,0x57f93c),(0x592ec0,0x592f00))) # native shot flag accessors

for address in (0x5559c8,):
    t.extraNative[t.MAIN+address]=lambda:t.ret(t.alloc(0x30))
for address in (0x5b02c4,0x5b0bd8,0x4f7120,0x599a7c,0x5b5fe8,0x5dc0d4,
                0x51259c,0x512618,0x503ae8):
    t.extraNative[t.MAIN+address]=lambda:t.ret()
# Stable canvas/debug counters; they do not replace the battle clock.
for address in (0x50be84,0x50bec0,0x512560,0x5125dc):
    t.extraNative[t.MAIN+address]=lambda:t.ret(1)
for offset in (0x48,0x50):t.put(arena+offset,'<Q',t.alloc(0x30))
for offset in (0xc0,0xf0,0x100):t.put(live.a+offset,'<Q',t.alloc(0x30))

ticks=0
pulses=0
def boundary(uc,pc,size,data):
    global ticks,pulses
    assert t.reg(0)==t.ENV and t.reg(1)==v
    if pc==t.symbols['_AGViewerTick']:ticks+=1
    else:pulses+=1
    t.ret()
for name in ('_AGViewerTick','_AGTurnPulse'):
    t.u.hook_add(UC_HOOK_CODE,boundary,begin=t.symbols[name],end=t.symbols[name])

t.call('_AGNativeWatchTraceReset',v)
clock=shots.clock
t.put(clock+0x10,'<Q',shots.millis)
t.put(clock+0x18,'<i',62)
frame_count=0
for number in range(2):
    live.dispatch(22,shots.shot)
    assert t.get(live.projectiles+0x118,'<B')==1
    positions=[]
    before_steps=pulses
    for frame in range(100):
        t.now+=.031;shots.millis+=31
        try:t.call('_AGNativeWatchRenderFrame',t.ENV,v)
        except UcError as error:
            raise AssertionError(('Native fixture failure',hex(t.u.reg_read(UC_ARM64_REG_PC)-t.MAIN)))from error
        frame_count+=1
        for pointer in shots.vector(t.get(live.projectileObject+0x30,'<Q')):
            positions.append((t.get(pointer+0x48,'<i'),t.get(pointer+0x7c,'<i'),t.get(pointer+0x84,'<i')))
        # The old Java update must not step these same projectiles again.
        state=bytes(t.u.mem_read(live.projectileObject,0x50))
        t.call('_AGNativeWatchGameUpdate',t.ENV,arena,v)
        assert bytes(t.u.mem_read(live.projectileObject,0x50))==state
        if not t.get(live.projectiles+0x118,'<B'):break
    else:raise AssertionError('Render-driven native arena did not finish the shot')
    assert len(set(positions))>40 and positions[0]==(0,467,349),positions[:2]
    assert any(x==815 and y==651 for _,x,y in positions)
    assert not shots.vector(t.get(live.projectileObject+0x30,'<Q'))
    assert pulses-before_steps==frame+1

assert t.get(clock+0x18,'<i')<62,'Render-driven original clock remained frozen'
out=t.alloc(40);assert t.call('_AGNativeWatchTraceRenderCopy',v,out)
counters=[t.get(out+i*8,'<Q')for i in range(5)]
assert counters==[frame_count,frame_count,frame_count,0,frame_count],counters
assert ticks==frame_count and pulses==frame_count
print('PASS compiled render scheduler -> original ARM64 arena.update -> projectile and clock bodies: two consecutive complete trajectories, busy-flag release, advancing clock, no second Java update. Actor/resource/JVM/transport boundaries mocked; physical live-room validation remains pending.')
