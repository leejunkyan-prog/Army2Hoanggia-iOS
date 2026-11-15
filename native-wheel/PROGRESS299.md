# Build299: recover the exited canvas thread after spectator return

The supplied298 device log has seven independent samples. PB1 completes888
update callbacks and its native canvas sequence stops at889. Its retained
Mach thread right returns MACH_SEND_INVALID_DEST (268435459) for both state
and thread-info requests, beginning2123 ms after the last update. None of the
peer snapshots contains a PB1 game thread. PB2 throughPB6 remain present and
continue updating. Thus the old PB1 update thread has exited; this is not a
live worker waiting for a monitor. Rendering and input continue on the main
thread. The room0 reply again installs130 rows, cleanup completes and the
area entrance remains at432 because no canvas update thread remains.

The log cannot preserve the last Java exception after that thread has already
ended.299 repairs the demonstrated missing-thread state without inventing a
second UI/physics clock:

- The native render callback arms recovery only for a watched scene. It waits
  until watching has ended, the native arena has been restored, any new watch
  offer is gone, and a room0 destination has nonempty received area data.
- A stale timestamp alone never permits recovery. mach_port_type must prove
  that the original retained thread right is a DEAD_NAME. A live sleeping,
  blocked, or otherwise unresponsive worker is never duplicated or stopped.
- Before watching, the original update callback retains its exact Runnable
  from Thread.currentThread().target through JNI and checks its native class.
  Original Thread.run's AOT also reads that Runnable field at offset0x50.
  The canvas's static navigation/screen fields are not Runnable references.
- The attached render Env constructs java.lang.Thread with that retained
  original GameCanvas Runnable, then calls Thread.start.
  The VM creates the new worker and its own Env. No UIKit timer invokes Java,
  and no saved Env is reused by a native pthread.
- The first original update callback rebinds the retained Mach right to the
  actual new worker. Recovery is complete only after that heartbeat advances.
  The Java Thread root remains pinned while starting; one original Runnable
  root per PB remains retained for later watch sessions. Delayed/live/unknown
  workers cannot cause another start. Explicitly ended replacements allow
  up to three attempts per watch, separated by checks and delay.
- Normal healthy exits disarm recovery after verified update progress.
  Existing native actors, area updates, key processing, transport and engine
  scheduling remain unchanged. No native game executable patch is added.
- Watch299-diagnostic.json retains the298 data and adds per-PB canvas_recovery
  attempts, recovered count, pending/failure/status metadata. Future device
  captures can establish that the original game loop resumed.

Validation includes an actual waiting pthread (no replacement allowed), its
actual exit/dead Mach right, a replacement created at the VM boundary with a
delayed heartbeat, reentrant/repeated renders, port rebinding and another PB
remaining live. An ARM64 control on compiled298 reproduces transition432 and
held input through100 renders across all six PBs. The compiled299 test uses
the unchanged original area animation and directional input methods to verify
that the replacement worker's normal updates bring432 to0 and consume the
down key. JNI Thread construction/scheduling is a boundary in that ARM64 test;
the Simulator test separately validates real kernel thread lifetime. Neither
test claims a live server or physical iPhone reproduction. Physical-device
confirmation is required for the uploaded device's automatic/manual exits.
