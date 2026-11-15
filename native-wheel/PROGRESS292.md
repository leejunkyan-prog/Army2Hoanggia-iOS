# Build292: APK input parity, bounded waits and device evidence

This build follows the user's physical Build291 recording: no aiming rays,
but one movement followed by a static clock62/angle209/HP1000 and no visible
shots. The live spectator defect is NOT established as fully resolved by
offline packet parsing or the earlier modal test.

Audit correction: GameCanvas calls the real scene update through5ae014 at
510ce0 BEFORE its modal branch. The later5112d8 branch selects dialog versus
battle INPUT, not scene update. Build291's modal cleanup matches APK input
behavior but its former regression label and freeze explanation were wrong.
The test now describes input routing correctly.

Changes:

- Native F1(-6/-21) opens Menu; F2(-7/-22) switches Camera. Remove both native
  and JavaScript F1-to-camera overrides; debounce key repeats. F2 during
  WebView startup must not cancel an already active spectator session.
- The native HUD owns the angle label. Remove the duplicate WebView angle
  text seen overlaid in the supplied iPhone video.
- Match supplied APK Wait106's30-second animation wait bound for spectators.
  Expiry releases the same shot/flash/move/flight busy flag; it does not choose
  turns or fabricate movement/shot packets. This recovers a stuck receiver,
  but by itself does not prove live animation works on the phone.
- Record scene entries, packet command metadata, wait stages/expirations and
  the first caught original native battle-update exception. The six catch
  shims preserve the original Throwable.printStackTrace call. No credentials,
  chat text or packet payloads are recorded.
- The existing Files/iTunes file-sharing configuration exposes the silent
  Documents/Watch292-diagnostic.json. UIKit saves metadata once per second
  during watching. This distinguishes missing packets, a blocked receive
  wait and repeated native update exceptions on the user's actual device.

Base remains the exact supplied Build290 unsigned IPA SHA256
097cca0d082dabdfca0b88039e32e25e9437b4f067ccadfe3e2bed942d149e7f.
The292 packager composes the291 turn guards and292 diagnostic catch bridges
with an exact-base hash, checked original instructions, bounded zero caves,
export validation and complete reversal checks. Endpoint configuration stays
180.93.120.67:19149. All unrelated IPA entries are unchanged.

Build with build_292.sh on macOS or the292 GitHub workflow. Package with
package_292.py Build290.ipa framework-292.zip Build292-unsigned.ipa.
The result still requires owner signing. No live login or physical iPhone is
available in this environment; full visual and live-server parity is pending
actual-device evidence, not asserted by the offline test results.
