# Build298: locate the actual stopped PB1 update thread

The device's Watch297-diagnostic.json and Watch297-watch.json agree:

- PB1 completes 974 update callbacks, then its canvas sequence stays at 975
  for 45,592 ms. It first stops on the native room screen, before the arena
  becomes current. Render callbacks and subsequent key events continue.
- The fresh room0 response contains 130 areas (IDs0 through129). Return and
  cleanup complete, the watch overlay is unmounted, keypad capture is released,
  no modal remains, and input passes to the original game.
- The area entrance transition stays at432, exactly the canvas width. The
  original area painter offsets its rows by that transition, and the original
  area update normally decreases it. This explains the empty-looking room.
- PB2 throughPB6 keep updating. The full application is not frozen.

This establishes an update-thread liveness failure. The297 metadata cannot
tell whether that thread has exited, is waiting for a Java monitor/network
operation, or is looping inside a native method. It does not justify replacing
the original UI/physics clock or injecting concurrent native scene updates.

Build298 retains all gameplay behavior and adds native thread evidence:

- The original update/render callbacks register their own Mach thread ports.
  One send right per callback source is retained so an exited thread cannot
  silently be confused with a reused port name.
- If a PB's updates are stale by1500 ms while its render/input is recent,
  the serial file worker reads its thread state, CPU time and frame chain.
- Relevant peer threads are sampled to help distinguish a waiting thread
  from the thread holding its monitor. No thread is suspended, resumed,
  signalled, or invoked through another thread's Java Env.
- Only executable image basenames and image-relative code offsets are
  exported. Stack contents, absolute addresses, account and packet data are
  not written. Unreadable/unmapped frames are marked explicitly.
- Samples are limited to one every5 seconds per stalled generation and a
  ring of16. Inactive/backgrounded PBs without recent render/input are ignored.
- Documents/Watch298-diagnostic.json keeps the existing native scalar history
  and adds `thread_samples`; Watch298-watch.json retains the lifecycle summary.
  Both continue to flush on backgrounding for retrieval through Files.

The new Simulator test uses an actual pthread blocked in pthread_cond_wait,
checks that the backtrace contains its real wait call site, verifies an
independently updating PB remains healthy, and verifies ordinary recovery
after releasing the test condition. Existing lifecycle and ARM64 regressions
remain in the workflow. The exact supplied293 executable and server endpoint
remain byte-identical in the IPA. This is a diagnostic build, not a claim
that the device hang is already fixed.
