"""Execute compiled render-clock ownership and lifecycle over all six PBs.

Native scene.update is a boundary here; projectile_progress292 separately
executes its real AOT projectile/clock methods. This test verifies that visible
renders actually invoke that boundary while an idle Java loop does not, and
that two update sources cannot advance the watched scene twice.
"""
import base64
import test_native_watch as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_X1

updates=(0x24f91d0,0x24fa4b0,0x24fb790,0x24fca70,0x24fdd50,0x24ff030)
steps=[0]*6;viewer_ticks=[0]*6;pulses=[0]*6
reenter=False
def boundary(uc,pc,size,data):
    if pc==t.symbols['_AGViewerTick']:
        assert t.reg(0)==t.ENV;viewer_ticks[t.reg(1)]+=1;t.ret()
    elif pc==t.symbols['_AGTurnPulse']:
        assert t.reg(0)==t.ENV;pulses[t.reg(1)]+=1;t.ret()
for name in ('_AGViewerTick','_AGTurnPulse'):
    t.u.hook_add(UC_HOOK_CODE,boundary,begin=t.symbols[name],end=t.symbols[name])
def update(v):
    def invoke():
        global reenter
        assert t.reg(0)==t.ENV
        steps[v]+=1
        if reenter:
            reenter=False
            t.u.reg_write(UC_ARM64_REG_X1,v)
            t.u.reg_write(UC_ARM64_REG_PC,t.symbols['_AGNativeWatchRenderFrame'])
        else:t.ret()
    return invoke
for v,address in enumerate(updates):t.extraNative[t.MAIN+address]=update(v)

def render(v,advance=.031):
    t.now+=advance
    return t.call('_AGNativeWatchRenderFrame',t.ENV,v)
def stats(v):
    out=t.alloc(40)
    assert t.call('_AGNativeWatchTraceRenderCopy',v,out)==1
    return [t.get(out+i*8,'<Q')for i in range(5)]

for v in range(6):
    t.stillWatching=True
    a,canvas,_,_,back,_,_=t.objects[v]
    for cmd,encoded in t.trace:
        packet=base64.b64decode(encoded)
        if cmd==-102 and packet[3]in(3,4,5):assert t.packet(v,packet)==1
        elif cmd==8:t.observe(v,cmd,packet)
    arena=t.get(a+0xe8,'<Q')
    render(v);assert steps[v]==0,'Partial snapshots must not advance physics'
    t.call('_AGNativeWatchGameUpdate',t.ENV,arena,v)
    assert steps[v]==0,'Java canvas advanced a partial spectator snapshot'
    assert t.packet(v,next(p for p in t.sp if p[3]==7))==1
    t.call('_AGNativeWatchTraceReset',v)

    # The failing device trace has no completed canvas scene update. A
    # render callback must progress independently of that Java update loop.
    render(v);assert steps[v]==1 and pulses[v]==1
    t.call('_AGNativeWatchGameUpdate',t.ENV,arena,v)
    render(v,.005);assert steps[v]==1,'Native and render callbacks doubled a physics step'
    render(v,.031);assert steps[v]==2
    render(v,20);assert steps[v]==3
    render(v,0);assert steps[v]==3,'Long stalls must not cause a catch-up burst'
    assert stats(v)==[5,3,3,0,1]

    reenter=True
    render(v);assert steps[v]==4 and not t.call('_AGNativeWatchRendering',v)
    assert pulses[v]==4,'Reentrant paint advanced the scene twice'

    other=t.alloc(0x80);t.put(canvas+0xb8,'<Q',other)
    render(v);assert steps[v]==4,'Native auxiliary screens must not tick the hidden arena'
    t.put(canvas+0xb8,'<Q',arena)

    # Retain the native twenty-update flash completion only if the Java
    # canvas counter is stationary; never add a second flash clock.
    t.put(canvas+0x124,'<I',123);t.put(canvas+0x13c,'<B',1)
    for _ in range(20):render(v)
    assert t.get(canvas+0x13c,'<B')==1
    render(v);assert t.get(canvas+0x13c,'<B')==0
    t.put(canvas+0x13c,'<B',1)
    for i in range(25):
        t.put(canvas+0x124,'<I',124+i);render(v)
    assert t.get(canvas+0x13c,'<B')==1,'Render clock replaced an active Java flash clock'
    t.put(canvas+0x13c,'<B',0)

    before=steps[v];t.stillWatching=False
    render(v);assert steps[v]==before
    t.call('_AGNativeWatchGameUpdate',t.ENV,arena,v)
    assert steps[v]==before,'Pending watch cleanup restarted participant physics'
    t.call('_AGNativeWatchEnd',t.ENV,v)
    assert t.get(canvas+0xb8,'<Q')==back
    t.call('_AGNativeWatchGameUpdate',t.ENV,arena,v)
    assert steps[v]==before+1,'Normal play no longer uses its original native update'
    assert viewer_ticks[v]>50
assert all(count==0 for count in t.pins.values())
print('PASS compiled render-clock routing: six PBs; idle-canvas progress, single physics owner, 30ms pacing, no catch-up bursts/reentry, native flash completion, auxiliary/cleanup safety and unchanged normal play')
