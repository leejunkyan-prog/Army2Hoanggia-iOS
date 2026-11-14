"""Reassemble the verified IPA and verify it before publishing an artifact."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import json
import os
import plistlib
import shutil

root = Path('delivery/build290')
manifest = json.loads((root / 'manifest.json').read_text())
validation = json.loads((root / 'validation.json').read_text())
endpoint = json.loads((root / 'endpoint290-check.json').read_text())
assert manifest['sha256'] == validation['ipa_sha256']
assert manifest['file'] == 'Army2HoangGia-2.4.1-Build290-JarServer-unsigned.ipa'
output = Path('ipa-output')
output.mkdir()
target = output / manifest['file']
with target.open('xb') as out:
    for part in manifest['parts']:
        raw = Path(part['path']).read_bytes()
        assert len(raw) == part['size']
        assert sha256(raw).hexdigest() == part['sha256']
        out.write(raw)
assert target.stat().st_size == manifest['bytes']
assert sha256(target.read_bytes()).hexdigest() == manifest['sha256']
app = 'Payload/Army2Hoanggia.app/'
with ZipFile(target) as ipa:
    assert ipa.testzip() is None
    assert len(ipa.namelist()) == len(set(ipa.namelist()))
    info = plistlib.loads(ipa.read(app + 'Info.plist'))
    assert info['CFBundleVersion'] == '290'
    assert info['CFBundleShortVersionString'] == '2.4.1'
    native = ipa.read(app + 'Army2Hoanggia')
    framework = ipa.read(app + 'Frameworks/AGWheel.framework/AGWheel')
    assert sha256(native).hexdigest() == validation['native_sha256']
    assert sha256(framework).hexdigest() == validation['framework_sha256']
    assert validation['host'].encode() + b'\0' in native
    assert validation['server_list_url'].encode() + b'\0' in native
assert endpoint['passed'] is True
assert len(endpoint['native_initializers']) == 6
for case in endpoint['native_initializers']:
    assert (case['host'], case['port'], case['url']) == (
        validation['host'], validation['game_port'], validation['server_list_url'])
for source in ['validation.json', 'endpoint290-check.json']:
    shutil.copyfile(root / source, output / source)
(output / 'SHA256SUMS.txt').write_text(manifest['sha256'] + '  ' + target.name + '\n')
print('PASS: assembled IPA, SHA256, ZIP CRC, native endpoint and unchanged Build289 framework')
print(manifest['sha256'], target.name)
summary = os.environ.get('GITHUB_STEP_SUMMARY')
if summary:
    with open(summary, 'a') as f:
        f.write('## Army2 iOS Build290\n\n'
                'Download the artifact below and unzip it to obtain the unsigned IPA.\n\n'
                f"Server from the supplied JAR: `{validation['host']}:{validation['game_port']}`. "
                'Build289 spectator/crafting framework preserved. Owner signing and physical-device verification are required.\n\n'
                f"SHA256: `{manifest['sha256']}`\n")
