"""Supplied APK styles, exact ShotFx pixels, and compiled native actor binding."""
from pathlib import Path
from io import BytesIO
import ctypes,subprocess,sys,struct,tempfile
from PIL import Image
from unicorn import UC_HOOK_CODE
import reference306 as ref
import test_inventory_device282 as t

def tint(rgba,a,b):
 r,g,blue,alpha=rgba
 light=(r*54+g*183+blue*19)>>8
 if not alpha or light<35:return bytes(rgba)
 mix=max(0,light-190)//3;out=[]
 for shift in (16,8,0):
  n=(((a>>shift)&255)*(100-mix)+((b>>shift)&255)*mix)//100
  n=n*(light*165//255+90)//255
  if light>235:n=(n*7+255)//8
  out.append(n)
 return bytes(out+[alpha])
palettes={}
for hero,head,style,a,b in ref.styles:
 assert t.call('_AGCostumeStyleLookup',hero,head,17)==style
 palettes.setdefault((hero,style),(a,b))
 for pixel in [(0,0,0,0),(16,32,64,255),(128,200,90,180),(255,255,255,255)]:
  result=t.call('_AGCostumeTint',int.from_bytes(bytes(pixel),'big'),a,b)&0xffffffff
  assert result==int.from_bytes(tint(pixel,a,b),'big')
assert t.call('_AGCostumeStyleLookup',10,100,17)==17
# Compile the exact production C on the host for exhaustive PNG comparisons.
# ARM64 calls above and one expansion below cross-check the compiled device code.
with tempfile.TemporaryDirectory() as folder:
 target=Path(folder)/('costume.dylib' if sys.platform=='darwin' else 'costume.so')
 subprocess.run(['cc','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-O1',str(ref.root/'CostumeEffects.c'),'-o',str(target)],check=True)
 lib=ctypes.CDLL(str(target));expand=lib.AGCostumeExpandRGBA
 expand.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_int)]
 free=ctypes.CDLL(None).free;free.argtypes=[ctypes.c_void_p]
 for hero in range(10):
  im=Image.open(BytesIO(ref.images[hero+1])).convert('RGBA');source=im.tobytes();buffer=ctypes.create_string_buffer(source)
  chosen=[s for h,s in palettes if h==hero];ptr=ctypes.c_void_p();height=ctypes.c_int()
  assert expand(hero,buffer,im.width,im.height,max(chosen),ctypes.byref(ptr),ctypes.byref(height))==1
  output=ctypes.string_at(ptr,im.width*height.value*4);free(ptr)
  assert output[:len(source)]==source,'Existing effect pixels must not change'
  block=im.width*(2 if hero==2 else 4 if hero==5 else 1)
  for style in chosen:
   a,b=palettes[hero,style]
   for y in range(block):
    if style*block+y<im.height:continue
    at=(style*block+y)*im.width*4
    expected=b''.join(tint(source[(y*im.width+x)*4:(y*im.width+x+1)*4],a,b) for x in range(im.width))
    assert output[at:at+im.width*4]==expected,(hero,style,y)
  if hero==0:
   t.instruction_limit=40000000;src=t.alloc(len(source));t.u.mem_write(src,source);out=t.alloc(8);oh=t.alloc(4)
   assert t.call('_AGCostumeExpandRGBA',hero,src,im.width,im.height,max(chosen),out,oh)==1
   assert t.get(oh,'<i')==height.value and bytes(t.u.mem_read(t.get(out,'<Q'),len(output)))==output

# The native fire method forwards +0x104 as the visual effect style.
raw=(ref.root/'build/base293-native').read_bytes()
assert raw[0x599dd8:0x599ddc]==bytes.fromhex('080541b9')
catalogs=(0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0)
arenaSlots=(0x2082e30,0x20b23a0,0x20e0090,0x210dd80,0x213ba70,0x2169760)
arraySlots=(0x207f060,0x20aec70,0x20dc970,0x210a660,0x2138350,0x2166040)
def hook(u,pc,size,_):
 if pc==t.symbols.get('_logFX'):t.ret() # UIKit/file logging is a boundary.
t.u.hook_add(UC_HOOK_CODE,hook)
for v in range(6):
 arenaClass=t.alloc(0x300);arena=t.alloc(0x40);canvas=t.alloc(0x180);group=t.alloc(0xe0);catalog=t.alloc(0xc0)
 t.put(t.B+arenaSlots[v],'<Q',arenaClass);t.put(arenaClass+0xe8,'<Q',arena);t.put(t.B+t.canvases[v],'<Q',canvas);t.put(canvas+0xb8,'<Q',arena)
 t.put(t.B+arraySlots[v],'<Q',group);t.put(t.B+catalogs[v],'<Q',catalog)
 players=[];effects=[];original=[]
 for hero in range(10):
  _,head,style,_,_=next(r for r in ref.styles if r[0]==hero)
  actor=t.alloc(0x200);outfit=t.alloc(0x20);headItem=t.alloc(0xd0);t.put(actor+0x60,'<Q',outfit);t.put(actor+0x104,'<i',7);t.put(actor+0x16c,'<B',hero);t.put(actor+0x16b,'<B',hero)
  t.put(headItem+0x80,'<q',head);t.put(headItem+0xc3,'<B',hero);parts=t.get(t.vector([0,headItem,0,0,0])+0x18,'<Q');t.put(outfit+0x10,'<Q',parts)
  im=t.alloc(0x30);t.put(im+0x20,'<ii',20,12000);effects.append(im);players.append(actor);original.append((bytes(t.u.mem_read(actor,0x200)),style,parts))
 t.put(catalog+0xa8,'<Q',t.get(t.vector(effects)+0x18,'<Q'));t.put(group+0xa0,'<Q',t.get(t.vector(players)+0x18,'<Q'))
 t.call('_AGCostumeTick',t.E,v)
 for actor,(before,style,parts) in zip(players,original):
  after=bytes(t.u.mem_read(actor,0x200));assert after==before[:0x104]+struct.pack('<i',style)+before[0x108:]
  t.put(parts+0x20,'<Q',0) # Remove the head: restore the original weapon effect.
 t.call('_AGCostumeTick',t.E,v)
 assert all(t.get(actor+0x104,'<i')==7 for actor in players)
# Optional live FX49 overrides are isolated by PB, malformed input preserves state.
packet=bytes([0])+bytes(22)+b'FX49\1'+struct.pack('>H',1)+struct.pack('>BHB',0,2345,12)
blob=t.alloc(len(packet));t.u.mem_write(blob,packet)
assert t.call('_AGCostumeCatalog',0,blob,len(packet))==1
assert t.call('_AGCostumeVariantStyle',0,0,2345,9)==12 and t.call('_AGCostumeVariantStyle',1,0,2345,9)==9
assert t.call('_AGCostumeCatalog',0,blob,len(packet)-1)==0
assert t.call('_AGCostumeVariantStyle',0,0,2345,9)==12
print('PASS costume306: all375 APK mappings and exact tint arithmetic; ten actual supplied effect PNGs expanded with original rows preserved; identical ARM64 expansion; six-PB head -> native shot style binding changes only the visual word, removal restores weapon style; bounded optional FX49 overrides and PB isolation')
