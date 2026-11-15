"""Interleave the native per-frame source rebind inside the real Detail callback.

The prior tests rebound before the callback. Here the rebind happens after the
classifier, during the wait/dialog boundary and before the original third v()
lookup. Transport, Java collection primitives and paint/text remain boundaries.
"""
from pathlib import Path
import json
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_SP,UC_ARM64_REG_LR,UC_ARM64_REG_PC,UC_ARM64_REG_X29
import test_inventory_device282 as t
import patch_recipe301 as patch
raw=(Path(__file__).parent/'build/base293-native').read_bytes()
fixed='_AGRecipeDetailObject' in t.symbols
if fixed:raw,edits=patch.patch_native(raw,Path(t.p).read_bytes())
cases=json.loads((Path(__file__).parent/'testdata/aot285.json').read_text())['inventory']
def load(at,size):
    off=patch.file_offset(at);t.u.mem_write(t.B+at,raw[off:off+size]);t.u.ctl_remove_cache(t.B+at,t.B+at+size)
load(patch.CAVE,6*0x60);load(patch.NAME,64)
requests=[];services={};request_targets={};labels=set();dialogs=set();casts=set();gear_text=set();prefixes=set();contains=set()
for c in cases:
    load(c['callback'],0x144);load(c['select'],0x6c);load(c['consume'],0x124)
    services[t.B+c['service']]=t.alloc(0x30);request_targets[t.B+c['request']]=c['variant']
    labels.add(t.B+c['label']);dialogs.add(t.B+c['dialog'])
    def branch(at):
        w=int.from_bytes(raw[at:at+4],'little');assert w&0xfc000000==0x94000000
        d=w&0x3ffffff;return at+4*(d-(1<<26)if d&(1<<25)else d)
    casts.add(t.B+branch(c['select']+0x50));gear_text.add(t.B+branch(c['callback']+0xfc))
    prefixes.add(t.B+branch(c['callback']+0x6c));contains.add(t.B+branch(c['callback']+0x80))
interleave=False;missing=False;active=None;plain=0
def hook(u,pc,size,_):
    global plain
    if pc==t.B+0x131cf70:
        name=bytes(u.mem_read(t.reg(1),80)).split(b'\0')[0].decode()
        assert name in ('AGRecipeDetail','AGRecipeDetailObject'),name
        t.ret(0 if missing else t.symbols['_'+name])
    elif pc in services:t.ret(services[pc])
    elif pc in request_targets:
        requests.append((request_targets[pc],t.reg(2)&255,t.reg(3),t.reg(4)));t.ret()
    elif pc in labels or pc in gear_text or pc in prefixes:t.ret(t.alloc(0x30))
    elif pc in contains:t.ret(1)
    elif pc in dialogs:
        plain+=1
        if interleave:
            # This is C6.n's ordinary assignment, scheduled after Detail was
            # classified. Its displayed index is now a different source item.
            screen,source,paper=active
            if fixed:assert t.get(t.u.reg_read(UC_ARM64_REG_SP),'<Q')==paper,'Resolved recipe is not rooted in the callback frame'
            index=t.get(screen+0xc8,'<i');arr=t.get(source+0x18,'<Q')
            t.put(screen+0x70,'<Q',source);t.put(screen+0x90,'<Q',t.get(arr+0x18+index*8,'<Q'))
        t.ret()
    elif pc==t.B+0x1dfce8:t.ret(t.get(t.reg(1)+0x24,'<i'))
    elif pc==t.B+0x1dfcb8:
        vec=t.reg(1);index=t.reg(2);assert 0<=index<t.get(vec+0x24,'<i')
        t.ret(t.get(t.get(vec+0x18,'<Q')+0x18+index*8,'<Q'))
    elif pc in casts:t.ret(t.reg(1))
