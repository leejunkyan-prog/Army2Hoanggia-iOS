"""Guard the original six PlayerManager.isMyTurn predicates during spectating.

The supplied APK has !SpectatorClient53.active && current == local. The AOT
iOS methods only compare the two slots. Keep the real local slot in bounds:
changing it to -1 breaks other native methods which index the actor array.

Each shim resolves the framework's exported AGViewerStillWatching once. A
missing framework/symbol takes the original path. Outside a watch session,
the displaced prologue and the entire original predicate execute unchanged.
Only verified zero padding in the existing RX __AGSCENE segment is used.
There are no new load commands, segments, imports, or server modifications.
"""
from hashlib import sha256
from struct import pack, unpack_from

BASE_NATIVE = '889afdfc35bdbb47f7f3abcd2327c97f631702158d2670f6c79c37b6d2485a06'
PREDICATES = (0x51336c, 0x60101c, 0x6e5ce0, 0x7ca9a4, 0x8af668, 0x99432c)
WRAPPERS = (0x51293c, 0x60068c, 0x6e5350, 0x7ca014, 0x8aecd8, 0x99399c)
PLAYER_CLASSES = (0x207f060, 0x20aec70, 0x20dc970, 0x210a660, 0x2138350, 0x2166040)
LOCAL_GETTERS = (0x53f3b4, 0x62b6ac, 0x710370, 0x7f5034, 0x8d9cf8, 0x9be9bc)
ORIGINAL = (
    'f44fbea9fd7b01a9fd43009168db009008810191080140f9134143390bb000947f02206be0179f1afd7b41a9f44fc2a8c0035fd6',
    'f44fbea9fd7b01a9fd43009168d500b008c13191080140f9134143399da900947f02206be0179f1afd7b41a9f44fc2a8c0035fd6',
    'f44fbea9fd7b01a9fd430091a8cf00f008c12591080140f9134143399da900947f02206be0179f1afd7b41a9f44fc2a8c0035fd6',
    'f44fbea9fd7b01a9fd43009108ca009008811991080140f9134143399da900947f02206be0179f1afd7b41a9f44fc2a8c0035fd6',
    'f44fbea9fd7b01a9fd43009148c400b008410d91080140f9134143399da900947f02206be0179f1afd7b41a9f44fc2a8c0035fd6',
    'f44fbea9fd7b01a9fd43009188be00d008010191080140f9134143399da900947f02206be0179f1afd7b41a9f44fc2a8c0035fd6',
)
CAVE = 0x250a000
CAVE_FILE = 0x24ca000
CACHE = 0x2500780
CACHE_FILE = 0x24c0780
NAME = CAVE + 0x700
DYLSYM = 0x131cf70
SYMBOL = b'AGViewerStillWatching\0'


