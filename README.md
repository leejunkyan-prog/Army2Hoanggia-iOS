# Army2 Hoang Gia iOS Build284

Native framework sources continued from Build283 (88924f760e4e8fa507eb873a53d39fe152897735).
Build branch: qa/ios-284-performance. GitHub Actions compiles the ARM64 iPhone framework, runs inventory/spectator fixtures and checks the lobby/watch UI.

Changes and test limits: native-wheel/PROGRESS284.md.
Build on macOS: bash native-wheel/build_284.sh.
Package the exact supplied Build283 IPA with the downloaded framework artifact: python3 native-wheel/package_284.py input-Build283.ipa framework-284.zip Army2HoangGia-Build284-unsigned.ipa.
The owner must sign the final IPA for installation. Physical-device testing is still required.

Legacy payload/source.zip.part archives and older build workflows remain in lykien0311-jpg/Army2Hoanggia-iOS. They are not inputs to this native framework build.
