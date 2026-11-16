# Build309 — server marquee and ranked bosses

Base: Build308 `b50d6b428324a0986a3bd732986369143c11e6f0`.
References: user-supplied `gs5kl1.apk`, the missing-marquee recordings, and
`Screenrecorder-2026-11-16-19-40-05-726.mp4` showing the Tinh anh boss.
Read-only server references: `Notice31`, `Notices68` and `BossRanks79` in
`lykien0311-jpg/army2-hoanggia-server`. No server code changes are required.

## Marquee

Handle cmd -116 (`writeUTF(text), writeInt(speed), writeInt(seconds)`) on the
existing receive bridge without advancing the Java stream. Decode modified
UTF-8 to UTF-16, including Vietnamese, NUL and surrogate pairs. Empty packets
clear the announcement; a new notice replaces the old one. Match APK
`Marquee31`: right-to-left at one pixel per native canvas counter tick,
including counter wrap, one complete pass, and optional expiry. The APK reads
but ignores the speed integer, so this client does the same.

Paint with the same native `fb1` font at y=1 after the original canvas painter,
above inventory/menu clips. Save and restore camera translation, clipping and
color. The existing spectator render-clock callback still runs exactly once.
An absent HUD export falls back to the original render bridge.

## Tinh anh / Thủ lĩnh / Cao thủ

Handle only -121 subtypes 2 (slot, rank, UTF name, maximum HP) and 4 (reset).
Other -121 market operations continue unchanged. Like `RankClient122`, map
rank 1/2/3 to the three titles, apply the server's maximum HP, and draw current
HP, the rank-colored bar/frame, extra rank3 markers, tinted body, and animated
POW flames. Use the original actor's position, images, mirroring and animation.
Derive label placement from the rendered sprite bounds; preserve the original
white pixels and the APK luminance/highlight formula. Effects use the original
41×188 POW texture and the APK's four nearest-neighbor frames and timing.

The paint context is thread-local and restored after nested or failed paints.
Only that actor's default boss HP painter is suppressed. Image hooks otherwise
forward the original image, geometry and packed integer arguments. Cache
converted textures with bounded roots/pixels; retry failed conversions and
avoid blocking a reentrant renderer. Clear rank state on server reset, match
start, login/connection change, arena change or actor-slot replacement. Dead
bosses receive no rank overlay. Do not change HP, damage or physics; maximum
HP comes exclusively from the authoritative rank packet, as in the APK.

## Verification

- Differential test against the actual APK Java color/pixel methods, plus
  modified-UTF and server packet boundary tests.
- Compiled ARM64 tests across six PBs: marquee lifecycle, canvas counter wrap,
  graphics state, all three ranks, current/max HP, actual image/HP hook routing,
  death/reset/login/connection isolation and single render-clock ownership.
- Static bridge execution checks full argument preservation, callee-saved
  registers, stack alignment, packed drawRegion coordinates, original HP
  fallback and absent-export behavior. Packaging checks every changed native
  byte against disjoint, audited edits in existing executable padding.
- Existing inventory308, Chicky307, event, recipe, spectator, Simulator and web
  regressions remain in the Build309 workflow.

The generated IPA is unsigned. OS/JVM/graphics primitives are mocked by ARM64
tests; physical iPhone and live-account verification are not claimed.
