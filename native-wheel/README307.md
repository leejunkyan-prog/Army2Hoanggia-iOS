# Build307 — bulk gems, Chicky and event ranking

Base: `fc68afe8e858c97b62bba507c71ca4a926260d67` (Build306). Packaging keeps the
same hash-checked Build293 native input and its 13 existing recipe patch sites.
Server endpoints, packet formats, crafting probabilities and quantities are
unchanged. The new artifact is `Army2HoangGia-2.4.1-Build307-GemsChickyEvent-unsigned.ipa`.

## Gem inventory

The original bulk-combine callback sets `C6+0xd4` when a selected item is a
consumable. It leaves that flag set after sending. Build306 mistook it for menu
visibility and therefore kept restoring the old private display after cmd27
had inserted the newly received gem into the canonical inventory.

Build307 defers ordering on the real menu's `+0x2c` visibility byte, the actual
modal pointer and quantity-selection mode. It never clears or repurposes the
native `containsConsumables` flag. After the result closes, the received gem
is first and selected. A subsequent 8→9 upgrade promotes level9; reopening the
chest keeps session order, and a new connection restores gear/gem/stone groups.

`test_inventory_receive307.py` executes all six unchanged native bulk callbacks
and reproduces the persistent flag. PB1 additionally runs the original cmd27
parser, native gem insertion/stack merge and material consumption. It checks
the 2000→311 result, 7→8→9, an existing destination stack, visible-menu deferral,
reopening and login grouping. The uploaded Build306 fails this test at the
first new-gem visibility assertion. Stream/JVM/transport operations are mocked;
this test does not craft on an account.

## Chicky

The original secondary projectile constructor leaves its style at0. New Chicky
shots with that value now capture the firing manager's retained costume style.
Normal chicken bodies use the exact selected row of the costume sheet; POW
chickens, eggs and their rotated frames use the same APK palette. Capturing the
style once prevents a later shot from recoloring a projectile already in flight.
A failed image conversion retries; sprites commit all frames together, avoiding
partial/double tinting. Only image references change; physics and damage remain
native.

`test_chicky307.py` executes the native secondary constructor, then the compiled
render binding for six PBs, both normal/POW modes, inherited/explicit styles,
rotated eggs, image-conversion retries and root cleanup. PNG/UIKit conversion
is a boundary. The existing exhaustive APK palette/PNG tests are retained.

## Event menu

The title changes from mixed-case `Sự kiện` to `SỰ KIỆN`. The native title atlas
contains uppercase Vietnamese only, so the previous value could render only
`S`. The test checks the JNI string and that every character exists in the
actual title atlas; the row index and native action remain unchanged.

## Validation limits

The Build307 workflow compiles the iPhone ARM64 framework, runs the new
regressions and existing inventory/recipe/spectator/profile tests, checks web UI
integration, and packages an unsigned IPA with SHA-256 and endpoint reports.
A passing emulation/Simulator/CI build is not a physical-device or live-server
result. Device acceptance remains: bulk 7→8 and 8→9, logout/login grouping,
Chicky normal/POW and eggs for the selected costumes, and the event label/action.
