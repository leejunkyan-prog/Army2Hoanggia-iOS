"""Compiled Chicky body/egg style inheritance, retries and per-shot lifetime."""
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_PC
import test_inventory_device282 as t

raw=(Path(__file__).parent/'build/base293-native').read_bytes()
catalogs=(0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0)
arenas=(0x2082e30,0x20b23a0,0x20e0090,0x210dd80,0x213ba70,0x2169760)
converted={};calls=[];fail_source=0;failed=False
SET=t.F+0x21000;t.put(t.JNI+174*8,'<Q',SET)
def hook(u,pc,size,_):
 global failed
 if pc==t.symbols['_AGCostumeImage']:
  key=tuple(t.reg(i) for i in range(1,6));calls.append(key)
  if key[0]==fail_source and not failed:failed=True;t.ret(0);return
  if key not in converted:converted[key]=t.alloc(0x30)
  t.ret(converted[key])
 elif pc==SET:t.put(t.reg(1)+0x18+t.reg(2)*8,'<Q',t.reg(3));t.ret()
 elif pc==t.B+0xaaa258:t.ret()
 elif pc==t.B+0x577880:u.reg_write(UC_ARM64_REG_PC,t.STOP)
t.u.hook_add(UC_HOOK_CODE,hook)
def array(rows):return t.get(t.vector(rows)+0x18,'<Q')
def image():
 p=t.alloc(0x30);t.put(p+0x20,'<ii',20,20);return p
# Execute the original overload used for secondary bullets up to its call to
# initialize images: it does not inherit/write the visual style word at+4c.
t.u.mem_write(t.B+0x577778,raw[0x577778:0x577884])
t.symbols['_native_secondary_constructor']=t.B+0x577778
p=t.alloc(0x100);t.call('_native_secondary_constructor',t.E,p,20,0,0,0)
assert t.get(p+0x4c,'<i')==0

for v in range(6):
 canvas=t.alloc(0x180);arena=t.alloc(0x200);active=t.alloc(0x80);manager=t.alloc(0x80);catalog=t.alloc(0xc0)
 t.put(t.B+t.canvases[v],'<Q',canvas);t.put(t.B+arenas[v],'<Q',arena)
 t.put(canvas+0xb8,'<Q',active);t.put(arena+0xe8,'<Q',active);t.put(arena+0xe0,'<Q',manager)
 t.put(t.B+catalogs[v],'<Q',catalog);sheets=[image() for _ in range(10)];t.put(catalog+0xa8,'<Q',array(sheets))
 for phase in (0,1):
  # Default body, styled body and egg both use the exact same firing style.
  t.put(manager+0x58,'<i',48);t.put(manager+0x64,'<b',phase)
  rows=[];snapshots=[]
  for kind,style in ((19,0),(19,48),(20,0),(20,48)):
   p=t.alloc(0x100);src=image();helper=rotations=0;rotated=[]
   t.put(p+0xcf,'<B',kind);t.put(p+0x4c,'<i',style);t.put(p+0x7c,'<ii',123,456);t.put(p+0xa0,'<i',11)
   if kind==19:t.put(p+0x28,'<Q',src)
   else:
    helper=t.alloc(0x40);t.put(helper+0x18,'<Q',src);t.put(helper+0x20,'<iiii',4,12,11,2)
    rotated=[image(),0,image()];rotations=array(rotated);t.put(helper+0x10,'<Q',rotations);t.put(p+0x38,'<Q',helper)
   rows.append(p);snapshots.append((p,kind,src,helper,rotations,rotated,bytes(t.u.mem_read(p,0x100))))
  t.put(manager+0x30,'<Q',t.vector(rows));t.call('_AGCostumeRender',t.E,v)
  for p,kind,src,helper,rotations,rotated,before in snapshots:
   frames=1 if kind==19 and phase==0 else 0
   key=(sheets[6] if frames==1 else src,sheets[6],6,48,frames)
   dest=helper+0x18 if helper else p+0x28
   assert t.get(dest,'<Q')==converted[key],(v,phase,kind,'body/egg style mismatch')
   for i,source in enumerate(rotated):
    assert t.get(rotations+0x18+i*8,'<Q')==(converted[source,sheets[6],6,48,0] if source else 0)
   after=bytearray(t.u.mem_read(p,0x100))
   if not helper:after[0x28:0x30]=before[0x28:0x30]
   assert bytes(after)==before,'Only image fields may change'
  before=len(calls);t.put(manager+0x58,'<i',55);t.call('_AGCostumeRender',t.E,v)
  assert len(calls)==before,'A later firing style recolored an existing projectile'
  # First conversion fails on one rotated frame. None of the sprite images
  # may commit until all are ready; retry must use the original sources.
  p=t.alloc(0x100);helper=t.alloc(0x40);src=image();rotated=[image(),image()]
  t.put(p+0xcf,'<B',20);t.put(p+0x38,'<Q',helper);t.put(helper+0x18,'<Q',src)
  rotations=array(rotated);t.put(helper+0x10,'<Q',rotations)
  t.put(manager+0x30,'<Q',t.vector([p]));fail_source=rotated[-1];failed=False
  t.call('_AGCostumeRender',t.E,v)
  assert failed and t.get(helper+0x18,'<Q')==src
  assert [t.get(rotations+0x18+i*8,'<Q') for i in range(2)]==rotated
  # Retain captured style55 even if the manager starts another turn before retry.
  t.put(manager+0x58,'<i',48);t.call('_AGCostumeRender',t.E,v)
  assert t.get(helper+0x18,'<Q')==converted[src,sheets[6],6,55,0]
  for i,source in enumerate(rotated):assert t.get(rotations+0x18+i*8,'<Q')==converted[source,sheets[6],6,55,0]
  fail_source=0;t.put(manager+0x30,'<Q',t.vector([]));t.call('_AGCostumeRender',t.E,v)
 t.put(canvas+0xb8,'<Q',0);t.call('_AGCostumeRender',t.E,v)
assert all(n==0 for n in t.pins.values()),t.pins
print('PASS307 compiled ARM64: native secondary constructor leaves style0; six PBs bind normal/POW Chicky and eggs to the firing costume; normal body crops the exact sheet row; rotated eggs match; in-flight style is stable; failed image conversion retries atomically; physical projectile fields untouched and JNI roots balanced. PNG/UIKit conversion is mocked.')
