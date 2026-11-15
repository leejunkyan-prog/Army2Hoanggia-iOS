"""Reproduce a stale loading modal stopping the original battle update route.

Execute the original Build290 GameCanvas branch and native screen methods,
then the compiled spectator adapter over all six PBs. Resource creation and
JNI remain fixtures. The regression proves update routing, not device visuals.
"""
import base64
from hashlib import sha256
from pathlib import Path
import sys

import test_native_watch as t
from unicorn.arm64_const import UC_ARM64_REG_PC, UC_ARM64_REG_SP, UC_ARM64_REG_LR, UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X19, UC_ARM64_REG_X21

root = Path(__file__).resolve().parent
native = Path(sys.argv[2]) if len(sys.argv) > 2 else root / 'build/base290-native'
raw = native.read_bytes()
assert sha256(raw).hexdigest() == '889afdfc35bdbb47f7f3abcd2327c97f631702158d2670f6c79c37b6d2485a06'


def original(address, size):
    at = t.MAIN + address
    t.u.mem_write(at, raw[address:address + size])
    t.nativeRanges.append((at, at + size))
    t.u.ctl_remove_cache(at, at + size)


# Real Arena.show -> Screen.show -> GameCanvas.current setter. Their only
# external operation clears input arrays; it does not affect the modal slot.
for address, size in ((0x542b58, 0x20), (0x5ad9e8, 0x38), (0x50b910, 0x40),
                      (0x5112d8, 0x24)):
    original(address, size)
t.extraNative[t.MAIN + 0x5acdf8] = lambda: t.ret()


def initialize():
    t.put(t.reg(1) + 9, '<B', 2)
    t.ret()


t.extraNative[t.MAIN + 0x12e7330] = initialize
t.put(t.MAIN + t.canvas[0] + 9, '<B', 2)


def native_show(arena, back):
    t.u.reg_write(UC_ARM64_REG_SP, t.STACK + 0x30000)
    t.u.reg_write(UC_ARM64_REG_LR, t.STOP)
    for register, value in ((UC_ARM64_REG_X0, t.ENV), (UC_ARM64_REG_X1, arena),
                            (UC_ARM64_REG_X2, back)):
        t.u.reg_write(register, value)
    t.u.emu_start(t.MAIN + 0x542b58, t.STOP + 4, count=10000)
    assert t.u.reg_read(UC_ARM64_REG_PC) == t.STOP


route = []


def dialog_tick():
    route.append('dialog.update')
    t.ret()


def finish_modal():
    route.append('skip scene.update')
    t.u.emu_stop()


def enter_scene():
    route.append('scene.update branch')
    t.u.emu_stop()


t.extraNative[t.MAIN + 0x5db71c] = dialog_tick
t.extraNative[t.MAIN + 0x511394] = finish_modal
t.extraNative[t.MAIN + 0x5112fc] = enter_scene


def frame_route():
    route.clear()
    t.u.reg_write(UC_ARM64_REG_SP, t.STACK + 0x30000)
    t.u.reg_write(UC_ARM64_REG_X19, t.ENV)
    t.u.reg_write(UC_ARM64_REG_X21, t.MAIN + t.canvas[0])
    t.u.emu_start(t.MAIN + 0x5112d8, t.STOP + 4, count=100)
    return route[:]


a, canvas, _, _, back, _, _ = t.objects[0]
modal, arena = t.alloc(0x80), t.alloc(0x100)
t.put(canvas + 0x108, '<Q', modal)
native_show(arena, back)
assert t.get(canvas + 0xb8, '<Q') == arena
assert t.get(canvas + 0x108, '<Q') == modal, 'Baseline changed: original show already clears modal'
assert frame_route() == ['dialog.update', 'skip scene.update'], 'Baseline must reproduce the frozen battle route'
t.put(canvas + 0xb8, '<Q', back)
t.put(canvas + 0x108, '<Q', 0)

for variant in range(6):
    a, canvas, _, _, back, _, _ = t.objects[variant]
    for attempt in range(2):
        t.stillWatching = True
        pending = t.alloc(0x80)
        for command, encoded in t.trace:
            packet = base64.b64decode(encoded)
            if command == -102 and packet[3] in (3, 4, 5, 7):
                if packet[3] == 5:
                    # cmd8 can show/rebind loading state after the initial
                    # wait-token dismissal. It is deliberately a new dialog.
                    t.put(canvas + 0x108, '<Q', pending)
                assert t.packet(variant, packet) == 1
                if packet[3] in (5, 7):
                    assert t.get(canvas + 0xb8, '<Q') == t.get(a + 0xe8, '<Q')
                    assert t.get(canvas + 0x108, '<Q') == 0, 'Snapshot leaves the native modal blocking updates'
                    if variant == 0:
                        assert frame_route() == ['scene.update branch']
            elif command in (8, 24, 22):
                t.observe(variant, command, packet)
        # Opening an auxiliary dialog during a live match remains supported.
        unrelated = t.alloc(0x80)
        t.put(canvas + 0x108, '<Q', unrelated)
        t.call('_AGNativeWatchTick', t.ENV, variant)
        assert t.get(canvas + 0x108, '<Q') == unrelated
        t.call('_AGNativeWatchEnd', t.ENV, variant)

    # Canceled/no-longer-owned snapshot cannot clear another screen's modal.
    t.stillWatching = True
    for command, encoded in t.trace:
        packet = base64.b64decode(encoded)
        if command == -102 and packet[3] in (3, 4):
            assert t.packet(variant, packet) == 1
        elif command == 8:
            t.observe(variant, command, packet)
    destination, unrelated = t.alloc(0x100), t.alloc(0x80)
    t.put(canvas + 0xb8, '<Q', destination)
    t.put(canvas + 0x108, '<Q', unrelated)
    t.stillWatching = False
    assert t.packet(variant, next(p for p in t.sp if p[3] == 5)) == 0
    assert t.get(canvas + 0xb8, '<Q') == destination
    assert t.get(canvas + 0x108, '<Q') == unrelated
    t.call('_AGNativeWatchEnd', t.ENV, variant)

print('PASS original GameCanvas modal freeze reproduced; compiled snapshot clears stale modal, resumes scene-update route, six PBs/re-entry; live and canceled unrelated dialogs preserved')
