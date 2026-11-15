"""Run the original cmd101 recreation, result callback and -18 reply gate.

Allocation, UTF/StringBuilder, vectors and command text are boundaries. The
controller parser, singleton setter, identity comparisons, recipe parent store,
result callback and screen activation execute the unchanged iPhone ARM64.
The baseline301 control must parse replies yet fail to reopen the formula.
No account, live server or craft operation is used.
"""
import struct
import test_spectator_live291 as s
from unicorn.arm64_const import UC_ARM64_REG_SP,UC_ARM64_REG_LR,UC_ARM64_REG_X0,UC_ARM64_REG_PC
t=s.t
fixed='_AGInventoryPrepareRecipe' in t.symbols
clazz=t.alloc(0x180);root=t.alloc(0xe0);recipe_class=t.alloc(0x180);recipe=t.alloc(0x80)
table=t.alloc(0x100);t.put(clazz+0x28,'<Q',table);t.put(table+0x60,'<Q',t.MAIN+0x590ae4)
t.put(root,'<Q',clazz);t.put(recipe,'<Q',recipe_class)
t.put(t.MAIN+0x2091350,'<Q',clazz);t.put(clazz+0xa0,'<Q',root)
t.put(t.MAIN+0x2087cf0,'<Q',recipe_class);t.put(recipe_class+0xa0,'<Q',recipe)
t.put(recipe+0x50,'<Q',root);t.put(recipe+0x10,'<Q',t.alloc(0x30))
vec=t.alloc(0x40);t.put(recipe+0x48,'<Q',vec);rows=[];activations=[]
def utf():
    n=struct.unpack_from('>H',s.data,s.cursor)[0];s.cursor+=2
    assert s.cursor+n<=len(s.data);s.cursor+=n;t.ret(t.alloc(0x30))
def fresh_inventory():
    p=t.alloc(0xe0);t.put(p,'<Q',clazz);t.ret(p)
def clear_rows():
    assert t.reg(1)==vec;rows.clear();t.put(vec+0x24,'<i',0);t.ret()
def add_row():
    assert t.reg(1)==vec;rows.append(t.reg(2));t.put(vec+0x24,'<i',len(rows));t.ret()
def formula_commands():
    assert t.reg(1)==recipe and len(rows)>0
    assert 0<=t.get(recipe+0x58,'<i')<len(rows)
    activations.append(t.get(recipe+0x50,'<Q'));t.ret()
for start,end in ((0x55f640,0x55f67c),(0x5906cc,0x590708),(0x590708,0x590748),
                  (0x55f748,0x55f784),(0x560350,0x560374),(0x515ae4,0x515b20),
                  (0x5ad9e8,0x5ada44),(0x590ae4,0x590b1c),(0x50b910,0x50b950)):
    t.nativeRanges.append((t.MAIN+start,t.MAIN+end));t.u.ctl_remove_cache(t.MAIN+start,t.MAIN+end)
t.extraNative.update({
    t.MAIN+0x590680:fresh_inventory,t.MAIN+0x590748:lambda:t.ret(),
    # Stop cmd101 only after its original constructor + singleton assignment.
    # Item replacement payloads are independently covered by inventory tests.
    t.MAIN+0x528028:s.halt,
    t.MAIN+0xa642f0:utf,t.MAIN+0x1dfcd8:clear_rows,t.MAIN+0x1dfcac:add_row,
    t.MAIN+0x50c264:lambda:t.ret(),
    t.MAIN+0x50b8d4:lambda:t.ret(t.get(s.c+0xb8,'<Q')),
    t.MAIN+0x5748b4:lambda:t.ret(s.back),
    t.MAIN+0x5603b0:formula_commands,t.MAIN+0x5908e0:lambda:t.ret(),
    t.MAIN+0x5acdf8:lambda:t.ret(),
    t.MAIN+0x5d6274:lambda:t.ret(t.alloc(0x80)),t.MAIN+0x5d62c0:lambda:t.ret(),
    t.MAIN+0x514824:lambda:t.ret(t.alloc(0xd0)),
    t.MAIN+0x4f4a38:lambda:s.arr(8),t.MAIN+0x1fcf38:lambda:s.arr(2),
    t.MAIN+0x12e7d88:lambda:s.arr(8),
    t.MAIN+0xabd104:lambda:t.ret(t.alloc(0x40)),t.MAIN+0xabd150:lambda:t.ret(),
    t.MAIN+0xabd3d8:lambda:t.ret(t.reg(1)),t.MAIN+0xabd9b0:lambda:t.ret(t.alloc(0x30)),
    t.MAIN+0x1f64a4:lambda:t.ret(t.alloc(0x30)),
})
for off in range(0x5373b8,0x537598,0x28):t.extraNative[t.MAIN+off]=lambda:t.ret(t.alloc(0x30))
def invoke(address,*args):
    t.u.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,n in enumerate(args):t.u.reg_write(UC_ARM64_REG_X0+i,n)
    t.u.emu_start(t.MAIN+address,t.STOP+4,count=1000000)
    assert t.u.reg_read(UC_ARM64_REG_PC)==t.STOP
def reply(recipe_id,count):
    # Native fields per minimal option: gear ID, name, level/type/template,
    # material count, cost, cost label, token count and eligibility bytes.
    payload=b'\1'+struct.pack('>qB',recipe_id,count)+bytes(28*count)
    array=t.alloc(0x14+len(payload));stream=t.alloc(0x30)
    t.put(array+0x10,'<i',len(payload));t.u.mem_write(array+0x14,payload)
    t.put(stream+0x10,'<Q',array);t.put(stream+0x18,'<i',len(payload))
    t.put(s.message+0x20,'<Q',stream);t.put(s.message+0x30,'<b',-18)
    if fixed:t.call('_AGInventoryPrepareRecipe',t.ENV,s.message,0)
    assert t.get(stream+0x20,'<i')==0,'Preparation consumed reply bytes'
    s.dispatch(-18,payload)
    assert len(rows)==count and all(t.get(row+0x48,'<q')==recipe_id for row in rows)

missed=0
for turn in range(24):
    t.put(s.c+0xb8,'<Q',recipe)
    s.dispatch(101,b'')
    replacement=t.get(clazz+0xa0,'<Q');assert replacement!=root
    # The real craft-result callback retrieves +0x50 and calls its native
    # activator. It returns to the old chest, not the newly assigned singleton.
    invoke(0x515ae4,t.ENV,t.alloc(0x20))
    assert t.get(s.c+0xb8,'<Q')==root and t.get(clazz+0xa0,'<Q')==replacement
    count=3 if turn%3 else 1;t.put(recipe+0x58,'<i',2)
    before=len(activations);reply(125 if turn%2 else 126,count)
    if fixed:
        assert t.get(clazz+0xa0,'<Q')==root
        assert t.get(s.c+0xb8,'<Q')==recipe and t.get(recipe+0x50,'<Q')==root
        assert activations[before:]==[root],'No formula activation or duplicate activation'
        assert t.get(recipe+0x58,'<i')==(2 if count==3 else 0),'Invalid level retained, or valid level lost'
    else:
        assert t.get(s.c+0xb8,'<Q')==root and len(activations)==before
        missed+=1
if fixed:
    print('PASS original ARM64 cmd101 + craft result + complete -18 parsing: 24 refresh/reopen cycles, same/different recipes, 1/3 options, real parent+0x50, one native activation per reply, no render tick or request retry')
else:
    assert missed==24
    print('CONTROL Build301 reproduced: 24/24 replies completely parsed but formula activation skipped after cmd101 replaced the inventory singleton')
