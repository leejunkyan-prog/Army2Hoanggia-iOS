"""Decode a room0 reply with the original iPhone controller and area screen.

Socket input primitives, strings/vector allocation and rendering resources are
boundaries. Row decoding, full list installation, scroll bounds and destination
activation execute the unchanged ARM64 game instructions. No live login occurs.
"""
import struct
import test_spectator_live291 as s

t = s.t
vectors, strings = {}, {}
area, area_class, menu = (t.alloc(0x100) for _ in range(3))
t.put(t.MAIN + 0x2089f70, '<Q', area_class)
t.put(t.MAIN + 0x2089f70 + 9, '<B', 2)
for start, end in ((0x573060, 0x5730ac), (0x573a60, 0x573b4c),
                   (0x573b9c, 0x573c90), (0x5ad9e8, 0x5ada20)):
    t.nativeRanges.append((t.MAIN + start, t.MAIN + end))
    # The snapshot fixture has already visited the base activator as a
    # mocked boundary. Drop that translation after loading the real AOT.
    t.u.ctl_remove_cache(t.MAIN + start, t.MAIN + end)

def vector_new():
    p = t.alloc(0x40)
    vectors[p] = []
    t.ret(p)

def vector_add():
    vectors[t.reg(1)].append(t.reg(2))
    t.put(t.reg(1) + 0x24, '<i', len(vectors[t.reg(1)]))
    t.ret()

def utf():
    length = struct.unpack_from('>H', s.data, s.cursor)[0]
    s.cursor += 2
    value = s.data[s.cursor:s.cursor + length].decode('utf-8')
    s.cursor += length
    p = t.alloc(0x20)
    strings[p] = value
    t.ret(p)

def canvas_set():
    t.put(s.c + 0xb8, '<Q', t.reg(1))
    t.ret()

t.extraNative.update({
    t.MAIN + 0x555538: lambda: t.ret(s.back),
    t.MAIN + 0xa6c7c8: lambda: t.ret(len(s.data) - s.cursor),
    t.MAIN + 0x54af2c: lambda: t.ret(t.alloc(0x40)),
    t.MAIN + 0x54af78: lambda: t.ret(),
    t.MAIN + 0xa642f0: utf,
    t.MAIN + 0xbe3f1c: vector_new,
    t.MAIN + 0xbe6b7c: lambda: t.ret(),
    t.MAIN + 0x1dfcac: vector_add,
    t.MAIN + 0x1dfce8: lambda: t.ret(len(vectors[t.reg(1)])),
    t.MAIN + 0x572d48: lambda: t.ret(area),
    t.MAIN + 0x54d738: lambda: t.ret(menu),
    t.MAIN + 0x50bff0: lambda: t.ret(0),
    t.MAIN + 0x5ac398: lambda: t.ret(20),
    t.MAIN + 0x50bec0: lambda: t.ret(450),
    t.MAIN + 0x5acdf8: lambda: t.ret(),
    t.MAIN + 0x50b910: canvas_set,
    t.MAIN + 0x50c0e0: lambda: t.ret(37),
    t.MAIN + 0x50bd58: lambda: t.ret(650),
    t.MAIN + 0x53edc4: lambda: t.ret(0),
    t.MAIN + 0x538448: lambda: t.ret(t.alloc(0x30)),
})

previous_vector = None
for count in (14, 67, 130, 1, 14):
    # A reply is room ID followed by every area, without an artificial count
    # limit. A second reply must replace the previous list, never append to it.
    payload = bytes([0])
    for i in range(count):
        name = ('Khu vuc ' + str(i)).encode('utf-8')
        payload += struct.pack('>BbbBIBH', i, i % 8, 8, i % 3,
                               1000 + i, 0, len(name)) + name + bytes([i % 2])
    t.put(s.c + 0xb8, '<Q', s.back)
    t.put(area_class + 0xd0, '<i', 9)
    s.dispatch(7, payload)
    assert t.get(s.c + 0xb8, '<Q') == area, 'Reply did not activate native area list'
    assert t.get(area + 0x4d, '<B') == 0, 'Reply selected a different room'
    installed = t.get(area_class + 0xc0, '<Q')
    assert installed != previous_vector and len(vectors[installed]) == count
    assert t.get(area_class + 0xd0, '<i') == 0, 'Area selection was not reset'
    assert t.get(area_class + 0xe8, '<B') == 1
    for i, row in enumerate(vectors[installed]):
        assert t.get(row + 0x1d, '<B') == i
        assert t.get(row + 0x1e, '<b') == i % 8
        assert t.get(row + 0x1f, '<b') == 8
        assert t.get(row + 0x1c, '<B') == i % 3
        assert t.get(row + 0x18, '<i') == 1000 + i
        assert strings[t.get(row + 0x10, '<Q')] == 'Khu vuc ' + str(i)
        assert t.get(row + 0x20, '<b') == i % 2
    previous_vector = installed

print('PASS unchanged iPhone ARM64 cmd7 room0 reply: complete 14/67/130/1-area lists, '
      'all row fields, replacement replies, selection reset and native screen activation')

