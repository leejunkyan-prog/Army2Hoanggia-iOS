"""Read-only native return diagnostics against the compiled ARM64 library.

The supplied296 log has130 rows and completed cleanup. Exercise those exact
states plus hidden rows, a modal and pressed keys, without fabricating a fix.
"""
import struct
import test_native_watch as t

classes=(0x2089f70,0x20b8f10,0x20e6c00,0x21148f0,0x21425e0,0x21702d0)
for v in range(6):
    canvas=t.objects[v][1]
    klass=t.alloc(0x100);area=t.alloc(0x100);rows=t.alloc(0x40);array=t.alloc(0x18+130*8)
    first=t.alloc(0x30);last=t.alloc(0x30)
    t.put(first+0x1d,'<B',0);t.put(last+0x1d,'<B',129)
    t.put(t.MAIN+classes[v],'<Q',klass);t.put(klass+0xa0,'<Q',area)
    t.put(klass+0xc0,'<Q',rows);t.put(rows+0x24,'<i',130);t.put(rows+0x18,'<Q',array)
    t.put(array+0x10,'<i',130);t.put(array+0x18,'<Q',first);t.put(array+0x18+129*8,'<Q',last)
    t.put(canvas+0xb8,'<Q',area);t.put(area+0x4d,'<B',0);t.put(area+0x44,'<i',432)
    t.put(klass+0xe9,'<B',1);t.put(klass+0xe8,'<B',1)
    t.put(klass+0xd0,'<i',3);t.put(klass+0xd4,'<iii',60,40,0);t.put(klass+0xe4,'<i',2000)
    pressed=t.alloc(0x14+32);released=t.alloc(0x14+32)
    for p in (pressed,released):t.put(p+0x10,'<i',32)
    t.put(pressed+0x14+8,'<B',1);t.put(released+0x14+6,'<B',1)
    t.put(canvas+0xa0,'<QQ',pressed,released);t.put(canvas+0x108,'<Q',t.alloc(0x30))
    observed=(klass,area,rows,array,canvas,pressed,released)
    sizes=(0x100,0x100,0x40,0x18+130*8,0x200,0x14+32,0x14+32)
    before=[bytes(t.u.mem_read(p,n)) for p,n in zip(observed,sizes)]
    t.call('_AGNativeWatchReturnDiagnostic',t.ENV,v)
    out=t.alloc(256);assert t.call('_AGReturnDiagnosticCopy',v,out)==1
    d=struct.unpack('<22i',t.u.mem_read(out+64,88))
    assert d[0:6]==(1,1,130,1,1,432),d
    assert d[6:10]==(3,60,40,2000),d
    assert d[10]==1 and d[12:14]==(1,1),d
    assert d[18:21]==(0,0,129),d
    assert [bytes(t.u.mem_read(p,n)) for p,n in zip(observed,sizes)]==before,'Diagnostics mutated native screen/input memory'
    t.put(klass+0xe9,'<B',0)
    t.call('_AGNativeWatchReturnDiagnostic',t.ENV,v);t.call('_AGReturnDiagnosticCopy',v,out)
    assert t.get(out+64+3*4,'<i')==0,'Hidden-list gate was not captured'
    t.call('_AGReturnInput',v,0,-7,1);t.call('_AGReturnDiagnosticCopy',v,out)
    assert t.get(out+156,'<i')==-7 and t.get(out+160,'<i')==1
    t.call('_AGReturnInput',v,0,ord('A'),0);t.call('_AGReturnDiagnosticCopy',v,out)
    assert t.get(out+156,'<i')==0,'Typed input entered diagnostic data'
    t.call('_AGReturnPulse',v,0);t.call('_AGReturnPulse',v,1);t.call('_AGReturnDiagnosticCopy',v,out)
    assert t.get(out,'<Q')>0 and t.get(out+8,'<Q')>0
    t.now+=1
    assert t.call('_AGReturnShouldSample',v)==1 and t.call('_AGReturnShouldSample',v)==0

print('PASS compiled ARM64 return diagnostics: six PBs, exact130 rows, visibility/transition/scroll/modal/key state, heartbeat and blocker metadata, no native writes or typed-character logging')
