"""Differential APK Java palette and actual server wire-format boundaries."""
import ctypes as c,random,struct,subprocess,tempfile
from pathlib import Path
root=Path(__file__).parent
class Packet(c.Structure):
 _fields_=[(x,c.c_int) for x in ('kind','slot','rank','maximum','seconds')]+[('length',c.c_size_t),('text',c.c_uint16*32768)]
def mutf(s):
 out=bytearray()
 raw=s.encode('utf-16-be','surrogatepass')
 for i in range(0,len(raw),2):
  n=int.from_bytes(raw[i:i+2],'big')
  if 0<n<128:out.append(n)
  elif n<2048:out.extend((192|(n>>6),128|(n&63)))
  else:out.extend((224|(n>>12),128|((n>>6)&63),128|(n&63)))
 return struct.pack('>H',len(out))+out
with tempfile.TemporaryDirectory(prefix='army-hud309-') as tmp:
 tmp=Path(tmp);lib=tmp/'protocol.so'
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-shared','-fPIC',str(root/'HUDProtocol.c'),'-o',str(lib)],check=True,capture_output=True)
 api=c.CDLL(str(lib));api.AGHUDParse.argtypes=[c.c_int,c.c_void_p,c.c_size_t,c.POINTER(Packet)];api.AGRankPixel.argtypes=[c.c_uint32,c.c_int,c.c_int];api.AGRankPixel.restype=c.c_uint32
 def parse(command,wire):
  p=Packet();buf=c.create_string_buffer(wire);return api.AGHUDParse(command,buf,len(wire),c.byref(p)),p
 greeting='Chào mừng bạn đến với Army2 Hoàng Gia!     •     Sự kiện mới\0😀'
 wire=mutf(greeting)+struct.pack('>ii',30,0);ok,p=parse(-116,wire)
 assert ok and p.kind==1 and p.seconds==0
 assert bytes(p.text)[:p.length*2]==greeting.encode('utf-16-le')
 for cap in (1,43960,2**31-1):
  for rank,title in enumerate(('Tinh anh','Thủ lĩnh','Cao thủ'),1):
   ok,p=parse(-121,bytes((2,127,rank))+mutf(title)+struct.pack('>i',cap))
   assert ok and (p.kind,p.slot,p.rank,p.maximum)==(2,127,rank,cap)
 ok,p=parse(-121,b'\4');assert ok and p.kind==4
 for bad in (wire[:-1],wire+b'0',b'\0\1\0'+bytes(8),b'\0\2\xc1\x80'+bytes(8),b'\0\4\xf0\x9f\x98\x80'+bytes(8)):
  assert not parse(-116,bad)[0]
 for bad in (b'\4\0',bytes((2,128,1))+mutf('x')+struct.pack('>i',20),bytes((2,8,4))+mutf('x')+struct.pack('>i',20),bytes((2,8,1))+mutf('x')+struct.pack('>i',0)):
  assert not parse(-121,bad)[0]
 assert not parse(-120,wire)[0]
 ok,p=parse(-116,mutf('new')+struct.pack('>ii',200,-1));assert ok and p.seconds==0
 subprocess.run(['javac','-d',str(tmp),str(root/'testdata/RankPixelsAPK.java')],check=True,capture_output=True)
 rng=random.Random(309);colors=[rng.getrandbits(32) for _ in range(3000)]
 colors += [a<<24|v<<16|v<<8|v for a in (0,1,127,255) for v in range(256)]
 colors += [0xffebeced,0xffececed,0xff23aaff,0x7f005511,0xffffffff]
 cases=[(p,r,f) for p in colors for r in (1,2,3) for f in (0,1)]
 wire=b''.join(struct.pack('>IBB',*row) for row in cases)
 expected=subprocess.run(['java','-cp',str(tmp),'RankPixelsAPK'],input=wire,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
 assert len(expected)==len(cases)*4
 for i,(pixel,rank,fire) in enumerate(cases):assert api.AGRankPixel(pixel,rank,fire)==struct.unpack_from('>I',expected,i*4)[0],(hex(pixel),rank,fire)
print('PASS309 protocol: server marquee/rank packets, Vietnamese + modified-UTF NUL/surrogates, malformed input rejection, full positive HP range; 24,000+ pixel cases match the actual APK Java methods, including white preservation and flame highlights.')
