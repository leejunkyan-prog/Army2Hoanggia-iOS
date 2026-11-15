# Build294: reactivate the destination after watching

Base: the user-supplied Build293 IPA, SHA2563d307b2951c6a8540052d4d259d9307b56bcf9103cd5989e39bbf3301e136378.
Its entire native executable remains byte-identical (SHA25693e9c074725e3e5d087192cf29b498df8f71bbf542e9d09d7f20c4bc17a6f6c0).
Server remains180.93.120.67:19149. The293 render-clock/live-playback bridges and crafting fixes are preserved.

The supplied video shows working projectile/HP playback and an empty area
screen on return. The supplied trace was saved while still watching, so it
does not independently establish the state of the cleanup after leaving.

The adapter called the nonvirtual base Screen.a()V directly. On all six PBs,
that routine only clears keys and sets GameCanvas.current. It bypasses the
destination override, unlike the reference's back.a_() invocation. The original
virtual a()V bridge is38hex bytes after that base method and dispatches through
the real class vtable at+60hex.294 calls that bridge, restoring watch-owned
globals before destination activation. It does not undo a destination's new
roster state or clear its new loading dialog afterward. A failed restoration
keeps the cleanup roots/state for a later retry rather than freeing a visible
arena's resources. The final294 diagnostic is also saved during overlay close,
with end_received and cleanup_pending flags.

Regression test_watch_exit294.py executes the actual six native virtual
bridges and screen setters; a destination override models room initialization
and its transport boundary. Baseline293 fails because the override is never
called.294 must activate it once, preserve destination changes/dialogs,
complete cleanup idempotently, and allow a second watch/end cycle with
balanced JNI roots. Existing live movement/shot, render-clock/bridge/projectile,
snapshot, camera and crafting tests remain required.

The workflow reconstructs the exact supplied293 from the pinned293 framework
and stored290 inputs and checks its full IPA hash before packaging294. No
change to the supplied293 executable is permitted by package_294.py.
The unsigned output still requires owner signing and an iPhone test; offline
regressions do not establish live server or device parity.
