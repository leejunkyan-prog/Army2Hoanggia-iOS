"""Run real base activation during compiled teardown, with unavailable rows.

The old virtual destination path is the failing control: its real area a()
dereferences rows before transport can refresh them. JNI resources and the
socket are boundaries; base activation, key reset and screen setter are AOT.
"""
import base64
from pathlib import Path
import test_native_watch as t

raw=(Path(__file__).parent/'build/base293-native').read_bytes()
bases=(0x5ad9e8,0x69625c,0x77af20,0x85fbe4,0x9448a8,0xa2956c)
area_classes=(0x2089f70,0x20b8f10,0x20e6c00,0x21148f0,0x21425e0,0x21702d0)

def target(at):
    word=int.from_bytes(raw[at:at+4],'little')
    assert word&0xfc000000==0x94000000
    delta=word&0x3ffffff
    return at+4*(delta-(1<<26) if delta&(1<<25) else delta)

def load(at,size):
    t.u.mem_write(t.MAIN+at,raw[at:at+size])
    t.nativeRanges.append((t.MAIN+at,t.MAIN+at+size))
    t.u.ctl_remove_cache(t.MAIN+at,t.MAIN+at+size)

def reject_virtual():
    raise AssertionError('CLEANUP_DEPENDS_ON_DESTINATION_OVERRIDE: room reply and battlefield return blocked')

for v,base in enumerate(bases):
    canvas=t.objects[v][1]
    load(base,0x38)
    reset=target(base+0x1c)
    setter=target(base+0x28)
    load(reset,0xc0)
    load(setter,0x40)
    t.put(t.MAIN+t.canvas[v]+9,'<B',2)
    # Actual reset walks pressed/released key arrays via two native getters.
    keys=[t.alloc(0x14+32) for _ in range(2)]
    for arr in keys:t.put(arr+0x10,'<i',32);t.u.mem_write(arr+0x14,bytes([1])*32)
    for at in range(reset,reset+0xc0,4):
        word=int.from_bytes(raw[at:at+4],'little')
        if word&0xfc000000==0x94000000:
            fn=target(at)
            if raw[fn:fn+4]==bytes.fromhex('f44fbea9'):
                # Getter bodies expose array fields in their final ldr x0.
                code=raw[fn:fn+0x40]
                if bytes.fromhex('005140f9') in code:t.extraNative[t.MAIN+fn]=lambda arr=keys[0]:t.ret(arr)
                elif bytes.fromhex('005540f9') in code:t.extraNative[t.MAIN+fn]=lambda arr=keys[1]:t.ret(arr)
    # Keep the virtual bridge executable, but make any destination override
    # fatal. A base-only return must not touch this table or its missing rows.
    load(base+0x38,0x24)
    back=t.objects[v][4];klass=t.alloc(0x100);vtable=t.alloc(0x100)
    t.put(back,'<Q',klass);t.put(klass+0x28,'<Q',vtable)
    trap=t.FAKE+0x38000+v*0x100;t.put(vtable+0x60,'<Q',trap)
    t.extraNative[trap]=reject_virtual
    t.stillWatching=True
    for cmd,encoded in t.trace:
        p=base64.b64decode(encoded)
        if cmd==-102 and p[3] in (3,4,5,7):assert t.packet(v,p)==1
        elif cmd==8:t.observe(v,cmd,p)
    t.stillWatching=False
    assert t.call('_AGNativeWatchTryEnd',t.ENV,v)==1
    assert t.get(canvas+0xb8,'<Q')==back
    assert not t.call('_AGNativeWatchRunning',v)
    for arr in keys:assert bytes(t.u.mem_read(arr+0x14,32))==bytes(32)
    assert t.call('_AGNativeWatchTryEnd',t.ENV,v)==1

    # Return acknowledgement requires the actual native area instance,
    # room0 and a nonempty vector. A socket enqueue or empty reply is not it.
    t.put(t.MAIN+area_classes[v],'<Q',klass)
    t.put(klass+0xa0,'<Q',back);t.put(back+0x4d,'<B',0)
    t.put(klass+0xc0,'<Q',0)
    assert t.call('_AGNativeWatchRoomStatus',t.ENV,v)==0
    rows=t.alloc(0x40);t.put(klass+0xc0,'<Q',rows)
    count=[0]
    t.extraNative[t.MAIN+0x1dfce8]=lambda count=count:t.ret(count[0])
    assert t.call('_AGNativeWatchRoomStatus',t.ENV,v)==0
    count[0]=67
    assert t.call('_AGNativeWatchRoomStatus',t.ENV,v)==67
    t.put(back+0x4d,'<B',1)
    assert t.call('_AGNativeWatchRoomStatus',t.ENV,v)==0xffffffff
    t.put(back+0x4d,'<B',0);t.put(canvas+0xb8,'<Q',t.alloc(0x80))
    assert t.call('_AGNativeWatchRoomStatus',t.ENV,v)==0xffffffff

assert all(n==0 for n in t.pins.values())
print('PASS compiled ARM64: six PBs, real base activation/key reset, no destination override dependency, null/empty/full room0 acknowledgement and navigation cancellation')
