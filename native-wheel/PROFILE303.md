Build303 — battlefield equipment information

The battlefield profile used a separate450-pixel painter and a plain cloud
background. The outside game uses the active PB's GameCanvas dimensions.
Read those dimensions for all lobby tabs and use the same native bitmap
assets, equipment frame, slot layout, upgrade effects, palm/airship background
and34-pixel footer. Equipment details use a native-size bottom sheet with
keyboard/touch scrolling. Long totals remain available in the Chỉ số sheet.

Each profile open/refresh sends the existing CT46 op2 request with the selected
rank and account ID. Seal that ID/rank/name/serial into the pending request;
reject mismatched or late replies, including a refresh received after closing
the profile. Render the character, worn-item IDs, upgrades, optional costume,
totals, per-item flat/percent bonuses, expiry, empty sockets and gems from that
one response. A character may have changed since the board was loaded, so
the fresh profile avatar takes precedence over the board avatar. The logged-in
hero, local inventory and local GEM1/GEM2 cache are not profile data sources.
Absent equipment-detail metadata stays explicitly unavailable.

The five physical slots and optional costume retain their original protocol
indices when empty slots are skipped or the lower four-item grid is paged.
Menu contains Chi tiết, Chỉ số and Cập nhật; all actions are read-only.

Inventory icons must come from the exact per-profile server PNG or the live
server catalog keyed by character, physical slot and item ID. Avatar clothing
sprites are not inventory icons and are never used as a profile fallback.
Catalog frames use their actual square width rather than a hardcoded16px
crop. Browser checks compare two distinct server PNGs and catalog frames
with the same+16 upgrade, including missing catalog entries and decode timing.
All fixture screenshots visibly identify themselves as synthetic test data.
Numeric stat cells scroll only when their full text exceeds the cell width.

Opening a profile automatically writes Documents/Profile303-diagnostic.json.
It records the selected account ID, PB, hero, stats, six physical item IDs,
upgrades, detail arrays, icon source codes, PNG lengths and catalog frame
dimensions. A whitelist excludes names, item text, image bytes and packet
payloads. History is bounded to32 samples and writes use a serial file worker.
The real Simulator panel test verifies the exported file and history bound.

The native ranking submenu and web event screen now say Sự kiện. On the game
thread, use JNI to replace only String[][][7][3] in the six audited ranking
classes after their normal initialization. Native event action/index, other
labels and the executable remain unchanged. The compiled ARM64 test checks
the class addresses against the original AOT instructions and exercises all
six PBs, array reconstruction, bounds, repeat ticks and JNI references.

Validation: protocol/model + browser fixtures cover top1 Magenta with diamond3
and+16, a different logged-in hero, changed hero since ranking, a second account,
fresh changed gear on reopening, all six slot/detail/gem associations, full HP,
wrong/late response rejection, empty slots and missing extensions. Browser
screenshots exercise native432 geometry and multiple viewport sizes. Compiled
ARM64 checks read the exact dimensions and account ABI independently for six
PBs, including a missing local player. Existing crafting302 and watch299 checks
remain in CI. Fixtures are synthetic; live-account/iPhone confirmation is still
required. The client displays the fresh existing server reply as returned;
server code, endpoint literals and protocol formats are unchanged.

Package303 retains exactly the13 audited301 native request edits over293.
The native executable is byte-identical to302; changes are in the framework,
viewer files and bundle version. New viewer/profile.js is included explicitly
in the framework manifest and package checks.
