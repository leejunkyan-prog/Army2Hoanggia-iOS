# Build296: complete watch teardown before destination initialization

The supplied video still shows a blank, unresponsive room0 after Build295.
The user also reports the battlefield return. Both destinations were held
behind native cleanup, including a virtual call into the saved screen's
initializer. The real area initializer sets currentScreen and then reads its
row vector. An unavailable vector throws after the screen is visible; cleanup
then retries the same initializer and never reaches SP2/room7 or the battlefield
window callback. The previous regression substituted a successful destination
override and did not cover that dependency.

296 restores world/roster/camera state, then uses the original base screen
activator to reset keys and install the saved screen. It does not invoke the
destination override during teardown. The unchanged room7 controller owns
area initialization after a fresh reply. The battlefield's existing UIKit
window can return after teardown without initializing the hidden native page.
Ticks from the game/render callbacks are serialized per PB, including reentry.

A queued room7 send is no longer treated as successful receipt. Return state
remains until a well-formed, nonempty room0 reply has arrived and the native
room0 screen contains rows. Dropped/empty replies retry at one-second intervals
up to ten attempts. Session changes, navigation away and a new watch cancel
the old recovery. Battlefield returns never request room0.

Verification includes the compiled six-PB cleanup with the original base
activator, input reset and screen setter. The Build295 binary must fail the
new destination-dependency check. The Simulator imports production Spectator,
Lobby, GameViewport and WatchSurface together: all six PBs, manual/automatic
return, actual battlefield window hiding/restoration, JavaScript response,
return callback, key routing and restoration of the original game window.
Dropped/empty/delayed room replies and navigation cancellation are exercised.
Existing ARM64 parsing, render-clock, snapshot, projectile and crafting checks
remain required. Native transport/JNI/resources are explicit boundaries.

Watch296-diagnostic.json adds reply rows, acknowledged return and battlefield
destination. The new IPA is packaged over the exact supplied Build293; the
game executable and server endpoint remain byte-identical. It is unsigned.
The video does not contain device diagnostics, so the exact device failure
site and a successful physical iPhone/live-server result remain unconfirmed.