def _branch(pc, target, link=False):
    delta = target - pc
    assert delta % 4 == 0 and -(1 << 27) <= delta < 1 << 27
    return (0x94000000 if link else 0x14000000) | ((delta // 4) & 0x3ffffff)


def _adr(pc, target, register):
    delta = target - pc
    assert -(1 << 20) <= delta < 1 << 20
    return 0x10000000 | ((delta & 3) << 29) | (((delta >> 2) & 0x7ffff) << 5) | register


def _adrp(pc, target, register):
    delta = ((target & ~4095) - (pc & ~4095)) >> 12
    assert -(1 << 20) <= delta < 1 << 20
    return 0x90000000 | ((delta & 3) << 29) | (((delta >> 2) & 0x7ffff) << 5) | register


def shim(variant):
    address = CAVE + variant * 0x100
    words = []
    labels, fixups = {}, []

    def emit(word):
        words.append(word)

    def pc():
        return address + 4 * len(words)

    def cb(base, register, label):
        fixups.append((len(words), base | register, label))
        emit(0)

    emit(0xa9be7bfd)                         # stp x29,x30,[sp,#-32]!
    emit(0xf9000be0)                         # str x0,[sp,#16] (Env)
    emit(_adrp(pc(), CACHE, 9))
    emit(0xf9400000 | ((CACHE & 4095) // 8 << 10) | (9 << 5) | 16)
    cb(0xb5000000, 16, 'resolved')           # cbnz x16,resolved
    emit(0x92800020)                         # mov x0,#-2 (RTLD_DEFAULT)
    emit(_adr(pc(), NAME, 1))
    emit(_branch(pc(), DYLSYM, True))
    emit(0xaa0003f0)                         # mov x16,x0
    emit(_adrp(pc(), CACHE, 9))
    emit(0xf9000000 | ((CACHE & 4095) // 8 << 10) | (9 << 5) | 16)
    labels['resolved'] = pc()
    cb(0xb4000000, 16, 'original')           # cbz x16,original
    emit(0x52800000 | variant << 5)          # mov w0,#variant
    emit(0xd63f0200)                         # blr x16
    cb(0x35000000, 0, 'watching')            # cbnz w0,watching
    labels['original'] = pc()
    emit(0xf9400be0)                         # ldr x0,[sp,#16]
    emit(0xa8c27bfd)                         # ldp x29,x30,[sp],#32
    emit(0xa9be4ff4)                         # displaced original prologue
    emit(_branch(pc(), PREDICATES[variant] + 4))
    labels['watching'] = pc()
    emit(0x52800000)                         # mov w0,#0
    emit(0xa8c27bfd)
    emit(0xd65f03c0)                         # ret
    for index, base, label in fixups:
        delta = labels[label] - (address + index * 4)
        assert delta % 4 == 0 and -(1 << 20) <= delta < 1 << 20
        words[index] = base | (((delta // 4) & 0x7ffff) << 5)
    return b''.join(pack('<I', word) for word in words)


def framework_exports(framework, symbol):
    """Read the dyld export trie; a private symbol-table name is insufficient."""
    assert framework[:8] == bytes.fromhex('cffaedfe0c000001')
    pos, export = 32, None
    for _ in range(unpack_from('<I', framework, 16)[0]):
        command, size = unpack_from('<II', framework, pos)
        assert size >= 8 and pos + size <= len(framework)
        if command in (0x22, 0x80000022):
            export = unpack_from('<II', framework, pos + 40)
        elif command == 0x80000033:
            export = unpack_from('<II', framework, pos + 8)
        pos += size
    if not export or not export[1]:
        return False
    offset, size = export
    assert offset + size <= len(framework)
    trie = framework[offset:offset + size]

    def uleb(at):
        number, shift = 0, 0
        while True:
            assert at < len(trie) and shift < 64
            byte = trie[at]
            at += 1
            number |= (byte & 127) << shift
            if not byte & 128:
                return number, at
            shift += 7

    pending, seen = [(0, b'')], set()
    while pending:
        at, prefix = pending.pop()
        assert at not in seen and at < len(trie)
        seen.add(at)
        terminal, cursor = uleb(at)
        if terminal and prefix == symbol:
            return True
        cursor += terminal
        assert cursor < len(trie)
        children = trie[cursor]
        cursor += 1
        for _ in range(children):
            end = trie.index(0, cursor)
            label = trie[cursor:end]
            child, cursor = uleb(end + 1)
            if symbol.startswith(prefix + label):
                pending.append((child, prefix + label))
    return False


def patch_native(original, framework):
    assert sha256(original).hexdigest() == BASE_NATIVE, 'Require exact supplied Build290 native executable'
    assert framework[:8] == bytes.fromhex('cffaedfe0c000001')
    assert framework_exports(framework, b'_AGViewerStillWatching'), 'Framework must export spectator-state guard'
    assert original[CACHE_FILE:CACHE_FILE + 8] == bytes(8)
    assert original[CAVE_FILE:CAVE_FILE + 0x800] == bytes(0x800)
    result, edits = bytearray(original), []

    def change(offset, raw, purpose):
        before = bytes(result[offset:offset + len(raw)])
        result[offset:offset + len(raw)] = raw
        edits.append({'offset': offset, 'before': before.hex(), 'after': raw.hex(),
                      'file_offset': hex(offset), 'size': len(raw), 'purpose': purpose,
                      'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(raw).hexdigest()})

    for variant, entry in enumerate(PREDICATES):
        assert original[entry:entry + 0x34] == bytes.fromhex(ORIGINAL[variant])
        change(CAVE_FILE + variant * 0x100, shim(variant), f'PB{variant + 1} spectator-aware turn shim')
        change(entry, pack('<I', _branch(entry, CAVE + variant * 0x100)),
               f'PB{variant + 1} original isMyTurn entry')
    change(CAVE_FILE + 0x700, SYMBOL, 'Framework spectator-state export name')
    assert len(result) == len(original)
    return bytes(result), edits
