"""Reproduce298's dead-canvas state, then exercise the compiled recovery.

Java Thread creation/worker scheduling and Mach port state are boundaries here;
test_canvas_recovery299.m separately uses actual kernel thread death/rebinding.
Area animation and directional input execute the unchanged AOT instructions for
all six PBs. The same fixture on the compiled298 is the failing control.
"""
from pathlib import Path
import struct
import lief
from unicorn import UC_HOOK_CODE
import test_room_reply295 as reply
t=reply.t
raw=(Path(__file__).parent/'build/base293-native').read_bytes()
m=lief.MachO.parse(raw)[0]
fixed='_AGCanvasRecoveryFrame' in t.symbols
classes=(0x2089f70,0x20b8f10,0x20e6c00,0x21148f0,0x21425e0,0x21702d0)
def offset(address):
    return next(s.file_offset+address-s.virtual_address for s in m.segments if s.virtual_address<=address<s.virtual_address+s.virtual_size)
def pointer(address):return struct.unpack_from('<Q',raw,offset(address))[0]
def target(at):
    word=int.from_bytes(raw[at:at+4],'little');assert word&0xfc000000==0x94000000,hex(at)
    d=word&0x3ffffff
    return at+4*(d-(1<<26) if d&(1<<25) else d)
def load(at,size):
    t.u.mem_write(t.MAIN+at,raw[at:at+size]);t.nativeRanges.append((t.MAIN+at,t.MAIN+at+size));t.u.ctl_remove_cache(t.MAIN+at,t.MAIN+at+size)
def boundary(uc,pc,size,data):t.ret()
for name in ('_AGViewerTick','_AGTurnPulse'):
    t.u.hook_add(UC_HOOK_CODE,boundary,begin=t.symbols[name],end=t.symbols[name])
def string(at):return bytes(t.u.mem_read(at,100)).split(b'\0')[0].decode()
thread_class=t.alloc(0x100);threads={};started=[];fail_start=False;exception_pending=False
tracking=0;original_java_thread=t.alloc(0x80)
def find_class():assert string(t.reg(1))=='java/lang/Thread';t.ret(thread_class)
def method():
    name,signature=string(t.reg(2)),string(t.reg(3))
    assert (name,signature) in [('<init>','(Ljava/lang/Runnable;)V'),('start','()V'),('isAlive','()Z')]
    t.ret({'<init>':1,'start':2,'isAlive':3}[name])
def construct():
    assert t.reg(2)==1
    original=t.get(t.reg(3),'<Q');variant=next(v for v,entry in enumerate(fixtures) if original==entry['runnable'])
    obj=t.alloc(0x80);threads[obj]={'v':variant,'target':original,'alive':False};t.ret(obj)
def start():
    global exception_pending
    assert t.reg(2)==2 and t.reg(3)==0
    obj=t.reg(1);threads[obj]['alive']=not fail_start;started.append(obj);exception_pending=fail_start;t.ret()
def get_class():assert t.reg(1) in threads;t.ret(thread_class)
def alive():assert t.reg(2)==3;t.ret(threads[t.reg(1)]['alive'])
def static_method():assert string(t.reg(2))=='currentThread' and string(t.reg(3))=='()Ljava/lang/Thread;';t.ret(4)
def field():assert string(t.reg(2))=='target' and string(t.reg(3))=='Ljava/lang/Runnable;';t.ret(5)
def get_target():assert t.reg(1)==original_java_thread and t.reg(2)==5;t.ret(fixtures[tracking]['runnable'])
def clear_exception():
    global exception_pending
    exception_pending=False;t.ret()
for i,(slot,handler) in enumerate([(6,find_class),(33,method),(30,construct),(63,start),(31,get_class),(39,alive),(228,lambda:t.ret(exception_pending)),(17,clear_exception),(113,static_method),(116,lambda:t.ret(original_java_thread)),(94,field),(95,get_target)]):
    pc=t.FAKE+0x36000+i*0x100;t.put(t.JNI+slot*8,'<Q',pc);t.extraNative[pc]=handler
