"""Recover the exact tested Build289 from existing private repository bytes.

The reference payload is already in this repository. Its four endpoint edits
and version increment are reversed to the exact user-requested Build289 IPA.
No live server is contacted. The reference branch is never changed.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from hashlib import sha256
from copy import copy
import json, plistlib, os

EXPECTED_IPA = '5f43445cfd98effa8b8b0ed41dfbf788a508a7407cd95365f45e21c43b6b545f'
EXPECTED_NATIVE = '2e7f2aec10ed36009c851c3baaade8f75dab35ba6d0f9be3b932ef64f08bca73'
EXPECTED_FRAMEWORK = 'cf3cfa879b7e36ff86ac0916affb7cdb76ee6922132d9d9ffa5aaa3507d859b1'
APP = 'Payload/Army2Hoanggia.app/'
reference = Path('delivery/build290')
manifest = json.loads((reference / 'manifest.json').read_text())
validation = json.loads((reference / 'validation.json').read_text())
assert manifest['sha256'] == '097cca0d082dabdfca0b88039e32e25e9437b4f067ccadfe3e2bed942d149e7f'
assert validation['source_ipa_sha256'] == EXPECTED_IPA
scratch = Path('delivery/build289/reference.ipa')
with scratch.open('xb') as target:
    for part in manifest['parts']:
        data = Path(part['path']).read_bytes()
        assert len(data) == part['size']
        assert sha256(data).hexdigest() == part['sha256']
        target.write(data)
assert sha256(scratch.read_bytes()).hexdigest() == manifest['sha256']
output = Path('ipa-output')
output.mkdir()
target = output / 'Army2HoangGia-2.4.1-Build289-NewSv-unsigned.ipa'
with ZipFile(scratch) as source:
    native = bytearray(source.read(APP + 'Army2Hoanggia'))
    assert sha256(native).hexdigest() == validation['native_sha256']
    for edit in validation['native_edits']:
        at = edit['offset']
        before, after = bytes.fromhex(edit['before']), bytes.fromhex(edit['after'])
        assert len(before) == len(after)
        assert native[at:at + len(after)] == after
        native[at:at + len(before)] = before
    assert sha256(native).hexdigest() == EXPECTED_NATIVE
    assert b'180.93.195.228\0' in native
    assert b'http://180.93.195.228:18080/server.txt\0' in native
    info = plistlib.loads(source.read(APP + 'Info.plist'))
    assert info['CFBundleVersion'] == '290'
    info['CFBundleVersion'] = '289'
    replacement = {APP + 'Army2Hoanggia': bytes(native),
                   APP + 'Info.plist': plistlib.dumps(info, fmt=plistlib.FMT_BINARY)}
    with ZipFile(target, 'x', ZIP_DEFLATED, compresslevel=6) as result:
        for item in source.infolist():
            result.writestr(copy(item), replacement.get(item.filename, source.read(item.filename)))
assert target.stat().st_size == 27596608
assert sha256(target.read_bytes()).hexdigest() == EXPECTED_IPA, 'Delivery differs from the tested IPA'
with ZipFile(target) as result:
    assert result.testzip() is None
    assert len(result.namelist()) == len(set(result.namelist()))
    assert sha256(result.read(APP + 'Frameworks/AGWheel.framework/AGWheel')).hexdigest() == EXPECTED_FRAMEWORK
report = dict(build=289, ipa_sha256=EXPECTED_IPA, native_sha256=EXPECTED_NATIVE,
              framework_sha256=EXPECTED_FRAMEWORK, server_unchanged_from_user_ipa=True,
              host='180.93.195.228', port=19149, physical_device_tested=False,
              tests_run='https://github.com/leejunkyan-prog/Army2Hoanggia-iOS/actions/runs/43611482531')
(output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
(output / 'SHA256SUMS.txt').write_text(EXPECTED_IPA + '  ' + target.name + '\n')
summary = os.environ.get('GITHUB_STEP_SUMMARY')
if summary:
    with open(summary, 'a') as f:
        f.write('## Army2 Build289\n\nDownload and unzip the artifact to obtain the unsigned IPA. '
                'Original server preserved: `180.93.195.228:19149`. '
                'ARM64 and interface checks passed; owner signing and iPhone testing are required.\n\n'
                f'SHA256: `{EXPECTED_IPA}`\n')
print('PASS exact tested Build289 IPA, ZIP CRC, original executable/server and framework hashes')
