"""Retarget the verified Build287 IPA to the server in the supplied NewSv JAR.

Only endpoint literals, their native UTF lengths, the five old fallback ports,
and CFBundleVersion change. The GitHub-built spectator/crafting framework stays
byte-identical to Build287. No client release/login marker changes.
"""
from copy import copy
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import argparse
import json
import plistlib

BASE_IPA = '1c5fc520007b06cee33936d26b81a4bb7d0c090df0d336684452c4e17a2990dd'
BASE_NATIVE = '6cdd39d83a4e221b75cbcb30c5780c0c5f3e69503e2e733e3dad6e867a6f36e7'
BASE_FRAMEWORK = '91d393e157d8d191a57d6a64f6ca581abc6604f9adcbc399bd009b43a18828f2'
SERVER_JAR = '86abf205c0f1de745dba7f7b581b7d81e4485c6c72fc66ceed6ebc3ea811d505'
OLD_HOST, HOST = '180.93.120.67', '180.93.195.228'
OLD_URL = f'http://{OLD_HOST}:18080/server.txt'
URL = f'http://{HOST}:18080/server.txt'
PORT = 19149
INITIALIZERS = (0x570218, 0x65a7cc, 0x73f490, 0x824154, 0x908e18, 0x9edadc)
APP = 'Payload/Army2Hoanggia.app/'
NATIVE = APP + 'Army2Hoanggia'
FRAMEWORK = APP + 'Frameworks/AGWheel.framework/AGWheel'


def patch_native(original):
    assert sha256(original).hexdigest() == BASE_NATIVE, 'Unexpected native baseline'
    data = bytearray(original)
    edits = []

    def replace(offset, old, new):
        assert len(old) == len(new)
        assert data[offset:offset + len(old)] == old
        if old != new:
            data[offset:offset + len(new)] = new
            edits.append({'offset': offset, 'before': old.hex(), 'after': new.hex()})

    for offset, capacity, old, new, length_at in (
        (0x145f160, 16, OLD_HOST, HOST, 0x570308),
        (0x145f190, 40, OLD_URL, URL, 0x570380),
    ):
        assert len(new.encode()) + 1 <= capacity
        replace(offset, old.encode().ljust(capacity, b'\0'),
                new.encode().ljust(capacity, b'\0'))
        # RoboVM's string getter takes an explicit UTF-16 length in w3.
        old_word = 0x52800003 | (len(old) << 5)
        new_word = 0x52800003 | (len(new) << 5)
        replace(length_at, old_word.to_bytes(4, 'little'), new_word.to_bytes(4, 'little'))

    for i, start in enumerate(INITIALIZERS):
        at = start + 0x44
        old_port = 19149 if i == 0 else 19129
        replace(at, (0x52800009 | old_port << 5).to_bytes(4, 'little'),
                (0x52800009 | PORT << 5).to_bytes(4, 'little'))

    assert OLD_HOST.encode() not in data
    restored = bytearray(data)
    for edit in edits:
        at, before, after = edit['offset'], bytes.fromhex(edit['before']), bytes.fromhex(edit['after'])
        assert restored[at:at + len(after)] == after
        restored[at:at + len(before)] = before
    assert restored == original, 'Changes escaped endpoint allowlist'
    assert len(data) == len(original)
    return bytes(data), edits


def package(source, target):
    source, target = Path(source), Path(target)
    assert sha256(source.read_bytes()).hexdigest() == BASE_IPA
    assert not target.exists(), 'Do not overwrite a previous delivery'
    with ZipFile(source) as base:
        raw, edits = patch_native(base.read(NATIVE))
        assert sha256(base.read(FRAMEWORK)).hexdigest() == BASE_FRAMEWORK
        info = plistlib.loads(base.read(APP + 'Info.plist'))
        assert info['CFBundleVersion'] == '287'
        assert info['CFBundleShortVersionString'] == '2.4.1'
        info['CFBundleVersion'] = '288'
        changed = {NATIVE: raw, APP + 'Info.plist': plistlib.dumps(info, fmt=plistlib.FMT_BINARY)}
        target.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=6) as out:
            for zi in base.infolist():
                out.writestr(copy(zi), changed.get(zi.filename, base.read(zi.filename)))
        with ZipFile(target) as out:
            assert out.testzip() is None
            assert out.namelist() == base.namelist()
            assert len(out.namelist()) == len(set(out.namelist()))
            actual = [n for n in base.namelist() if base.read(n) != out.read(n)]
            assert set(actual) == set(changed)
            assert sha256(out.read(FRAMEWORK)).hexdigest() == BASE_FRAMEWORK
            assert out.read(NATIVE) == raw
    result = {
        'ipa': target.name, 'ipa_sha256': sha256(target.read_bytes()).hexdigest(),
        'ipa_bytes': target.stat().st_size, 'source_ipa_sha256': BASE_IPA,
        'native_sha256': sha256(raw).hexdigest(), 'source_jar_sha256': SERVER_JAR,
        'host': HOST, 'game_port': PORT, 'server_list_url': URL,
        'build': 288, 'version': '2.4.1', 'pb_variants': 6,
        'framework_unchanged_from_build287': True, 'framework_sha256': BASE_FRAMEWORK,
        'changed_zip_entries': actual, 'native_edits': edits,
        'physical_device_tested': False, 'live_server_login_tested': False,
    }
    target.with_suffix('.validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_ipa')
    parser.add_argument('target_ipa')
    args = parser.parse_args()
    package(args.source_ipa, args.target_ipa)
