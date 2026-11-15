Build302 — recipe screen owner after crafting

Craft301 device evidence: five accepted Detail actions, each followed by a
command -18 reply (1060 bytes for125; 1054 bytes for126). The four126 replies
arrived within124–177ms but left the chest open. Game/input callbacks remained
alive. This is beyond the request-selection race covered by301.

The original ARM64 cmd101 constructs a fresh C6 and assigns its singleton.
The craft-result callback retrieves the recipe screen's parent at +0x50 and
activates that retained C6. The -18 parser installs the options, then opens
the formula only if the current screen equals C6's singleton (or the shop).
After this sequence those identities differ. Build301 reproduces24/24 missed
formula activations with complete1/3-option replies in the new AOT control.

Before a nonzero -18 recipe reply reaches the original dispatcher, bind C6's
singleton to the attached same-PB chest (or its audited recipe parent). No
render tick, repeated request or automatic craft is involved. Skip craft
result0, malformed/truncated replies and unrelated current screens. Also
preserve the private chest session through the actual recipe parent+0x50;
the previous+0x10 assumption referred to callback wrappers/commands.

Craft302-diagnostic.json adds singleton/root agreement, recipe option count,
selected option and parent agreement. Event kind3 records agreement before
and after receive-side binding and the native guard result. Existing bounded
history, thread evidence and heartbeat diagnostics remain available. Packet
bodies, item text, equipment UIDs and account identifiers are not exported.

Validation: unchanged native101/result/-18 paths in Unicorn,24 consecutive
reopens, same/different recipes,1/3 options and exactly one formula activation;
six-PB compiled bridge checks for real child layout, retained pins, refreshed
handles, source/selection/cursor preservation and invalid/late/foreign-PB
exclusions; Simulator JSON export plus existing watch299 and inventory tests.
Allocation, stream/string/vector primitives and text resources are boundaries
in the AOT test; this is not a physical iPhone or live account test.

Packaging retains the13 audited301 request edits over the exact293 input.
Build302 adds no further native executable edits. Server endpoints, packet
formats and crafting operations are unchanged.
