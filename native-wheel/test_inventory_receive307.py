"""Native bulk-combine callback + real cmd27 gem updates, not a replaced list.

Run the unchanged six iPhone callbacks that leave C6.containsConsumables at1.
PB1 also executes the original dispatcher, gem insertion/stack merge and C6
material consumption. Only streams, JVM Vector operations, strings, icon-cache
lookup and packet transport are boundaries; no live account is contacted.
"""
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_LR, UC_ARM64_REG_PC
import test_inventory_device282 as t

raw=(Path(__file__).parent/'build/base293-native').read_bytes()
t.u.mem_write(t.B,raw[:26050560])
callbacks=(0x4f5ee4,0x5e48dc,0x6c95a0,0x7ae264,0x892f28,0x977bec)
services=(0x5010d4,0x5ef70c,0x6d43d0,0x7b9094,0x89dd58,0x982a1c)
service_slots=(0x207b870,0x20ab650,0x20d9350,0x2107040,0x2134d30,0x2162a20)
# The same native field store exists in all six original bulk callbacks.
for callback in callbacks:
 assert raw[callback+0x1d0:callback+0x1d4]==bytes.fromhex('09510339')

calls={};payload=b'';position=0;expected=None;sends=[]
def read(fmt):
 global position
 n=struct.calcsize(fmt);assert position+n<=len(payload)
 value=struct.unpack_from(fmt,payload,position)[0];position+=n;t.ret(value)
def utf():
 global position
 n=struct.unpack_from('>H',payload,position)[0];position+=2
 assert position+n<=len(payload);position+=n;t.ret(t.alloc(0x30))
def intarray():
 n=t.reg(1);p=t.alloc(0x14+4*n);t.put(p+0x10,'<i',n);t.ret(p)
def insert():
 vec,obj,index=t.reg(1),t.reg(2),t.reg(3);n=t.get(vec+0x24,'<i');old=t.get(vec+0x18,'<Q')
 rows=[t.get(old+0x18+8*i,'<Q') for i in range(n)];rows.insert(index,obj)
 a=t.alloc(0x18+8*(n+4));t.put(a+0x10,'<i',n+4)
 for i,p in enumerate(rows):t.put(a+0x18+8*i,'<Q',p)
 t.put(vec+0x18,'<Q',a);t.put(vec+0x24,'<i',n+1);t.ret()
def ctor():t.put(t.reg(1)+0x90,'<q',1);t.ret()
def send():
 assert t.reg(2)==0 and t.reg(3)==1
 sent=(t.get(t.reg(4)+0x14,'<i'),t.get(t.reg(5)+0x14,'<i'))
 assert sent==expected,(sent,expected)
 sends.append(sent);t.ret()
# Decode the actual per-PB send call target, instead of inventing its address.
def branch_target(at):
 w=struct.unpack_from('<I',raw,at)[0];assert w>>26==0x25
 imm=w&0x3ffffff
 if imm&(1<<25):imm-=1<<26
 return at+4*imm
calls[0x12e7d28]=intarray
for v,callback in enumerate(callbacks):
 calls[services[v]]=lambda:t.ret(t.alloc(0x30))
 calls[branch_target(callback+0x284)]=send
ranges=[(a,a+0x304) for a in callbacks]
ranges += [(0x518210,0x537000),(0x5a791c,0x5a7978),
           (0x5a8e20,0x5a901c),(0x5ab9f8,0x5abb20),(0x591da4,0x591ec8)]
stream=t.alloc(0x30);message=t.alloc(0x50);t.put(message+0x20,'<Q',stream)
state={}
calls.update({
 0x4f98cc:lambda:t.ret(stream),0xa63e54:lambda:read('>b'),
 0xa63fa8:lambda:read('>i'),0xa6419c:lambda:read('>q'),0xa642f0:utf,
 0x12e7330:lambda:t.ret(),0x5b9e60:lambda:t.ret(t.item(0,0)),0x5b9eac:ctor,
 0x1dfcb8:lambda:t.ret(t.get(t.get(t.reg(1)+0x18,'<Q')+0x18+8*t.reg(2),'<Q')),
 0x1dfce8:lambda:t.ret(t.get(t.reg(1)+0x24,'<i')),
 0x1b65d4:lambda:t.ret(t.reg(1)),0x1dfcc8:insert,
 0x5a901c:lambda:t.ret(t.alloc(0x30)),0x5a9044:lambda:t.ret(t.alloc(0x30)),
 0xab9404:lambda:t.ret(t.alloc(0x30)),0xabc20c:lambda:t.ret(t.reg(1)),
 0xabc3d0:lambda:t.ret(t.reg(1)),0xab96d8:lambda:t.ret(t.reg(1)),
 0x5b7aa8:lambda:t.ret(1),0x5b7af4:lambda:t.ret(t.alloc(0x30)),
 0x5906cc:lambda:t.ret(state['screen']),0x5a779c:lambda:t.ret(state['user']),
 0x5a9728:lambda:t.ret(),0x59215c:lambda:t.ret(),
})
def hook(u,pc,size,_):
 if not t.B<=pc<t.B+0x3000000:return
 off=pc-t.B
 if off in (0x534a70,0x519830):u.reg_write(UC_ARM64_REG_PC,t.STOP);return
 if off==0x1300d54 or off in t.refresh:return
 if off in calls:calls[off]();return
 if any(a<=off<b for a,b in ranges):return
 if off in (0xbe3f1c,0xbe6b7c,0xbe6ba0,0x1dfcac):return
 raise AssertionError(('Unexpected native boundary',hex(off),hex(u.reg_read(UC_ARM64_REG_LR)-t.B)))
t.u.hook_add(UC_HOOK_CODE,hook)
t.symbols['_original_dispatch']=t.B+0x518210

