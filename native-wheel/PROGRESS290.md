# Build290: server from the supplied Army2HoangGia.jar

Base: verified Build289 IPA SHA256 5f43445cfd98effa8b8b0ed41dfbf788a508a7407cd95365f45e21c43b6b545f.
User explicitly approved uploading the IPA to this private repository.
Retarget to 180.93.120.67:19149 and http://180.93.120.67:18080/server.txt, decoded from the supplied JAR TerrainMidlet static initializer.
JAR SHA256: b5ed7f1c96cbf1dc3864c3e575a5c3643332b0f8536d9f65eac071e30c6b7796.
Only host/URL native slots, their explicit UTF lengths and CFBundleVersion change from Build289. All six native initializers were executed in Unicorn with mocked JVM dependencies and returned the matching host, port and URL. The full Build289 spectator/crafting framework and all other files remain byte-identical.
Build289 framework SHA256: cf3cfa879b7e36ff86ac0916affb7cdb76ee6922132d9d9ffa5aaa3507d859b1.
To package: python3 native-wheel/package_290.py Build289.ipa Army2HoangGia.jar Build290-unsigned.ipa.
To verify: python3 native-wheel/verify_endpoint290.py Build290-unsigned.ipa. Requires unicorn.
The delivery branch stores binary transport parts and reassembles the SHA256-verified IPA as an Actions artifact. Owner signing is required. No physical-device or live-server login test has been performed.
