# Build293: spectator render clock and retained game window

The supplied Watch292-diagnostic.json reports a ready PB1 snapshot, native
watch running, 64 received packets, last command21, one expired movement wait
and zero recorded scene completions or Java exceptions. The old
`scene_entries` field counts the post-update pulse, not function entry. Zero
therefore does not distinguish an idle update loop from a blocked update, or
establish that rendering/transport as a whole stopped. `wait_stage:2` records
the latest wait exit; it is not evidence of a currently blocked wait.

Build293 gives watched simulation a single clock at native GameCanvas.paint.
Using that callback's attached RoboVM Env, it runs the unchanged original
arena.update at most once per30ms. The Java GameCanvas update bridge defers
watched updates so that actors and projectiles cannot advance twice. Normal
participant play still calls its original update. Incomplete snapshots,
native auxiliary screens, cancellation, reentry and stalled-frame catch-up
have explicit guards. Native twenty-step flash completion is retained when
the Java canvas counter is stationary. Packet contents, turns, HP and shot
paths still come from the server and original dispatcher.

The transparent watch UI is now a child of the existing game root controller.
It does not create a UIWindow, replace the game root, or take key-window
ownership. The production WatchSurface component passes native keypad and
auxiliary-dialog touches through and follows the game view bounds. Build292's
F1 Menu / F2 Camera mapping and removal of spectator aiming rays remain.

Verification:

- Compiled ARM64 render-clock regression covers all six PB variants, snapshot
  barriers, single update ownership, pacing, reentry, native auxiliary screens,
  flash completion, cancellation and returning to normal play.
- Independent Unicorn execution of all twelve patched paint/update bridges
  checks JNI arguments, stack/register preservation, original paint execution,
  dyld lookup caching and missing-export fallback.
- Original command parsers, movement-completion and projectile regressions
  remain. Render integration additionally executes the original PB1 arena,
  projectile and clock bodies through the compiled render scheduler for two
  consecutive shots. Actor, resource, JVM and transport boundaries are mocked.
- An iOS Simulator app executes the production WatchSurface implementation:
  original key window/root retained, display-link frames continue, native
  keypad/auxiliary touches pass through, bounds changes and unmounting work.
  This is a component integration test, not the complete RoboVM game.
- Exact Build290 base hashing, disjoint zero caves, checked instructions,
  required dyld exports and full reversal of enumerated native edits remain
  required by the293 packager. The endpoint stays180.93.120.67:19149.

Watch293-diagnostic.json retains the old metadata and adds watch flags,
render callbacks, attempted/completed/failed render steps and deferred canvas
updates. No credentials, packet payloads or chat text are recorded.

The unsigned IPA requires owner signing. No physical iPhone, game account or
live-server session is available here. The uploaded292 trace guides this
change; complete live spectator parity is not claimed by these offline and
Simulator checks and remains subject to actual-device validation.
