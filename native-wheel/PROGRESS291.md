# Build291: spectator live playback

Base: exact user-supplied Build290 JAR-server unsigned IPA.

This build replaces the AGWheel framework and its viewer resources and applies
strictly enumerated spectator bridge patches to the game executable. The
packager reverses every listed patch to prove the rest of the executable is
unchanged, and checks that endpoint initializers/literals remain byte-identical
to Build290. The bundle build number changes from 290 to 291.

Build on macOS: `bash native-wheel/build_291.sh`. The
`fix/ios-291-spectator-live` workflow compiles the framework and runs the native
ARM64 and browser regressions. Additional Build291 ARM64 regressions named
`native-wheel/test_*291.py` are picked up automatically.

Package locally:

```sh
python3 native-wheel/package_291.py Build290.ipa framework-291.zip Build291-unsigned.ipa
```

The packager requires `patch_spectator291.patch_native(original, framework)`
to return the patched executable and a list of offset/before/after edits.
It verifies exact input hashes, the overlay manifest, preserved files,
Mach-O unsigned status, and bundle version. It writes a validation JSON beside
the resulting IPA. Owner signing is required for installation.

Implementation findings and final validation results are pending. Automated
regressions alone do not establish physical-device or live-server parity.
