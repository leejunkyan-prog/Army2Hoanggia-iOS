# Build291: spectator update loop and APK spectator state

Base: exact user-supplied Build290 JAR-server IPA,
SHA256 `097cca0d082dabdfca0b88039e32e25e9437b4f067ccadfe3e2bed942d149e7f`.
Reference APK `gs5kl1.apk`, SHA256
`823586872a0076b6aad4b8f5ca4c4faa3a72e8c0d597d8a444251538fc9efd9d`.

The uploaded iOS video shows map/clock rendering with aim rays and combat
controls while the label says spectator. The APK video shows movement,
projectiles, an explosion, then HP changing from 169300 to 168518. Both show
angle text and the lower F1/F2/keypad; those should remain. These recordings
are different fights, not a synchronized network trace.

Three source-level differences from the supplied APK are corrected:

1. After showing the arena, SP5 must close the native loading dialog. The
   original GameCanvas branch loads canvas+0x108 and updates that dialog,
   skipping scene.update while it remains non-null. Native arena.show only
   changes the current screen and clears input; it does not close dialogs.
   Map painting can therefore succeed without updating actors/projectiles.
   The adapter now closes the dialog only after confirming its own watched
   arena is current. Canceled/inactive views cannot clear destination dialogs.
2. The APK's PlayerManager.isMyTurn includes !SpectatorClient53.active; the
   six AOT predicates compare indices alone. SP5 assigns a valid local index
   for native array accesses, so the AOT grants participant HUD/aim behavior.
   A guarded bridge now returns false during an active watch. Outside watch,
   the original predicate executes unchanged, including safe symbol fallback.
   Never set local slot to -1: other native routines index it directly.
3. During snapshot replay, APK command51 stores authoritative current HP and
   runs the normal native death transition for nonpositive HP. It skips damage
   text, flash, animation waits and timer changes. The iOS adapter now follows
   that path before SP7; live HP packets keep the original game handler.

Original command21/22/51 parsing and native battle state are tested separately
from the snapshot/JNI fixtures. Native rendering/physics still owns actors,
projectiles, explosions and destructible terrain. No simulated web battlefield
or timer-driven state replacement is introduced.

Build: `bash native-wheel/build_291.sh` on macOS, or the Build291 workflow on
`fix/ios-291-spectator-live`. Package with `package_291.py Build290.ipa
framework-291.zip Build291-unsigned.ipa`. The packager verifies exact base
hashes, the framework's exported watch guard, bounded native edits and reversal
of every native edit. Endpoint initializers/getters/literals and all unrelated
IPA files remain unchanged. The server stays 180.93.120.67:19149.

Validation executes compiled iPhone ARM64 and original supplied AOT code in
Unicorn with resource/JVM/transport boundaries mocked. It includes original
and patched predicates across all six PBs, snapshot HP/death handling,
pending-modal update routing, and native movement/shot/HP dispatch. Existing
inventory, crafting, snapshot barrier, camera and UI regressions remain.

No physical iPhone or live game account has been used. Offline regressions do
not establish complete device/server parity. The unsigned IPA requires owner
signing and an actual watch-session check on the phone, including leave and
re-enter. See the accompanying test logs and validation JSON for exact scope.
