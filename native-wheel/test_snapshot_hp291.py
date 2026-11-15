"""Execute snapshot HP replay in the compiled iPhone ARM64 framework.

Snapshot command51 is authoritative state. It must not invoke the live damage
flash or wait for animations before SP7. Native death is mocked at its AOT
entry; all packet validation and HP writes execute in the compiled adapter.
This is an offline regression, not a physical-device or live-server test.
"""
import base64
import struct

import test_native_watch as t


DEATH = (0x5978c0, 0x6807ec, 0x7654b0, 0x84a174, 0x92ee38, 0xa13afc)
deaths = []


def replay(v, cmd, payload):
    at = t.alloc(max(1, len(payload)))
    if payload:
        t.u.mem_write(at, payload)
    return t.call('_AGNativeWatchReplay', t.ENV, v, cmd, at, len(payload))


def hp(slot, value, flags=0):
    return bytes([slot]) + struct.pack('>qB', value, flags)


def death_callback(v):
    def die():
        assert t.reg(0) == t.ENV
        player = t.reg(1)
        assert player and t.get(player + 0x68, '<q') <= 0
        deaths.append((v, player))
        t.put(player + 0x16f, '<B', 5)
        t.ret()
    return die


for v, at in enumerate(DEATH):
    t.extraNative[t.MAIN + at] = death_callback(v)

assert '_AGNativeWatchReplay' in t.symbols
for v in range(6):
    a, canvas, g, cam, back, old_map, old_tiles = t.objects[v]
    t.stillWatching = True
    t.put(canvas + 0x13c, '<B', 0)
    assert replay(v, 51, hp(0, 123)) == 0, 'Inactive replay consumed HP'

    for cmd, encoded in t.trace:
        payload = base64.b64decode(encoded)
        if cmd == -102 and payload[3] in (3, 4, 5):
            assert t.packet(v, payload) == 1
        elif cmd == 8:
            t.observe(v, cmd, payload)
    assert not t.call('_AGNativeWatchRunning', v)
    players = t.get(t.MAIN + t.actors[v], '<Q')
    roster = t.get(players + 0xa0, '<Q')
    player = t.get(roster + 0x18, '<Q')
    other = t.get(roster + 0x20, '<Q')
    assert player and other
    assert t.get(roster + 0x28, '<Q') == 0

    t.put(player + 0x70, '<q', 24680)
    t.put(player + 0x152, '<B', 0x5a)
    t.put(canvas + 0x13c, '<B', 1)
    clock = t.get(a + 0x110, '<Q')
    clock_before = bytes(t.u.mem_read(clock, 0x30))
    waits_before = t.waitCalls
    death_before = len(deaths)

    assert replay(v, 51, hp(0, 321, 1)) == 1
    assert t.get(player + 0x68, '<q') == 321
    assert replay(v, 51, hp(1, 765)) == 1
    assert t.get(other + 0x68, '<q') == 765
    # Preserve full signed Java-long precision; this is not a short damage delta.
    assert replay(v, 51, hp(0, 0x123456789abcdef)) == 1
    assert t.get(player + 0x68, '<q') == 0x123456789abcdef
    assert len(deaths) == death_before

    for cmd, payload in ((50, hp(0, 7)), (51, b''), (51, hp(0, 7)[:-1]),
                         (51, hp(0, 7) + b'\0'), (51, hp(2, 7)),
                         (51, hp(126, 7)), (51, hp(255, 7))):
        before = bytes(t.u.mem_read(player, 0x200))
        assert replay(v, cmd, payload) == 0, (v, cmd, payload.hex())
        assert bytes(t.u.mem_read(player, 0x200)) == before

    assert replay(v, 51, hp(0, 0)) == 1
    assert deaths[-1] == (v, player) and len(deaths) == death_before + 1
    assert t.get(player + 0x68, '<q') == 0
    assert t.get(player + 0x16f, '<B') == 5
    assert replay(v, 51, hp(1, -7)) == 1
    assert deaths[-1] == (v, other) and len(deaths) == death_before + 2
    assert t.get(other + 0x68, '<q') == -7
    assert t.get(player + 0x70, '<q') == 24680, 'Snapshot overwrote max HP'
    assert t.get(player + 0x152, '<B') == 0x5a, 'Snapshot started damage animation'
    assert t.get(canvas + 0x13c, '<B') == 1, 'Snapshot changed flash state'
    assert bytes(t.u.mem_read(clock, 0x30)) == clock_before, 'Snapshot changed clock'
    assert t.waitCalls == waits_before, 'Snapshot waited for live animation'

    assert t.packet(v, next(p for p in t.sp if p[3] == 7)) == 1
    assert t.call('_AGNativeWatchRunning', v)
    before = bytes(t.u.mem_read(player, 0x200))
    assert replay(v, 51, hp(0, 999)) == 0, 'Live HP bypassed original game handler'
    assert bytes(t.u.mem_read(player, 0x200)) == before
    assert len(deaths) == death_before + 2

    t.stillWatching = False
    t.call('_AGNativeWatchEnd', t.ENV, v)
    assert t.get(canvas + 0xb8, '<Q') == back
    assert replay(v, 51, hp(0, 777)) == 0, 'Restored session consumed stale HP'
    assert bytes(t.u.mem_read(player, 0x200)) == before

assert len(deaths) == 12
assert all(n == 0 for n in t.pins.values())
print('PASS compiled snapshot HP: six PBs, full signed HP state, native death, '
      'no damage flash/wait/clock mutation, malformed/missing actors pass, '
      'live and canceled sessions use original handlers')
