Build304: native profile icons and inventory session order

The supplied Profile303 diagnostic reproduced the deployed failure: all six
ICON lengths were zero, the extra atlas was absent, but the selected hero6,
IDs56/54/55/57/58/2046, upgrades and complete item bonuses were present. The
APK video displays those same totals and bonuses with native item images.
303's strict image selection incorrectly depended on an optional image reply
and omitted the native catalog/cache that the outside equipment screen uses.

For a missing image, the web profile now queues a bounded, read-only request
containing its selected account/serial/hero and six physical item IDs. The
original game worker resolves the exact hero/slot/template in its own PB's
loaded equipment catalog, reads j5_.i (+0x88), and uses the same icon cache/key
as j5_.paint. Costume images come from the separate native ID/image registry.
No logged-in inventory, own hero, guessed tier/upgrade mapping or avatar crop
supplies a profile icon. Export the existing Image pixels as a PNG, then reject
late/wrong-account/wrong-hero/wrong-item replies in the web view. Details and
totals stay those of the one targeted CT46 reply; no stats are synthesized.

The native image bridge is included in Notes77.m, retaining its game-thread
exception guard. Image dimensions and arrays are bounded; JNI image/array
references are released even on a guarded failure. Profile304-diagnostic.json
adds native icon IDs/status and source5 (native server catalog image). Image
bytes, text, credentials and packets are still excluded from the report.

The inventory previously discarded its item history on close and treated a
replacement C6 as a new chest. Bulk gem results can recreate C6, so a new
level8 gem was grouped into the middle instead of being promoted. Preserve
numeric item order for the socket/login session, across C6 replacement,
recipe children and close/reopen. Only a changed/disconnected session resets
that history and restores equipment/gem/stone grouping. Newly received or
increased stacks move first after the result dialog closes; select the new
first item so a residual level7 stack cannot scroll it out of view. Recipe
callback selection remains stable. Server vectors, handles and quantities
remain untouched; a closed display releases all JNI roots.

Validation uses the captured numeric303 state without any ICON/atlas, and
checks six exact native-cache image replies, costume/details, full totals,
stale replies and decoded pixel equality in the browser. Fixture screenshots
explicitly label test icons. ARM64 checks audit six catalog and service
addresses against original AOT instructions, run the original Image.l pixel
reader, and cover 2000 level7 gems ->311 level8 with four level7 remaining,
C6 recreation, dialogs, reopen, gains while away, and login grouping. The
real Simulator web handler/game tick/PNG encoder/WK decoder also compares
actual pixels. Existing watch recovery and crafting regressions remain.

Package304 retains the13 audited301 executable edits; its native executable
is byte-identical to303. Source293, endpoint checks and the eight framework
manifest entries are unchanged. Live-device confirmation is still distinct
from these fixtures and Simulator tests.
