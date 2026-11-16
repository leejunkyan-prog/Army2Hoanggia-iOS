"""Use the actual supplied equipment sheet, and poison the unrelated cache."""
from io import BytesIO
from PIL import Image
from unicorn import UC_HOOK_CODE
import struct
import test_inventory_device282 as t
import reference306 as ref
atlas=Image.open(BytesIO(ref.images[0])).convert('RGBA');w,h=atlas.size;rgba=atlas.tobytes()
image=t.alloc(0x30);array=t.alloc(0x14+len(rgba));t.put(array+0x10,'<i',w*h)
t.u.mem_write(array+0x14,b''.join(rgba[i:i+4][::-1] for i in range(0,len(rgba),4)))
t.put(image+0x10,'<Q',array);t.put(image+0x20,'<ii',w,h)
catalogs=(0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0)
def hook(u,pc,size,_):
 if pc==t.B+0xc46b40:raise AssertionError('Profile used the unrelated generic cache instead of the native equipment sheet')
t.u.hook_add(UC_HOOK_CODE,hook)
for v in range(6):
 c=t.alloc(0xc0);pool=t.alloc(0xc0);t.put(t.B+catalogs[v],'<Q',c);t.put(t.B+t.pools[v],'<Q',pool);t.put(pool+0xb0,'<Q',image);heroes=[]
 for hero_id in range(10):
  slots=[]
  for s in range(5):
   choices=[r for r in ref.rows if r['hero']==hero_id and r['slot']==s and 260<=r['icon']<=350]
   row=choices[0] if choices else next(r for r in ref.rows if r['hero']==hero_id and r['slot']==s)
   item=t.alloc(0xd0);t.put(item+0x80,'<q',row['id']);t.put(item+0x88,'<q',row['icon'])
   slot=t.alloc(0x20);t.put(slot+0x18,'<b',s);t.put(slot+0x10,'<Q',t.vector([item]));slots.append(slot)
   # Query only after installing all heroes below.
   row['_query']=(v,hero_id,s,row['id'],row['icon'])
  hero=t.alloc(0x20);t.put(hero+0x1a,'<b',hero_id);t.put(hero+0x10,'<Q',t.vector(slots));heroes.append(hero)
 t.put(c+0xb0,'<Q',t.vector(heroes))
 queries=[r.pop('_query') for r in ref.rows if '_query' in r]
 for vv,hero,s,id,frame in queries:
  out=t.alloc(24);assert t.call('_AGProfileIconRead',t.E,v,hero,s,id,out)==1,(v,hero,s,id)
  actual=bytes(t.u.mem_read(t.get(out+16,'<Q'),16*16*4));expected=atlas.crop((0,frame*w,16,frame*w+16)).tobytes()
  assert actual==expected,(v,hero,s,id,frame)
 assert t.call('_AGProfileIconRead',t.E,v,0,0,32767,t.alloc(24))==0
assert all(n==0 for n in t.pins.values())
print('PASS supplied APK/export306: all ten heroes and five slots in six PBs, exact template -> icon ID -> native equipment atlas PNG pixels; unrelated cache never read; missing IDs rejected, no own-account dependency')
