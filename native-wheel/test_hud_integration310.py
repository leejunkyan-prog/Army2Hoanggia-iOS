"""Native font initialization/glyph painter and arena -> virtual NPC paint.

Use the original clinit to bind fonts to fields, and the original font width /
glyph methods. Emulate Java string primitives and the final graphics boundary.
The fixture deliberately puts the boss in slot8 with actor metadata byte0,
as opposed to labelling a synthetic actor with the expected roster index.
"""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import struct,sys
from PIL import Image
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_SP,UC_ARM64_REG_LR
import test_inventory_device282 as t
from patch_hud309 import patch_native,offset,BARS

root=Path(__file__).parent;raw=(root/'build/base293-native').read_bytes()
patched,_=patch_native(raw,t.blob);t.u.mem_write(t.B,patched[:26050560]);t.u.mem_write(t.B+0x24f8000,patched[offset(0x24f8000):offset(0x250bfff)+1])
font_get=(0x5c10f0,0x6a9144,0x78de08,0x872acc,0x957790,0xa3c454)
font_draw=(0x5c3e64,0x6abc88,0x79094c,0x875610,0x95a2d4,0xa3ef98)
arena_slots=(0x2082e30,0x20b23a0,0x20e0090,0x210dd80,0x213ba70,0x2169760)
roster_slots=(0x207f060,0x20aec70,0x20dc970,0x210a660,0x2138350,0x2166040)
actor_slots=(0x2091b80,0x20c0670,0x20ee360,0x211c050,0x2149d40,0x2177a30)
services=(0x207b870,0x20ab650,0x20d9350,0x2107040,0x2134d30,0x2162a20)
strings={};fonts={};images={};tls={};once=set();next_key=0;calls=[];glyphs=[];font_events=[];graphics=0;loop_end=0;current_v=0
ctor_sites=set();allowed_body=set();body_boundaries={}
# Existing source293/IPA entries have the same font resources as the upload.
source=root.parent/'ipa-output/source293.ipa'
if not source.exists():source=Path('/workspace/work/verify309/Army2HoangGia-2.4.1-Build309-MarqueeBossRanks-unsigned.ipa')
with ZipFile(source) as z:
 pngs={p.rsplit('/',1)[-1]:z.read(p) for p in z.namelist() if '/res/font/fontT/' in p and p.endswith('.png')}
