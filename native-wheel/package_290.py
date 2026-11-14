"""Apply the supplied JAR's server settings to the verified Build289 IPA."""
from copy import copy
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
from zipfile import ZipFile, ZIP_DEFLATED
import json
import plistlib

BASE_IPA = '5f43445cfd98effa8b8b0ed41dfbf788a508a7407cd95365f45e21c43b6b545f'
BASE_NATIVE = '2e7f2aec10ed36009c851c3baaade8f75dab35ba6d0f9be3b932ef64f08bca73'
BASE_FRAMEWORK = 'cf3cfa879b7e36ff86ac0916affb7cdb76ee6922132d9d9ffa5aaa3507d859b1'
SERVER_JAR = 'b5ed7f1c96cbf1dc3864c3e575a5c3643332b0f8536d9f65eac071e30c6b7796'
OLD_HOST, HOST = '180.93.195.228', '180.93.120.67'
OLD_URL = f'http://{OLD_HOST}:18080/server.txt'
URL = f'http://{HOST}:18080/server.txt'
PORT = 19149
INITIALIZERS = (0x570218, 0x65a7cc, 0x73f490, 0x824154, 0x908e18, 0x9edadc)
APP = 'Payload/Army2Hoanggia.app/'
NATIVE = APP + 'Army2Hoanggia'
FRAMEWORK = APP + 'Frameworks/AGWheel.framework/AGWheel'


def patch_native(original):
    assert sha256(original).hexdigest() == BASE_NATIVE
    data = bytearray(original)
    edits = []
    for offset, capacity, old, new, length_at in (
        (0x145f160, 16, OLD_HOST, HOST, 0x570308),
        (0x145f190, 40, OLD_URL, URL, 0x570380),
    ):
        assert len(new.encode()) + 1 <= capacity
        before = old.encode().ljust(capacity, b'\0')
        after = new.encode().ljust(capacity, b'\0')
        assert data[offset:offset + capacity] == before
        data[offset:offset + capacity] = after
        edits.append({'offset': offset, 'before': before.hex(), 'after': after.hex()})
        before = (0x52800003 | len(old) << 5).to_bytes(4, 'little')
        after = (0x52800003 | len(new) << 5).to_bytes(4, 'little')
        assert data[length_at:length_at + 4] == before
        data[length_at:length_at + 4] = after
        edits.append({'offset': length_at, 'before': before.hex(), 'after': after.hex()})
    for start in INITIALIZERS:
        assert unpack_from('<I', data, start + 0x44)[0] == 0x52800009 | PORT << 5
    assert OLD_HOST.encode() not in data
    restored = bytearray(data)
    for edit in edits:
        offset = edit['offset']
        before, after = bytes.fromhex(edit['before']), bytes.fromhex(edit['after'])
        assert restored[offset:offset + len(after)] == after
        restored[offset:offset + len(before)] = before
    assert restored == original and len(data) == len(original)
    return bytes(data), edits


def package(source, jar, target):
    source, jar, target = map(Path, (source, jar, target))
    assert sha256(source.read_bytes()).hexdigest() == BASE_IPA
    assert sha256(jar.read_bytes()).hexdigest() == SERVER_JAR
    assert not target.exists()
    with ZipFile(source) as base:
        native, edits = patch_native(base.read(NATIVE))
        assert sha256(base.read(FRAMEWORK)).hexdigest() == BASE_FRAMEWORK
        info = plistlib.loads(base.read(APP + 'Info.plist'))
        assert info['CFBundleVersion'] == '289'
        assert info['CFBundleShortVersionString'] == '2.4.1'
        info['CFBundleVersion'] = '290'
        changed = {NATIVE: native, APP + 'Info.plist': plistlib.dumps(info, fmt=plistlib.FMT_BINARY)}
        target.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=6) as out:
            for entry in base.infolist():
                out.writestr(copy(entry), changed.get(entry.filename, base.read(entry.filename)))
        with ZipFile(target) as out:
            assert out.testzip() is None
            assert out.namelist() == base.namelist()
            assert len(out.namelist()) == len(set(out.namelist()))
            actual = [name for name in out.namelist() if base.read(name) != out.read(name)]
            assert set(actual) == set(changed)
            assert out.read(NATIVE) == native
            assert sha256(out.read(FRAMEWORK)).hexdigest() == BASE_FRAMEWORK
    result = {
        'ipa': target.name, 'ipa_sha256': sha256(target.read_bytes()).hexdigest(),
        'ipa_bytes': target.stat().st_size, 'source_ipa_sha256': BASE_IPA,
        'native_sha256': sha256(native).hexdigest(), 'source_jar_sha256': SERVER_JAR,
        'host': HOST, 'game_port': PORT, 'server_list_url': URL,
        'build': 290, 'version': '2.4.1', 'pb_variants': 6,
        'framework_unchanged_from_build289': True, 'framework_sha256': BASE_FRAMEWORK,
        'changed_zip_entries': actual, 'native_edits': edits,
        'zip_crc_valid': True, 'zip_paths_unique': True, 'requires_signing': True,
        'physical_device_tested': False, 'live_server_login_tested': False,
    }
    target.with_suffix('.validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    import sys
    package(*sys.argv[1:])
