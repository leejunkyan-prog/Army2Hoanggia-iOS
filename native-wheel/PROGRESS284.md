# Build 284 – inventory and spectator loading

Source: exact Build283 snapshot `88924f760e4e8fa507eb873a53d39fe152897735`
from `lykien0311-jpg/Army2Hoanggia-iOS`. Target:
`leejunkyan-prog/Army2Hoanggia-iOS`, branch `qa/ios-284-performance`.
The planned new branch contains the native framework sources and relevant tests.
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

## Migration authorization

Auto-review previously rejected the source-tree upload, requesting explicit
approval for the private source/assets transfer. Both connected repository
owners, private visibility and admin rights were verified. The user has now
approved the specific transfer described below after being asked explicitly.
The GitHub commit, build and artifact validation are still pending.

Requested transfer: the native framework inputs, relevant tests and game images
from the exact Build283 source snapshot, plus the Build284 changes, into the
private repository leejunkyan-prog/Army2Hoanggia-iOS on branch
qa/ios-284-performance. Legacy payload archives are excluded. CI has read-only
repository access. The local source and changes remain committed and preserved.

Final run ID, result and delivered IPA checksum remain pending.
