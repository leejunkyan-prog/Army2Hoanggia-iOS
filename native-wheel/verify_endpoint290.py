"""Run the six original ARM64 TerrainMidlet initializers with mocked JVM calls.

Accept an actual IPA/native executable, or the source-hashed AOT fixture on CI.
Both literal getters and all native initializer stores run as original ARM64.
This proves startup configuration, not a live connection to the game server.
"""
from pathlib import Path
from struct import pack, unpack_from
from zipfile import ZipFile
import argparse
import json

from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3
from unicorn.arm64_const import UC_ARM64_REG_LR, UC_ARM64_REG_PC, UC_ARM64_REG_SP

from package_290 import BASE_NATIVE, INITIALIZERS, HOST, URL, PORT, NATIVE

BASE, STACK, HEAP, STOP = 0x100000000, 0x700000000, 0x600000000, 0x300000000
GET_HOST, GET_URL, STRING = 0x5702f0, 0x570368, 0x12e8038


def branch(raw, at):
    word = unpack_from('<I', raw, at)[0]
    assert word & 0xfc000000 == 0x94000000
    n = word & 0x3ffffff
    return at + 4 * (n - (1 << 26) if n & (1 << 25) else n)


def verify(data):
    u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    u.mem_map(BASE, 0x2400000)
    u.mem_write(BASE, bytes(data[:0x2400000]))
    u.mem_map(STACK, 0x40000)
    u.mem_map(HEAP, 0x10000)
    u.mem_map(STOP, 0x1000)
    objects, external = {}, set()
    strings_seen = []
    for start in INITIALIZERS:
        for at in range(start, start + 0xd8, 4):
            if unpack_from('<I', data, at)[0] & 0xfc000000 == 0x94000000:
                target = branch(data, at)
                if target not in (GET_HOST, GET_URL):
                    external.add(BASE + target)

    def finish(value=0):
        u.reg_write(UC_ARM64_REG_X0, value)
        u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_LR))

    def hook(_uc, pc, _size, _ctx):
        if pc == STOP:
            u.emu_stop()
        elif pc == BASE + STRING:
            ptr, length = u.reg_read(UC_ARM64_REG_X2), u.reg_read(UC_ARM64_REG_X3)
            actual = bytes(u.mem_read(ptr, 100)).split(b'\0')[0].decode()
            assert length == len(actual), ('Truncated native server literal', actual, length)
            obj = HEAP + 0x8000 + len(objects) * 0x100
            objects[obj] = actual
            strings_seen.append(actual)
            u.mem_write(u.reg_read(UC_ARM64_REG_X1), pack('<Q', obj))
            finish(obj)
        elif pc in external:
            finish()

    u.hook_add(UC_HOOK_CODE, hook)
    cases = []
    for i, start in enumerate(INITIALIZERS):
        # Decode the original class-global ADRP+ADD pair, never replace its stores.
        at = start + 0x14
        adrp, add = unpack_from('<II', data, at)
        n = ((adrp >> 5 & 0x7ffff) << 2) | (adrp >> 29 & 3)
        if n & (1 << 20):
            n -= 1 << 21
        slot = ((BASE + at) & ~0xfff) + (n << 12) + (add >> 10 & 0xfff)
        cls = HEAP + i * 0x1000
        u.mem_write(cls, bytes(0x1000))
        u.mem_write(slot, pack('<Q', cls))
        u.reg_write(UC_ARM64_REG_X0, HEAP + 0x7000)
        u.reg_write(UC_ARM64_REG_SP, STACK + 0x30000)
        u.reg_write(UC_ARM64_REG_LR, STOP)
        u.emu_start(BASE + start, STOP + 4, count=1000)
        assert u.reg_read(UC_ARM64_REG_PC) == STOP
        assert u.reg_read(UC_ARM64_REG_SP) == STACK + 0x30000
        host_ptr = unpack_from('<Q', u.mem_read(cls + 0xb0, 8))[0]
        url_ptr = unpack_from('<Q', u.mem_read(cls + 0xc8, 8))[0]
        port = unpack_from('<I', u.mem_read(cls + 0xdc, 4))[0]
        assert (objects[host_ptr], port, objects[url_ptr]) == (HOST, PORT, URL)
        cases.append({'pb': i + 1, 'host': objects[host_ptr], 'port': port, 'url': objects[url_ptr]})
    assert strings_seen == [HOST, URL] * 6
    return {'passed': True, 'native_initializers': cases,
            'boundary_dependencies': 'JVM string allocation and non-network settings are mocked',
            'live_server_login_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input')
    parser.add_argument('--fixture', action='store_true')
    parser.add_argument('--report')
    args = parser.parse_args()
    if args.fixture:
        fixture = json.loads(Path(args.input).read_text())
        assert fixture['source_sha256'] == BASE_NATIVE
        data = bytearray(0x2400000)
        for entry in fixture['ranges']:
            at, raw = entry['offset'], bytes.fromhex(entry['hex'])
            data[at:at + len(raw)] = raw
    elif args.input.endswith('.ipa'):
        with ZipFile(args.input) as z:
            data = z.read(NATIVE)
    else:
        data = Path(args.input).read_bytes()
    result = verify(data)
    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

