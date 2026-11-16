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
several unrelated Vietnamese server announcements across six PBs. Existing
protocol/pixel differential checks and native, Simulator and interface
regressions are retained. Packaging reuses the audited Build309 native patch
sites; the production changes are confined to the framework and build number.

The generated IPA is unsigned. ARM64 emulation substitutes OS/JVM/graphics
boundaries and does not claim physical-iPhone or live-server testing.