t.extraNative[t.MAIN+0x1dfce8]=lambda:t.ret(t.get(t.reg(1)+0x24,'<i'))
fixtures=[]
for v,klass in enumerate(classes):
    # Finish any snapshot left by the existing production packet fixtures.
    t.stillWatching=False;t.call('_AGNativeWatchEnd',t.ENV,v)
    canvas=t.objects[v][1];area=t.alloc(0x100);a=t.alloc(0x100);vector=t.alloc(0x40);runnable=t.alloc(0x80);keys=t.alloc(0x14+32)
    t.put(t.MAIN+klass,'<Q',a);t.put(a+0xa0,'<Q',area);t.put(a+0xc0,'<Q',vector);t.put(vector+0x24,'<i',130)
    t.put(a+0xe8,'<BB',1,1);t.put(a+0xe4,'<i',4679);t.put(area+0x44,'<i',432);t.put(area+0x4d,'<B',0)
    t.put(runnable,'<Q',canvas);t.put(canvas+0xb0,'<Q',t.objects[v][4]);t.put(canvas+0xb8,'<Q',area);t.put(canvas+0x130,'<ii',432,0)
    t.put(canvas+0x128,'<i',602);t.put(canvas+0x124,'<i',889);t.put(canvas+0xa0,'<Q',keys)
    t.put(keys+0x10,'<i',32);t.put(keys+0x1c,'<B',1)
    table=pointer(t.MAIN+klass+0x28);step=pointer(table+0x98)-t.MAIN;input_=pointer(table+0x88)-t.MAIN
    load(step,0x90);load(input_,0x450);load(target(step+0x34),0x44)
    t.extraNative[t.MAIN+target(step+0x28)]=lambda:t.ret() # shared background/resource update only
    t.extraNative[t.MAIN+target(input_+0x28)]=lambda:t.ret() # base soft-key commands; no arrow logic
    t.extraNative[t.MAIN+target(input_+0x60)]=lambda keys=keys:t.ret(keys)
    for pos in (0x150,0x1f4,0x21c):t.extraNative[t.MAIN+target(input_+pos)]=lambda:t.ret(0)
    t.extraNative[t.MAIN+target(input_+0x20c)]=lambda:t.ret(20)
    t.extraNative[t.MAIN+target(input_+0x364)]=lambda:t.ret(602)
    fixtures.append({'canvas':canvas,'area':area,'klass':a,'runnable':runnable,'keys':keys,'step':step,'input':input_})
load(0xaa731c,0x5c);load(0xaa8658,0xc);t.put(t.MAIN+0x21aa560+9,'<B',2)
def render(v):return t.call('_AGNativeWatchRenderFrame',t.ENV,v)
def state(v):
    out=t.alloc(40);t.call('_AGCanvasRecoveryCopy',v,out)
    return struct.unpack('<QQQiii',t.u.mem_read(out,36))
for v,f in enumerate(fixtures):
    tracking=v
    if fixed:t.call('_AGCanvasRecoveryTrack',t.ENV,v)
    t.threadPort=1000+v;t.call('_AGReturnPulse',v,0);t.deadPorts.add(t.threadPort)
    t.stillWatching=True;render(v);assert len(started)==v if fixed else not started
    t.stillWatching=False;t.now+=2
    before=len(started)
    for _ in range(100):render(v)
    assert t.get(f['area']+0x44,'<i')==432 and t.get(f['keys']+0x1c,'<B')==1,'Render supplied an unsolicited second UI clock'
    if not fixed:
        assert len(started)==before,'Control unexpectedly started a replacement'
        continue
    assert len(started)==before+1 and threads[started[-1]]['target']==f['runnable'],'Wrong or duplicated Thread.start'
    # Even a slow but live replacement may not be duplicated after timeout.
    t.now+=2.1;render(v);t.now+=2.1;render(v);assert len(started)==before+1
    t.threadPort=2000+v
    t.symbols['_originalAreaStep']=t.MAIN+f['step'];t.symbols['_originalAreaInput']=t.MAIN+f['input']
    for _ in range(12):
        t.now+=.031;t.call('_AGReturnPulse',v,0)
        t.call('_originalAreaStep',t.ENV,f['area']);t.call('_originalAreaInput',t.ENV,f['area'])
    render(v)
    assert t.get(f['area']+0x44,'<i')==0,'Original area entrance remained off-screen'
    assert t.get(f['klass']+0xd0,'<i')==1 and t.get(f['keys']+0x1c,'<B')==0,'Original directional input did not resume'
    assert state(v)==(1,1,0,0,0,2),state(v)
    assert t.pins[started[-1]]==0,'Recovery retained a healthy thread root'
    # A later unrelated death is outside this completed watch's ownership.
    t.deadPorts.add(t.threadPort);t.now+=2;render(v);assert len(started)==before+1
if not fixed:
    print('PASS baseline298 reproduces supplied trace across six PBs: dead update loop,130 rows, transition432 and held input persist through100 renders; no recovery')
else:
    # Re-enter a watch, then repeatedly lose replacement threads before their
    # first callback. isAlive=false permits only three delayed attempts.
    v=0;t.stillWatching=True;render(v);t.stillWatching=False;fail_start=True
    before=len(started)
    for _ in range(3):
        t.now+=1.1;render(v);assert state(v)[4]==1
        t.now+=2.1;render(v);assert state(v)[4]==0
    t.now+=100
    for _ in range(50):render(v)
    assert len(started)==before+3,'Repeated child failures spawned unbounded threads'
    roots={f['runnable'] for f in fixtures}
    assert all(n==(1 if p in roots else 0) for p,n in t.pins.items()),t.pins
    print('PASS compiled299: six original Runnable targets, exactly one replacement, no parallel render UI clock, actual AOT transition432->0 and down-key consumption, live delayed-start safety, dead-port rebind, roots released, bounded failure retries and no unrelated restarts')
