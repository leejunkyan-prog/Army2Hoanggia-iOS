"""Execute compiled watch metadata and first native exception capture.

Only the standard JNI Throwable.toString boundary is mocked; counters,
first-error retention and trace snapshots execute in the iPhone framework.
"""
import test_native_watch as t
from unicorn.arm64_const import UC_ARM64_REG_SP

message=b'java.lang.NullPointerException: battle update fixture'
exception=t.alloc(0x30);cls=t.alloc(0x30);method=t.alloc(0x20);string=t.alloc(0x30)
utf=t.alloc(len(message)+1);t.u.mem_write(utf,message+b'\0')
jni_calls=[]
def jni(slot):
    def invoke():
        jni_calls.append(slot)
        assert t.reg(0)==t.ENV
        if slot==31:assert t.reg(1)==exception;t.ret(cls)
        elif slot==33:
            assert t.reg(1)==cls
            assert bytes(t.u.mem_read(t.reg(2),9))==b'toString\0'
            t.ret(method)
        elif slot==36:assert (t.reg(1),t.reg(2),t.reg(3))==(exception,method,0);t.ret(string)
        elif slot==169:assert t.reg(1)==string;t.ret(utf)
        elif slot==170:assert (t.reg(1),t.reg(2))==(string,utf);t.ret()
    return invoke
for slot in (31,33,36,169,170):
    address=t.FAKE+0x31000+slot*16
    t.put(t.JNI+slot*8,'<Q',address);t.extraNative[address]=jni(slot)

def snprintf():
    # Darwin ARM64 places variadic arguments on the stack.
    source=t.get(t.u.reg_read(UC_ARM64_REG_SP),'<Q')
    raw=bytes(t.u.mem_read(source,512)).split(b'\0',1)[0]
    assert bytes(t.u.mem_read(t.reg(2),3))==b'%s\0'
    t.u.mem_write(t.reg(0),raw[:t.reg(1)-1]+b'\0');t.ret(len(raw))
t.extraNative[t.names['_snprintf']]=snprintf

for variant in range(6):
    t.call('_AGNativeWatchTraceReset',variant);t.stillWatching=True
    t.call('_AGNativeWatchTraceFrame',variant)
    t.call('_AGNativeWatchTracePacket',variant,22,0xffffffff)
    t.call('_AGNativeWatchTraceWait',variant,0,3,1)
    t.call('_AGNativeWatchTraceWait',variant,0,3,3)
    before=len(jni_calls)
    t.call('_AGNativeWatchTraceException',t.ENV,exception,variant)
    assert len(jni_calls)==before+5
    t.call('_AGNativeWatchTraceException',t.ENV,exception,variant)
    assert len(jni_calls)==before+5,'Repeated faults must retain first error without allocating every frame'
    output=t.alloc(576);assert t.call('_AGNativeWatchTraceCopy',variant,output)==1
    assert [t.get(output+i*8,'<Q')for i in range(5)]==[1,1,2,1,1]
    assert [t.get(output+40+i*4,'<i')for i in range(5)]==[22,-1,0,3,3]
    assert bytes(t.u.mem_read(output+60,512)).split(b'\0',1)[0]==message
    t.stillWatching=False
    t.call('_AGNativeWatchTraceFrame',variant)
    t.call('_AGNativeWatchTraceException',t.ENV,exception,variant)
    assert t.call('_AGNativeWatchTraceCopy',variant,output)==1
    assert t.get(output,'<Q')==1 and t.get(output+16,'<Q')==2
print('PASS compiled watch trace: six PBs, packet/frame/wait metadata, JNI exception text, first-error retention and inactive-session filtering')
