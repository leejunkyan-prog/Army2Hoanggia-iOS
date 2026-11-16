# Build306 APK parity

The supplied APK uses one scrolling ranking list, native-sized cards and a pinned self card. This build follows its 50-pixel row geometry at native width432, gap row, rank badges, profile card centering and idle poses4/5. Appearance slot icons are resolved separately from the stat-bearing worn items.

The body image has ten frames, confirmed by executing the original AOT Outfit.draw. The former divide-by5 portrait reader was corrected to divide-by10.

Two icon defects were found with the supplied equipment export: the web catalog parser skipped49 bytes where the original format contains59 bytes; and native profile extraction consulted a generic downloaded-image cache instead of the equipment screen's complete icon sheet at pool+0xb0. The fixture includes the unchanged public export with1556 templates, actual icon PNG and ten projectile sheets.

Costume shot styles follow all375 records in ShotFx122.DATA in the supplied APK. Optional live FX49 metadata overrides these records. Existing projectile pixels remain intact. Missing mapped rows use the exact APK luminance/palette calculation. The native actor's visual style word at+0x104 is updated before native shot handling; removing the costume restores the original weapon style. No damage, trajectory, server endpoint or packet body is rewritten. Costume306-diagnostic.json records numeric style/binding events.

The gem regression exercises2595 level7 ->347 level8 ->43 level9 with residual stacks, newest-first selection, reopen preservation, and a fresh-login gear/gem/stone grouping. The original six C6.n updates and grid callbacks are also exercised.

Source APK SHA256: 823586872a0076b6aad4b8f5ca4c4faa3a72e8c0d597d8a444251538fc9efd9d
Source costume ZIP SHA256: 6319c40a334e2e398945fa47671a258ac394c3eb1fe7fc1713f98c8a9c845ee3
Fixture equip306.bin SHA256: 74a5cd2faa46bf7f9877fde523dd3ccac711412141f8197f268cb8de5d4ef30c

Checks use compiled iPhone ARM64 code, actual supplied PNG/cache bytes, browser integration and iOS Simulator regressions. Physical-device validation is not claimed. Test images and fixture identities are not live account screenshots.
