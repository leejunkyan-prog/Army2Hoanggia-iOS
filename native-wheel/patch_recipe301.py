"""Keep the classified recipe object through the native callback's send.

The original callback selects the inventory three times. A native update can
rebind its display to the server vector after classification and before the
third selection. Keep the resolved object in the callback's unused stack slot
instead. No executable pages are modified at runtime.
"""
from hashlib import sha256
from struct import pack,unpack_from
import patch_spectator291 as aot

BASE_NATIVE='93e9c074725e3e5d087192cf29b498df8f71bbf542e9d09d7f20c4bc17a6f6c0'
CALLBACKS=(0x511e94,0x5ffbe4,0x6e48a8,0x7c956c,0x8ae230,0x992ef4)
SELECTORS=(0x5920f0,0x67b6ac,0x760370,0x845034,0x929cf8,0xa0e9bc)
CAVE,NAME=0x2508700,0x2508660
SYMBOL=b'AGRecipeDetailObject\0'
def file_offset(at):return at-0x40000 if 0x24f8000<=at<0x250c000 else at
def shim(v):
    start=CAVE+v*0x60;callback=CALLBACKS[v];words=[];labels={};fix=[]
    def pc():return start+len(words)*4
    def put(w):words.append(w)
    def cb(op,reg,label):fix.append((len(words),op|reg,label));put(0)
    put(0xa9bc7bfd) # stp x29,x30,[sp,#-64]!
    put(0x910003fd) # mov x29,sp
    put(0xa90107e8) # stp x8,x1,[sp,#16]
    put(0xf90023e8) # str x8,[sp,#64] -- caller's sp[0], legacy fallback
    put(0x92800020) # RTLD_DEFAULT
    put(aot._adr(pc(),NAME,1));put(aot._branch(pc(),0x131cf70,True))
    cb(0xb4000000,0,'fallback')
    put(0xaa0003f0);put(0xaa1303e0);put(0xf9400be1);put(0xd63f0200)
    cb(0xb4000000,0,'fallback') # object pointer, not a truncated boolean
    put(0xf90023e0) # store the exact resolved/classified object in caller sp[0]
    fix.append((len(words),None,'accepted'));put(0)
    labels['fallback']=pc()
    put(0xa94107e8);put(0xa8c47bfd)
    cb(0x34000000,20,'gear')
    put(aot._branch(pc(),callback+0x64))
    labels['gear']=pc();put(aot._branch(pc(),callback+0xf4))
    labels['accepted']=pc();put(0xa94107e8);put(0xa8c47bfd);put(aot._branch(pc(),callback+0x8c))
    for index,op,label in fix:
        at=start+index*4;delta=labels[label]-at
        words[index]=aot._branch(at,labels[label]) if op is None else op|(((delta//4)&0x7ffff)<<5)
    assert len(words)*4<=0x60
    return b''.join(pack('<I',w)for w in words).ljust(0x60,b'\0')
def patch_native(original,framework):
    assert sha256(original).hexdigest()==BASE_NATIVE
    result=bytearray(original);edits=[]
    def change(at,raw,why):
        off=file_offset(at);before=bytes(result[off:off+len(raw)]);result[off:off+len(raw)]=raw
        edits.append({'offset':off,'address':at,'purpose':why,'before':before.hex(),'after':raw.hex(),
            'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(raw).hexdigest()})
    name=file_offset(NAME)
    assert original[name:name+64]==b'AGRecipeDetail\0'.ljust(64,b'\0')
    change(NAME,SYMBOL.ljust(64,b'\0'),'Resolve the exact classified object, retaining boolean API for old callers')
    for v,callback in enumerate(CALLBACKS):
        cave=CAVE+v*0x60;off=file_offset(cave)
        assert original[off:off+12]==bytes.fromhex('fd7bbca9fd030091e80701a9')
        hook=unpack_from('<I',original,callback+0x60)[0]
        assert hook==aot._branch(callback+0x60,cave)
        at=callback+0xa8
        expected=(0xf9400fe8,0xf9000be0,0xf9400908,0x3940011f,0xf9400901,0x3940003f,0xaa1303e0,aot._branch(callback+0xc4,SELECTORS[v],True))
        assert original[at:at+32]==b''.join(pack('<I',w)for w in expected),hex(at)
        # Preserve service returned in x0, then load the held item. Never call
        # inventory.v() after the label/wait path can schedule another update.
        stable=(0xf9000be0,0xf94003e0)+(0xd503201f,)*6
        change(cave,shim(v),f'PB{v+1} per-callback recipe root and unchanged legacy fallback')
        change(at,b''.join(pack('<I',w)for w in stable),f'PB{v+1} send the same item that Detail classified')
    assert len(result)==len(original)
    # Verify every byte outside the declared disjoint edits remains intact.
    end=0
    for edit in sorted(edits,key=lambda e:e['offset']):
        at=edit['offset'];assert at>=end and result[end:at]==original[end:at]
        end=at+len(bytes.fromhex(edit['after']))
    assert result[end:]==original[end:]
    assert aot.framework_exports(framework,b'_AGRecipeDetailObject'),'Missing exported resolved-item classifier'
    return bytes(result),edits
