"""Exercise receive-side owner repair and real recipe child layout on six PBs."""
import struct
import test_inventory_device282 as t
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
recipe_classes=(0x2087cf0,0x20b6f10,0x20e4c00,0x21128f0,0x21405e0,0x216e2d0)
getters=(0x55f640,0x64a3c4,0x72f088,0x813d4c,0x8f8a10,0x9dd6d4)
raw=(Path(__file__).parent/'build/base293-native').read_bytes()
dis=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
for address,clazz in zip(getters,recipe_classes):
    text=list(dis.disasm(raw[address:address+0x70],address))
    page=next(int(i.op_str.split('#')[1],16)for i in text if i.mnemonic=='adrp' and i.op_str.startswith('x19,'))
    offset=next(int(i.op_str.split('#')[1],16)for i in text if i.mnemonic=='add' and i.op_str.startswith('x19, x19,'))
    assert page+offset==clazz
    # The identically shaped Z5.i follows the getter by 0x108.
    assert raw[address+0x124:address+0x128]==bytes.fromhex('622a00f9'),'Actual recipe parent is not +0x50'
assert '_AGInventoryPrepareRecipe' in t.symbols
for v in range(6):
    canvas=t.alloc(0x180);root=t.alloc(0xe0);clazz=t.alloc(0x180);pool=t.alloc(0xc0)
    rc=t.alloc(0x180);recipe=t.alloc(0x80);t.put(recipe,'<Q',rc);t.put(rc+0xa0,'<Q',recipe)
    for address,value in ((t.canvases[v],canvas),(t.classes[v],clazz),(t.pools[v],pool),(recipe_classes[v],rc)):t.put(t.B+address,'<Q',value)
    t.put(root,'<Q',clazz);t.put(clazz+0xa0,'<Q',root);t.put(canvas+0xb8,'<Q',root)
    old=t.item(126,2);source=t.vector([t.item(7,1000),old]);t.put(pool+0xa8,'<Q',source)
    t.call('_AGInventoryOrder',t.E,v,canvas,root,1)
    display=t.get(root+0x70,'<Q');t.put(root+0xc8,'<i',t.ids(display).index(126))
    t.put(recipe+0x50,'<Q',root);t.put(recipe+0x10,'<Q',t.alloc(0x30));t.put(canvas+0xb8,'<Q',recipe)
    t.call('_AGInventoryOrder',t.E,v,canvas,recipe,0)
    assert t.pins[display]==1,'Real formula child prematurely closed the inventory session'
    latest=t.item(126,1);t.put(pool+0xa8,'<Q',t.vector([t.item(7,900),latest]))
    assert t.call('_AGInventoryResolve',t.E,old)==latest
    message=t.alloc(0x40);stream=t.alloc(0x30);array=t.alloc(0x80)
    t.put(message+0x20,'<Q',stream);t.put(stream+0x10,'<Q',array)
    t.put(array+0x10,'<i',64);t.put(stream+0x18,'<i',13);t.put(stream+0x20,'<i',3)
    t.put(message+0x30,'<b',-18);t.u.mem_write(array+0x17,b'\1'+struct.pack('>qB',126,3))
    for current in (root,recipe):
        replacement=t.alloc(0xe0);t.put(replacement,'<Q',clazz);t.put(clazz+0xa0,'<Q',replacement)
        t.put(canvas+0xb8,'<Q',current)
        unchanged=bytes(t.u.mem_read(message,0x40))+bytes(t.u.mem_read(stream,0x30))+bytes(t.u.mem_read(array,0x80))+bytes(t.u.mem_read(root,0xe0))
        t.call('_AGInventoryPrepareRecipe',t.E,message,v)
        assert t.get(clazz+0xa0,'<Q')==root
        assert t.get(canvas+0xb8,'<Q')==current
        assert unchanged==bytes(t.u.mem_read(message,0x40))+bytes(t.u.mem_read(stream,0x30))+bytes(t.u.mem_read(array,0x80))+bytes(t.u.mem_read(root,0xe0))
    # Late replies after leaving, craft result0, truncated/malformed streams,
    # another command and a different PB cannot adopt a foreign screen.
    for mode in ('outside','result','short','position','command','foreign_pb'):
        replacement=t.alloc(0xe0);t.put(replacement,'<Q',clazz);t.put(clazz+0xa0,'<Q',replacement)
        t.put(canvas+0xb8,'<Q',root if mode!='outside' else t.alloc(0x80))
        t.put(message+0x30,'<b',27 if mode=='command' else -18)
        t.put(stream+0x18,'<i',12 if mode=='short' else 13)
        t.put(stream+0x20,'<i',14 if mode=='position' else 3)
        t.put(array+0x17,'<B',0 if mode=='result' else 1)
        t.call('_AGInventoryPrepareRecipe',t.E,message,(v+1)%6 if mode=='foreign_pb' else v)
        assert t.get(clazz+0xa0,'<Q')==replacement,mode
    t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
assert all(n==0 for n in t.pins.values())
print('PASS compiled six-PB receive binding: audited native parent+0x50, preserved child session/pins, refreshed handles, repaired owner before parsing, untouched source/selection/packet/cursor, late/result/malformed/foreign-PB exclusions')
