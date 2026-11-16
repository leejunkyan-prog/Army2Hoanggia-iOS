"""Read the actual public equipment export supplied with the APK reference."""
from pathlib import Path
from hashlib import sha256
import struct,json
root=Path(__file__).parent
meta=json.loads((root/'fixtures/apk306.json').read_text())
raw=(root/'fixtures/equip306.bin').read_bytes()
assert sha256(raw).hexdigest()==meta['equip_sha256']
pos=0
def read(fmt):
 global pos
 fmt='>'+fmt;out=struct.unpack_from(fmt,raw,pos);pos+=struct.calcsize(fmt);return out[0] if len(out)==1 else out
rows=[]
for _ in range(read('B')):
 hero=read('B');version=read('h')
 for _ in range(read('B')):
  slot=read('B')
  for _ in range(read('B')):
   id=read('h');style=read('B') if slot==0 else 0;icon=read('h');level=read('b')
   rects=[read('hhbbbb') for _ in range(6)];stats=read('10b')
   rows.append(dict(hero=hero,slot=slot,id=id,style=style,icon=icon,rects=rects))
images=[]
for _ in range(11):
 n=read('H');images.append(raw[pos:pos+n]);pos+=n
assert pos==len(raw) and len(rows)==1556
styles=[]
for i in range(0,len(meta['shot_fx_data']),20):
 s=meta['shot_fx_data'][i:i+20];styles.append((int(s[:2],16),int(s[2:6],16),int(s[6:8],16),int(s[8:14],16),int(s[14:20],16)))
