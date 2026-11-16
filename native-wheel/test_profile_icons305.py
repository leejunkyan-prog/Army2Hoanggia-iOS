"""Regression: individual native icon textures retain one complete source atlas.
The old pixel reader returns frame0 for all items; compare real bundled pixels.
"""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import struct
from PIL import Image
import test_inventory_device282 as t
from unicorn import UC_HOOK_CODE

raw=(Path(__file__).parent/'build/base293-native').read_bytes()
t.u.mem_write(t.B+0xc48ea0,raw[0xc48ea0:0xc49028])
root=Path(__file__).resolve().parent.parent
source=root/'ipa-output/source293.ipa'
if source.exists():
 with ZipFile(source) as z:png=z.read('Payload/Army2Hoanggia.app/res/imgIcon.png')
else:png=Path('/workspace/work/profile305-video/imgIcon.png').read_bytes()
atlas=Image.open(BytesIO(png)).convert('RGBA');w,h=atlas.size
assert w==16 and h%16==0
rgba=atlas.tobytes();words=[int.from_bytes(rgba[i:i+4],'big') for i in range(0,len(rgba),4)]
catalogs=(0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0)
cache=t.alloc(0x20);texture=t.alloc(0x30);pixmap=t.alloc(0x30);buffer=t.alloc(0x20)
native_bytes=t.alloc(len(rgba));t.u.mem_write(native_bytes,rgba)
NEW=t.F+0x21300;DELETE=t.F+0x21400;ADDRESS=t.F+0x21500;CAPACITY=t.F+0x21600
for i,p in [(179,NEW),(23,DELETE),(230,ADDRESS),(231,CAPACITY)]:t.put(t.JNI+8*i,'<Q',p)
strings={};images={};fast=False;old_failures=0
fixed='_AGProfileAvatarRead' in t.symbols
def hook(u,pc,size,_):
 if pc==t.B+0xc46b40:t.ret(cache)
 elif pc==t.B+0xab216c:
  p=t.alloc(0x20);strings[p]=t.reg(1);t.ret(p)
 elif pc==t.B+0xbc88a0:t.ret(images.get(strings[t.reg(2)],0))
 elif pc==t.B+0x1b4ba8:t.ret(texture)
 elif pc==t.B+0x39dc58:t.ret(1)
 elif pc==t.B+0x39dd54:t.ret(0)
 elif pc==t.B+0x39dd00:t.ret(pixmap)
 elif pc==t.B+0x398e0c:t.ret(w)
 elif pc==t.B+0x398e30:t.ret(h)
 elif pc==t.B+0x398fe8:t.ret(buffer)
 elif pc==ADDRESS:t.ret(native_bytes if fast else 0)
 elif pc==CAPACITY:t.ret(len(rgba))
 elif pc==NEW:
  n=t.reg(1);p=t.alloc(0x14+4*n);t.put(p+0x10,'<i',n);t.ret(p)
 elif pc==DELETE:t.ret()
 elif pc==t.B+0x1db1f8:t.ret(words[t.reg(3)*w+t.reg(2)])
t.u.hook_add(UC_HOOK_CODE,hook)
for v in range(6):
 c=t.alloc(0xc0);t.put(t.B+catalogs[v],'<Q',c);heroes=[]
 # Same template ID, different character: native icon rows must stay distinct.
 for hero_id,frame in [(hero,50+hero*20+v) for hero in range(10)]:
  item=t.alloc(0xd0);t.put(item+0x80,'<q',56);t.put(item+0x88,'<q',frame)
  slot=t.alloc(0x20);t.put(slot+0x18,'<b',0);t.put(slot+0x10,'<Q',t.vector([item]))
  hero=t.alloc(0x20);t.put(hero+0x1a,'<b',hero_id);t.put(hero+0x10,'<Q',t.vector([slot]));heroes.append(hero)
  picture=t.alloc(0x30);t.put(picture+0x20,'<ii',16,16);t.put(picture+0x18,'<Q',texture);images[frame]=picture
 t.put(c+0xb0,'<Q',t.vector(heroes));actual=[]
 for hero_id,frame in [(hero,50+hero*20+v) for hero in range(10)]:
  fast=bool(v%2);out=t.alloc(24);assert t.call('_AGProfileIconRead',t.E,v,hero_id,0,56,out)==1
  pixels=bytes(t.u.mem_read(t.get(out+16,'<Q'),16*16*4));expected=atlas.crop((0,frame*16,16,(frame+1)*16)).tobytes()
  if fixed:assert pixels==expected,(v,hero_id,frame)
  else:
   assert pixels==atlas.crop((0,0,16,16)).tobytes()
   assert pixels!=expected;old_failures+=1
  actual.append(pixels)
 if fixed:assert len(set(actual))==10
assert all(n==0 for n in t.pins.values())
print('PASS native305 real atlas rows: six PBs, ten heroes same template ID -> different native icon rows, complete source atlas behind16px textures, exact original PNG pixels, direct buffer and Pixmap paths' if fixed else 'CONTROL304: reproduced first-frame substitution for60 character icon lookups with the original Image.l code')
