"""A new gem must survive C6 recreation and reopen; grouping starts at login."""
from pathlib import Path
import struct
import test_inventory_device282 as t
serviceSlots=(0x207b870,0x20ab650,0x20d9350,0x2107040,0x2134d30,0x2162a20)
sites=(0x5010e0,0x5ef718,0x6d43dc,0x7b90a0,0x89dd64,0x982a28)
raw=(Path(__file__).parent/'build/base293-native').read_bytes()
for a,expected in zip(sites,serviceSlots):
    p,q=struct.unpack_from('<II',raw,a);imm=((p>>5)&0x7ffff)<<2|((p>>29)&3)
    if imm&(1<<20):imm-=1<<21
    assert (a&~4095)+(imm<<12)+((q>>10)&4095)==expected
for v in range(6):
    clazz=t.alloc(0x180);pool=t.alloc(0xc0);canvas=t.alloc(0x180)
    serviceClass=t.alloc(0xb0);service=t.alloc(0x30);t.put(t.B+serviceSlots[v],'<Q',serviceClass);t.put(serviceClass+0xa0,'<Q',service);t.put(service+0x10,'<Q',0x12300+v)
    t.put(t.B+t.classes[v],'<Q',clazz);t.put(t.B+t.pools[v],'<Q',pool);t.put(t.B+t.canvases[v],'<Q',canvas)
    def chest():
        p=t.alloc(0xe0);t.put(p,'<Q',clazz);t.put(clazz+0xa0,'<Q',p);t.put(canvas+0xb8,'<Q',p);return p
    def source(rows):
        vec=t.vector(rows);t.put(pool+0xa8,'<Q',vec);return vec
    def show(p):t.call('_AGInventoryOrder',t.E,v,canvas,p,1)
    screen=chest();gear=t.item(70001,equipment=True);gem7=t.item(7,2000);stone=t.item(103,10)
    vec=source([stone,gem7,gear]);t.put(screen+0x70,'<Q',vec);show(screen)
    assert t.displayed(screen)==[70001,7,103]
    t.put(screen+0xc8,'<i',1);t.put(screen+0x90,'<Q',gem7)
    # The bulk result recreates the singleton and source objects while its
    # native result dialog is still open. Four level7 gems remain.
    newer=chest();fresh=[t.item(70001,equipment=True),t.item(7,4),t.item(103,10),t.item(8,311)]
    vec=source(fresh);t.put(newer+0x70,'<Q',vec);t.put(newer+0x90,'<Q',fresh[1]);t.put(canvas+0x108,'<Q',123)
    show(newer);assert t.ids(vec)==[70001,7,103,8]
    t.put(canvas+0x108,'<Q',0);show(newer)
    assert t.displayed(newer)==[8,70001,7,103] and t.get(newer+0xc8,'<i')==0
    assert t.get(newer+0x90,'<Q')==fresh[3] and t.get(fresh[3]+0x90,'<q')==311
    assert t.ids(vec)==[70001,7,103,8] # server order/quantities unchanged
    t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
    reopened=chest();t.put(reopened+0x70,'<Q',vec);show(reopened)
    assert t.displayed(reopened)==[8,70001,7,103]
    # A genuinely new stone received while the chest is closed is first on
    # the next open, above the earlier new gem.
    t.call('_AGInventoryOrder',t.E,v,canvas,0,0);newstone=t.item(104,1);vec=source(fresh+[newstone])
    reopened=chest();t.put(reopened+0x70,'<Q',vec);show(reopened)
    assert t.displayed(reopened)==[104,8,70001,7,103]
    t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
    # Logout and login on a different connection discard the remembered
    # promotion order, then group gear / gems / stones from current items.
    t.put(service+0x10,'<Q',0);t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
    t.put(service+0x10,'<Q',0x45600+v);again=chest();t.put(again+0x70,'<Q',vec);show(again)
    assert t.displayed(again)==[70001,7,8,103,104]
    t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
assert all(n==0 for n in t.pins.values())
print('PASS inventory304: six PBs, 2000 level7 gems -> 311 level8 with four level7 remaining, result dialog and C6 replacement, first-slot visibility, reopen and away-screen gains, login-only grouping, unchanged server vectors/quantities and balanced display roots')
