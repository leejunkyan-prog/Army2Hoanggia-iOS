"""Use the actual supplied equipment sheet, and poison the unrelated cache."""
from io import BytesIO
from PIL import Image,ImageChops
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
chosen={}
for v in range(6):
 c=t.alloc(0xc0);pool=t.alloc(0xc0);t.put(t.B+catalogs[v],'<Q',c);t.put(t.B+t.pools[v],'<Q',pool);t.put(pool+0xb0,'<Q',image);heroes=[]
 for hero_id in range(10):
  slots=[]
  for s in range(5):
   choices=[r for r in ref.rows if r['hero']==hero_id and r['slot']==s and 260<=r['icon']<=350]
   row=choices[0] if choices else next(r for r in ref.rows if r['hero']==hero_id and r['slot']==s)
   item=t.alloc(0xd0);t.put(item+0x80,'<q',row['id']);t.put(item+0x88,'<q',row['icon'])
   for k in range(6):
    a=t.alloc(0x14+(12 if k<2 else 6));t.put(a+0x10,'<i',6)
    for pose in range(6):t.put(a+0x14+pose*(2 if k<2 else 1),'<h' if k<2 else '<b',row['rects'][pose][k])
    t.put(item+0x10+k*8,'<Q',a)
   chosen[v,hero_id,s]=row
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
# Real exported geometry has six poses. Check idle poses4/5 and rank pose0
# against independent composition, using a ten-frame body fixture.
def image_object(im):
 rgba=im.tobytes();a=t.alloc(0x14+len(rgba));t.put(a+0x10,'<i',im.width*im.height)
 t.u.mem_write(a+0x14,b''.join(rgba[i:i+4][::-1] for i in range(0,len(rgba),4)))
 p=t.alloc(0x30);t.put(p+0x10,'<Q',a);t.put(p+0x20,'<ii',im.width,im.height);return p
def array_object(rows):return t.get(t.vector(rows)+0x18,'<Q')
rects=[chosen[5,0,s]['rects'] for s in range(5)]
atlas_body=Image.open(ref.root/'viewer/art/hero0.png').convert('RGBA')
right=max(r[0]+max(0,r[2]) for poses in rects for r in poses);bottom=max(r[1]+max(0,r[3]) for poses in rects for r in poses)
atlas_body=atlas_body.crop((0,0,right,bottom));atlas_image=image_object(atlas_body)
body=Image.open(ref.root/'viewer/art/base0.png').convert('RGBA');strip=Image.new('RGBA',(body.width,body.height*10))
for pose in range(10):strip.paste(body,(0,pose*body.height))
body_image=image_object(strip);bodyClass=t.alloc(0xb0);t.put(t.B+0x2177a30,'<Q',bodyClass);t.put(bodyClass+0xa0,'<Q',array_object([body_image]));t.put(c+0xa0,'<Q',array_object([atlas_image]))
parts=t.alloc(20);t.u.mem_write(parts,struct.pack('<5i',*[chosen[5,0,s]['id'] for s in range(5)]))
for pose,mode in [(0,2),(4,0),(5,0)]:
 out=t.alloc(24);assert t.call('_AGProfileAvatarPoseRead',t.E,5,0,parts,pose,mode,out)==1
 expected=Image.new('RGBA',(80,80))
 for slot in (0,4,5,1,2,3):
  if slot==5:region=body;x=40-body.width//2-(mode==2 and body.width%2);y=64-body.height
  else:
   sx,sy,ww,hh,ox,oy=rects[slot][pose]
   if ww<=0 or hh<=0:continue
   region=atlas_body.crop((sx,sy,sx+ww,sy+hh));x=40-12+ox+18;y=64-24+oy+40
  expected.alpha_composite(region,(x,y))
 if mode==2:expected=expected.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 actual=Image.frombytes('RGBA',(80,80),bytes(t.u.mem_read(t.get(out+16,'<Q'),80*80*4)))
 assert max(hi for lo,hi in ImageChops.difference(actual,expected).getextrema())<=1,(pose,mode)
assert all(n==0 for n in t.pins.values())
print('PASS supplied APK/export306: all ten heroes and five slots in six PBs, exact template -> icon ID -> native equipment atlas PNG pixels; unrelated cache never read; missing IDs rejected, no own-account dependency')
