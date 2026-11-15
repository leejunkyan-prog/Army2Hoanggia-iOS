# Build297: measure native area rendering and input after watch exit

The supplied Watch296-diagnostic.json reports a manual exit on PB1:
room0_request_sent=true, one attempt, room0_reply_received=true,
room0_reply_rows=130 and room0_return_complete=true. cleanup_pending,
watch_active, still_watching and native_running are all false/zero. Snapshot
rendering completed201 steps without a recorded failure or expired wait.
This rules out the missing-request/unfinished-watch explanations for this
capture. The existing logical completion check does not establish visible
rows or functioning native input. No exact display/input failure is claimed.

297 is a diagnostic build over296's behavior. It adds read-only scalar samples
on the existing attached native callbacks: current screen kind, actual area
vector length and first/last IDs, native list visibility and transition flags,
scroll/selection, modal/flash state, pressed/released key counts, pointer flags,
canvas dimensions and update sequence. Separate game/render heartbeat ages
show a stopped callback even when no further native sample can complete.
The native input hook records which existing guard consumed a soft key.
Typed characters, packet bodies, tickets, credentials and account data are
excluded. Samples never call native screen activation or mutate game state.

An independent UIKit timer retains a three-minute timestamped history and
writes Documents/Watch297-diagnostic.json once per second and on leaving the
app. It also records visible window/root/child class names to identify an
unremoved overlay. Watch297-watch.json retains the296 watch-state summary,
with actual mount/keypad status recorded after unmounting. UIKit/file workers
only read copied scalars, never Java objects or another thread's Env.

The original ARM64 reply regression now includes all130 areas (including
IDs128/129). Compiled read-only diagnostics are checked across all six PBs,
including hidden rows, modal/input state, heartbeat metadata and unchanged
native memory. Simulator checks validate JSON/history export, character
filtering and unchanged key-window ownership. Existing return, rendering,
snapshot and crafting checks remain. These checks do not establish a
physical-device fix; the measured failure must be reproduced on the iPhone.

Reproduce the freeze, wait10seconds, press F2 once, wait5seconds, then send
Files > On My iPhone > Army2Hoanggia > Watch297-diagnostic.json. Keep the app
running while retrieving the file. A second capture after automatic finish
can be collected in the same way. Output IPA is unsigned; server and native
game executable remain byte-identical to296.
