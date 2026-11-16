"""Compiled six-PB HUD receive, real render routing and ranked paint state.

Game graphics/font/image conversion and OS/JNI primitives are boundaries.
Packet parsing, lifetime, scroll, rank geometry and image-hook logic execute
the actual iPhone ARM64 framework.
"""
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_SP
import test_inventory_device282 as t
from patch_hud309 import patch_native,offset,BARS,pair,memory,move,imm

raw=(Path(__file__).parent/'build/base293-native').read_bytes()
patched,_=patch_native(raw,t.blob)
t.u.mem_write(t.B,patched[:26050560])
for a,b in ((0x24f8000,0x2500000),(0x2500000,0x250c000)):
 t.u.mem_write(t.B+a,patched[offset(a):offset(b-1)+1])
font_get=[0x5c112c,0x6a8f50,0x78dc14,0x8728d8,0x95759c,0xa3c260]
font_draw=[0x5c3e64,0x6abc88,0x79094c,0x875610,0x95a2d4,0xa3ef98]
font_width=[0x5c4054,0x6abe50,0x790b14,0x8757d8,0x95a49c,0xa3f160]
for address in font_width:assert raw[address:address+44]==raw[font_width[0]:font_width[0]+44],'Width must enter the actual native method prologue'
arena_slots=[0x2082e30,0x20b23a0,0x20e0090,0x210dd80,0x213ba70,0x2169760]
roster_slots=[0x207f060,0x20aec70,0x20dc970,0x210a660,0x2138350,0x2166040]
actor_slots=[0x2091b80,0x20c0670,0x20ee360,0x211c050,0x2149d40,0x2177a30]
service_slots=[0x207b870,0x20ab650,0x20d9350,0x2107040,0x2134d30,0x2162a20]
strings={};labels=[];images=[];fills=[];colors=[];frames=[];native_calls=[];tls={};once_done=set();next_key=0;paint_count=0;original=t.F+0x31000;canvas_original=t.F+0x31200
font=t.alloc(0x40);fake_tint=t.alloc(0x40);pow_image=t.alloc(0x40);body=t.alloc(0x40)
t.put(body+0x20,'<ii',35,32);t.put(pow_image+0x20,'<ii',41,188)
NEWSTRING=t.F+0x31300;DELETE=t.F+0x31400;t.put(t.JNI+163*8,'<Q',NEWSTRING);t.put(t.JNI+23*8,'<Q',DELETE)
def s32(n):return struct.unpack('<i',struct.pack('<I',n&0xffffffff))[0]
current_v=0;current_player=0
def hook(u,pc,size,_):
 global next_key,paint_count
 if pc==NEWSTRING:
  text=bytes(u.mem_read(t.reg(1),t.reg(2)*2)).decode('utf-16-le','surrogatepass');p=t.alloc(0x30);strings[p]=text;t.ret(p)
 elif pc==DELETE:strings.pop(t.reg(1),None);t.ret()
 elif pc in [t.B+x for x in font_get]:t.ret(font)
 elif pc in [t.B+x for x in font_width]:t.ret(len(strings[t.reg(2)])*6)
 elif pc in [t.B+x for x in font_draw]:labels.append((strings[t.reg(3)],s32(t.reg(4)),s32(t.reg(5)),t.reg(6)));t.ret()
 elif pc==t.B+0x1c619c:
  g=t.reg(1);t.put(g+0x48,'<ii',t.get(g+0x48,'<i')+s32(t.reg(2)),t.get(g+0x4c,'<i')+s32(t.reg(3)));t.put(g+0x50,'<B',1);t.ret()
 elif pc==t.B+0x1c6190:
  g=t.reg(1);t.put(g+0x38,'<iiii',s32(t.reg(2))+t.get(g+0x48,'<i'),s32(t.reg(3))+t.get(g+0x4c,'<i'),s32(t.reg(4)),s32(t.reg(5)));t.ret()
 elif pc==t.B+0x1c6194:colors.append(t.reg(2));t.ret()
 elif pc in (t.B+0x1c6170,t.B+0x1c614c):fills.append((pc-t.B,)+tuple(s32(t.reg(i)) for i in range(2,6)));t.ret()
 elif pc in (t.B+0xc4558c,t.B+0xc452e0):
  images.append(tuple(t.reg(i) for i in range(8)));t.ret()
 elif pc==t.symbols['_AGRankImage']:
  native_calls.append(('tint',t.reg(1),t.reg(2),t.reg(3),t.reg(4)));t.ret(fake_tint)
 elif pc==t.symbols['_AGNativeWatchRenderFrame']:frames.append(t.reg(1));t.ret()
 elif pc==canvas_original:native_calls.append(('canvas',t.reg(1),t.reg(2)));t.ret()
 elif pc==original:
  # Original actor paint enters its real patched boss-bar entry, then the
  # patched region entry. No replacement for rank suppression/image logic.
  paint_count+=1;native_calls.append(('actor',t.reg(1)))
 elif pc==t.B+0x131cf70:
  name=bytes(u.mem_read(t.reg(1),80)).split(b'\0')[0].decode();t.ret(t.symbols.get('_'+name,0))
