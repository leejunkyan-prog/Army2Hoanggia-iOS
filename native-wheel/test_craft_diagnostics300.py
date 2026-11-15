"""Compiled diagnostic observations over the actual inventory bridge.

Craft/server/VM behavior is not synthesized as a physical-device fix. Verify
post-craft replacement, source/display index drift, classification rejection,
menu/modal metadata, bounded reply events and no mutation by the sampler.
"""
import re,struct
from pathlib import Path
import test_inventory_device282 as t
header=(Path(__file__).parent/'CraftDiagnostics.h').read_text()
cf=re.findall(r'CF_[A-Z_]+',header.split('};',1)[0]);cf={name:i for i,name in enumerate(cf[:-1])}
cepart=header.split('};',1)[1].split('};',1)[0]
ce=re.findall(r'CE_[A-Z_]+',cepart);ce={name:i for i,name in enumerate(ce[:-1])}
def snapshot(v):
    out=t.alloc(512);assert t.call('_AGCraftDiagnosticCopy',v,out)==1
    counters=struct.unpack('<5Q',t.u.mem_read(out,40))
    values=struct.unpack('<'+str(len(cf))+'q',t.u.mem_read(out+40,len(cf)*8))
    return counters,{name:values[i] for name,i in cf.items()}
def events():
    size=8+8*len(ce);out=t.alloc(128*size)
    n=t.call('_AGCraftEventsCopy',out,128)
    return [{name:t.get(out+j*size+8+i*8,'<q') for name,i in ce.items()}for j in range(n)]
for v in range(6):
    canvas=t.alloc(0x180);screen=t.alloc(0xe0);clazz=t.alloc(0x180);pool=t.alloc(0xc0)
    for address,value in [(t.canvases[v],canvas),(t.classes[v],clazz),(t.pools[v],pool)]:t.put(t.B+address,'<Q',value)
    t.put(screen,'<Q',clazz);t.put(clazz+0xa0,'<Q',screen);t.put(canvas+0xb8,'<Q',screen)
    old=t.item(238,6);gear=t.item(0x7edcba98,equipment=True);currency=t.item(7,6000)
    source=t.vector([old,currency,gear]);t.put(pool+0xa8,'<Q',source)
    t.call('_AGInventoryOrder',t.E,v,canvas,screen,1)
    display=t.get(screen+0x70,'<Q');index=t.ids(display).index(238)
    t.put(screen+0xc8,'<i',index);t.put(screen+0x90,'<Q',old)
    latest=t.item(238,5);server=t.vector([latest,gear,currency]);t.put(pool+0xa8,'<Q',server)
    # Real native update can rebind the vector while its displayed index is
    # still selected. The existing resolver must preserve its old behavior.
    t.put(screen+0x70,'<Q',server)
    argument=[latest,gear,currency][index]
    assert t.call('_AGRecipeDetail',t.E,argument)==1
    counters,d=snapshot(v)
    assert counters[1:4]==(1,1,0),counters
    assert d['CF_SLOT_ID']==238 and d['CF_SLOT_QUANTITY']==5 and d['CF_SOURCE_EQUALS_SLOT']==1,d
    action=events()[-1]
    assert action['CE_PB']==v+1 and action['CE_RESULT']==1 and action['CE_REASON']==2 and action['CE_OUTPUT_ID']==238,action
    # Sample exactly the post-craft menu state seen on the supplied video.
    menu=t.alloc(0x40);t.put(menu+0x10,'<Q',t.vector([t.alloc(0x30),t.alloc(0x30)]));t.put(menu+0x18,'<i',1);t.put(menu+0x2c,'<B',1)
    t.put(canvas+0xe0,'<Q',menu);t.put(screen+0xd4,'<BB',1,1);t.put(canvas+0x108,'<Q',t.alloc(0x30))
    observed=[(p,n) for p,n in [(canvas,0x180),(screen,0xe0),(clazz,0x180),(pool,0xc0),(server,0x30),(latest,0xd0),(old,0xd0),(menu,0x40)]]
    before=[bytes(t.u.mem_read(p,n))for p,n in observed]
    t.call('_AGCraftSample',t.E,v)
    assert [bytes(t.u.mem_read(p,n))for p,n in observed]==before,'Diagnostic sampler wrote native inventory/game state'
    _,d=snapshot(v)
    assert d['CF_MENU_VISIBLE']==1 and d['CF_MENU_INDEX']==1 and d['CF_MENU_COUNT']==2 and d['CF_MODAL']==1,d
    assert d['CF_MENU_FLAG']==1 and d['CF_AMOUNT_FLAG']==1 and d['CF_DISPLAY_IS_PRIVATE']==1,d
    # Native message is observed before dispatch, without reading its body
    # or moving its stream cursor. A secret marker must not enter event data.
    message=t.alloc(0x40);stream=t.alloc(0x30);array=t.alloc(0x80)
    t.put(message+0x20,'<Q',stream);t.put(message+0x30,'<b',-73);t.put(stream+0x10,'<Q',array)
    t.put(array+0x10,'<i',64);t.put(stream+0x18,'<i',32);t.put(stream+0x20,'<i',3)
    t.u.mem_write(array+0x14,b'PRIVATE_PACKET_BODY_DO_NOT_EXPORT')
    before=bytes(t.u.mem_read(stream,0x30))
    t.call('_AGCraftReceive',message,v)
    assert bytes(t.u.mem_read(stream,0x30))==before
    event=events()[-1];assert event['CE_KIND']==2 and event['CE_COMMAND']==-73 and event['CE_LENGTH']==29,event
    # Unknown recipe with no description must record its actual rejection.
    t.put(screen+0xd4,'<BB',0,0);t.put(canvas+0x108,'<Q',0);t.put(menu+0x2c,'<B',0)
    unknown=t.item(169,2);t.put(pool+0xa8,'<Q',t.vector([unknown,currency,gear]));t.call('_AGInventoryOrder',t.E,v,canvas,screen,1)
    index=t.ids(t.get(screen+0x70,'<Q')).index(169);t.put(screen+0xc8,'<i',index);t.put(screen+0x90,'<Q',unknown)
    assert t.call('_AGRecipeDetail',t.E,unknown)==0
    action=events()[-1];assert action['CE_PB']==v+1 and action['CE_REASON']==3 and action['CE_RESULT']==0,action
    # Equipment server UIDs are never exported as template IDs.
    index=t.ids(t.get(screen+0x70,'<Q')).index(0x7edcba98);t.put(screen+0xc8,'<i',index);t.put(screen+0x90,'<Q',gear)
    t.call('_AGCraftSample',t.E,v);_,d=snapshot(v);assert d['CF_SLOT_KIND']==1 and d['CF_SLOT_ID']==-1
    t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
# A noisy receive stream must remain bounded and preserve event ordering.
for i in range(180):
    t.now+=.01;t.call('_AGCraftReceive',message,5)
assert len(events())==128
assert all(n==0 for n in t.pins.values())
print('PASS compiled craft300: six PBs, post-craft handles/quantities, displayed-index drift, classifier accepted/rejected reasons, real menu/modal fields, read-only samples and packet cursor, no item text/equipment UID/payload export, bounded128 events; existing inventory behavior retained')
