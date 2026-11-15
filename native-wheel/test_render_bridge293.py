"""Run real patched canvas paint/update call sites and verify the ARM64 ABI."""
from pathlib import Path
import struct,sys,lief
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
import patch_spectator293 as patch

root=Path(__file__).resolve().parent
framework=Path(sys.argv[1]).read_bytes()
source=Path(sys.argv[2]) if len(sys.argv)>2 else root/'build/base290-native'
original=source.read_bytes();modified,edits=patch.patch_native(original,framework)
parsed=lief.MachO.parse(str(source));binary=parsed.at(0)
GOT,=[b.address for b in binary.dyld_info.bindings if b.symbol.name=='_dlsym']
MAIN,HEAP,STACK,FAKE=0x100000000,0x600000000,0x700000000,0x400000000
STOP,DLSYM,GAME,RENDER=FAKE,FAKE+0x100,FAKE+0x200,FAKE+0x300
ENV,ARENA,GRAPHICS=HEAP+0x100,HEAP+0x200,HEAP+0x300

class Engine:
    def __init__(self,raw,missing=False):
        self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.missing=missing
        self.events=[];self.lookups=0;self.variant=0;self.end=0
        for segment in binary.segments:
            if segment.name=='__PAGEZERO' or not segment.virtual_size:continue
            self.u.mem_map(segment.virtual_address,(segment.virtual_size+4095)&-4096)
            self.u.mem_write(segment.virtual_address,raw[segment.file_offset:segment.file_offset+segment.file_size])
        for address,size in ((HEAP,0x1000),(STACK,0x10000),(FAKE,0x1000)):self.u.mem_map(address,size)
        self.u.mem_write(GOT,struct.pack('<Q',DLSYM))
        self.u.hook_add(UC_HOOK_CODE,self.hook)
    def reg(self,i):return self.u.reg_read(UC_ARM64_REG_X0+i)
    def ret(self,value=0):
        for i in range(1,18):self.u.reg_write(UC_ARM64_REG_X0+i,0xd0000000+i)
        self.u.reg_write(UC_ARM64_REG_X0,value)
        self.u.reg_write(UC_ARM64_REG_PC,self.u.reg_read(UC_ARM64_REG_LR))
    def hook(self,uc,pc,size,unused):
        if pc==self.end:uc.emu_stop()
        elif pc==DLSYM:
            name=bytes(uc.mem_read(self.reg(1),64)).split(b'\0',1)[0]
            assert name in (patch.GAME_SYMBOL[:-1],patch.RENDER_SYMBOL[:-1])
            self.lookups+=1
            self.ret(0 if self.missing else GAME if name==patch.GAME_SYMBOL[:-1]else RENDER)
        elif pc==GAME:
            assert (self.reg(0),self.reg(1),self.reg(2))==(ENV,ARENA,self.variant)
            self.events.append('managed update');self.ret()
        elif pc==RENDER:
            assert (self.reg(0),self.reg(1))==(ENV,self.variant)
            self.events.append('render frame');self.ret()
        elif pc==MAIN+patch.ORIGINAL_UPDATES[self.variant]:
            assert (self.reg(0),self.reg(1))==(ENV,ARENA)
            self.events.append('original update');self.ret()
    def run(self,v,render):
        self.variant=v;self.events=[]
        at=MAIN+(patch.PAINTS[v]if render else patch.UPDATE_CALLS[v]);self.end=at+4
        sp=STACK+0xf000
        self.u.reg_write(UC_ARM64_REG_SP,sp);self.u.reg_write(UC_ARM64_REG_LR,STOP)
        for i,value in enumerate((ENV,ARENA,GRAPHICS)):self.u.reg_write(UC_ARM64_REG_X0+i,value)
        saved={i:0xa000000000+i for i in range(19,30)}
        for i,value in saved.items():self.u.reg_write(UC_ARM64_REG_X0+i,value)
        self.u.emu_start(at,self.end,count=10000)
        assert self.u.reg_read(UC_ARM64_REG_PC)==self.end
        assert self.u.reg_read(UC_ARM64_REG_SP)==sp-(0x60 if render else 0)
        assert all(self.reg(i)==value for i,value in saved.items())
        if render:
            assert (self.reg(0),self.reg(1),self.reg(2))==(ENV,ARENA,GRAPHICS)
            assert self.u.reg_read(UC_ARM64_REG_LR)==STOP
        else:assert self.u.reg_read(UC_ARM64_REG_LR)==self.end
        return self.events

baseline,fixed,missing=Engine(original),Engine(modified),Engine(modified,True)
for v in range(6):
    assert baseline.run(v,False)==['original update']
    assert baseline.run(v,True)==[]
    assert fixed.run(v,False)==['managed update']
    assert fixed.run(v,True)==['render frame']
    assert missing.run(v,False)==['original update']
    assert missing.run(v,True)==[]
assert fixed.lookups==2 and missing.lookups==12
print('PASS real canvas render/update bridges: six PBs, exact JNI arguments, original paint prologues, register/stack preservation, shared dynamic caches and safe missing-export fallback')
