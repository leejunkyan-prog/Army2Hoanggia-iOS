"""Run compiled iPhone inventory bridge; OS/JNI and selection paint are mocked."""
from pathlib import Path
import struct,sys
import lief
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
p=Path(sys.argv[1]);blob=p.read_bytes();m=lief.MachO.parse(str(p)).at(0)
L=0x200000000;B=0x100000000;H=0x600000000;F=0x400000000;S=0x700000000;STOP=F+0x30000
u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
for seg in m.segments:
 if seg.virtual_size:u.mem_map(L+seg.virtual_address,(seg.virtual_size+4095)&-4096);u.mem_write(L+seg.virtual_address,blob[seg.file_offset:seg.file_offset+seg.file_size])
u.mem_map(B,0x3000000);u.mem_map(H,0x800000);u.mem_map(F,0x40000);u.mem_map(S,0x40000)
symbols={s.name:L+s.value for s in m.symbols if s.value}
def put(a,f,*v):u.mem_write(a,struct.pack(f,*v))
def get(a,f):return struct.unpack(f,u.mem_read(a,struct.calcsize(f)))[0]
for rel in m.relocations:
 if rel.size==64 and int(rel.type)==1:put(L+rel.address,'<Q',get(L+rel.address,'<Q')+L)
names={};imports={}
for binding in m.dyld_info.bindings:
 name=binding.symbol.name
 if name not in names:names[name]=F+len(names)*256;imports[names[name]]=name
 put(L+binding.address,'<Q',names[name])
cursor=H+0x10000
now=100.0

def alloc(n):
 global cursor
 p=cursor;cursor+=(n+31)&-16;assert cursor<H+0x800000;u.mem_write(p,bytes(n));return p
E=H;JNI=H+0x1000;put(E,'<Q',JNI)
ENTER=F+0x20000;LEAVE=ENTER+0x100;put(JNI+217*8,'<Q',ENTER);put(JNI+218*8,'<Q',LEAVE)
PIN=ENTER+0x200;UNPIN=ENTER+0x300;put(JNI+21*8,'<Q',PIN);put(JNI+22*8,'<Q',UNPIN)
regs=[UC_ARM64_REG_X0+i for i in range(31)]
def reg(i):return u.reg_read(regs[i])
def ret(n=0):u.reg_write(UC_ARM64_REG_X0,n&((1<<64)-1));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
locks=0;refreshes=[];pins={};display_builds=0
pools=[0x2094ac0,0x20c34f0,0x20f11e0,0x211eed0,0x214cbc0,0x217a8b0]
classes=[0x2091350,0x20c0000,0x20edcf0,0x211b9e0,0x21496d0,0x21773c0]
canvases=[0x207dac0,0x20ad740,0x20db440,0x2109130,0x2136e20,0x2164b10]
refresh=[0x592220,0x67b7dc,0x7604a0,0x845164,0x929e28,0xa0eaec]

def row_sort_key(raw,cmp):
 key,qty,item,group,id,rank,fresh=struct.unpack('<QqQiiii',raw)
 if cmp==symbols['_byKey']:return (key,)
 if cmp==symbols['_grouped']:return (group,id if group else 0,rank)
 assert cmp==symbols['_updated'];return (-fresh,rank)

