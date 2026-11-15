"""Execute the compiled viewer sender through its real native message writer.

Message allocation/constructor, byte writer and socket send are JNI boundaries;
the framework's validation, same-session guard and payload loop execute ARM64.
"""
import re
from pathlib import Path
import test_native_watch as t

text = (Path(__file__).parent / 'NativeMap.h').read_text()
maps = [tuple(int(x, 16) for x in re.findall(r'0x[0-9a-f]+', row))
        for row in re.findall(r'\{([^{}]+)\}', text) if '0x' in row]
assert len(maps) == 6
messages, output = {}, []

def allocate():
    p, writer = t.alloc(0x50), t.alloc(0x30)
    t.put(p + 0x18, '<Q', writer)
    messages[p] = {'writer': writer, 'bytes': bytearray()}
    t.ret(p)

def ctor():
    messages[t.reg(1)]['command'] = t.reg(2) & 255
    t.ret()

def write():
    message = next(x for x in messages.values() if x['writer'] == t.reg(1))
    message['bytes'].append(t.reg(2) & 255)
    t.ret()

def send():
    message = messages[t.reg(2)]
    output.append((t.reg(1), message['command'], bytes(message['bytes'])))
    t.ret()

for service, alloc, construct, socket_send, room in maps:
    t.extraNative[t.MAIN + alloc] = allocate
    t.extraNative[t.MAIN + construct] = ctor
    t.extraNative[t.MAIN + socket_send] = send
t.extraNative[t.MAIN + 0xa64a3c] = write
room0 = t.alloc(1)
for v in range(6):
    session = t.get(t.serviceObjects[v] + 0x10, '<Q')
    t.call('_AGViewerConnection', t.ENV, v)
    assert t.reg(0) == session
    before = len(output)
    assert t.call('_AGViewerSend', t.ENV, v, session, 7, room0, 1) == 1
    assert output[before:] == [(session, 7, b'\0')]
    assert t.call('_AGViewerSend', t.ENV, v, session + 1, 7, room0, 1) == 0
    assert len(output) == before + 1, 'Old session sent to a replacement connection'
    assert t.call('_AGViewerSend', t.ENV, v, session, 7, room0, 0) == 0
    assert len(output) == before + 1

print('PASS compiled iPhone ARM64 room0 sender: six PB sessions, command7 byte0, '
      'real payload writer and rejection of stale sessions/invalid lengths')
