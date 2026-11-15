# Build300: diagnose craft success followed by failed Detail re-entry

The user confirms Build299 spectator viewing/return now works. In the supplied
11.7-second video, a diamond-glasses recipe opens normally, crafting reports
success, and the user returns to the chest. The cursor and menus keep working.
Subsequent Detail selections close the menu without reopening the recipe child.
This is not evidence that the whole app or canvas update thread has stopped.

The existing ARM64 recipe tests call the callback and verify the correct
request across handle replacement, source/display rebinding and repeated
crafting. They do not reproduce the device's complete menu/controller/server
sequence.300 does not claim the physical-device craft issue is fixed.

300 adds read-only observations to the unchanged299 behavior:

- Existing attached game/render callbacks sample chest/child ownership,
  source/private display counts, selected index, selected versus cached item,
  source-handle equality, remaining quantity, menu/amount/modal state and
  snapshot stability. No server Vector monitor is acquired.
- The actual AGRecipeDetail path records its original and resolved item
  metadata, handle replacement, the classifier result and the exact reason:
  known recipe ID, missing/short/mismatched description, matched prefix,
  missing JNI string, non-consumable or guarded native exception.
- Existing receive callbacks record command numbers and remaining lengths
  while the inventory is active or shortly after Detail. Packet bodies and
  stream positions are not changed. These events precede native dispatch;
  classifier acceptance does not establish successful packet delivery/craft.
- One bounded128-event ring and the existing timestamped three-minute scalar
  history are written automatically to Documents/Craft300-diagnostic.json,
  including on leaving the app to retrieve the file. No F2 action is needed.
- Only public consumable/template IDs and quantities are included. Equipment
  server UIDs, item names/descriptions, account balances, chat and packet body
  text are excluded. UIKit/file workers only consume copied scalar data.
- The original executable and server endpoint remain byte-identical.299's
  exited-canvas recovery and all existing gameplay paths remain enabled.

Validation checks real compiled inventory/classifier behavior across all six
PBs, post-craft handle/quantity replacement, displayed/source index drift,
rejection reasons, native menu/modal fields, sampler and stream immutability,
equipment UID omission and bounded receive events. A Simulator test verifies
automatic JSON/history export even after the callbacks stop, without window
changes or typed/payload text logging. Existing inventory, recipe and spectator
tests remain required in the workflow.

Device reproduction: craft successfully, return to the same chest, attempt
Detail twice while it fails, wait5-10seconds, then send
Files > On My iPhone > Army2Hoanggia > Craft300-diagnostic.json.
