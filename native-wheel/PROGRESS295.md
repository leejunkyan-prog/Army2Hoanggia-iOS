# Build295: request the full room0 list after leaving a live watch

Both new videos show a blank room0 after manual leave or automatic completion.
Build294 reactivated the saved native screen but did not send the normal
joinRoom(0) service request. Its virtual-activation fixture modeled a refresh
which the actual area screen does not request on its own. That test did not
establish a complete return flow.

The JAR service and unchanged iPhone controller agree on command7, one-byte
room ID.295 sends command7 with byte0 after native cleanup. Manual leave sends
SP2 first; server SP6 completion sends only the room request. The normal native
controller handles the response and installs every area supplied by the server.
There is no fabricated local list or fixed area count. A failed native send is
retried at one-second intervals on the same connection. Old sessions, declined
offers, unsent accepts, PB switches and battlefield returns keep their existing
destinations. Held viewer keys are cleared on finish. The existing overlay
close removes its controller and releases native keypad ownership.

test_watch_return295.m imports the production Spectator.m and runs its actual
receive, tick, accept, cancel and close methods in iOS Simulator, with actual
WatchSurface/WKWebView mounting. Battle execution and socket transport are
explicit boundaries. The same test must fail on Build294 specifically because
manual leave omits the room request.295 must pass for all six PBs, including
cleanup ordering, manual/automatic exits, duplicates, retry, session changes,
alternative destinations, overlay removal and key/touch passthrough.

test_room_reply295.py executes the unchanged ARM64 controller, area list setter
and area activation using synthetic complete replies of14,67,1and14 areas.
It verifies every decoded row field, replacement lists, selected room0, reset
selection and activation of the real native area screen. JNI allocation,
stream primitives and rendering resources are explicit test boundaries.
Existing live movement, projectile, render-clock, camera, snapshot and crafting
regressions remain required. These checks do not replace a real server/iPhone
test; no physical-device result is claimed.

Packaging starts from the exact supplied293 IPA (SHA256
3d307b2951c6a8540052d4d259d9307b56bcf9103cd5989e39bbf3301e136378).
The entire game executable remains byte-identical (SHA256
93e9c074725e3e5d087192cf29b498df8f71bbf542e9d09d7f20c4bc17a6f6c0),
including server180.93.120.67:19149 and the working293 live-render bridges.
Only framework code and bundle version change. Output remains unsigned.
