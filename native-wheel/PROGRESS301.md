# Build301: retain the classified recipe through the native request

The user's Craft300 log contains seven accepted Detail classifications on PB1.
The selected126 quantity changes2 to1 after successful crafting. The three
subsequent failed Detail taps still classify126, quantity1, with the source and
selected handles agreeing. The native game update continues throughout, with
no modal or input blocker left over. This rules out missing recipe recognition
and a stopped game loop for that capture.300's Notes-only packet observation
does not establish whether ordinary command-18 requests/replies were delivered.

The original native callback selects the inventory three times: before the
consumable check, before AGRecipeDetail, and again after showing its wait UI,
immediately before serializing the request. The game's normal inventory update
can rebind screen+0x70 to the server vector in that interval. The selected index
still belongs to the private ordered display. A post-craft source/display order
difference therefore changes the final request without changing the recorded
classifier result. Prior tests rebound the vector before the callback, missing
this later scheduling boundary.

A compiled300 control using the real ARM64 callback reproduces72 wrong sends
across six PBs:126/127/128 are recognized, then the late lookup sends material7
after a source rebind during the native wait/dialog boundary. Pre-craft calls
work in the same fixture. No live request is sent by this test.

301 adds AGRecipeDetailObject, retaining the boolean AGRecipeDetail ABI for old
callers. The new entry resolves/classifies once and returns the exact resolved
object. Six audited callback shims store it in an unused local stack slot.
The native send path reads that held object instead of doing the third v()
lookup. The service, operation1, amount255, request count and protocol bytes
remain unchanged. The local object root survives rendering/server updates and
expires with the callback; no persistent per-item cache is added.

Only13 disjoint byte ranges of the exact293 executable change: one export-name
slot, six existing96-byte shims and six32-byte late-lookup sequences. The patch
validates the source SHA, every displaced instruction and all untouched bytes.
There are no new segments/imports, no runtime code writes and no changes to
server literals or initializers. Packaging exports a byte-level patch manifest
and checks the actual dyld export trie before pairing the framework and native
callback. Old boolean callers, equipment detail and missing-export legacy
description handling remain supported.

Craft301-diagnostic.json retains300's fields. Receive observation moves from
the selectively invoked Notes hook to the common AGCorpseReceive entry, before
dispatch/consumption, so normal crafting responses can be observed as well.
Payloads/account text are still omitted.299's confirmed spectator recovery is
retained.

Validation covers72 real after-craft callback interleavings across all six PBs,
late source rebinding, refreshed handles, rebinding before classification,
exact object identity in the callback root, IDs126/127/128 (including signed
byte transport), exactly one correct request, gear/legacy fallback, temporary
JNI roots and caller register/stack preservation. Existing craft, inventory,
spectator and endpoint checks also run. Server transport/JVM collection/text
boundaries are fixtures; physical iPhone validation remains pending.
