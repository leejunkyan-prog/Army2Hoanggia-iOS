"""Compiled visual binding of native POW/egg/secondary shots, all six PBs.

Only PNG/UIKit image conversion is a boundary; the production traversal,
style selection, image-field writes and global-reference lifecycle execute.
"""
from unicorn import UC_HOOK_CODE
import test_inventory_device282 as t
import reference306 as ref

raw=(ref.root/'build/base293-native').read_bytes()
# Original constructor argument6 -> visual style+4c; sprite ref+38,
# sprite base image+18, and Granos POW resets the visual style to0.
assert raw[0x577990:0x577994]==bytes.fromhex('134d00b9')
assert raw[0x57887c:0x578880]==bytes.fromhex('1f4d00b9')
assert raw[0x5d8e38:0x5d8e3c]==bytes.fromhex('140d00f9')
assert raw[0x578550:0x578554]==bytes.fromhex('151d00f9')
catalogs=(0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0)
arenas=(0x2082e30,0x20b23a0,0x20e0090,0x210dd80,0x213ba70,0x2169760)
calls=[];converted={}
SET=t.F+0x21000;t.put(t.JNI+174*8,'<Q',SET)
def hook(u,pc,size,_):
 if pc==t.symbols['_AGCostumeImage']:
  key=tuple(t.reg(i) for i in range(1,6));calls.append(key)
  if key not in converted:converted[key]=t.alloc(0x30)
  t.ret(converted[key])
 elif pc==SET:t.put(t.reg(1)+0x18+t.reg(2)*8,'<Q',t.reg(3));t.ret()
t.u.hook_add(UC_HOOK_CODE,hook)
def array(items):return t.get(t.vector(items)+0x18,'<Q')
def image():
 p=t.alloc(0x30);t.put(p+0x20,'<ii',20,20);return p
for v in range(6):
 canvas=t.alloc(0x180);arena=t.alloc(0x200);active=t.alloc(0x80);manager=t.alloc(0x80);catalog=t.alloc(0xc0)
 t.put(t.B+t.canvases[v],'<Q',canvas);t.put(t.B+arenas[v],'<Q',arena);t.put(canvas+0xb8,'<Q',active);t.put(arena+0xe8,'<Q',active);t.put(arena+0xe0,'<Q',manager)
 sheets=[image() for _ in range(10)];t.put(t.B+catalogs[v],'<Q',catalog);t.put(catalog+0xa8,'<Q',array(sheets));t.put(manager+0x58,'<i',47)
 for phase in (0,1):
  t.put(manager+0x64,'<b',phase);rows=[];snapshots=[]
  expected={12:5,20:6}
  if phase:expected.update({0:0,9:3,11:5,19:6,21:7})
  for kind in (0,1,9,11,12,19,20,21,22):
   p=t.alloc(0x100);t.put(p+0xcf,'<B',kind);t.put(p+0x4c,'<i',0 if kind in (11,12) else 31)
   # Sentinels are real motion and lifecycle fields; image binding cannot alter them.
   t.put(p+0x48,'<i',37);t.put(p+0x7c,'<ii',467,349);t.put(p+0xa0,'<i',11)
   helper=0;rotation=0;original=image();rotated=[]
   if kind!=19:
    helper=t.alloc(0x40);t.put(helper+0x18,'<Q',original);t.put(helper+0x20,'<iiii',4,20,20,2);t.put(helper+0x30,'<B',kind in (9,21))
    if kind in (9,21):rotated=[0,image(),image(),0];rotation=array(rotated);t.put(helper+0x10,'<Q',rotation)
    t.put(p+0x38,'<Q',helper)
   else:t.put(p+0x28,'<Q',original)
   snapshots.append((kind,p,helper,rotation,original,rotated,bytes(t.u.mem_read(p,0x100)),bytes(t.u.mem_read(helper,0x40)) if helper else b''));rows.append(p)
  t.put(manager+0x30,'<Q',t.vector(rows));before=len(calls);t.call('_AGCostumeRender',t.E,v)
  for kind,p,helper,rot,original,rotated,old,oldHelper in snapshots:
   fresh=bytearray(t.u.mem_read(p,0x100));hero=expected.get(kind)
   if hero is not None:
    style=47 if kind in (11,12) else 31;frames=4 if kind==12 else 0
    key=(original,sheets[hero],hero,style,frames);assert key in converted,(v,phase,kind,key,calls)
    location=helper+0x18 if helper else p+0x28;assert t.get(location,'<Q')==converted[key]
    if helper:
     result=bytearray(t.u.mem_read(helper,0x40));result[0x18:0x20]=oldHelper[0x18:0x20];assert bytes(result)==oldHelper
    else:fresh[0x28:0x30]=old[0x28:0x30]
    if rot:
     for i,src in enumerate(rotated):assert t.get(rot+0x18+i*8,'<Q')==(converted[src,sheets[hero],hero,style,0] if src else 0)
   else:
    if helper:assert bytes(t.u.mem_read(helper,0x40))==oldHelper
   assert bytes(fresh)==old,(v,phase,kind,'Non-image projectile field changed')
  after=len(calls);assert after>before;t.call('_AGCostumeRender',t.E,v);assert len(calls)==after,'Tint applied repeatedly'
 # Leaving active arena releases every live-bullet root.
 t.put(canvas+0xb8,'<Q',0);t.call('_AGCostumeRender',t.E,v)
assert all(n==0 for n in t.pins.values()),t.pins
print('PASS compiled ARM64: six PBs, normal/POW cases, fixed Gun/Monkey/Granos/Tarzan images, Chicken eggs, all cached rotated images, secondary four-frame Granos style, repeated render idempotence and root cleanup; physics/lifecycle fields unchanged. UIKit PNG conversion is mocked.')