def hook(_,pc,size,data):
 global locks,display_builds
 if pc==STOP:u.emu_stop();return
 if pc==ENTER:raise AssertionError('Render callback attempted blocking server Vector MonitorEnter')
 if pc==LEAVE:locks-=1;assert locks==0;ret();return
 if pc==PIN:p=reg(1);pins[p]=pins.get(p,0)+1;ret(p);return
 if pc==UNPIN:p=reg(1);pins[p]-=1;assert pins[p]>=0;ret();return
 if pc==B+0x1300d54:put(reg(1),'<Q',get(E+0x38,'<Q'));put(E+0x38,'<Q',reg(1));ret();return
 if pc in [B+a for a in refresh]:
  screen=reg(1);refreshes.append((pc,screen))
  vec=get(screen+0x70,'<Q');array=get(vec+0x18,'<Q');index=get(screen+0xc8,'<i')
  assert 0<=index<get(vec+0x24,'<i')
  put(screen+0x90,'<Q',get(array+0x18+index*8,'<Q'))
  ret(1);return
 if pc==B+0xbe3f1c:display_builds+=1;ret(alloc(0x30));return
 if pc in (B+0xbe6b7c,B+0xbe6ba0):
  capacity=10 if pc==B+0xbe6b7c else reg(2)
  a=alloc(0x18+capacity*8);put(a+0x10,'<i',capacity)
  put(reg(1)+0x18,'<Q',a);put(reg(1)+0x10,'<I',0);ret();return
 if pc==B+0x1dfcac:
  v=reg(1);a=get(v+0x18,'<Q');n=get(v+0x24,'<i');assert n<get(a+0x10,'<i')
  put(a+0x18+n*8,'<Q',reg(2));put(v+0x24,'<i',n+1);ret();return
 if pc not in imports:return
 name=imports[pc]
 if name=='__dyld_get_image_header':ret(B)
 elif name=='_clock_gettime':put(reg(1),'<qq',int(now),round((now-int(now))*1000000000));ret()
 elif name in ('_pthread_mutex_lock','_pthread_mutex_trylock','_pthread_mutex_unlock'):ret()
 elif name=='_malloc':ret(alloc(reg(0)))
 elif name=='_calloc':ret(alloc(reg(0)*reg(1)))
 elif name=='_free':ret()
 elif name in ['_memcpy','_memmove','___memcpy_chk']:
  if name=='___memcpy_chk':assert reg(2)<=reg(3),'Native checked copy exceeds its destination'
  u.mem_write(reg(0),bytes(u.mem_read(reg(1),reg(2))));ret(reg(0))
 elif name in ['_memset','_bzero']:
  u.mem_write(reg(0),bytes([reg(1)&255])*reg(2)if name=='_memset'else bytes(reg(1)));ret(reg(0))
 elif name=='_qsort':
  ptr,n,sz,cmp=[reg(i)for i in range(4)];assert sz==40
  rows=[bytes(u.mem_read(ptr+i*sz,sz))for i in range(n)];rows.sort(key=lambda raw:row_sort_key(raw,cmp));u.mem_write(ptr,b''.join(rows));ret()
 elif name=='_bsearch':
  wanted=get(reg(0),'<Q');ptr,n,sz=reg(1),reg(2),reg(3);ret(next((ptr+i*sz for i in range(n)if get(ptr+i*sz,'<Q')==wanted),0))
 else:raise AssertionError(('unexpected import',name))
u.hook_add(UC_HOOK_CODE,hook)
def call(name,*args):
 u.reg_write(UC_ARM64_REG_SP,S+0x30000);u.reg_write(UC_ARM64_REG_LR,STOP)
 for i,v in enumerate(args):u.reg_write(regs[i],v)
 u.emu_start(symbols[name],STOP+4,count=1000000)
 assert u.reg_read(UC_ARM64_REG_PC)==STOP and locks==0
 return reg(0)
def item(id,quantity=1,equipment=False):
 p=alloc(0xd0);put(p+0xbd,'<B',not equipment);put(p+0x80,'<q',id);put(p+0x90,'<q',quantity);put(p+0xb0,'<I',id if equipment else 0);return p
def vector(rows):
 a=alloc(0x18+8*len(rows));put(a+0x10,'<I',len(rows))
 for i,p in enumerate(rows):put(a+0x18+8*i,'<Q',p)
 v=alloc(0x30);put(v+0x10,'<I',7);put(v+0x18,'<Q',a);put(v+0x24,'<I',len(rows));return v

def ids(v):
 a=get(v+0x18,'<Q');return [get(get(a+0x18+8*i,'<Q')+0x80,'<q')for i in range(get(v+0x24,'<I'))]
