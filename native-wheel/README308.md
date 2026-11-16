# Build308 — APK inventory parity

Based on Build307 commit `66b77e1ab13f7b80fad9f5cac87ccc188b8836c2`.
Reference: the supplied 49.226-second APK recording, especially the first
result around 10–12s, second result around 26s, and reopening after login at
38s. The supplied 38.4-second iPhone recording demonstrates the regressions.

## Behavior

- Opening the chest keeps its original left-to-right entrance. The native
  panel already animates `+0x34`; the grid clip reset previously cancelled
  that translation before painting the body. Restore the saved graphics
  translation after clearing the inherited clip, so frame and contents move
  together. Keep the existing native animation and responsive geometry.
- A cmd45 informational result permits one inventory snapshot while its OK
  dialog remains open. The preceding native cmd27 has already inserted or
  stacked the received item. Promote that item immediately. As in the APK,
  preserve the selected source stack if any remains. Actionable confirmation,
  menu and amount-entry positions stay stable. Consume the notification permit
  after a successful snapshot so it cannot affect a later confirmation.
- Observe successful cmd3 login replies to reset remembered display order,
  including repeated logins and account changes using the same service and
  Session objects. Regroup gear, gems and stones on the next chest opening.
  Opening/closing the chest during the same login still preserves new-item
  order. Neither observer consumes stream bytes or changes server items.

The Chicky colors and event title from Build307 remain included. Packaging
uses the same hash-checked Build293 input and existing 13 recipe patch sites.

## Checks

`test_inventory_slide308.py` executes original activation, easing and panel
paint for all six PBs and three viewport widths, then the compiled grid hook.
It checks all intermediate positions and full viewport clipping. Build307
fails because the grid body loses the entrance offset on the first frame.

`test_inventory_parity308.py` executes six original bulk callbacks. PB1 also
runs the actual cmd27 dispatcher, gem insertion, material consumption, stack
merge and cmd45 parser. It asserts 7→8→9 promotion before any OK tap, stable
source selection, later confirmation deferral, unchanged native quantities,
and grouping after cmd3 for two accounts with an unchanged Session pointer.
It also checks nonzero stream positions and rejected truncated login prefixes.
Build307 fails at the first promotion while the result is still visible.

CI compiles iPhone ARM64, runs these and the existing regressions, checks web
UI and Simulator return flow, and produces the unsigned Build308 IPA with
hash and endpoint reports. Java graphics, transport and OS boundaries are
mocked in ARM64 tests; no physical iPhone or live-account test is claimed.
