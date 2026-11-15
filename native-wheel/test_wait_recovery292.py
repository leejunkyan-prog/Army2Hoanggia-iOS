"""Execute compiled spectator waits and original AOT movement completion.

The supplied APK's Wait106 releases a stalled completion flag after 30 seconds.
Test all four iOS flags over all six variants, cancellation and a replaced actor.
Then interleave the real native base-actor update with the compiled wait: the
native 200-frame completion must release it before the deadline. JNI/resources
and the timed monitor boundary are fixtures, not a physical-device claim.
"""
import base64
from pathlib import Path
import sys

import test_native_watch as t
from unicorn.arm64_const import *

PROJECTILES = (0x208c790, 0x20bb5b0, 0x20e92a0, 0x2116f90, 0x2144c80, 0x2172970)


def start_watch(v):
    t.stillWatching = True
    for command, encoded in t.trace:
        packet = base64.b64decode(encoded)
        if command == -102 and packet[3] in (3, 4, 5, 7):
            assert t.packet(v, packet) == 1
        elif command == 8:
            t.observe(v, command, packet)
    assert t.call('_AGNativeWatchRunning', v)


def trace(v):
    output = t.alloc(576)
    assert t.call('_AGNativeWatchTraceCopy', v, output) == 1
    return (t.get(output + 24, '<Q'), t.get(output + 32, '<Q'),
            t.get(output + 48, '<i'), t.get(output + 52, '<i'),
            t.get(output + 56, '<i'))


for v in range(6):
    start_watch(v)
    arena, canvas, _, _, _, _, _ = t.objects[v]
    players = t.get(t.MAIN + t.actors[v], '<Q')
    roster = t.get(players + 0xa0, '<Q')
    player = t.get(roster + 0x18, '<Q')
    projectile = t.alloc(0x200)
    t.put(t.MAIN + PROJECTILES[v], '<Q', projectile)
    flags = (projectile + 0x118, canvas + 0x13c, player + 0x167, player + 0x14e)
    for kind, flag in enumerate(flags):
        t.call('_AGNativeWatchTraceReset', v)
        t.put(flag, '<B', 1)
        t.put(flag + 1, '<B', 0x5a)
        original_time, waits = t.now, []

        def stalled_wait():
            assert t.reg(2) == 16
            assert t.get(flag, '<B') == 1
            waits.append(t.now)
            t.now += 29 if len(waits) == 1 else 2
            t.ret()

        t.extraNative[t.MAIN + 0xaaa730] = stalled_wait
        t.call('_AGBattleAwait', t.ENV, canvas, v, kind, 0)
        assert len(waits) == 2 and t.now - original_time == 31
        assert t.get(flag, '<B') == 0, 'APK expiry did not release completion flag'
        assert t.get(flag + 1, '<B') == 0x5a, 'Expiry changed adjacent battle state'
        assert trace(v) == (1, 1, kind, 0, 3)

        # Cancellation cannot clear another session's completion flag, even
        # when the old deadline has elapsed while the monitor was waiting.
        t.call('_AGNativeWatchTraceReset', v)
        t.put(flag, '<B', 1)

        def canceled_wait():
            t.now += 31
            t.stillWatching = False
            t.ret()

        t.extraNative[t.MAIN + 0xaaa730] = canceled_wait
        t.call('_AGBattleAwait', t.ENV, canvas, v, kind, 0)
        assert t.get(flag, '<B') == 1
        assert trace(v) == (1, 0, kind, 0, 2)
        t.put(flag, '<B', 0)
        t.stillWatching = True

    # A roster replacement represents a new actor identity. Never clear the
    # replacement actor's flag merely because the prior wait expired.
    t.call('_AGNativeWatchTraceReset', v)
    t.put(player + 0x167, '<B', 1)
    replacement = t.alloc(0x200)
    t.put(replacement + 0x167, '<B', 1)

    def replaced_wait():
        t.now += 31
        t.put(roster + 0x18, '<Q', replacement)
        t.ret()

    t.extraNative[t.MAIN + 0xaaa730] = replaced_wait
    t.call('_AGBattleAwait', t.ENV, canvas, v, 2, 0)
    assert t.get(player + 0x167, '<B') == 1
    assert t.get(replacement + 0x167, '<B') == 1
    assert trace(v) == (1, 0, 2, 0, 2)
    t.put(roster + 0x18, '<Q', player)
    t.call('_AGNativeWatchEnd', t.ENV, v)

