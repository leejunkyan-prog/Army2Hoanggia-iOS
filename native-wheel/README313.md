# Build313 — Speed Max and stable chest

Input is the exact user-supplied Build312 RankForce IPA:
`8a39193b9843365fd81b863fc8aa03db066d27d6da6e1f184771602d21fe55c2`.
Its framework, RankForce changes, resources, server configuration and prior native hooks are retained. Only the native executable and CFBundleVersion are changed. Build313 is unsigned.

The supplied APK SHA256 is `823586872a0076b6aad4b8f5ca4c4faa3a72e8c0d597d8a444251538fc9efd9d`. Client46.pace/hoanggia.GdxBatch.loopSleep let the game loop run fast, while popup timing is33333333ns and movement/camera timing is25000000ns. The native IPA Max path instead jumped over sleep for the whole canvas loop. The supplied video also shows chest contents changing places while the selected cell stays still.

At Max,313 performs up to eight original arena updates per existing update owner. It covers native projectile, actor/boss animation and effect progression. It does not repeat keyboard/touch input, create another physics thread, or bypass spectator render ownership. The loop stops batching when the active screen changes or a menu/dialog appears. Levels0–9 keep one original simulation step.

Max sleeps1ms in the active unblocked arena to yield to receive/render work, and33ms in UI/menu scenes. During an active HP flash it places the existing visual counter at19; the next original GameCanvas step reaches20, clears the flag and follows its original notify path. HP values, packets, server turn predicates and server clocks are untouched. Server-scheduled boss attacks cannot be made to arrive earlier by changing an IPA; these changes accelerate local simulation/animation and pending visual waits.

The native chest C6.n method used to overwrite the private sorted display vector with the source vector before the later order hook repaired it. A concurrent painter could observe the intermediate order.313 keeps a nonnull display vector and uses that same vector for the native length read; null first-open initialization remains original. The unchanged312 inventory bridge still rebuilds the private display when source items/quantities change. Source vectors are never sorted or edited by this patch.

All six PBs are patched. New code occupies an extension of the existing RX AGSCENE segment; LINKEDIT is moved with all affected file offsets adjusted. Symbol values, dyld binding targets, LINKEDIT contents and existing data segments are verified unchanged. No runtime executable-memory writes or new dylib imports are introduced.

## Reproduce

Use Python with keystone-engine, lief, unicorn and Pillow, plus the existing regression fixture files in this repository:

```
python native-wheel/patch_speed313.py source312.ipa Army2HoangGia-2.4.1-Build313-MaxSpeed-unsigned.ipa
python native-wheel/verify_speed313.py source312.ipa Army2HoangGia-2.4.1-Build313-MaxSpeed-unsigned.ipa
```

Validation runs151 installed ARM64 hook/guard/ABI cases,12000 chest-store interleavings,3600 actual native C6.n prefix/unchanged312 bridge updates, and complete original arena/projectile integration. The same43-step trajectory requires44 single-step owner calls and6 Max owner calls, with identical per-projectile update states and normal busy release. Six actual native startup initializers retain their server configuration. Image/JNI/transport and selected actor operations are fixture boundaries, documented in the tests. No physical iPhone, live server, wall-time speed multiplier, or heat/battery result is claimed.
