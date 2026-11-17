"""Execute installed313 ARM64 hooks; original simulation is a boundary here.
Original projectile trajectory integration is a separate check.
"""
from pathlib import Path
from zipfile import ZipFile
import json,struct,sys,lief
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
import patch_speed313 as p
r=Path(__import__('os').environ.get('ARMY2_SPEED_QA',str(Path(__file__).parent/'build/speed313')));report=json.loads((r/'Army2HoangGia-2.4.1-Build313-MaxSpeed-unsigned.validation.json').read_text());raw=(r/'native313').read_bytes();base=(r/'native312').read_bytes()
m=lief.MachO.parse(raw).at(0);B=0x100000000;H=0x600000000;S=0x700000000;STOP=H+0xf0000
u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(B,0x3000000);u.mem_map(H,0x100000);u.mem_map(S,0x100000)
for seg in m.segments:
 if seg.file_size:u.mem_write(seg.virtual_address,raw[seg.file_offset:seg.file_offset+seg.file_size])
regs=[UC_ARM64_REG_X0+i for i in range(29)]+[UC_ARM64_REG_X29,UC_ARM64_REG_X30]
def put(a,f,*v):u.mem_write(a,struct.pack(f,*v))
def get(a,f):return struct.unpack(f,u.mem_read(a,struct.calcsize(f)))[0]
def reg(i):return u.reg_read(regs[i])
def setreg(i,x):u.reg_write(regs[i],x&((1<<64)-1))
def ret(x=0):setreg(0,x);u.reg_write(UC_ARM64_REG_PC,reg(30))
mode='';speed=10;calls=0;sleeps=[];cut=0;stops={STOP};v=0;checks=[]
canvas=H+0x1000;arenaClass=H+0x2000;arena=H+0x3000;menu=H+0x4000;other=H+0x5000;env=H+0x6000
allGetters={B+x['getter'] for x in report['variants']};allOriginal={B+x['original'] for x in report['variants']}
def hook(uc,pc,size,data):
 global calls
 if pc in stops:uc.emu_stop();return
 if pc in allGetters:ret(speed);return
 if pc in allOriginal:
  assert reg(0)==env and reg(1)==arena
  calls+=1
  if cut and calls==cut:put(canvas+0xb8,'<Q',other)
  for i in range(19):setreg(i,H+0x7000+i*16)
  ret(0x1234);return
 if pc==B+0xac30dc:
  assert reg(0)==env;sleeps.append(reg(1));ret();return
u.hook_add(UC_HOOK_CODE,hook)
def reset():
 global calls,sleeps,cut,stops
 calls=0;sleeps=[];cut=0;stops={STOP}
 for i in range(31):setreg(i,H+0x8000+i*32)
 u.reg_write(UC_ARM64_REG_SP,S+0x80000);setreg(29,S+0x81000);setreg(30,STOP)
 setreg(0,env);setreg(1,arena)
 u.mem_write(canvas,bytes(0x200));put(canvas+0xb8,'<Q',arena);put(arenaClass+0xe8,'<Q',arena)
 put(B+p.CANVAS[v],'<Q',canvas);put(B+p.ARENA[v],'<Q',arenaClass)
def run(at):
 u.emu_start(B+at,B+0x3000000,count=100000)
 assert u.reg_read(UC_ARM64_REG_PC) in stops