def receive(gain,quantity,material=None,consumed=0):
 global payload,position
 # User.updateRuong: type3 stacked gain (or type1 singleton) then type0 loss.
 payload=bytes([2 if material is not None else 1,3 if quantity>1 else 1])+struct.pack('>q',gain)
 if quantity>1:payload+=struct.pack('>q',quantity)
 payload+=bytes(4) # two empty modified-UTF strings
 if material is not None:payload+=bytes([0])+struct.pack('>iq',material,consumed)
 position=0;t.put(message+0x30,'<b',27)
 t.call('_original_dispatch',t.E,t.alloc(0x40),message)
 assert position==len(payload)

def combine(v,screen,item,quantity):
 global expected
 expected=(t.get(item+0x80,'<q'),quantity)
 callback=t.alloc(0x20);t.put(callback+0x10,'<Q',screen)
 t.put(item+0xbc,'<B',1);t.put(item+0x98,'<q',quantity)
 t.symbols['_original_combine']=t.B+callbacks[v]
 t.call('_original_combine',t.E,callback)
 assert t.get(screen+0xd4,'<B')==1 # This persists; it is not a visible menu.
 assert t.get(screen+0xc4,'<i')==0

for v in range(6):
 canvas=t.alloc(0x180);clazz=t.alloc(0x180);screen=t.alloc(0xe0);pool=t.alloc(0xc0);user=t.alloc(0xd0)
 t.put(t.B+t.canvases[v],'<Q',canvas);t.put(t.B+t.classes[v],'<Q',clazz);t.put(t.B+t.pools[v],'<Q',pool)
 t.put(t.B+t.pools[v]+9,'<B',2);t.put(screen,'<Q',clazz);t.put(clazz+0xa0,'<Q',screen)
 t.put(pool+0xa0,'<Q',user);t.put(canvas+0xb8,'<Q',screen);t.put(user+0xb0,'<Q',t.vector([]))
 t.put(canvas+0x130,'<i',432);t.put(canvas+0x128,'<i',602)
 service_class=t.alloc(0xb0);service=t.alloc(0x30)
 t.put(t.B+service_slots[v],'<Q',service_class);t.put(service_class+0xa0,'<Q',service);t.put(service+0x10,'<Q',10000+v)
 gear=t.item(70001,equipment=True);seven=t.item(37,2000);stone=t.item(103,40)
 vec=t.vector([gear,seven,stone]);t.put(pool+0xa8,'<Q',vec);t.put(screen+0x70,'<Q',vec)
 t.call('_AGInventoryTick',t.E,v);assert t.displayed(screen)==[70001,37,103]
 combine(v,screen,seven,2000)
 t.put(canvas+0x108,'<Q',t.alloc(0x30))
 if v==0:
  state.update(screen=screen,user=user);receive(38,311,37,1996)
  eight=t.get(t.get(vec+0x18,'<Q')+0x18,'<Q')
 else:
  # Other PB callbacks run native; the shared ordering bridge's receive input
  # is supplied here. PB1 above exercises the complete original cmd27 parser.
  eight=t.item(38,311);t.put(seven+0x90,'<q',4)
  vec=t.vector([eight,gear,seven,stone]);t.put(pool+0xa8,'<Q',vec)
 t.call('_AGInventoryTick',t.E,v);assert t.displayed(screen)==[70001,37,103]
 t.put(canvas+0x108,'<Q',0);t.call('_AGInventoryTick',t.E,v)
 assert t.displayed(screen)[0]==38,'containsConsumables must not freeze the new gem'
 assert t.get(screen+0x90,'<Q')==eight and t.get(eight+0x90,'<q')==311
 combine(v,screen,eight,311)
 if v==0:
  receive(39,43,38,307);nine=t.get(t.get(vec+0x18,'<Q')+0x18,'<Q')
 else:
  nine=t.item(39,43);t.put(eight+0x90,'<q',4)
  vec=t.vector([nine,eight,gear,seven,stone]);t.put(pool+0xa8,'<Q',vec)
 t.call('_AGInventoryTick',t.E,v);assert t.displayed(screen)[:2]==[39,38]
 assert t.get(screen+0x90,'<Q')==nine
 t.call('_AGInventoryOrder',t.E,v,canvas,0,0);t.call('_AGInventoryTick',t.E,v)
 assert t.displayed(screen)[:2]==[39,38]
 if v==0:
  receive(39,10);t.call('_AGInventoryTick',t.E,v)
  assert t.get(nine+0x90,'<q')==53
  menu=t.alloc(0x30);t.put(canvas+0xe0,'<Q',menu);t.put(menu+0x2c,'<B',1)
  receive(104,1);t.call('_AGInventoryTick',t.E,v)
  assert t.displayed(screen)[0]==39,'A truly visible menu must freeze positions'
  t.put(menu+0x2c,'<B',0);t.call('_AGInventoryTick',t.E,v)
  assert t.displayed(screen)[0]==104
 t.put(service+0x10,'<Q',0);t.call('_AGInventoryTick',t.E,v)
 t.put(service+0x10,'<Q',20000+v);t.call('_AGInventoryTick',t.E,v)
 assert t.displayed(screen)==[70001,37,38,39,103]+([104] if v==0 else [])
 assert t.get(screen+0xd4,'<B')==1,'Do not rewrite the native protocol flag'
 t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
assert len(sends)==12 and all(n==0 for n in t.pins.values())
print('PASS307: 12 unchanged native combine sends across six PBs; persistent containsConsumables flag; PB1 original cmd27 insertion, stack gain and material loss; 7->8->9 newest first, selected and visible after results; actual menu deferral; reopen retains order; new login groups gems/stones; balanced roots. JVM/transport boundaries are mocked, no device/live-server claim.')
