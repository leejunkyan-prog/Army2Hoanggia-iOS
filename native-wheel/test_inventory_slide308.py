"""Original six-PB panel activation/easing/paint followed by the grid hook.

The Java graphics boundary records translations and absolute clipping. The
unchanged AOT functions supply the actual entrance positions, not a recreated
animation. Build307 loses the body's translation at the very first frame.
"""
from pathlib import Path
import re,struct
from unicorn import UC_HOOK_CODE
import test_inventory_device282 as t

raw=(Path(__file__).parent/'build/base293-native').read_bytes()
t.u.mem_write(t.B,raw[:26050560])
grid=(Path(__file__).parent/'GridMap.h').read_text()
layouts=[int(x,16) for x in re.findall(r'\{(0x[0-9a-f]+),0x[0-9a-f]+,GM_LAYOUT,\d,0\}',grid)]
paints=[int(x,16) for x in re.findall(r'\{(0x[0-9a-f]+),0x[0-9a-f]+,GM_HALF_INNER,\d,0\}',grid)]
def target(at):
 w=struct.unpack_from('<I',raw,at)[0];assert w>>26==0x25
 n=w&0x3ffffff
 return at+4*(n-(1<<26) if n&(1<<25) else n)
def signed(n):return struct.unpack('<i',struct.pack('<I',n&0xffffffff))[0]
calls={};clips=[];headers=[];width=432
def translate():
 p=t.reg(1)
 for off,r in ((0x48,2),(0x4c,3)):t.put(p+off,'<i',t.get(p+off,'<i')+signed(t.reg(r)))
 t.put(p+0x50,'<B',1);t.ret()
def clip():
 p=t.reg(1);clips.append((signed(t.reg(2))+t.get(p+0x48,'<i'),signed(t.reg(3))+t.get(p+0x4c,'<i'),signed(t.reg(4)),signed(t.reg(5))));t.ret()
def header():
 headers.append(t.get(t.reg(1)+0x48,'<i'));t.ret()
def hook(u,pc,size,_):
 if pc==t.B+0x1c619c:translate()
 elif pc==t.B+0x1c6190:clip()
 elif pc in calls:calls[pc]()
t.u.hook_add(UC_HOOK_CODE,hook)

for v in range(6):
 ctor=target(layouts[v]-0xd0);activate=ctor+0x34;paint=ctor+0x84
 update=target(ctor+0xf0+0x20)-0x2c
 # Audit the pure easing body, including the actual native offset fields.
 assert raw[update:update+4]==bytes.fromhex('29204629')
 t.symbols['_native_open']=t.B+activate;t.symbols['_native_ease']=t.B+update;t.symbols['_native_panel_paint']=t.B+paint
 calls[t.B+target(activate+0x24)]=lambda:t.ret(width)
 calls[t.B+target(activate+0x3c)]=lambda:t.ret()
 calls[t.B+target(paint+0x28)]=lambda:t.ret() # underlying screen paint
 calls[t.B+target(paint+0x58)]=header
 for width in (320,432,768):
  canvas=t.alloc(0x180);screen=t.alloc(0xe0);clazz=t.alloc(0x180);pool=t.alloc(0xc0)
  t.put(t.B+t.canvases[v],'<Q',canvas);t.put(t.B+t.classes[v],'<Q',clazz);t.put(t.B+t.pools[v],'<Q',pool)
  t.put(screen,'<Q',clazz);t.put(clazz+0xa0,'<Q',screen);t.put(canvas+0xb8,'<Q',screen)
  t.put(canvas+0x130,'<i',width);t.put(canvas+0x128,'<i',602)
  vec=t.vector([t.item(37,2000)]);t.put(pool+0xa8,'<Q',vec);t.put(screen+0x70,'<Q',vec)
  t.call('_AGInventoryTick',t.E,v)
  t.call('_native_open',t.E,screen,t.alloc(0x80))
  assert t.get(screen+0x34,'<i')==-width and t.get(screen+0x30,'<i')==0
  positions=[];g=t.alloc(0x60);frame=t.alloc(31*8)
  t.put(frame+19*8,'<Q',t.E);t.put(frame+20*8,'<Q',g)
  for i in range(32):
   x=t.get(screen+0x34,'<i');positions.append(x)
   t.put(g+0x48,'<ii',0,0);t.put(g+0x50,'<B',1)
   t.call('_native_panel_paint',t.E,screen,g)
   assert headers[-1]==x
   t.call('_AGGridAdjust',frame,t.B+paints[v])
   assert clips[-1]==(0,0,width,602),'Inherited clip must cover the viewport'
   assert t.get(g+0x48,'<i')==x,'Chest body lost the native left-to-right entrance offset'
   assert t.get(g+0x4c,'<i')==0
   t.call('_native_ease',t.E,screen)
  assert positions[0]==-width and positions[-1]==0
  assert all(a<=b for a,b in zip(positions,positions[1:]))
  assert len(set(positions))>5,'Entrance must contain intermediate positions'
  t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
assert all(n==0 for n in t.pins.values())
print('PASS308: unchanged AOT activation, easing and panel paint for six PBs at three widths; frame/body share all 32 entrance positions; full viewport clip retained; roots balanced. Graphics/JVM primitives mocked, no device claim.')
