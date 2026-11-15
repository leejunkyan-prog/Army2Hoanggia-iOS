"""Execute Build290's real local-turn predicates before/after the Build291 bridge.

Usage: python test_spectator_turn291.py compiled-AGWheel [Build290-executable]
The default executable is build/base290-native, restored from the repository's
SHA256-verified delivery archive by CI. No server session or iPhone is simulated.
"""
from pathlib import Path
import struct
import sys

import lief
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *

import patch_spectator291 as patch

ROOT = Path(__file__).resolve().parent
framework = Path(sys.argv[1]).read_bytes()
native_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'build/base290-native'
original = native_path.read_bytes()
modified, edits = patch.patch_native(original, framework)
assert edits and len(modified) == len(original)
fw = lief.MachO.parse(str(Path(sys.argv[1]))).at(0)
assert '_AGViewerStillWatching' in {s.name for s in fw.exported_symbols}, 'dlsym cannot resolve a hidden symbol'
image = lief.MachO.parse(str(native_path)).at(0)
MAIN, HEAP, STACK, FAKE = 0x100000000, 0x600000000, 0x700000000, 0x400000000
STOP, WATCH, DLSYM = FAKE, FAKE + 0x1000, FAKE + 0x1200
ENV = HEAP + 0x100
ARENA_CLASSES = [0x2082e30, 0x20b23a0, 0x20e0090, 0x210dd80, 0x213ba70, 0x2169760]
# Use the original image's actual dynamic binding, independently of the
# patcher's branch-target constant. This catches virtual/file offset mistakes.
DLSYM_GOT, = [b.address for b in image.dyld_info.bindings if b.symbol.name == '_dlsym']


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
        self.put(DLSYM_GOT, '<Q', DLSYM)
        self.missing = missing
        self.watching = False
        self.variant = 0
        self.lookups = 0
        self.callbacks = []
        self.getters = []
        for v in range(6):
            players, arena = HEAP + 0x1000 + v * 0x800, HEAP + 0x1400 + v * 0x800
            self.put(MAIN + patch.PLAYER_CLASSES[v], '<Q', players)
            self.put(MAIN + patch.PLAYER_CLASSES[v] + 9, '<B', 2)
            self.put(MAIN + ARENA_CLASSES[v], '<Q', arena)
            self.put(MAIN + ARENA_CLASSES[v] + 9, '<B', 2)
        self.u.hook_add(UC_HOOK_CODE, self.hook)

    def put(self, address, fmt, *values):
        self.u.mem_write(address, struct.pack(fmt, *values))

    def reg(self, i):
        return self.u.reg_read(UC_ARM64_REG_X0 + i)

    def return_from_mock(self, result):
        # Ordinary C calls may destroy caller-saved registers. The bridge must
        # retain the original JNI environment and its caller's callee-saved ABI.
        for i in range(1, 18):
            self.u.reg_write(UC_ARM64_REG_X0 + i, 0xd0000000 + i)
        self.u.reg_write(UC_ARM64_REG_X0, result)
        self.u.reg_write(UC_ARM64_REG_PC, self.u.reg_read(UC_ARM64_REG_LR))

    def hook(self, uc, pc, size, opaque):
        if pc == STOP:
            uc.emu_stop()
        elif pc == DLSYM:
            name = bytes(uc.mem_read(self.reg(1), len(patch.SYMBOL)))
            assert name == b'AGViewerStillWatching\0', name
            self.lookups += 1
            self.return_from_mock(0 if self.missing else WATCH)
        elif pc == WATCH:
            assert self.reg(0) == self.variant, ('wrong PB passed to spectator guard', self.variant, self.reg(0))
            self.callbacks.append(self.variant)
            self.return_from_mock(int(self.watching))
        elif pc in {MAIN + address for address in patch.LOCAL_GETTERS}:
            assert self.reg(0) == ENV, 'bridge did not restore JNI environment before native fallback'
            self.getters.append(pc)
            # Execute the original AOT getter; do not replace its result.

    def run(self, v, entry, local, turn, watching):
        self.variant, self.watching = v, watching
        self.put(HEAP + 0x1000 + v * 0x800 + 0xd0, '<B', turn)
        self.put(HEAP + 0x1400 + v * 0x800 + 0x266, '<B', local)
        sp = STACK + 0xf000
        self.u.reg_write(UC_ARM64_REG_SP, sp)
        self.u.reg_write(UC_ARM64_REG_LR, STOP)
        self.u.reg_write(UC_ARM64_REG_X0, ENV)
        preserved = {i: 0xa000000000 + i for i in range(19, 30)}
        for i, value in preserved.items():
            self.u.reg_write(UC_ARM64_REG_X0 + i, value)
        before_getters, before_callbacks = len(self.getters), len(self.callbacks)
        self.u.emu_start(MAIN + entry, STOP + 4, count=10000)
        assert self.u.reg_read(UC_ARM64_REG_PC) == STOP, 'predicate did not return'
        assert self.u.reg_read(UC_ARM64_REG_SP) == sp, 'stack pointer changed'
        assert self.u.reg_read(UC_ARM64_REG_LR) == STOP, 'return address changed'
        for i, value in preserved.items():
            assert self.reg(i) == value, ('callee-saved register changed', i)
        result = self.u.reg_read(UC_ARM64_REG_W0)
        return result, len(self.getters) - before_getters, len(self.callbacks) - before_callbacks


baseline, fixed, unavailable = Engine(original), Engine(modified), Engine(modified, missing=True)
cases = 0
for v in range(6):
    for entry in (patch.PREDICATES[v], patch.WRAPPERS[v]):
        # Snapshot startup assigns a valid local slot to a watched actor. The
        # original compares only indices and consequently grants a local turn.
        assert baseline.run(v, entry, 0, 0, True) == (1, 1, 0)
        for local, turn in ((0, 0), (1, 1), (7, 7), (99, 99), (0, 1), (7, 0)):
            assert fixed.run(v, entry, local, turn, True) == (0, 0, 1), 'spectator retained participant turn'
            # Leaving watch restores actual native participant behavior,
            # including both local and remote turns, without rewriting slots.
            assert fixed.run(v, entry, local, turn, False) == (int(local == turn), 1, 1)
            # An unavailable symbol must safely execute the original predicate.
            assert unavailable.run(v, entry, local, turn, True) == (int(local == turn), 1, 0)
            cases += 3
assert baseline.lookups == 0
assert fixed.lookups == 1, ('successful dlsym should share its cached function across PBs', fixed.lookups)
assert unavailable.lookups >= 6
print(f'PASS original/patched ARM64 local-turn predicates: six PBs, wrapper and direct entry, {cases} state cases; spectator false, participant restoration, real AOT getters, missing-symbol fallback, JNI environment, SP/LR and x19-x29 preserved')