t.u.hook_add(UC_HOOK_CODE,hook)
# Avoid replacing the harness's existing import hook: teach it POSIX TLS by
# removing only these imports from its dictionary and handling them above.
tls_imports={a:n for a,n in t.imports.items() if n in ('_pthread_once','_pthread_key_create','_pthread_getspecific','_pthread_setspecific','_snprintf')}
for a in tls_imports:del t.imports[a]
def posix(u,pc,size,_):
 global next_key
 name=tls_imports.get(pc)
 if name=='_pthread_once':
  if t.reg(0) not in once_done:
   once_done.add(t.reg(0));u.reg_write(UC_ARM64_REG_PC,t.reg(1))
  else:t.ret()
 elif name=='_pthread_key_create':t.put(t.reg(0),'<I',next_key);next_key+=1;t.ret()
 elif name=='_pthread_getspecific':t.ret(tls.get(t.reg(0),0))
 elif name=='_pthread_setspecific':tls[t.reg(0)]=t.reg(1);t.ret()
 elif name=='_snprintf':
  fmt=bytes(u.mem_read(t.reg(2),16)).split(b'\0')[0];assert fmt==b'%lld/%d'
  sp=u.reg_read(UC_ARM64_REG_SP);text=f"{t.get(sp,'<q')}/{t.get(sp+8,'<i')}".encode()
  assert len(text)<t.reg(1);u.mem_write(t.reg(0),text+b'\0');t.ret(len(text))
t.u.hook_add(UC_HOOK_CODE,posix)
def mutf(s):return struct.pack('>H',len(s.encode()))+s.encode()
def receive(v,cmd,data,prefix=b'abc'):
 array=t.alloc(0x14+len(prefix)+len(data));t.put(array+0x10,'<i',len(prefix)+len(data));t.u.mem_write(array+0x14,prefix+data)
 stream=t.alloc(0x30);t.put(stream+0x10,'<Q',array);t.put(stream+0x18,'<i',len(prefix)+len(data));t.put(stream+0x20,'<i',len(prefix))
 message=t.alloc(0x40);t.put(message+0x20,'<Q',stream);t.put(message+0x30,'<b',cmd)
 result=t.call('_AGHUDReceive',t.E,message,v);assert t.get(stream+0x20,'<i')==len(prefix);return result

def painter(v):
 words=[0xd10143ff,pair(False,29,30,48),pair(False,19,20,16),memory(False,21,32),move(19,0),move(20,1),move(21,2),imm(3,0)]
 def address(r,p):
  words.append(0xd2800000|((p&65535)<<5)|r)
  for i in (1,2,3):words.append(0xf2800000|(i<<21)|(((p>>(16*i))&65535)<<5)|r)
 address(16,t.B+BARS[v]);words.append(0xd63f0200)
 words.extend((move(0,19),move(1,21)));address(2,body)
 words.extend((imm(3,0),imm(4,0),imm(5,35),imm(6,32),imm(7,0),imm(8,200),0xb90003e8,imm(8,300),0xb90007e8,imm(8,33),0xb9000be8))
 address(16,t.B+0x1c6150);words.extend((0xd63f0200,pair(True,19,20,16),memory(True,21,32),pair(True,29,30,48),0x910143ff,0xd65f03c0))
 t.u.mem_write(original,b''.join(struct.pack('<I',w) for w in words))