# Execute original native movement completion, not a mock which clears the
# watched flag. The existing original-dispatch regression supplies its AOT
# image, actor and exact stream/resource boundaries.
import test_spectator_live291 as live

for first, last in ((0x598be0, 0x5999dc), (0x59bde0, 0x59bf40)):
    t.nativeRanges.append((t.MAIN + first, t.MAIN + last))
player = live.actor0
# Angle math and limits do not decide movement completion in this blocked-walk
# fixture; the native 200-frame fallback must settle the authoritative target.
t.extraNative[t.MAIN + 0x5124a4] = lambda: t.ret(0)
t.extraNative[t.MAIN + 0x57fab0] = lambda: t.ret(0)
t.extraNative[t.MAIN + 0x59f770] = lambda: t.ret(0)
t.extraNative[t.MAIN + 0x59f3dc] = lambda: t.ret(0)
limits = t.alloc(0x14 + 40)
t.put(limits + 0x10, '<i', 20)
t.put(live.playerglobals + 0xa8, '<Q', limits)
t.put(live.playerglobals + 0xa0, '<Q', limits)
notifications = []
t.extraNative[t.MAIN + 0x51803c] = lambda: t.ret(live.monitor)
t.extraNative[t.MAIN + 0xaaa524] = lambda: (notifications.append(t.reg(1)), t.ret())


def update_actor():
    # The render and receiver threads have distinct stacks. Sharing their
    # stack memory here corrupts the suspended C wait's context variables.
    t.u.reg_write(UC_ARM64_REG_SP, t.STACK + 0x20000)
    t.u.reg_write(UC_ARM64_REG_LR, t.STOP)
    t.u.reg_write(UC_ARM64_REG_X0, t.ENV)
    t.u.reg_write(UC_ARM64_REG_X1, player)
    t.u.emu_start(t.MAIN + 0x598be0, t.STOP + 4, count=100000)
    assert t.u.reg_read(UC_ARM64_REG_PC) == t.STOP


frame_flags = []


def timed_frame():
    assert t.reg(2) == 16
    saved = t.u.context_save()
    # The timed monitor wait releases the receiver's monitor so the render
    # thread can run original movement completion and its native notification.
    t.put(live.monitor + 8, '<I', 0)
    update_actor()
    frame_flags.append(t.get(player + 0x167, '<B'))
    t.now += .016
    t.u.context_restore(saved)
    t.ret()


t.extraNative[t.MAIN + 0xaaa730] = timed_frame
t.put(player + 0x114, '<ii', 500, 380)
t.put(player + 0xb8, '<ii', 600, 380)
t.put(player + 0x12c, '<ii', 600, 380)
t.put(player + 0x16f, '<B', 1)
t.put(player + 0x167, '<B', 1)
t.put(player + 0xb0, '<i', 0)
t.call('_AGNativeWatchTraceReset', 0)
t.u.reg_write(UC_ARM64_REG_SP, t.STACK + 0x30000)
t.u.reg_write(UC_ARM64_REG_LR, t.STOP)
for i, value in enumerate((t.ENV, live.monitor, 0, 2, 0)):
    t.u.reg_write(UC_ARM64_REG_X0 + i, value)
# Nested Unicorn frame execution stops at its own boundary. Resume the
# receiver context there, preserving its actual compiled wait-loop state.
pc = t.symbols['_AGBattleAwait']
for _ in range(300):
    t.u.emu_start(pc, t.STOP + 4, count=1000000)
    pc = t.u.reg_read(UC_ARM64_REG_PC)
    if pc == t.STOP:
        break
else:
    raise AssertionError('Native actor completion did not release compiled wait')
assert len(frame_flags) == 200 and frame_flags[-1] == 0
assert t.get(player + 0x114, '<i') == 600
assert len(notifications) == 1 and trace(0) == (1, 0, 2, 0, 2)
print('PASS compiled spectator APK wait parity: all four flags, six PBs, 30s expiry, cancellation/identity safety; actual AOT movement completion releases compiled wait at 200 native updates before expiry')
