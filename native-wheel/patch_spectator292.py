"""Compose the verified spectator turn fix with native scene fault tracing.

The diagnostic hook preserves the original Throwable.printStackTrace call.
It neither skips a native exception nor fabricates battle progress. The
framework decides whether the exception belongs to an active watch session.
Only exact Build290 instructions and pre-existing zero padding are patched.
"""
from hashlib import sha256
from struct import pack, unpack_from
import patch_spectator291 as prior

CATCHES = (0x546690, 0x6322f8, 0x716fbc, 0x7fbc80, 0x8e0944, 0x9c5608)
PRINT = 0xaccdec
CAVE = 0x250a800
CAVE_FILE = 0x24ca800
CACHE = 0x2500790
CACHE_FILE = 0x24c0790
NAME = CAVE + 0x700
DYLSYM = 0x131cf70
SYMBOL = b'AGNativeWatchTraceException\0'


def shim(variant):
    address = CAVE + variant * 0x100
    words, labels, fixups = [], {}, []
    def pc(): return address + 4 * len(words)
    def emit(word): words.append(word)
    def cb(opcode, register, target):
        fixups.append((len(words), opcode | register, target)); emit(0)
    emit(0xa9bd7bfd)                         # stp x29,x30,[sp,#-48]!
    emit(0xa90107e0)                         # stp x0,x1,[sp,#16]
    emit(prior._adrp(pc(), CACHE, 9))
    emit(0xf9400000 | ((CACHE & 4095) // 8 << 10) | (9 << 5) | 16)
    cb(0xb5000000, 16, 'resolved')
    emit(0x92800020)                         # mov x0,#-2
    emit(prior._adr(pc(), NAME, 1))
    emit(prior._branch(pc(), DYLSYM, True))
    emit(0xaa0003f0)                         # mov x16,x0
    emit(prior._adrp(pc(), CACHE, 9))
    emit(0xf9000000 | ((CACHE & 4095) // 8 << 10) | (9 << 5) | 16)
    labels['resolved'] = pc()
    cb(0xb4000000, 16, 'print')
    emit(0xa94107e0)                         # ldp x0,x1,[sp,#16]
    emit(0x52800002 | variant << 5)          # mov w2,#variant
    emit(0xd63f0200)                         # blr x16
    labels['print'] = pc()
    emit(0xa94107e0)
    emit(prior._branch(pc(), PRINT, True))
    emit(0xa8c37bfd)                         # ldp x29,x30,[sp],#48
    emit(0xd65f03c0)
    for index, opcode, label in fixups:
        delta = labels[label] - (address + index * 4)
        assert delta % 4 == 0 and -(1 << 20) <= delta < 1 << 20
        words[index] = opcode | (((delta // 4) & 0x7ffff) << 5)
    return b''.join(pack('<I', word) for word in words)


def patch_native(original, framework):
    assert prior.framework_exports(framework, b'_AGNativeWatchTraceException'), 'Framework must export native watch fault tracing'
    patched, edits = prior.patch_native(original, framework)
    assert original[CACHE_FILE:CACHE_FILE + 8] == bytes(8)
    assert original[CAVE_FILE:CAVE_FILE + 0x800] == bytes(0x800)
    result = bytearray(patched)
    def change(offset, after, purpose):
        before = bytes(result[offset:offset + len(after)])
        result[offset:offset + len(after)] = after
        edits.append({'offset': offset, 'before': before.hex(), 'after': after.hex(),
                      'file_offset': hex(offset), 'size': len(after), 'purpose': purpose,
                      'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(after).hexdigest()})
    for variant, at in enumerate(CATCHES):
        expected = pack('<I', prior._branch(at, PRINT, True))
        assert original[at:at + 4] == expected
        # Bind the call to the native catch block, not another print call.
        assert original[at - 8:at] == bytes.fromhex('a10352f8e00313aa')
        change(CAVE_FILE + variant * 0x100, shim(variant), f'PB{variant + 1} native scene exception tracing bridge')
        change(at, pack('<I', prior._branch(at, CAVE + variant * 0x100, True)),
               f'PB{variant + 1} Arena.update catch printStackTrace call')
    change(CAVE_FILE + 0x700, SYMBOL, 'Native scene fault tracing export name')
    assert len(result) == len(original)
    return bytes(result), edits
