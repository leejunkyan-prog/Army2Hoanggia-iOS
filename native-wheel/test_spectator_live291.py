"""Run the original Build290 network dispatcher and live actor state setup.

Primitive JNI/stream/resource operations are mocked. Command decoding,
compressed trajectory reconstruction, movement scheduling, Actor.fire and
projectile initialization execute original iPhone ARM64 instructions.
This is not a renderer, a live server test, or a physical iPhone test.
"""
import sys,base64,struct
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import test_native_watch as t
import lief
from unicorn.arm64_const import *
native=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'build/base290-native'
raw=native.read_bytes()
assert sha256(raw).hexdigest()=='889afdfc35bdbb47f7f3abcd2327c97f631702158d2670f6c79c37b6d2485a06'
m=lief.MachO.parse(str(native)).at(0)
for s in m.segments:
 if s.name in ('__TEXT','__AGWHEEL','__AGDATA'):
  at=s.virtual_address-t.MAIN;t.u.mem_write(t.MAIN+at,raw[s.file_offset:s.file_offset+s.file_size])
t.nativeRanges.append((t.MAIN+0x518210,t.MAIN+0x537000))
t.nativeRanges.extend((t.MAIN+x,t.MAIN+y) for x,y in ((0x599ad0,0x59a2a0),(0x583650,0x5836d8),(0x598b38,0x598bc0),(0x59c704,0x59c754),(0x512e40,0x512ff4),(0x512734,0x512798),(0x57ff10,0x57ff9c)))
v=0;a,c,g,cam,back,oldMap,oldTiles=t.objects[v]
t.stillWatching=True
for cmd,encoded in t.trace:
 p=base64.b64decode(encoded)
 if cmd==-102 and p[3] in (3,4,5,7):assert t.packet(v,p)==1
 elif cmd==8:t.observe(v,cmd,p)
players=t.get(t.MAIN+0x207f060,'<Q');roster=t.get(players+0xa0,'<Q');arena=t.get(a+0xe8,'<Q')
monitor=t.alloc(0x40);ctrl=t.alloc(0xc0);t.put(t.MAIN+0x2081150,'<Q',ctrl);t.put(ctrl+0xa8,'<Q',monitor)
thread=t.alloc(0x20);t.put(thread,'<I',1);t.put(t.ENV+0x18,'<Q',thread)
input=t.alloc(0x40);message=t.alloc(0x50);t.put(message+0x20,'<Q',input)
cursor=0;data=b'';reads=[];calls=[]
def read(fmt):
 global cursor
 n=struct.calcsize(fmt);assert cursor+n<=len(data),(hex(t.u.reg_read(UC_ARM64_REG_LR)-t.MAIN),fmt,cursor,len(data))
 value=struct.unpack_from(fmt,data,cursor)[0];reads.append((cursor,fmt,value));cursor+=n;t.ret(value)
def halt():t.u.reg_write(UC_ARM64_REG_PC,t.STOP)
def cas():t.put(t.reg(2),'<I',t.reg(1));t.ret(1)
t.extraNative.update({
 t.MAIN+0x1300d54:lambda:t.ret(),t.MAIN+0x12e7330:lambda:t.ret(),
 t.MAIN+0x4f98cc:lambda:t.ret(input),t.MAIN+0xa63e54:lambda:read('>b'),
 t.MAIN+0xa63df0:lambda:read('>B'),t.MAIN+0xa64208:lambda:read('>h'),
 t.MAIN+0xa63fa8:lambda:read('>i'),t.MAIN+0xa6419c:lambda:read('>q'),
 t.MAIN+0x5123ac:lambda:t.ret(roster),t.MAIN+0x53f3b4:lambda:t.ret(t.get(a+0x266,'<B')),
 t.MAIN+0x50b8d4:lambda:t.ret(arena),t.MAIN+0x53edc4:lambda:t.ret(arena),
 t.MAIN+0x519830:halt,t.MAIN+0x534a74:halt,t.MAIN+0x51c064:halt,
 t.MAIN+0x131cb08:cas,t.MAIN+0x12e841c:lambda:t.ret(),
 t.MAIN+0x532308:halt,t.MAIN+0x532310:halt,
})
def arr(width):
 n=t.reg(1);assert n<=10000;p=t.alloc(0x18+n*width);t.put(p+0x10,'<i',n);t.ret(p)
t.extraNative[t.MAIN+0x5177ec]=lambda:arr(8)
t.extraNative[t.MAIN+0x12e7cc8]=lambda:arr(2)
def aset():t.put(t.reg(1)+0x18+8*t.reg(2),'<Q',t.reg(3));t.ret()
t.extraNative[t.MAIN+0x12e7f74]=aset
for off in (0x512ff4,0x51301c,0x513044,0x51306c):t.extraNative[t.MAIN+off]=lambda:t.ret(t.alloc(0x30))
# Debug strings are resource work, not battle simulation.
t.extraNative[t.MAIN+0x55566c]=lambda:t.ret(0)
t.extraNative[t.MAIN+0xab9404]=lambda:t.ret(t.alloc(0x40))
for off in (0xabc20c,0xabc3a4,0xabc3d0,0xab96d8):t.extraNative[t.MAIN+off]=lambda:t.ret(t.reg(1))
# Exact debug-string getters reached by these commands; all other
# unexpected native dependencies remain fatal in test_native_watch.hook.
for off in (0x537ca0,0x537cc8,0x537cf0,0x5380d8,0x538100,0x538128):
 t.extraNative[t.MAIN+off]=lambda:t.ret(t.alloc(0x30))