t.u.hook_add(UC_HOOK_CODE,hook)
def invoke(at,*args):
    stack=t.S+0x30000;t.u.reg_write(UC_ARM64_REG_SP,stack);t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
    preserved={i:0xab000000+i for i in range(19,29)}
    t.u.reg_write(UC_ARM64_REG_X29,0xabcd0000)
    for i,val in preserved.items():t.u.reg_write(t.regs[i],val)
    for i,val in enumerate(args):t.u.reg_write(t.regs[i],val)
    t.u.emu_start(t.B+at,t.STOP+4,count=1000000)
    assert t.u.reg_read(UC_ARM64_REG_PC)==t.STOP and t.u.reg_read(UC_ARM64_REG_SP)==stack
    assert {i:t.reg(i)for i in preserved}==preserved,'Native callback changed callee-saved registers'
    assert t.u.reg_read(UC_ARM64_REG_X29)==0xabcd0000,'Native callback changed caller frame pointer'
    return t.reg(0)
reproduced=0
for c in cases:
    v=c['variant']
    for recipe in (126,127,128):
        canvas=t.alloc(0x180);screen=t.alloc(0xe0);clazz=t.alloc(0x180);pool=t.alloc(0xc0)
        t.put(t.B+t.canvases[v],'<Q',canvas);t.put(t.B+t.classes[v],'<Q',clazz);t.put(t.B+t.pools[v],'<Q',pool)
        t.put(screen,'<Q',clazz);t.put(clazz+0xa0,'<Q',screen);t.put(canvas+0xb8,'<Q',screen)
        wrapper=t.alloc(0x20);callback=t.alloc(0x20);t.put(wrapper+0x10,'<Q',screen);t.put(callback+0x10,'<Q',wrapper)
        paper=t.item(recipe,8);gear=t.item(50001,equipment=True);material=t.item(7,9000)
        source=t.vector([paper,gear,material]);t.put(pool+0xa8,'<Q',source);t.call('_AGInventoryOrder',t.E,v,canvas,screen,1)
        def select():
            display=t.get(screen+0x70,'<Q');index=t.ids(display).index(recipe)
            t.put(screen+0xc8,'<i',index);t.put(screen+0x90,'<Q',paper)
        select();active=(screen,source,paper);interleave=False
        before=len(requests);invoke(c['callback'],t.E,callback)
        assert requests[before:]==[(v,recipe,1,255)],'Control failed before craft/rebind'
        for turn in range(4):
            t.call('_AGInventoryOrder',t.E,v,canvas,screen,1);select()
            invoke(c['consume'],t.E,screen,recipe,1)
            paper=t.item(recipe,7-turn);new_gear=t.item(60000+turn,equipment=True)
            source=t.vector([paper,gear,new_gear,material]);t.put(pool+0xa8,'<Q',source)
            t.call('_AGInventoryOrder',t.E,v,canvas,screen,1);select()
            active=(screen,source,paper);interleave=True
            if turn%2:t.put(screen+0x70,'<Q',source) # first lookup can also be source-indexed
            before=len(requests);invoke(c['callback'],t.E,callback)
            expected=(v,recipe,1,255)
            if fixed:assert requests[before:]==[expected],('Classified/send item changed',v,turn,requests[before:])
            else:
                assert requests[before:]==[(v,7,1,255)],('Baseline must reproduce the late lookup sending material7',requests[before:])
                reproduced+=1
        interleave=False;t.call('_AGInventoryOrder',t.E,v,canvas,screen,1)
        display=t.get(screen+0x70,'<Q');index=t.ids(display).index(50001);t.put(screen+0xc8,'<i',index);t.put(screen+0x90,'<Q',gear)
        before=len(requests);invoke(c['callback'],t.E,callback);assert len(requests)==before,'Equipment became a recipe'
        if fixed:
            # Missing export uses the unchanged native description predicate,
            # and its classified object still has a valid rooted send target.
            t.call('_AGInventoryOrder',t.E,v,canvas,screen,1);select()
            t.put(paper+0x68,'<Q',t.alloc(0x30));missing=True;interleave=True
            before=len(requests);invoke(c['callback'],t.E,callback)
            assert requests[before:]==[(v,recipe,1,255)],'Legacy missing-export fallback lost its held item'
            missing=False;interleave=False
        t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
assert all(n==0 for n in t.pins.values())
if fixed:print('PASS301 real ARM64 Detail callbacks: six PBs,72 after-craft interleavings, exact classified126/127/128 sent once despite late source rebind/handle replacement, input rebind before classifier, gear and missing-export fallback, JNI roots and register/stack preservation')
else:print(f'PASS baseline300 reproduces {reproduced} wrong requests: correct recipe classifier followed by late native lookup sending material7 after craft')
