"""Compare compiled avatar composition with original AOT gear painter geometry.
Native objects use fixture IDs above the bundled catalog, with real bundled
sprite pixels. This does not claim to capture a live account or server atlas.
"""
from pathlib import Path
import json,re,struct
from PIL import Image,ImageChops
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_SP,UC_ARM64_REG_LR,UC_ARM64_REG_PC
import test_inventory_device282 as t

root=Path(__file__).parent
art=json.loads(re.search(r'= (\{.*\});',(root/'viewer/art.js').read_text()).group(1))
raw=(root/'build/base293-native').read_bytes()
t.u.mem_write(t.B+0x5ba510,raw[0x5ba510:0x5ba914])
t.u.mem_write(t.B+0x515100,raw[0x515100:0x5157d0])
t.u.mem_write(t.B+0x1461ca0,raw[0x1461ca0:0x1461cc0])
catalogs=(0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0)
actors=(0x2091b80,0x20c0670,0x20ee360,0x211c050,0x2149d40,0x2177a30)
def objects(rows):return t.get(t.vector(rows)+0x18,'<Q')
def native_image(im):
 im=im.convert('RGBA');w,h=im.size;data=im.tobytes();a=t.alloc(0x14+len(data));t.put(a+0x10,'<i',w*h)
 t.u.mem_write(a+0x14,b''.join(data[i:i+4][::-1] for i in range(0,len(data),4)))
 p=t.alloc(0x30);t.put(p+0x10,'<Q',a);t.put(p+0x20,'<ii',w,h);return p
