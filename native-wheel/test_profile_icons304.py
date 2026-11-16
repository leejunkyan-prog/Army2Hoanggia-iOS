"""Exercise the compiled bridge and original Image.l ARM64 pixel reader.
OS/JNI allocation, cached image objects and Pixmap.getPixel are boundaries.
No per-profile ICON section, own inventory or logged-in hero is supplied.
"""
from pathlib import Path
import struct
import test_inventory_device282 as t
from unicorn import UC_HOOK_CODE

raw=(Path(__file__).parent/'build/base293-native').read_bytes()
catalogs=(0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0)
consumables=(0x2098970,0x20c7200,0x20f4ef0,0x2122be0,0x21508d0,0x217e5c0)
sites=(0x515058,0x602b78,0x6e783c,0x7cc500,0x8b11c4,0x995e88)
consume_sites=(0x5b7cb0,0x6a0024,0x784ce8,0x8699ac,0x94e670,0xa33334)
def address(site):
    adrp,add=struct.unpack_from('<II',raw,site)
    imm=((adrp>>5)&0x7ffff)<<2|((adrp>>29)&3)
    if imm&(1<<20):imm-=1<<21
    return (site&~4095)+(imm<<12)+((add>>10)&4095)
assert tuple(map(address,sites))==catalogs
assert tuple(map(address,consume_sites))==consumables
# Execute this unmodified original method, including scanline indexing and
# its transparent-key handling, instead of mocking the pixel-copy routine.
t.u.mem_write(t.B+0xc48ea0,raw[0xc48ea0:0xc49028])
NEW=t.F+0x21300;DELETE=t.F+0x21400
t.put(t.JNI+179*8,'<Q',NEW);t.put(t.JNI+23*8,'<Q',DELETE)
cache=t.alloc(0x20);texture=t.alloc(0x30);pixmap=t.alloc(0x30)
images={};strings={};pixel_values=[];pixel_reads=0;deleted=[];arrays=[];cache_keys=[]
def hook(u,pc,size,_):
    global pixel_reads
    if pc==t.B+0xc46b40:t.ret(cache)
    elif pc==t.B+0xab216c:
        p=t.alloc(0x20);strings[p]=t.reg(1);t.ret(p)
    elif pc==t.B+0xbc88a0:
        assert t.reg(1)==cache;key=strings[t.reg(2)];cache_keys.append(key);t.ret(images.get(key,0))
    elif pc==NEW:
        n=t.reg(1);p=t.alloc(0x14+4*n);t.put(p+0x10,'<i',n);arrays.append(p);t.ret(p)
    elif pc==DELETE:deleted.append(t.reg(1));t.ret()
    elif pc==t.B+0x1b4ba8:t.ret(texture)
    elif pc==t.B+0x39dc58:t.ret(1)
    elif pc==t.B+0x39dd54:t.ret(0)
    elif pc==t.B+0x39dd00:t.ret(pixmap)
    elif pc==t.B+0x398e0c:t.ret(16)
    elif pc==t.B+0x398e30:t.ret(16)
    elif pc==t.B+0x398fe8:t.ret(0)
    elif pc==t.B+0x1db1f8:
        assert t.reg(1)==pixmap;pixel_reads+=1;t.ret(pixel_values[t.reg(3)*16+t.reg(2)])
t.u.hook_add(UC_HOOK_CODE,hook)
def obj_array(rows):
    v=t.vector(rows);return v
def image(values,direct=False):
    p=t.alloc(0x30);t.put(p+0x20,'<ii',16,16)
    if direct:
        a=t.alloc(0x14+4*len(values));t.put(a+0x10,'<i',len(values));t.u.mem_write(a+0x14,struct.pack('<256I',*values));t.put(p+0x10,'<Q',a)
    else:t.put(p+0x18,'<Q',texture)
    return p
for v in range(6):
    clazz=t.alloc(0xc0);t.put(t.B+catalogs[v],'<Q',clazz)
    gear=t.alloc(0xd0);t.put(gear+0x80,'<q',56);t.put(gear+0x88,'<q',210+v)
    slot=t.alloc(0x20);t.put(slot+0x18,'<b',0);t.put(slot+0x10,'<Q',obj_array([gear]))
    hero=t.alloc(0x20);t.put(hero+0x1a,'<b',6);t.put(hero+0x10,'<Q',obj_array([slot]));t.put(clazz+0xb0,'<Q',obj_array([hero]))
    pixel_values=[0x50b4ffff if i%2 else 0xdcdce6ff for i in range(256)]
    picture=image(pixel_values,direct=v%2==1);images[210+v]=picture
    out=t.alloc(24);before=pixel_reads
    assert t.call('_AGProfileIconRead',t.E,v,6,0,56,out)==1
    assert (t.get(out,'<i'),t.get(out+4,'<i'),t.get(out+8,'<i'),t.get(out+12,'<i'))==(0,16,16,210+v)
    pixels=t.get(out+16,'<Q');assert bytes(t.u.mem_read(pixels,8))==bytes.fromhex('dcdce6ff50b4ffff')
    assert pixel_reads-before==(256 if v%2==0 else 0)
    # The same template on another hero/slot must not find this image.
    assert t.call('_AGProfileIconRead',t.E,v,9,0,56,out)==0 and t.get(out,'<i')==1
    assert t.call('_AGProfileIconRead',t.E,v,6,1,56,out)==0 and t.get(out,'<i')==1
    assert t.call('_AGProfileIconRead',t.E,v,6,0,43,out)==0 and t.get(out,'<i')==1
    # Costume registry is separate from the character equipment templates.
    generic=t.alloc(0xb0);entry=t.alloc(0x20);t.put(entry+0x18,'<q',2046);t.put(entry+0x10,'<Q',picture)
    t.put(generic+0xa0,'<Q',obj_array([entry]));t.put(t.B+consumables[v],'<Q',generic)
    assert t.call('_AGProfileIconRead',t.E,v,6,5,2046,out)==1 and t.get(out+12,'<i')==-1
    assert bytes(t.u.mem_read(t.get(out+16,'<Q'),4))==bytes.fromhex('dcdce6ff')
    assert t.call('_AGProfileIconRead',t.E,v,6,5,2999,out)==0 and t.get(out,'<i')==3
    images.pop(210+v);assert t.call('_AGProfileIconRead',t.E,v,6,0,56,out)==0 and t.get(out,'<i')==3
    images[210+v]=picture;t.put(picture+0x20,'<i',129)
    assert t.call('_AGProfileIconRead',t.E,v,6,0,56,out)==0 and t.get(out,'<i')==4
assert arrays==deleted and all(n==0 for n in t.pins.values())
print('PASS native profile icons: six AOT-audited catalogs, hero/slot/item lookup and exact native icon key, no ICON/atlas/own-account dependency, separate costume registry, RGBA pixel copy, direct pixel arrays, bounded image size and balanced JNI references')
