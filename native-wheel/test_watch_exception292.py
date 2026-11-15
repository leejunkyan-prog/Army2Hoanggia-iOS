"""Exercise the real native Arena.update catch call before/after tracing.

The logger and original Throwable.printStackTrace are boundary mocks. This
proves the trace bridge preserves the original error path, JNI arguments and
ARM64 ABI, including a missing-symbol fallback. It does not prove live play.
"""
from pathlib import Path
import struct
import sys
import lief
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *
import patch_spectator292 as patch

ROOT = Path(__file__).resolve().parent
framework = Path(sys.argv[1]).read_bytes()
native_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'build/base290-native'
original = native_path.read_bytes()
modified, edits = patch.patch_native(original, framework)
image_file = lief.MachO.parse(str(native_path))
image = image_file.at(0)
DLSYM_GOT, = [b.address for b in image.dyld_info.bindings if b.symbol.name == '_dlsym']
MAIN, HEAP, STACK, FAKE = 0x100000000, 0x600000000, 0x700000000, 0x400000000
STOP, TRACE, DLSYM = FAKE, FAKE + 0x1000, FAKE + 0x1200
ENV, THROWABLE = HEAP + 0x100, HEAP + 0x400

class Engine:
    def __init__(self, raw, missing=False):
        self.u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        for segment in image.segments:
            if segment.name == '__PAGEZERO' or not segment.virtual_size:
                continue
            self.u.mem_map(segment.virtual_address, (segment.virtual_size + 4095) & -4096)
            self.u.mem_write(segment.virtual_address, raw[segment.file_offset:segment.file_offset + segment.file_size])
        for address, size in ((HEAP, 0x10000), (STACK, 0x10000), (FAKE, 0x2000)):
            self.u.mem_map(address, size)
        self.u.mem_write(DLSYM_GOT, struct.pack('<Q', DLSYM))
        self.missing = missing
        self.lookups = 0
        self.variant = 0
        self.events = []
        self.end = 0
        self.u.hook_add(UC_HOOK_CODE, self.hook)

    def reg(self, i):
        return self.u.reg_read(UC_ARM64_REG_X0 + i)

    def ret(self, result=0):
        for i in range(1, 18):
            self.u.reg_write(UC_ARM64_REG_X0 + i, 0xd0000000 + i)
        self.u.reg_write(UC_ARM64_REG_X0, result)
        self.u.reg_write(UC_ARM64_REG_PC, self.u.reg_read(UC_ARM64_REG_LR))

    def hook(self, uc, pc, size, opaque):
        if pc == self.end:
            uc.emu_stop()
        elif pc == DLSYM:
            assert bytes(uc.mem_read(self.reg(1), len(patch.SYMBOL))) == patch.SYMBOL
            self.lookups += 1
            self.ret(0 if self.missing else TRACE)
        elif pc == TRACE:
            assert (self.reg(0), self.reg(1), self.reg(2)) == (ENV, THROWABLE, self.variant)
            self.events.append('trace')
            self.ret()
        elif pc == MAIN + patch.PRINT:
            assert (self.reg(0), self.reg(1)) == (ENV, THROWABLE), 'Original print received altered JNI arguments'
            self.events.append('original print')
            self.ret()

    def run(self, variant):
        self.variant = variant
        self.events.clear()
        at = MAIN + patch.CATCHES[variant]
        self.end = at + 4
        sp = STACK + 0xf000
        self.u.reg_write(UC_ARM64_REG_SP, sp)
        self.u.reg_write(UC_ARM64_REG_LR, STOP)
        self.u.reg_write(UC_ARM64_REG_X0, ENV)
        self.u.reg_write(UC_ARM64_REG_X1, THROWABLE)
        saved = {i: 0xa000000000 + i for i in range(19, 30)}
        for i, value in saved.items():
            self.u.reg_write(UC_ARM64_REG_X0 + i, value)
        self.u.emu_start(at, self.end, count=10000)
        assert self.u.reg_read(UC_ARM64_REG_PC) == self.end
        assert self.u.reg_read(UC_ARM64_REG_SP) == sp
        assert self.u.reg_read(UC_ARM64_REG_LR) == self.end
        assert all(self.reg(i) == value for i, value in saved.items())
        return self.events[:]

baseline, traced, missing = Engine(original), Engine(modified), Engine(modified, missing=True)
for variant in range(6):
    assert baseline.run(variant) == ['original print']
    assert traced.run(variant) == ['trace', 'original print']
    assert missing.run(variant) == ['original print']
assert baseline.lookups == 0
assert traced.lookups == 1, 'Trace export cache should be shared by all PBs'
assert missing.lookups == 6
assert patch.prior.framework_exports(framework, b'_AGNativeWatchTraceException')
print('PASS actual Arena.update exception call sites: six PBs, logger before unchanged original print, JNI arguments, SP/LR/x19-x29 preserved, missing-symbol fallback and shared resolver cache')
