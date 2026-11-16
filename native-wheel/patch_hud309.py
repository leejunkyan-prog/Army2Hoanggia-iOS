"""Audited static hooks for APK marquee and ranked-boss rendering.

Use unused RX padding and three unused RW resolver slots in the supplied
Build293. Existing receive/actor bridges remain in use. No runtime code writes.
"""
from struct import pack,unpack_from
from hashlib import sha256
import patch_recipe301 as recipe
import patch_spectator291 as aot
PAINTS=(0x50feec,0x5fdc64,0x6e2928,0x7c75ec,0x8ac2b0,0x990f74)
BARS=(0x5a2e34,0x68b928,0x7705ec,0x8552b0,0x939f74,0xa1ec38)
CAVE=0x2509100
CACHE=0x25007b0
NAMES=(CAVE+0xd00,CAVE+0xd40,CAVE+0xd80)
SYMBOLS=(b'AGHUDCanvasPaint\0',b'AGHUDSkipBar\0',b'AGHUDImage\0')
def offset(a):return a-0x40000 if 0x24f8000<=a<0x250c000 else a
def pair(load,a,b,off):return (0xa9400000 if load else 0xa9000000)|((off//8&127)<<15)|(b<<10)|(31<<5)|a
def memory(load,r,off):return (0xf9400000 if load else 0xf9000000)|((off//8)<<10)|(31<<5)|r
def move(dst,src):return 0xaa0003e0|(src<<16)|dst
def imm(r,n):return 0x52800000|(n<<5)|r
class Code:
 def __init__(self,start):self.start=start;self.words=[];self.labels={};self.fix=[]
 def pc(self):return self.start+4*len(self.words)
 def emit(self,*words):self.words.extend(words)
 def label(self,name):self.labels[name]=self.pc()
 def cb(self,op,r,name):self.fix.append((len(self.words),op|r,name));self.emit(0)
 def address(self,r,p):self.emit(aot._adrp(self.pc(),p,r),0x91000000|((p&4095)<<10)|(r<<5)|r)
 def resolve(self,which):
  cache=CACHE+which*8;self.emit(aot._adrp(self.pc(),cache,9),0xf9400000|((cache&4095)//8<<10)|(9<<5)|16)
  self.cb(0xb5000000,16,'resolved')
  self.emit(0x92800020);self.address(1,NAMES[which]);self.emit(aot._branch(self.pc(),0x131cf70,True),move(16,0))
  self.emit(aot._adrp(self.pc(),cache,9),0xf9000000|((cache&4095)//8<<10)|(9<<5)|16)
  self.label('resolved');self.cb(0xb4000000,16,'fallback')
 def finish(self,limit):
  for i,op,name in self.fix:
   delta=self.labels[name]-(self.start+i*4);assert delta%4==0 and -(1<<20)<=delta<(1<<20)
   self.words[i]=op|(((delta//4)&0x7ffff)<<5)
  data=b''.join(pack('<I',w) for w in self.words);assert len(data)<=limit;return data
def frame(c,size):c.emit(0xd10003ff|(size<<10),pair(False,29,30,0))
def leave(c,size):c.emit(pair(True,29,30,0),0x910003ff|(size<<10))
def canvas(v):
 c=Code(CAVE+v*0xb0);frame(c,80);c.emit(pair(False,0,1,16),memory(False,2,32));c.resolve(0)
 c.emit(pair(True,0,1,16),memory(True,2,32),imm(3,v));c.address(4,CAVE+0xb00+v*16);c.emit(0xd63f0200)
 leave(c,80);c.emit(0xd65f03c0);c.label('fallback');c.emit(pair(True,0,1,16),memory(True,2,32));leave(c,80)
 c.emit(aot._branch(c.pc(),0x250b600+v*0x100));return c.finish(0xb0)
def bar(v):
 c=Code(CAVE+0x500+v*0xa0);frame(c,80);c.emit(pair(False,0,1,16),pair(False,2,3,32));c.resolve(1)
 c.emit(pair(True,0,1,16),memory(True,2,32),imm(3,v),0xd63f0200);c.cb(0x35000000,0,'skip')
 c.label('fallback');c.emit(pair(True,0,1,16),pair(True,2,3,32));leave(c,80);c.emit(aot._branch(c.pc(),CAVE+0xc00+v*16))
 c.label('skip');leave(c,80);c.emit(0xd65f03c0);return c.finish(0xa0)
def image(region):
 c=Code(CAVE+0x900+region*0xc0);frame(c,128)
 for i in range(0,8,2):c.emit(pair(False,i,i+1,16+i*8))
 c.emit(pair(True,8,9,128),pair(False,8,9,80));c.resolve(2)
 c.emit(0x910043e0,imm(1,region),0xd63f0200) # x0=sp+16, r[8] contains packed int arguments
 c.label('fallback')
 for i in range(0,8,2):c.emit(pair(True,i,i+1,16+i*8))
 leave(c,128);c.emit(aot._branch(c.pc(),0xc4558c if region else 0xc452e0));return c.finish(0xc0)
def patch_native(original,framework):
 assert sha256(original).hexdigest()==recipe.BASE_NATIVE
 for name in SYMBOLS:assert aot.framework_exports(framework,b'_'+name[:-1]),name
 result,edits=recipe.patch_native(original,framework);result=bytearray(result)
 assert original[offset(CAVE):offset(CAVE)+0xf00]==bytes(0xf00)
 assert original[offset(CACHE):offset(CACHE)+24]==bytes(24)
 def change(at,raw,why):
  off=offset(at);before=bytes(result[off:off+len(raw)]);result[off:off+len(raw)]=raw
  edits.append({'offset':off,'address':at,'before':before.hex(),'after':raw.hex(),'purpose':why,'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(raw).hexdigest()})
 for v in range(6):
  assert unpack_from('<I',original,PAINTS[v])[0]==aot._branch(PAINTS[v],0x250b600+v*0x100)
  assert original[BARS[v]:BARS[v]+4]==bytes.fromhex('f85fbca9')
  change(CAVE+v*0xb0,canvas(v),f'PB{v+1} canvas painter with existing render clock and final marquee')
  change(CAVE+0x500+v*0xa0,bar(v),f'PB{v+1} skip only the active ranked-boss default HP painter')
  change(CAVE+0xb00+v*16,pack('<II',0xa9ba6ffc,aot._branch(CAVE+0xb00+v*16+4,PAINTS[v]+4)),f'PB{v+1} original canvas prologue')
  change(CAVE+0xc00+v*16,original[BARS[v]:BARS[v]+4]+pack('<I',aot._branch(CAVE+0xc00+v*16+4,BARS[v]+4)),f'PB{v+1} original boss HP prologue')
  change(PAINTS[v],pack('<I',aot._branch(PAINTS[v],CAVE+v*0xb0)),f'PB{v+1} canvas paint entry')
  change(BARS[v],pack('<I',aot._branch(BARS[v],CAVE+0x500+v*0xa0)),f'PB{v+1} boss HP paint entry')
 assert original[0x1c6144:0x1c6148]==pack('<I',aot._branch(0x1c6144,0xc452e0))
 assert original[0x1c6150:0x1c6164]==bytes.fromhex('e8274029ea0b40b9e9ab0029e80300b90bfd2914')
 for region,site in enumerate((0x1c6144,0x1c6150)):
  change(CAVE+0x900+region*0xc0,image(region),'Scoped ranked-boss image/region geometry and tint bridge')
  change(site,pack('<I',aot._branch(site,CAVE+0x900+region*0xc0)),'Graphics image entry; identical original path outside ranked paint')
 for at,name in zip(NAMES,SYMBOLS):change(at,name,'HUD bridge export name')
 end=0
 for edit in sorted(edits,key=lambda x:x['offset']):
  off=edit['offset'];assert off>=end and result[end:off]==original[end:off];end=off+len(bytes.fromhex(edit['after']))
 assert result[end:]==original[end:] and len(result)==len(original)
 return bytes(result),edits