for v,j in enumerate(report['variants']):
 for speed in range(11):
  reset();saved=[reg(i) for i in range(19,30)];sp=u.reg_read(UC_ARM64_REG_SP)
  run(j['old_update']);assert calls==(8 if speed==10 else 1),(v,speed,calls)
  assert [reg(i) for i in range(19,30)]==saved and u.reg_read(UC_ARM64_REG_SP)==sp
  checks.append(['batch',v,speed,calls])
 speed=10
 for case in ('menu','dialog','outside','null_canvas','null_arena','transition'):
  reset()
  if case=='menu':put(canvas+0xe0,'<Q',menu);put(menu+0x2c,'<B',1)
  if case=='dialog':put(canvas+0x108,'<Q',other)
  if case=='outside':put(canvas+0xb8,'<Q',other)
  if case=='null_canvas':put(B+p.CANVAS[v],'<Q',0)
  if case=='null_arena':put(arenaClass+0xe8,'<Q',0)
  if case=='transition':cut=3
  run(j['old_update']);assert calls==(3 if case=='transition' else 1),(v,case,calls)
  checks.append(['batch_guard',v,case,calls])
 for case in ('arena','menu','dialog','outside','null_canvas','null_arena','hp'):
  reset()
  if case=='menu':put(canvas+0xe0,'<Q',menu);put(menu+0x2c,'<B',1)
  if case=='dialog':put(canvas+0x108,'<Q',other)
  if case=='outside':put(canvas+0xb8,'<Q',other)
  if case=='null_canvas':put(B+p.CANVAS[v],'<Q',0)
  if case=='null_arena':put(arenaClass+0xe8,'<Q',0)
  put(canvas+0x13c,'<B',case=='hp');put(canvas+0x118,'<i',4)
  # Enter the Max branch with exactly the original wrapper's32-byte frame.
  sp=u.reg_read(UC_ARM64_REG_SP);u.reg_write(UC_ARM64_REG_SP,sp-32);put(sp-32,'<QQQ',S+0x81000,STOP,env)
  saved=[reg(i) for i in range(19,30)];stops={B+j['loop']};run(j['old_pace']+0x5c)
  assert sleeps==([1] if case in ('arena','hp') else [33]),(v,case,sleeps)
  assert u.reg_read(UC_ARM64_REG_SP)==sp and reg(29)==S+0x81000 and reg(30)==STOP
  assert [reg(i) for i in range(19,30)]==saved
  assert get(canvas+0x118,'<i')==(19 if case=='hp' else 4)
  checks.append(['pace',v,case,sleeps])
 # Native chest vector store: source order can never replace a live display.
 reset();source=H+0x9000;display=H+0xa000;screen=H+0xb000
 for current in (0,display):
  for i in range(1000):
   put(screen+0x70,'<Q',current);setreg(8,source);setreg(9,screen);setreg(10,0x11223344)
   sp=u.reg_read(UC_ARM64_REG_SP);stops={B+j['inventory_site']+4};run(j['inventory_site'])
   assert get(screen+0x70,'<Q')==(current or source) and reg(8)==(current or source)
   assert reg(9)==screen and reg(10)==0x11223344 and u.reg_read(UC_ARM64_REG_SP)==sp
 checks.append(['stable_inventory',v,2000])
 # Original update prologue/branch displaced byte-for-byte, all previous hooks intact.
 assert raw[j['original']-0x40000:j['original']-0x40000+4]==base[j['old_update']-0x40000:j['old_update']-0x40000+4]
# Actual PB1 GameCanvas HP flag-clearing block: reaches its original notify path.
v=0;reset();put(canvas+0x13c,'<B',1);put(canvas+0x118,'<i',19);setreg(21,B+p.CANVAS[0]);put(reg(29)-0x60,'<i',1)
stops={B+0x510d48,B+0x510e18};run(0x510ce4)
assert u.reg_read(UC_ARM64_REG_PC)==B+0x510d48 and get(canvas+0x13c,'<B')==0 and get(canvas+0x118,'<i')==0
checks.append(['original_hp_clear_and_notify_path',True])
result={'passed':True,'checks':checks,'chest_iterations':12000,'physical_device_tested':False,'boundaries':'Original arena update is mocked in this hook/ABI test; native trajectory integration is separate. No server connection.'}
(r/'speed313-checks.json').write_text(json.dumps(result,indent=2));print('PASS',len(checks),'six-PB speed/guard/ABI cases and12000 native inventory-store interleavings; eight original simulation calls only on active unblocked Max; original HP clear/notify path reached; low speeds preserved.')
