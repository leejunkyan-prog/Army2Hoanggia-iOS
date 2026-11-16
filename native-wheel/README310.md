# Build310 — native announcement font and ranked-boss identity

Base: Build309 `d599395d4d357be9ac5959220c30d44a6875ee77`.
References: the supplied APK, the white outlined server announcement screenshot,
and the latest IPA/APK boss comparison recordings.

All server announcements use the native `fb1.png` bitmap font (15 pixels,
white with black outline), with the existing scroll/lifetime/position rules.
The previous PB1 getter selected the 21-pixel title atlas; the other five
entries also required auditing against their own AOT font class. The new
six-entry table points to each real `+0xc0` field getter. No notice text is
hardcoded or filtered by content.

Rank rendering resolves the actor by object identity in the active arena's
roster, exactly as APK `NativeDragon105.slot` does. The actor metadata byte at
`+0x16b` is not a roster index. A rank packet can therefore update maximum HP
while the former painter never finds that actor's rank. Preserve the existing
three rank titles, tinted native body, animated flames and custom HP display.

The new integration fixture runs the original font class initializer and
glyph-width/glyph-paint routines, using the real IPA font textures. It checks
several unrelated Vietnamese server announcements across six PBs. It also runs
the original arena roster loop, production Aura shim, virtual dispatch and NPC
body painter for all three ranks, with metadata values 0, 3 and 255 while the
boss remains in roster slot8. It verifies the title/current-max HP glyphs,
body tint, POW flames, suppressed default HP bar and restored graphics state.
The previous Build309 binary fails both new appearance/identity checks.
Existing
protocol/pixel differential checks and native, Simulator and interface
regressions are retained. Packaging reuses the audited Build309 native patch
sites; the production changes are confined to the framework and build number.

## Local validation and current build blocker

The unchanged HUD.c compiles to an iOS12 ARM64 object locally. A separate
C-only Darwin ARM64 library (Zig0.14.1, macOS12 target) was loaded beside the
previous framework through `test_hud_cross310.py`. The new integration fixture,
existing HUD lifecycle test and static bridge checks all pass. This fallback
is a code/ABI check; it is not an Xcode-built framework or installable IPA.
The APK Java/protocol differential test also passes 24,000+ pixel cases.

Reproduce the C-only fallback with the prior AGWheel binary and the Python
dependencies used by the normal workflow:

```sh
zig cc -target aarch64-macos.12.0 -std=c11 -O1 -dynamiclib -nostdlib \
  -Wl,-undefined,dynamic_lookup native-wheel/HUD.c -o HUD310.dylib
python native-wheel/test_hud_cross310.py PREVIOUS_AGWHEEL HUD310.dylib test_hud_integration310
python native-wheel/test_hud_cross310.py PREVIOUS_AGWHEEL HUD310.dylib test_hud309
python native-wheel/test_hud_cross310.py PREVIOUS_AGWHEEL HUD310.dylib test_hud_bridges309
```

GitHub currently rejects job startup with: "The job was not started because
recent account payments have failed or your spending limit needs to be
increased." Xcode compilation, full Simulator/interface regressions and a
new IPA artifact remain pending the account's Billing & plans resolution.
The PR remains a draft until those checks pass. Physical-iPhone or live-server
testing is not claimed. The planned IPA is unsigned.