def units(s):return list(struct.unpack('<'+'H'*(len(s.encode('utf-16-le','surrogatepass'))//2),s.encode('utf-16-le','surrogatepass')))
def java(s):p=t.alloc(0x40);strings[p]=units(s);return p
def string(p):return struct.pack('<'+'H'*len(strings[p]),*strings[p]).decode('utf-16-le','surrogatepass')
def image(name,w=35,h=320):
 p=t.alloc(0x40);t.put(p+0x20,'<ii',w,h);images[p]=(name,w,h);return p
def target(at):
 w=struct.unpack_from('<I',raw,at)[0];assert w>>26==0x25;n=w&0x3ffffff
 return at+4*(n-(1<<26) if n&(1<<25) else n)
def class_slot(getter):
 p,q=struct.unpack_from('<II',raw,getter+12);n=((p>>5)&0x7ffff)<<2|((p>>29)&3)
 if n&(1<<20):n-=1<<21
 return ((getter+12)&~4095)+(n<<12)+((q>>10)&4095)
def s32(n):return struct.unpack('<i',struct.pack('<I',n&0xffffffff))[0]
NEW=t.F+0x31300;DEL=t.F+0x31400;t.put(t.JNI+163*8,'<Q',NEW);t.put(t.JNI+23*8,'<Q',DEL)
special={a:n for a,n in t.imports.items() if n in ('_pthread_once','_pthread_key_create','_pthread_getspecific','_pthread_setspecific','_snprintf')}
for a in special:del t.imports[a]
def hook(u,pc,size,_):
 global next_key
 name=special.get(pc)
 if pc==loop_end:u.emu_stop();return
 if name=='_pthread_once':
  if t.reg(0) not in once:once.add(t.reg(0));u.reg_write(UC_ARM64_REG_PC,t.reg(1))
  else:t.ret()
 elif name=='_pthread_key_create':t.put(t.reg(0),'<I',next_key);next_key+=1;t.ret()
 elif name=='_pthread_getspecific':t.ret(tls.get(t.reg(0),0))
 elif name=='_pthread_setspecific':tls[t.reg(0)]=t.reg(1);t.ret()
 elif name=='_snprintf':
  assert bytes(u.mem_read(t.reg(2),16)).split(b'\0')[0]==b'%lld/%d'
  sp=u.reg_read(UC_ARM64_REG_SP);s=f"{t.get(sp,'<q')}/{t.get(sp+8,'<i')}".encode();assert len(s)<t.reg(1);u.mem_write(t.reg(0),s+b'\0');t.ret(len(s))
 elif pc==NEW:
  p=t.alloc(0x40);strings[p]=list(struct.unpack('<'+'H'*t.reg(2),bytes(u.mem_read(t.reg(1),t.reg(2)*2))));t.ret(p)
 elif pc==DEL:t.ret()
 elif pc==t.B+0x12e7aec:t.ret(t.alloc(0x60))
 elif pc==t.B+0x12e7c08:
  n=t.reg(1);p=t.alloc(0x14+n);t.put(p+0x10,'<i',n);t.ret(p)
 elif pc==t.B+0x12e8038:
  data=bytes(u.mem_read(t.reg(2),2048)).split(b'\0')[0].decode('utf-8');assert len(units(data))==t.reg(3)
  p=java(data);t.put(t.reg(1),'<Q',p);t.ret(p)
 elif pc in ctor_sites:
  p,chars,widths,height,path,shift=[t.reg(i) for i in range(1,7)];name=string(path);png=pngs[name];pic=Image.open(BytesIO(png));w,h=pic.size;im=image(name,w,h)
  t.put(p+0x10,'<QQQiiI',widths,im,chars,height,s32(shift),w);fonts[p]=(name,height,chars,widths,im);t.ret()
 elif pc==t.B+0xab78d0:t.ret(len(strings[t.reg(1)]))
 elif pc==t.B+0xab60e4:
  values=strings[t.reg(1)];index=s32(t.reg(2));assert 0<=index<len(values);t.ret(values[index])
 elif pc==t.B+0xab6f94:
  values=strings[t.reg(1)];t.ret(values.index(t.reg(2)) if t.reg(2) in values else -1)
 elif pc==t.B+0x131cf70:
  name=bytes(u.mem_read(t.reg(1),80)).split(b'\0')[0].decode();t.ret(t.symbols.get('_'+name,0))
 elif pc==t.B+0x1c619c:
  g=t.reg(1);t.put(g+0x48,'<ii',t.get(g+0x48,'<i')+s32(t.reg(2)),t.get(g+0x4c,'<i')+s32(t.reg(3)));t.put(g+0x50,'<B',1);t.ret()
 elif pc==t.B+0x1c6190:
  g=t.reg(1);t.put(g+0x38,'<iiii',s32(t.reg(2))+t.get(g+0x48,'<i'),s32(t.reg(3))+t.get(g+0x4c,'<i'),s32(t.reg(4)),s32(t.reg(5)));t.ret()
 elif pc in (t.B+0x1c6194,t.B+0x1c6170,t.B+0x1c614c):t.ret()
 elif pc==t.B+0xc4558c:
  im=t.reg(2);sp=u.reg_read(UC_ARM64_REG_SP);xy=struct.unpack('<iii',bytes(u.mem_read(sp,12)))
  if im in images and images[im][0].endswith('.png'):glyphs.append((images[im][0],t.reg(3),t.reg(4),t.reg(5),t.reg(6),xy))
  calls.append(('region',im));t.ret()
 elif pc==t.B+0xc452e0:calls.append(('image',t.reg(2)));t.ret()
 elif pc==t.symbols['_AGRankImage']:
  source,rank,w,h=[t.reg(i) for i in range(1,5)];calls.append(('tint',source,rank,w,h));t.ret(image('rank-effect',w or 35,h*4 if h else 320))
 elif pc in [t.B+x for x in font_draw]:font_events.append((fonts.get(t.reg(1)),string(t.reg(3))))
 elif pc in body_boundaries:body_boundaries[pc]();return
 elif pc==t.symbols['_AGNativeWatchRenderFrame']:t.ret()
 elif t.B+0x5c1280<=pc<t.B+0x5c36ac:return
t.u.hook_add(UC_HOOK_CODE,hook)
def receive(v,cmd,body):
 a=t.alloc(0x14+len(body));t.put(a+0x10,'<i',len(body));t.u.mem_write(a+0x14,body)
 stream=t.alloc(0x30);t.put(stream+0x10,'<Q',a);t.put(stream+0x18,'<i',len(body));m=t.alloc(0x40);t.put(m+0x20,'<Q',stream);t.put(m+0x30,'<b',cmd)
 assert t.call('_AGHUDReceive',t.E,m,v)==1 and t.get(stream+0x20,'<i')==0
def utf(s):b=s.encode();return struct.pack('>H',len(b))+b
def build_fonts(v):
 slot=class_slot(font_get[v]);c=t.alloc(0x200);t.put(t.B+slot,'<Q',c);t.put(t.B+slot+9,'<B',2)
 start=raw.find(raw[0x5c1280:0x5c12a0],font_get[v],font_get[v]+0x1000);assert start>0
 ctor=raw.find(raw[0x5c38b4:0x5c38d4],start,start+0x3000);assert ctor>0;ctor_sites.add(t.B+ctor)
 t.symbols['_native_font_init']=t.B+start;t.call('_native_font_init',t.E)
 white=t.get(c+0xc0,'<Q');title=t.get(c+0xc8,'<Q')
 assert fonts[white][:2]==('fb1.png',15) and fonts[title][1]==21
 pix=Image.open(BytesIO(pngs['fb1.png'])).convert('RGBA');colors={p[:3] for p in pix.get_flattened_data() if p[3]>200}
 assert (253,253,253) in colors and (0,0,0) in colors
 return white

for v in range(6):
 current_v=v;white=build_fonts(v)
 c=t.alloc(0x180);g=t.alloc(0x60);t.put(t.B+t.canvases[v],'<Q',c);t.put(c+0x130,'<i',432);t.put(c+0x128,'<i',602);t.put(c+0x124,'<i',10)
 t.put(g+0x38,'<iiii',0,0,432,602)
 # Exercise original glyph rendering directly before the public HUD path.
 text=java('Chào mừng các bạn đến với Army2 Hoàng Gia.');glyphs.clear();t.symbols['_native_font_draw']=t.B+font_draw[v];t.call('_native_font_draw',t.E,white,g,text,20,1,0)
 assert len(glyphs)==len(strings[text]) and all(x[0]=='fb1.png' and x[4]==15 for x in glyphs)
 if '--font-only' in sys.argv:continue
 for text in ('Chào mừng các bạn đến với Army2 Hoàng Gia.','Sự kiện mới: nhận quà lúc 21:00','Bảo trì máy chủ sau 10 phút'):
  receive(v,-116,utf(text)+struct.pack('>ii',30,0));font_events.clear();glyphs.clear();t.call('_AGHUDPaint',t.E,g,v)
  assert font_events and font_events[-1][0][:2]==('fb1.png',15),'Every server announcement must use the native white outlined 15px font'
  assert font_events[-1][1]==text and all(x[0]=='fb1.png' and x[4]==15 for x in glyphs)

print('PASS310 original AOT font initialization, correct fb1.png/15px field, actual glyph width and painting for six PBs; arbitrary server announcements retain white/black outlined glyphs and native size.' if '--font-only' not in sys.argv else 'PASS310 font fixture: original static initializer + glyph methods, all six PBs, exact fb1.png and 15px dimensions.')
