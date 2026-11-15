"""Exercise end-of-watch using the actual six AOT virtual screen activators.

An area screen override represents its refresh request. The real base Screen
activator cannot reach that override; merely changing canvas.current is not
enough. Network transport and area reply data remain boundary fixtures.
"""
import base64
from pathlib import Path
import test_native_watch as t

source = Path(__file__).parent / 'build/base293-native'
raw = source.read_bytes()
base_methods = (0x5ad9e8, 0x69625c, 0x77af20, 0x85fbe4, 0x9448a8, 0xa2956c)
requests = [0] * 6

def branch(at):
    word = int.from_bytes(raw[at:at + 4], 'little')
    assert word & 0xfc000000 == 0x94000000
    delta = word & 0x3ffffff
    return at + 4 * (delta - (1 << 26) if delta & (1 << 25) else delta)

for v, original in enumerate(base_methods):
    virtual = original + 0x38
    assert raw[virtual + 0x14:virtual + 0x24] == bytes.fromhex(
        '280040f9081540f9023140f940001fd6'), 'Unexpected native virtual a()V dispatch'
    for at, size in ((original, 0x5c), (branch(original + 0x28), 0x40)):
        t.u.mem_write(t.MAIN + at, raw[at:at + size])
        t.nativeRanges.append((t.MAIN + at, t.MAIN + at + size))
        t.u.ctl_remove_cache(t.MAIN + at, t.MAIN + at + size)
    t.extraNative[t.MAIN + branch(original + 0x1c)] = lambda: t.ret()
    t.put(t.MAIN + t.canvas[v] + 9, '<B', 2)

for v in range(6):
    a, canvas, world, camera, back, old_map, old_tiles = t.objects[v]
    roster_class = t.get(t.MAIN + t.actors[v], '<Q')
    original_roster = t.get(roster_class + 0xa0, '<Q')
    original_local = t.get(a + 0x266, '<B')
    original_turn = t.get(roster_class + 0xd0, '<B')
    klass, vtable = t.alloc(0x80), t.alloc(0x100)
    t.put(back, '<Q', klass)
    t.put(klass + 0x28, '<Q', vtable)
    activation = t.FAKE + 0x38000 + v * 0x100
    t.put(vtable + 0x60, '<Q', activation)
    fresh_roster, loading = t.alloc(0x30), t.alloc(0x30)

    def refresh(v=v, a=a, canvas=canvas, world=world, back=back,
                old_map=old_map, old_tiles=old_tiles, roster_class=roster_class,
                original_roster=original_roster, original_local=original_local,
                original_turn=original_turn, fresh_roster=fresh_roster, loading=loading):
        assert (t.reg(0), t.reg(1)) == (t.ENV, back)
        assert t.get(a + 0xc8, '<Q') == old_map, 'Area activated before restoring its world'
        assert t.get(world + 0xb8, '<Q') == old_tiles
        assert t.get(a + 0x266, '<B') == original_local
        assert t.get(roster_class + 0xa0, '<Q') == original_roster
        assert t.get(roster_class + 0xd0, '<B') == original_turn
        assert not t.get(canvas + 0x108, '<Q'), 'Battle dialog survived into destination activation'
        requests[v] += 1
        t.put(canvas + 0xb8, '<Q', back)
        # The destination owns these values now. Old watch state must never
        # overwrite an immediate reply or hide its new loading dialog.
        t.put(roster_class + 0xa0, '<Q', fresh_roster)
        t.put(canvas + 0x108, '<Q', loading)
        t.ret()

    t.extraNative[activation] = refresh
    t.stillWatching = True
    for cmd, encoded in t.trace:
        packet = base64.b64decode(encoded)
        if cmd == -102 and packet[3] in (3, 4, 5, 7):
            assert t.packet(v, packet) == 1
        elif cmd == 8:
            t.observe(v, cmd, packet)
    assert t.call('_AGNativeWatchRunning', v)
    t.put(canvas + 0x108, '<Q', t.alloc(0x20))
    t.stillWatching = False
    assert t.call('_AGNativeWatchTryEnd', t.ENV, v) == 1
    assert requests[v] == 1, 'End restored only the base screen; area refresh override was skipped'
    assert t.get(canvas + 0xb8, '<Q') == back
    assert t.get(roster_class + 0xa0, '<Q') == fresh_roster, 'Cleanup overwrote the area refresh state'
    assert t.get(canvas + 0x108, '<Q') == loading, 'Cleanup hid the destination loading dialog'
    assert not t.call('_AGNativeWatchRunning', v)
    assert t.call('_AGNativeWatchTryEnd', t.ENV, v) == 1
    assert requests[v] == 1, 'Completed cleanup reactivated the screen twice'
    # Finish the mocked reply, then enter/exit a second watch from the area.
    t.put(canvas + 0x108, '<Q', 0)
    t.put(roster_class + 0xa0, '<Q', original_roster)
    t.stillWatching = True
    for cmd, encoded in t.trace:
        packet = base64.b64decode(encoded)
        if cmd == -102 and packet[3] in (3, 4, 5, 7): assert t.packet(v, packet) == 1
        elif cmd == 8: t.observe(v, cmd, packet)
    t.stillWatching = False
    assert t.call('_AGNativeWatchTryEnd', t.ENV, v) == 1
    assert requests[v] == 2

assert all(n == 0 for n in t.pins.values())
print('PASS actual AOT return dispatch: six PBs, destination refresh override, world restored before activation, destination state/dialog retained, cleanup idempotence and repeated watch/end')