body_images=[];atlas_images=[];references=[];rectangles=[];parts=[]
for hero in range(10):
 rects=[next(v for k,v in art['gear'].items() if k.startswith(f'{hero}:{s}:') and v[2] and v[3]) for s in range(5)]
 atlas=Image.open(root/f'viewer/art/hero{hero}.png').convert('RGBA')
 atlas=atlas.crop((0,0,max(r[0]+r[2] for r in rects),max(r[1]+r[3] for r in rects)))
 body=Image.open(root/f'viewer/art/base{hero}.png').convert('RGBA')
 strip=Image.new('RGBA',(body.width,body.height*10));strip.paste(body,(0,0))
 body_images.append(native_image(strip));atlas_images.append(native_image(atlas));rectangles.append(rects)
 ids=[300+hero*5+s for s in range(5)];parts.append(ids)
 assert all(f'{hero}:{s}:{id}' not in art['gear'] for s,id in enumerate(ids))
 ref=Image.new('RGBA',(80,80));ew=30 if hero==3 else 29 if hero==6 else 32 if hero==7 else 24;eh=32 if hero in (3,7) else 24
 for s in (0,4,5,1,2,3):
  if s==5:im=body;x=40-body.width//2-(body.width&1);y=64-body.height
  else:
   sx,sy,w,h,ox,oy=rects[s];im=atlas.crop((sx,sy,sx+w,sy+h));x=40-ew//2+ox+18;y=64-eh+oy+40
  ref.alpha_composite(im,(x,y))
 references.append(ref.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
atlas_array=objects(atlas_images);body_array=objects(body_images);draws=[]
def hook(u,pc,size,_):
 if pc==t.B+0x5146fc:t.ret(atlas_array)
 elif pc==t.B+0x592bdc:t.ret(body_array)
 elif pc==t.B+0x1c61b0:t.ret(t.get(t.reg(1)+0x20,'<i'))
 elif pc==t.B+0x1c61a0:t.ret(t.get(t.reg(1)+0x24,'<i'))
 elif pc==t.B+0x12e76d8:t.ret()
 elif pc==t.B+0x1c6150:
  sp=u.reg_read(UC_ARM64_REG_SP);draws.append((t.reg(2),*[t.reg(k)&0xffffffff for k in range(3,7)],t.get(sp,'<i'),t.get(sp+4,'<i')));t.ret()
t.u.hook_add(UC_HOOK_CODE,hook)
for v in range(6):
 c=t.alloc(0xc0);actor=t.alloc(0xb0);t.put(t.B+catalogs[v],'<Q',c);t.put(t.B+actors[v],'<Q',actor)
 t.put(c+0xa0,'<Q',atlas_array);t.put(actor+0xa0,'<Q',body_array);heroes=[]
 for hero in range(10):
  slots=[]
  for s,r in enumerate(rectangles[hero]):
   item=t.alloc(0xd0);t.put(item+0x80,'<q',parts[hero][s]);t.put(item+0xc3,'<b',hero)
   for k,value in enumerate(r):
    a=t.alloc(0x18);t.put(a+0x10,'<i',1);t.put(a+0x14,'<h' if k<2 else '<b',value);t.put(item+0x10+k*8,'<Q',a)
   slot=t.alloc(0x20);t.put(slot+0x18,'<b',s);t.put(slot+0x10,'<Q',t.vector([item]));slots.append(slot)
   # Execute the game's unmodified piece painter to audit every placement.
   draws.clear();t.u.reg_write(UC_ARM64_REG_SP,t.S+0x30000);t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
   for i,arg in enumerate((t.E,item,t.alloc(0x60),0,0,40,64)):t.u.reg_write(t.regs[i],arg)
   t.u.emu_start(t.B+0x5ba510,t.STOP+4,count=100000)
   assert t.u.reg_read(UC_ARM64_REG_PC)==t.STOP and len(draws)==1
   ew=30 if hero==3 else 29 if hero==6 else 32 if hero==7 else 24;eh=32 if hero in (3,7) else 24
   assert draws[0]==(atlas_images[hero],*r[:4],40-ew//2+r[4]+18,64-eh+r[5]+40),(hero,s,draws)
  h=t.alloc(0x20);t.put(h+0x1a,'<b',hero);t.put(h+0x10,'<Q',t.vector(slots));heroes.append(h)
 t.put(c+0xb0,'<Q',t.vector(heroes))
 for hero in range(10):
  # Execute the original complete Outfit.draw, not an assumed body stride.
  outfit=t.alloc(0x20);slots=t.get(heroes[hero]+0x10,'<Q');slotArray=t.get(slots+0x18,'<Q');templates=[]
  for slot in range(5):
   slotObject=t.get(slotArray+0x18+slot*8,'<Q');vec=t.get(slotObject+0x10,'<Q');templates.append(t.get(t.get(vec+0x18,'<Q')+0x18,'<Q'))
  t.put(outfit+0x10,'<Q',objects(templates));draws.clear();previous=t.get(t.E+0x38,'<Q')
  t.u.reg_write(UC_ARM64_REG_SP,t.S+0x30000);t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
  for i,arg in enumerate((t.E,outfit,t.alloc(0x60),0,0,40,64)):t.u.reg_write(t.regs[i],arg)
  t.u.emu_start(t.B+0x515100,t.STOP+4,count=200000);assert t.u.reg_read(UC_ARM64_REG_PC)==t.STOP
  bodyDraw=next(row for row in draws if row[0]==body_images[hero]);assert bodyDraw[4]==t.get(body_images[hero]+0x24,'<i')//10
  assert len(draws)==6;t.put(t.E+0x38,'<Q',previous)
  p=t.alloc(20);t.u.mem_write(p,struct.pack('<5i',*parts[hero]));out=t.alloc(24)
  assert t.call('_AGProfileAvatarRead',t.E,v,hero,p,out)==1,(v,hero)
  assert (t.get(out+4,'<i'),t.get(out+8,'<i'))==(80,80)
  result=Image.frombytes('RGBA',(80,80),bytes(t.u.mem_read(t.get(out+16,'<Q'),80*80*4)))
  delta=ImageChops.difference(result,references[hero]);assert max(hi for lo,hi in delta.getextrema())<=1,(v,hero)
  assert result.tobytes()!=references[hero].transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
  # A missing character/template must not borrow another hero's equipment.
  t.put(p,'<i',9999);assert t.call('_AGProfileAvatarRead',t.E,v,hero,p,out)==0
assert all(n==0 for n in t.pins.values())
print('PASS avatar305: ten heroes across six PBs, original complete AOT Outfit.draw and its ten-frame body stride, plus piece placements (300 draws), exact live-catalog fixture IDs absent from static metadata, real bundled sprite pixels vs independent Pillow composition, complete pose facing right, missing template rejected and balanced JNI roots')