def dispatch(cmd,p):
 global data,cursor,reads,calls
 data=p;cursor=0;reads=[];calls=[];t.put(message+0x30,'<b',cmd)
 sp=t.STACK+0x30000-0x60;t.u.reg_write(UC_ARM64_REG_SP,sp)
 for i in range(31):t.u.reg_write(UC_ARM64_REG_X0+i,0)
 t.u.reg_write(UC_ARM64_REG_X0,t.ENV);t.u.reg_write(UC_ARM64_REG_X1,t.alloc(0x40));t.u.reg_write(UC_ARM64_REG_X2,message);t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
 t.u.emu_start(t.MAIN+0x518210,t.STOP+4,count=1000000)
 assert t.u.reg_read(UC_ARM64_REG_PC)==t.STOP
 assert cursor==len(data),(cmd,cursor,len(data))
playerglobals=t.alloc(0x200);t.put(t.MAIN+0x2091b80,'<Q',playerglobals)
projectileObject=t.alloc(0x100);t.put(projectileObject+0x30,'<Q',t.alloc(0x30));t.extraNative[t.MAIN+0x1dfce8]=lambda:t.ret(0);t.put(a+0xe0,'<Q',projectileObject)
t.extraNative[t.MAIN+0x53ed88]=lambda:t.ret(projectileObject)
t.extraNative[t.MAIN+0x51293c]=lambda:t.ret(0)
t.extraNative[t.MAIN+0x59a2a0]=lambda:t.ret(t.alloc(0x30))
t.extraNative[t.MAIN+0x12e76d8]=lambda:t.ret()
t.extraNative[t.MAIN+0x24ffe08]=lambda:t.ret()
projectiles=t.alloc(0x200);t.put(projectiles+0xc0,'<Q',t.alloc(0x30));t.put(t.MAIN+0x208c790,'<Q',projectiles)
for start,end in ((0x57f978,0x57f9b8),):
 t.nativeRanges.append((t.MAIN+start,t.MAIN+end))
t.extraNative[t.MAIN+0xaaa258]=lambda:t.ret()
t.extraNative[t.MAIN+0xbe3f1c]=lambda:t.ret(t.alloc(0x30))
t.extraNative[t.MAIN+0xbe6b7c]=lambda:t.ret()
t.u.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);t.u.reg_write(UC_ARM64_REG_LR,t.STOP);t.u.reg_write(UC_ARM64_REG_X0,t.ENV);t.u.reg_write(UC_ARM64_REG_X1,projectileObject)
t.u.emu_start(t.MAIN+0x57ff10,t.STOP+4,count=100000)
# Stop after real shot setup, at the engine animation wait. The separate
# modal regression verifies that GameCanvas actually reaches scene.update.
t.extraNative[t.MAIN+0x24f9010]=halt
hp_calls=[]
def hp_boundary():
 hp_calls.append((t.reg(1),t.reg(2),t.reg(3)));t.ret()
t.extraNative[t.MAIN+0x59a974]=hp_boundary
for cmd,encoded in t.trace:
 if cmd in (21,22,51):dispatch(cmd,base64.b64decode(encoded))
actor0=t.get(roster+0x18,'<Q')
assert hp_calls[0][1:]==(1000,0) and hp_calls[1][1:]==(1000,0)
# Values above 32 bits catch an accidental int parser in the old native code.
wide_hp=2**40+123
dispatch(51,struct.pack('>BqB',0,wide_hp,7))
assert hp_calls[-1]==(actor0,wide_hp,7)
# The native fire method, rather than a mock, installs the projectile paths.
assert t.get(actor0+0x114,'<i')==466 and t.get(actor0+0x118,'<i')==380
assert t.get(actor0+0xa4,'<i')==85 and t.get(actor0+0x16f,'<B')==4
assert t.get(projectiles+0x118,'<B')==1
xs=t.get(projectileObject+0x10,'<Q');ys=t.get(projectileObject+0x18,'<Q')
xpath=t.get(xs+0x18,'<Q');ypath=t.get(ys+0x18,'<Q')
assert t.get(xpath+0x10,'<i')==46 and t.get(ypath+0x10,'<i')==46
assert t.get(xpath+0x14,'<h')==467 and t.get(ypath+0x14,'<h')==349
assert t.get(xpath+0x16,'<h')==468 and t.get(ypath+0x16,'<h')==335
# A changed movement echo executes the original movement scheduler.
dispatch(21,struct.pack('>Bhh',0,506,380))
assert t.get(actor0+0x12c,'<i')==506 and t.get(actor0+0x130,'<i')==380
assert t.get(actor0+0x167,'<B')==1
print('PASS original Build290 ARM64 dispatcher: cmd21 movement scheduling; cmd22 full 46-point trajectory decoding, native Actor.fire and projectile initialization; cmd51 64-bit HP arguments. Animation wait and rendering are separate tests.')
