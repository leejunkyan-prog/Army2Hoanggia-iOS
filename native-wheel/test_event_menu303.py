"""Run the compiled native menu edit against the six audited AOT class slots."""
from pathlib import Path
import struct
import test_inventory_device282 as t
from unicorn import UC_HOOK_CODE

sites=(0x53da28,0x629df0,0x70eab4,0x7f3778,0x8d843c,0x9bd100)
slots=(0x20822b0,0x20b19a0,0x20df690,0x210d380,0x213b070,0x2168d60)
native=Path(__file__).parent/'build/base293-native'
code=native.read_bytes()
for site,slot in zip(sites,slots):
    adrp,add=struct.unpack_from('<II',code,site)
    assert adrp&0x9f00001f==0x90000015 and add&0xffc003ff==0x910002b5
    imm=((adrp>>5)&0x7ffff)<<2|((adrp>>29)&3)
    if imm&(1<<20):imm-=1<<21
    assert (site&~4095)+(imm<<12)+((add>>10)&4095)==slot

NEW=t.F+0x21000;RELEASE=NEW+0x100;SET=NEW+0x200
t.put(t.JNI+163*8,'<Q',NEW);t.put(t.JNI+23*8,'<Q',RELEASE);t.put(t.JNI+174*8,'<Q',SET)
created=[];released=[];writes=[]
def hook(u,pc,size,_):
    if pc==NEW:
        text=bytes(u.mem_read(t.reg(1),t.reg(2)*2)).decode('utf-16-le')
        assert text=='Sự kiện';p=t.alloc(0x30);created.append(p);t.ret(p)
    elif pc==RELEASE:released.append(t.reg(1));t.ret()
    elif pc==SET:
        a,i,value=t.reg(1),t.reg(2),t.reg(3)
        assert i==3 and t.pins[a]==1 and t.pins[value]==1
        t.put(a+0x18+8*i,'<Q',value);writes.append((a,i,value));t.ret()
t.u.hook_add(UC_HOOK_CODE,hook)
def array(n):
    p=t.alloc(0x18+8*max(8,n));t.put(p+0x10,'<i',n);return p
for v,slot in enumerate(slots):
    assert t.call('_AGEventMenuTitle',t.E,v)==0 # not initialized: no forced init
    clazz=t.alloc(0xf0);t.put(t.B+slot,'<Q',clazz)
    assert t.call('_AGEventMenuTitle',t.E,v)==0
    outer=array(8);labels=array(4);other=array(4)
    t.put(clazz+0xa0,'<Q',outer);t.put(outer+0x18+7*8,'<Q',labels);t.put(outer+0x18+6*8,'<Q',other)
    for i in range(4):t.put(labels+0x18+i*8,'<Q',0x1110+i);t.put(other+0x18+i*8,'<Q',0x2220+i)
    assert t.call('_AGEventMenuTitle',t.E,v)==1
    title=t.get(labels+0x18+3*8,'<Q');assert title==created[-1]
    assert [t.get(labels+0x18+i*8,'<Q') for i in range(3)]==[0x1110,0x1111,0x1112]
    assert [t.get(other+0x18+i*8,'<Q') for i in range(4)]==[0x2220,0x2221,0x2222,0x2223]
    assert t.get(clazz+0xdc,'<i')==0 # selection/action state untouched
    before=len(writes)
    for _ in range(20):assert t.call('_AGEventMenuTitle',t.E,v)==0
    assert len(writes)==before
    replacement=array(4);t.put(outer+0x18+7*8,'<Q',replacement)
    assert t.call('_AGEventMenuTitle',t.E,v)==1 and t.get(replacement+0x30,'<Q')==title
    for target,bad in ((outer,7),(outer,33),(replacement,3),(replacement,17)):
        old=t.get(target+0x10,'<i');t.put(target+0x10,'<i',bad)
        assert t.call('_AGEventMenuTitle',t.E,v)==0;t.put(target+0x10,'<i',old)
assert t.call('_AGEventMenuTitle',0,0)==0 and t.call('_AGEventMenuTitle',t.E,6)==0
assert len(created)==len(released)==6 and len(writes)==12
assert all(n==(1 if p in created else 0) for p,n in t.pins.items())
print('PASS compiled native event title: six AOT-audited PB class slots, exact Unicode Sự kiện, only ranking row3 changed, replacement arrays, invalid bounds, no repeated JNI work, balanced array roots')
