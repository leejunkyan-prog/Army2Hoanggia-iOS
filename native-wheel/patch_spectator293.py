"""Attach spectator simulation to the native canvas render callback.

Keep the original update path for ordinary play. During a watch session the
framework owns a single render clock, avoiding both a missing update loop
and duplicate physics when the Java canvas loop also runs.
"""
from hashlib import sha256
from struct import pack
import patch_spectator291 as aot
import patch_spectator292 as previous

PAINTS=(0x50feec,0x5fdc64,0x6e2928,0x7c75ec,0x8ac2b0,0x990f74)
UPDATE_CALLS=(0x24f91ec,0x24fa4cc,0x24fb7ac,0x24fca8c,0x24fdd6c,0x24ff04c)
ORIGINAL_UPDATES=(0x24f91d0,0x24fa4b0,0x24fb790,0x24fca70,0x24fdd50,0x24ff030)
CAVE,CAVE_FILE=0x250b000,0x24cb000
CACHE,CACHE_FILE=0x25007a0,0x24c07a0
GAME_NAME,RENDER_NAME=CAVE+0xc00,CAVE+0xc40
GAME_SYMBOL=b'AGNativeWatchGameUpdate\0'
RENDER_SYMBOL=b'AGNativeWatchRenderFrame\0'
DYLSYM=0x131cf70

def file_offset(address):
    return address-0x40000 if 0x24f8000<=address<0x250c000 else address

def shim(variant,render):
    start=CAVE+(0x600 if render else 0)+variant*0x100
    cache=CACHE+(8 if render else 0)
    name=RENDER_NAME if render else GAME_NAME
    words=[];labels={};fixups=[]
    def pc():return start+len(words)*4
    def emit(word):words.append(word)
    def cb(op,reg,label):fixups.append((len(words),op|reg,label));emit(0)
    emit(0xa9bc7bfd) # stp x29,x30,[sp,#-64]!
    emit(0xa90107e0) # stp x0,x1,[sp,#16]
    emit(0xf90013e2) # str x2,[sp,#32]
    emit(aot._adrp(pc(),cache,9))
    emit(0xf9400000|((cache&4095)//8<<10)|(9<<5)|16)
    cb(0xb5000000,16,'resolved')
    emit(0x92800020) # RTLD_DEFAULT
    emit(aot._adr(pc(),name,1))
    emit(aot._branch(pc(),DYLSYM,True))
    emit(0xaa0003f0)
    emit(aot._adrp(pc(),cache,9))
    emit(0xf9000000|((cache&4095)//8<<10)|(9<<5)|16)
    labels['resolved']=pc()
    cb(0xb4000000,16,'fallback')
    emit(0xa94107e0) # restore env / arena
    emit((0x52800001 if render else 0x52800002)|(variant<<5))
    emit(0xd63f0200)
    if not render:
        fixups.append((len(words),None,'done'));emit(0)
    labels['fallback']=pc()
    if render:
        emit(0xa94107e0)
        emit(0xf94013e2)
        emit(0xa8c47bfd)
        emit(0xa9ba6ffc) # displaced canvas paint prologue
        emit(aot._branch(pc(),PAINTS[variant]+4))
    else:
        emit(0xa94107e0)
        emit(aot._branch(pc(),ORIGINAL_UPDATES[variant],True))
        labels['done']=pc()
        emit(0xa8c47bfd)
        emit(0xd65f03c0)
    for index,op,label in fixups:
        at=start+index*4
        if op is None:words[index]=aot._branch(at,labels[label])
        else:
            delta=labels[label]-at;assert delta%4==0 and -(1<<20)<=delta<(1<<20)
            words[index]=op|(((delta//4)&0x7ffff)<<5)
    assert len(words)*4<=0x100
    return b''.join(pack('<I',word)for word in words)

def patch_native(original,framework):
    for symbol in (b'_AGNativeWatchGameUpdate',b'_AGNativeWatchRenderFrame'):
        assert aot.framework_exports(framework,symbol),'Missing render-clock export: '+symbol.decode()
    patched,edits=previous.patch_native(original,framework)
    assert original[CAVE_FILE:CAVE_FILE+0x1000]==bytes(0x1000)
    assert original[CACHE_FILE:CACHE_FILE+16]==bytes(16)
    result=bytearray(patched)
    def change(offset,raw,purpose):
        before=bytes(result[offset:offset+len(raw)]);result[offset:offset+len(raw)]=raw
        edits.append({'offset':offset,'before':before.hex(),'after':raw.hex(),
                      'purpose':purpose,'before_sha256':sha256(before).hexdigest(),
                      'after_sha256':sha256(raw).hexdigest()})
    for v in range(6):
        assert original[PAINTS[v]:PAINTS[v]+4]==bytes.fromhex('fc6fbaa9')
        call=UPDATE_CALLS[v];off=file_offset(call)
        assert original[off:off+4]==pack('<I',aot._branch(call,ORIGINAL_UPDATES[v],True))
        change(CAVE_FILE+v*0x100,shim(v,False),f'PB{v+1} native update dispatch bridge')
        change(CAVE_FILE+0x600+v*0x100,shim(v,True),f'PB{v+1} canvas render entry bridge')
        change(off,pack('<I',aot._branch(call,CAVE+v*0x100,True)),f'PB{v+1} managed update call')
        change(PAINTS[v],pack('<I',aot._branch(PAINTS[v],CAVE+0x600+v*0x100)),f'PB{v+1} canvas paint entry')
    change(CAVE_FILE+0xc00,GAME_SYMBOL,'Native update dispatch export name')
    change(CAVE_FILE+0xc40,RENDER_SYMBOL,'Native render clock export name')
    assert len(result)==len(original)
    return bytes(result),edits
