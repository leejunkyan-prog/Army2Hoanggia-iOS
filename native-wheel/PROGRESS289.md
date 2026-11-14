# Build289: spectator synchronization and crafting re-entry

Base branch: qa/ios-288-new-server, commit 60af118f7dda81ac42c9d99ad6f9f4bf19ec4842.
Use only the exact user-supplied Build288 NewSv IPA (SHA256
b6547d99ac52841cc80cd77e77d69218dc1940e01dea27f970925a9dd69678c3).

The original 0.4-second render timer could mark an incomplete spectator
snapshot as live. Later native HP/status replay would then wait for battle
animations instead of remaining in synchronization mode. Completion now
requires SP7, or a complete live movement/shot packet for legacy servers.
The native adapter enforces this barrier even if completion is attempted
prematurely. Finish resets snapshot flash and the authoritative clock.
The matching SP6 end token schedules native scene restoration; cleanup also
closes battle dialogs so the previous area list is visible again. The
existing menu, camera, direction, F1/F2 and PB routes remain in use. The angle
label no longer has an additional cyan rectangle absent from the APK video.

Crafting: native C6.n can rebind the chest vector while dialogs are up.
The displayed selection index then selects a different source item. A new
regression executed on the supplied B288 framework selected recipe 120 but
sent recipe 121. Rebind the private display before deferring a dialog frame,
and resolve the visible selection even for an action between render ticks.
The server vector order and item handles are never rewritten.

Build: bash native-wheel/build_289.sh on macOS, or the Build289 Actions
workflow. Package: python native-wheel/package_289.py Build288.ipa
framework-289.zip Build289-unsigned.ipa. The packager requires byte-for-byte
identity of the entire original executable. Endpoint is preserved:
180.93.195.228:19149, list http://180.93.195.228:18080/server.txt, all 6 PBs.

Tests execute the compiled iPhone ARM64 code in Unicorn with mocked JNI,
transport, allocations, and UI primitives, including original AOT recipe
callbacks. They do not represent a physical iPhone or live server test.
The IPA requires owner signing before installation. Device verification of
watch entry, live shots/HP/clock, end-to-area and repeated craft/detail is
still required; automated success alone does not establish visual parity
or that the reported phone freezes are fully resolved.