def displayed(screen):return ids(get(screen+0x70,'<Q'))
for v in range(6 if __name__=='__main__' else 0):
 canvas=alloc(0x180);screen=alloc(0xe0);clazz=alloc(0x180);pool=alloc(0xc0)
 put(B+canvases[v],'<Q',canvas);put(canvas+0xb8,'<Q',screen);put(screen,'<Q',clazz);put(B+classes[v],'<Q',clazz);put(B+pools[v],'<Q',pool);put(clazz+0xa0,'<Q',screen)
 put(canvas+0x130,'<i',432);put(screen+0x50,'<i',19);put(screen+0x54,'<i',68);put(screen+0x58,'<i',408);put(screen+0x5c,'<i',520);put(screen+0xc0,'<i',7);put(screen+0xb8,'<i',54)
 geometry=alloc(28);assert call('_AGInventoryGeometry',v,geometry)==1;assert struct.unpack('<7i',u.mem_read(geometry,28))==(432,12,68,408,520,7,54)
 rows=[item(104,5),item(70001,equipment=True),item(7,99),item(120,1)];vec=vector(rows);put(pool+0xa8,'<Q',vec);put(screen+0x70,'<Q',vec);put(screen+0x90,'<Q',rows[0])
 call('_AGInventoryOrder',E,v,canvas,screen,1);assert displayed(screen)==[70001,7,104,120]
 assert ids(vec)==[104,70001,7,120],'Server Vector must not be reordered'
 display=get(screen+0x70,'<Q');builds=display_builds
 for _ in range(20):
  # Native update assigns its source Vector each frame before the bridge runs.
  put(screen+0x70,'<Q',vec)
  call('_AGInventoryOrder',E,v,canvas,screen,1)
 assert get(screen+0x70,'<Q')==display and display_builds==builds,'Unchanged frame rebuilt the display'
 assert get(screen+0x90,'<Q')==rows[1]
 child=alloc(0x80);put(child+0x10,'<Q',screen);put(canvas+0xb8,'<Q',child);call('_AGInventoryOrder',E,v,canvas,child,0)
 fresh=[item(70001,equipment=True),item(7,99),item(105,1),item(120,1)];nextvec=vector(fresh);put(pool+0xa8,'<Q',nextvec);put(canvas+0xb8,'<Q',screen)
 put(canvas+0x108,'<Q',123);call('_AGInventoryOrder',E,v,canvas,screen,1);assert get(screen+0x70,'<Q')==display
 put(canvas+0x108,'<Q',0);call('_AGInventoryOrder',E,v,canvas,screen,1);assert displayed(screen)==[105,70001,7,120]
 assert ids(nextvec)==[70001,7,105,120]
 assert get(screen+0x90,'<Q')==fresh[2]and get(fresh[2]+0x90,'<q')==1,'Show the new item at the first slot after its result closes'
 # Selected recipe must resolve into the next server vector at action time.
 put(screen+0xc8,'<i',3);put(screen+0x90,'<Q',fresh[3]);newpaper=item(120,1);replacement=vector([fresh[0],newpaper,fresh[2],fresh[1]]);put(pool+0xa8,'<Q',replacement)
 assert call('_AGInventoryResolve',E,fresh[3])==newpaper
 assert displayed(screen)==[105,70001,7,120] and get(screen+0xc8,'<i')==3 and get(screen+0x90,'<Q')==newpaper
 child=alloc(0x80);put(child+0x10,'<Q',screen);put(canvas+0xb8,'<Q',child)
 newer=item(120,1);put(pool+0xa8,'<Q',vector([fresh[0],newer,fresh[2],fresh[1]]))
 assert call('_AGInventoryResolve',E,newpaper)==newer
 assert get(screen+0x90,'<Q')==newer
 put(canvas+0xb8,'<Q',screen)
 call('_AGInventoryOrder',E,v,canvas,screen,0);call('_AGInventoryOrder',E,v,canvas,screen,1);assert displayed(screen)==[105,70001,7,120]
 assert any(pc==B+refresh[v]for pc,s in refreshes)
 # Simulate 100 refreshes while keeping template IDs and handles unchanged.
 for turn in range(100):
  put(fresh[1]+0x90,'<q',100+turn);call('_AGInventoryOrder',E,v,canvas,screen,1);assert displayed(screen)[0]==7
 # Empty and large real Vectors are valid chest states.
 call('_AGInventoryOrder',E,v,canvas,0,0)
 empty=vector([]);put(pool+0xa8,'<Q',empty);put(screen+0x70,'<Q',empty)
 call('_AGInventoryOrder',E,v,canvas,screen,1);assert displayed(screen)==[]
 call('_AGInventoryOrder',E,v,canvas,0,0)
 # Start another login before testing the default grouped order.
 serviceSlots=[0x207b870,0x20ab650,0x20d9350,0x2107040,0x2134d30,0x2162a20]
 serviceClass=alloc(0xb0);service=alloc(0x30);put(B+serviceSlots[v],'<Q',serviceClass);put(serviceClass+0xa0,'<Q',service);put(service+0x10,'<Q',0x123000+v)
 many=vector([item(i,100+i)for i in range(40,0,-1)]);put(pool+0xa8,'<Q',many);put(screen+0x70,'<Q',many)
 call('_AGInventoryOrder',E,v,canvas,screen,1);assert displayed(screen)==list(range(1,41))
 assert ids(many)==list(range(40,0,-1))
 index=24;put(screen+0xc8,'<i',index)
 put(screen+0x70,'<Q',many)
 call('_AGInventoryOrder',E,v,canvas,screen,1)
 selected=get(screen+0x90,'<Q');assert get(selected+0x80,'<q')==25 and get(selected+0x90,'<q')==125
 call('_AGInventoryOrder',E,v,canvas,0,0)
assert all(n==0 for n in pins.values()),pins
if __name__=='__main__':print('PASS compiled ARM64 bridge: six variants, 600 updates, zero blocking monitor calls, unchanged server vectors, stable unchanged frames, vector replacement, dialog deferral, crafting return, recipe resolution, preserved reopen order, login grouping and balanced JNI roots')