for v in range(6):
 painter(v)
 current_v=v;c=t.alloc(0x180);arena=t.alloc(0x300);arena_class=t.alloc(0x100);array_class=t.alloc(0xb0);actor_class=t.alloc(0x200)
 t.put(t.B+t.canvases[v],'<Q',c);t.put(t.B+arena_slots[v],'<Q',arena_class);t.put(arena_class+0xe8,'<Q',arena);t.put(c+0xb8,'<Q',arena)
 t.put(t.B+roster_slots[v],'<Q',array_class);t.put(t.B+actor_slots[v],'<Q',actor_class);t.put(actor_class+0x148,'<Q',pow_image)
 objects=t.alloc(0x18+16*8);t.put(objects+0x10,'<i',16);t.put(array_class+0xa0,'<Q',objects)
 p=t.alloc(0x200);t.put(objects+0x18+8*8,'<Q',p);t.put(p+0x16b,'<B',8);t.put(p+0x68,'<qq',43960,10000);t.put(p+0x114,'<ii',200,300)
 service_class=t.alloc(0xb0);service=t.alloc(0x20);t.put(t.B+service_slots[v],'<Q',service_class);t.put(service_class+0xa0,'<Q',service);t.put(service+0x10,'<Q',v+123)
 t.put(c+0x130,'<i',432);t.put(c+0x128,'<i',602);t.put(c+0x124,'<i',100)
 g=t.alloc(0x60);t.put(g+0x38,'<iiii',17,29,340,420);t.put(g+0x48,'<ii',-71,13);t.put(g+0x50,'<B',1);saved=bytes(t.u.mem_read(g+0x28,0x2c))
 greeting='Chào mừng Army2 Hoàng Gia!'
 assert receive(v,-116,mutf(greeting)+struct.pack('>ii',30,0))==1
 labels.clear();t.call('_AGHUDPaint',t.E,g,v);assert labels[-1]==(greeting,432,1,0)
 t.put(c+0x124,'<i',115);t.call('_AGHUDPaint',t.E,g,v);assert labels[-1][1]==417
 t.call('_AGHUDPaint',t.E,g,v);assert labels[-1][1]==417,'Painting twice must not advance the canvas counter'
 assert bytes(t.u.mem_read(g+0x28,0x2c))==saved
 # Frame wrap matches GameCanvas's 0..10000 counter.
 t.put(c+0x124,'<i',10000);receive(v,-116,mutf('wrap')+struct.pack('>ii',200,0));t.put(c+0x124,'<i',2);t.call('_AGHUDPaint',t.E,g,v);assert labels[-1][1]==429
 t.put(c+0x124,'<i',800);n=len(labels);t.call('_AGHUDPaint',t.E,g,v);assert len(labels)==n,'A completed pass must stop'
 receive(v,-116,mutf('timed')+struct.pack('>ii',5,1));t.now+=2;n=len(labels);t.call('_AGHUDPaint',t.E,g,v);assert len(labels)==n
 receive(v,-116,mutf('replacement')+struct.pack('>ii',30,0));receive(v,-116,mutf('')+bytes(8));n=len(labels);t.call('_AGHUDPaint',t.E,g,v);assert len(labels)==n
 assert receive(v,-121,b'\0')==0 and receive(v,-121,b'\3\1')==0,'Market packets must continue to their original handler'
 for rank,title in enumerate(('Tinh anh','Thủ lĩnh','Cao thủ'),1):
  assert receive(v,-121,bytes((2,8,rank))+mutf(title)+struct.pack('>i',43960))==1
  assert t.get(p+0x70,'<q')==43960
  labels.clear();native_calls.clear();before=bytes(t.u.mem_read(p,0x200))
  assert t.call('_AGRankPaintActor',t.E,p,g,v,original)==1
  assert ('actor',p) in native_calls and labels[0][0]==title and labels[1][0]=='43960/43960'
  assert labels[0][1:]==(200,256,2) and labels[1][1:]==(200,225,2),'Rank labels must follow actual native sprite bounds'
  assert ('tint',body,rank,0,0) in native_calls,'Only body images enter the rank tint'
  assert bytes(t.u.mem_read(p,0x200))==before
  assert bytes(t.u.mem_read(g+0x28,0x2c))==saved and all(not x for x in tls.values())
  assert any(x[0]=='tint' and x[1]==pow_image and x[2]==rank for x in native_calls)
  labels.clear();t.call('_AGAuraPaintActor',t.E,p,g,v,original);assert labels[0][0]==title,'Existing production actor bridge must reach the new ranked painter'
  t.put(p+0x68,'<q',12345);labels.clear();t.call('_AGRankPaintActor',t.E,p,g,v,original);assert labels[-1][0]=='12345/43960'
  t.put(p+0x68,'<q',0);assert not t.call('_AGRankPaintActor',t.E,p,g,v,original)
  t.put(p+0x68,'<q',43960)
 receive(v,-121,b'\4');assert not t.call('_AGRankPaintActor',t.E,p,g,v,original)
 receive(v,-121,bytes((2,8,1))+mutf('Tinh anh')+struct.pack('>i',43960));receive(v,20,b'');assert not t.call('_AGRankPaintActor',t.E,p,g,v,original)
 receive(v,-121,bytes((2,8,1))+mutf('Tinh anh')+struct.pack('>i',43960));receive(v,3,bytes(23));assert not t.call('_AGRankPaintActor',t.E,p,g,v,original)
 receive(v,-121,bytes((2,8,1))+mutf('Tinh anh')+struct.pack('>i',43960));t.put(service+0x10,'<Q',v+999);assert not t.call('_AGRankPaintActor',t.E,p,g,v,original)
 t.call('_AGHUDCanvasPaint',t.E,c,g,v,canvas_original);assert frames[-1]==v and native_calls[-1]==('canvas',c,g)
assert not strings and all(not x for x in tls.values())
print('PASS309 compiled six-PB HUD: real wire parsing, scrolling/counter wrap/expiry/replacement, preserved clip/camera, three named ranks and exact HP, per-boss color/fire routing, death/reset/new-login/connection isolation, same native actor and once-only render-clock routing. JVM graphics/image conversion are mocked; no physical-device claim.')
