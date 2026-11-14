"""Execute B285's actual AOT recipe callback, selection and consumption code.

The framework is the actual Apple ARM64 build. Only transport, Java Vector
primitives and UI text/paint are substituted. No live account is accessed.
"""
import base64,json
from pathlib import Path
import test_inventory_device282 as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_SP,UC_ARM64_REG_LR

fixture=json.loads((Path(__file__).parent/'testdata/aot285.json').read_text())
assert fixture['source_sha256']=='6cdd39d83a4e221b75cbcb30c5780c0c5f3e69503e2e733e3dad6e867a6f36e7'
for address,data in fixture['chunks'].items():t.u.mem_write(t.B+int(address,16),base64.b64decode(data))
requests=[];services={};request_targets={};text_targets=set()
cast_targets=set()
for case in fixture['inventory']:
 services[t.B+case['service']]=t.alloc(0x30)
 request_targets[t.B+case['request']]=case['variant']
 text_targets|={t.B+case['label'],t.B+case['dialog']}
 at=case['select']+0x50;word=t.get(t.B+at,'<I');assert word>>26==0b100101
 offset=word&0x3ffffff
 cast_targets.add(t.B+at+4*(offset-(1<<26)if offset&(1<<25)else offset))

def hook(u,pc,size,_):
 if pc==t.B+0x131cf70:
  name=bytes(u.mem_read(t.reg(1),80)).split(b'\0')[0].decode()
  assert name=='AGRecipeDetail';t.ret(t.symbols['_'+name])
 elif pc in services:t.ret(services[pc])
 elif pc in request_targets:
  assert t.reg(0)==t.E
  requests.append((request_targets[pc],t.reg(2)&255,t.reg(3),t.reg(4)))
  t.ret()
 elif pc in text_targets:t.ret(t.alloc(0x30))
 elif pc==t.B+0x1dfce8:t.ret(t.get(t.reg(1)+0x24,'<i'))
 elif pc==t.B+0x1dfcb8:
  vec=t.reg(1);index=t.reg(2);n=t.get(vec+0x24,'<i')
  assert 0<=index<n
  t.ret(t.get(t.get(vec+0x18,'<Q')+0x18+index*8,'<Q'))
 elif pc in cast_targets:t.ret(t.reg(1))
 elif pc==t.B+0x1dfcdc:
  vec=t.reg(1);obj=t.reg(2);a=t.get(vec+0x18,'<Q');n=t.get(vec+0x24,'<i')
  rows=[t.get(a+0x18+8*i,'<Q')for i in range(n)];rows.remove(obj)
  for i,row in enumerate(rows):t.put(a+0x18+8*i,'<Q',row)
  t.put(vec+0x24,'<i',len(rows));t.ret()
t.u.hook_add(UC_HOOK_CODE,hook)

def invoke(address,*args):
 t.u.reg_write(UC_ARM64_REG_SP,t.S+0x30000);t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
 for i,n in enumerate(args):t.u.reg_write(t.regs[i],n)
 try:t.u.emu_start(t.B+address,t.STOP+4,count=1000000)
 except Exception:
  print('AOT failure',hex(address),'variant',v,'PC',hex(t.u.reg_read(UC_ARM64_REG_PC)),'LR',hex(t.u.reg_read(UC_ARM64_REG_LR)))
  raise
 assert t.u.reg_read(UC_ARM64_REG_PC)==t.STOP
 return t.reg(0)

for case in fixture['inventory']:
 v=case['variant'];canvas=t.alloc(0x180);screen=t.alloc(0xe0);clazz=t.alloc(0x180);pool=t.alloc(0xc0)
 t.put(t.B+t.canvases[v],'<Q',canvas);t.put(canvas+0xb8,'<Q',screen)
 t.put(screen,'<Q',clazz);t.put(t.B+t.classes[v],'<Q',clazz);t.put(t.B+t.pools[v],'<Q',pool)
 t.put(clazz+0xa0,'<Q',screen)
 source=[t.item(7,1000),t.item(120,50),t.item(121,50)]
 t.put(pool+0xa8,'<Q',t.vector(source));t.call('_AGInventoryOrder',t.E,v,canvas,screen,1)
 wrapper=t.alloc(0x20);callback=t.alloc(0x20);t.put(wrapper+0x10,'<Q',screen);t.put(callback+0x10,'<Q',wrapper)
 for turn in range(24):
  recipe_id=120 if turn<12 else 121
  displayed=t.get(screen+0x70,'<Q');index=t.ids(displayed).index(recipe_id)
  t.put(screen+0xc8,'<i',index)
  selected=invoke(case['select'],t.E,screen);t.put(screen+0x90,'<Q',selected)
  # Craft consumes through the original method; server then replaces item
  # handles and delivers a new piece of gear while the chest stays open.
  old_quantity=t.get(selected+0x90,'<q')
  invoke(case['consume'],t.E,screen,recipe_id,1)
  assert t.get(selected+0x90,'<q')==old_quantity-1
  fresh=[]
  for item in source:
   fresh.append(t.item(t.get(item+0x80,'<q'),t.get(item+0x90,'<q'),equipment=not t.get(item+0xbd,'<B')))
  fresh.append(t.item(70000+turn,equipment=True))
  source=fresh;t.put(pool+0xa8,'<Q',t.vector(source))
  t.call('_AGInventoryOrder',t.E,v,canvas,screen,1)
  latest=next(item for item in source if t.get(item+0x80,'<q')==recipe_id)
  assert invoke(case['select'],t.E,screen)==latest,('Craft changed the recipe callback target',v,turn,t.displayed(screen))
  # Native C6.n rebinds its source vector on EVERY update, even while
  # the menu/amount/result dialog is open. The selected index is still
  # an index into the sorted display, not into this source.
  t.put(screen+0x70,'<Q',t.get(pool+0xa8,'<Q'))
  t.put(canvas+0x108,'<Q',t.alloc(0x40))
  if turn%2==0:t.call('_AGInventoryOrder',t.E,v,canvas,screen,1)
  before=len(requests);invoke(case['callback'],t.E,callback)
  t.put(canvas+0x108,'<Q',0)
  assert requests[before:]==[(v,recipe_id,1,255)],('Wrong or duplicate recipe request',requests[before:])
  # A server refresh may also arrive while a recipe child/menu is open.
  newer=t.item(recipe_id,t.get(latest+0x90,'<q'))
  source=[newer if item==latest else item for item in source]
  t.put(pool+0xa8,'<Q',t.vector(source));child=t.alloc(0x20)
  t.put(child+0x10,'<Q',screen);t.put(canvas+0xb8,'<Q',child)
  assert t.call('_AGInventoryResolve',t.E,latest)==newer,('Wrong PB or stale child recipe',v,turn)
  assert invoke(case['select'],t.E,screen)==newer
  t.put(canvas+0xb8,'<Q',screen)
 assert t.call('_AGRecipeDetail',t.E,t.item(120,equipment=True))==0,'Gear with matching low ID bits is not a recipe'
 t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
assert all(count==0 for count in t.pins.values())
print('PASS recipe dialog rebinding, actual B288 AOT: 6 variants, 144 consecutive craft/reopen-detail cycles, same and different recipes, refreshed handles during child/menu, exactly 1 correct request per tap, no chest exit')

