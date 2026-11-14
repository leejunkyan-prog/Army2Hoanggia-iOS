# Build 284 – inventory and spectator loading

Source: exact Build283 snapshot `88924f760e4e8fa507eb873a53d39fe152897735`
from `lykien0311-jpg/Army2Hoanggia-iOS`. Target:
`leejunkyan-prog/Army2Hoanggia-iOS`, branch `qa/ios-284-performance`.
The build branch contains the native framework sources and relevant tests.
The legacy `payload/source.zip.part*` archives stay in the original repository.
The build workflow has read-only repository permissions and returns its
output through GitHub Actions artifacts.

Baseline IPA SHA256: `5cbca2fd58ae4eacebf4d3be5bfd8d03b96b4e76d07bd2c5e85865901df1aae8`.
Game executable SHA256: `6cdd39d83a4e221b75cbcb30c5780c0c5f3e69503e2e733e3dad6e867a6f36e7`.

## Changes

- Inventory: removed blocking JNI MonitorEnter on the server Vector from the
  render callback. Grouping, updated-item promotion and recipe resolution use
  a separate display Vector; the server collection is never reordered.
  JNI roots keep snapshots alive and unstable snapshots are deferred.
- Spectator: cache byte-identical decoded terrain images within one watch
  session, capped at 64 images and four million pixels. Pixel arrays remain
  independent for each destructible tile. End/abort releases all cache roots.
- Cancellation: render-thread cleanup uses a nonblocking try-lock and retries
  on a later frame when snapshot construction owns the adapter lock.
- Packaging advances only CFBundleVersion to 284 and updates the verified
  framework overlay. It preserves the exact supplied Build283 game executable
  and all other unrelated archive entries.

## Checks and limits

- The new ARM64 inventory regression rejects Build283 because it calls the
  blocking server Vector monitor. This establishes the test detects the old
  behavior; it does not by itself reproduce a live phone deadlock.
- The pure inventory ordering fixture passed 500 consecutive updates.
- Shell and Python syntax checks passed before the GitHub build.
- GitHub compiles the device framework with Apple clang and runs the compiled
  ARM64 inventory and spectator fixtures for all six variants, plus web UI tests.
- No physical iPhone or live server session has been tested in this workspace.
  A successful build or mocked ARM64 test does not establish that the original
  loading time and freeze are resolved on the user's phone.

## Verified build result

The user explicitly approved this source/assets transfer. The private target
now contains 225 native build inputs, tests and game assets. Legacy archives
remain in the original repository; CI has read-only repository permissions.

Successful GitHub run: https://github.com/leejunkyan-prog/Army2Hoanggia-iOS/actions/runs/43573103522
Tested source commit: `f38aedd9a09b14528f27fe9e9bc159c8872db1f5`.
Both framework and interface jobs passed. Apple ARM64 fixtures covered six
variants, 600 inventory updates with no blocking server monitor, and 312
independent terrain tiles with image reuse, cancellation and restoration.
The first UI fixture failed on file-origin canvas restrictions; serving the
fixture over same-origin localhost HTTP resolved it without removing assertions.

Verified framework artifact ID: `14105072720`.
Artifact ZIP SHA256: `c4838509913042c7e782cbf7a4328f281dafb388d42463f15874d3ae25846d93`.
Final file: `Army2HoangGia-2.4.1-Build284-unsigned.ipa`, 27592164 bytes.
IPA SHA256: `490135fe19ae5d8352628f8b88d816daa211339d1758952c42e50ff01fc8b902`.
ZIP integrity, unique entries, build version 284 and preservation of the game
executable were checked. Unrelated resources are byte-identical; lobby.html
only loses one trailing blank line in addition to the framework/version update.

This IPA must be signed by its owner. Physical iPhone and live-server tests,
including actual load-time comparison with the supplied APK video, remain
outstanding. Automated checks do not establish that both reported phone issues
are resolved in production.
