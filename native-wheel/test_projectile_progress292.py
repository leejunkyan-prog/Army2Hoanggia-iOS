"""Original ARM64 projectile progression, completion, and clock ticking.

Extends the real command22 parser/Actor.fire fixture past its old animation
wait boundary. Two consecutive shots execute the original manager update,
bullet constructor/update and completion code. Sprite/audio/transport/JVM
boundaries are fixtures; this is not a physical-device freeze reproduction,
terrain-impact rendering test, or a test of the entire GameCanvas thread.
"""
import base64
import test_spectator_live291 as live
from unicorn.arm64_const import UC_ARM64_REG_SP, UC_ARM64_REG_LR, UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_PC

t = live.t
vectors = {}
def vector(pointer):
    return vectors.setdefault(pointer, [])
def size():
    t.ret(len(vector(t.reg(1))))
def element():
    t.ret(vector(t.reg(1))[t.reg(2)])
def append():
    vector(t.reg(1)).append(t.reg(2)); t.ret()
def remove_index():
    del vector(t.reg(1))[t.reg(2)]; t.ret()
def clear():
    vector(t.reg(1)).clear(); t.ret()
def remove_object():
    vector(t.reg(1)).remove(t.reg(2)); t.ret(1)
for address, callback in ((0x1dfce8,size),(0x1dfcb8,element),(0x1dfcac,append),
                          (0x1dfce0,remove_index),(0x1dfcd8,clear),(0x1dfcdc,remove_object)):
    t.extraNative[t.MAIN + address] = callback

# These are real AOT bodies. All unlisted native calls still fail the fixture.
for start, end in (
    (0x5810f4,0x583540), # manager.update (includes its switch tables)
    (0x57ff9c,0x580fdc), # create bullet from decoded trajectory
    (0x57789c,0x5779bc), (0x577bd4,0x578f18), # bullet construction
    (0x57b638,0x57cbac), # bullet.update: coordinates and trajectory index
    (0x5836d8,0x583c50), (0x580fdc,0x5810f4), # remove/completion
    (0x576d44,0x576d94), (0x579214,0x579250), (0x5794a8,0x5794b8),
    (0x579c40,0x579cbc), (0x53e7dc,0x53e818), (0x53f248,0x53f284),
    (0x4f6d38,0x4f6d74), (0x4f6e68,0x4f6ee0), # native map bounds
    (0xaa6f80,0xaa6fd0), (0xaa7bfc,0xaa7c10), # Math.abs
    (0x5930f0,0x5931e8), (0x50ba04,0x50ba84), # flags and shooter origin
    (0x5b0754,0x5b0794), (0x5b0bac,0x5b0bd8), # camera target setters
    (0x58a6ec,0x58a9b4), # normal clock tick, before its exception handler
):
    t.nativeRanges.append((t.MAIN+start,t.MAIN+end))

# Sprite creation, visual effects, audio and outgoing shot completion packets
# do not replace projectile motion or its busy-flag completion.
for address in (0x50c2a8,0x5d8d4c):
    t.extraNative[t.MAIN+address] = lambda: t.ret(t.alloc(0x60))
for address in (0x5d8df4,0x5d8f90,0x58439c,0x5b6094,0x504a88):
    t.extraNative[t.MAIN+address] = lambda: t.ret()
t.extraNative[t.MAIN+0x53eef8] = lambda: t.ret(t.alloc(0x40))
t.extraNative[t.MAIN+0x576a80] = lambda: t.ret(t.alloc(0x200))
t.extraNative[t.MAIN+0x1c2c98] = lambda: t.ret(t.reg(1)) # checked class cast
# Deterministic visual jitter, not trajectory generation.
t.extraNative[t.MAIN+0x59fa1c] = lambda: t.ret(0)
t.extraNative[t.MAIN+0x53ed0c] = lambda: t.ret(t.get(live.a+0xd8,'<Q'))
t.extraNative[t.MAIN+0x512798] = lambda: t.ret(live.actor0)
# Exact StringBuilder/debug-literal/PrintStream boundaries reached by bullet0.
for address in (0x5019a8,0x5019d0,0x583d18,0x583cc8,0x583cf0,0x583c78,
                0x583ca0,0x583c50,0x578f18,0x583628,0xabf21c,0xabd104):
    t.extraNative[t.MAIN+address] = lambda: t.ret(t.alloc(0x30))
for address in (0xabd150,0xabd3d8,0xabd9b0,0xabd334,0xabd298,0xabd26c,
                0xabd2f8,0xabf628,0xabf700,0xa7eee4):
    t.extraNative[t.MAIN+address] = lambda: t.ret(t.reg(1))

# Match Java's static projectile-history arrays, normally set by class init.
for offset in (0xa0,0xa8,0xb0,0xb8):
    array = t.alloc(0x14+20*4); t.put(array+0x10,'<i',20)
    t.put(live.projectiles+offset,'<Q',array)
t.put(live.projectiles+0xd8,'<i',20)

millis = 100000
t.extraNative[t.MAIN+0xabf3a8] = lambda: t.ret(millis)
clock = t.get(live.a+0x110,'<Q')
t.put(clock+0x10,'<Q',millis)
t.put(clock+0x18,'<i',62)
t.put(clock+0x20,'<B',1)
def invoke(address, receiver):
    t.u.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000)
    t.u.reg_write(UC_ARM64_REG_LR,t.STOP)
    t.u.reg_write(UC_ARM64_REG_X0,t.ENV)
    t.u.reg_write(UC_ARM64_REG_X1,receiver)
    t.u.emu_start(t.MAIN+address,t.STOP+4,count=1000000)
    assert t.u.reg_read(UC_ARM64_REG_PC)==t.STOP

shot = next(base64.b64decode(encoded) for command,encoded in t.trace if command==22)
completed = []
for number in range(2):
    if number:
        live.dispatch(22,shot)
    assert t.get(live.projectiles+0x118,'<B')==1
    positions = []
    for frame in range(100):
        invoke(0x5810f4,live.projectileObject)
        for pointer in vector(t.get(live.projectileObject+0x30,'<Q')):
            positions.append((t.get(pointer+0x48,'<i'),t.get(pointer+0x7c,'<i'),t.get(pointer+0x84,'<i')))
        millis += 25
        invoke(0x58a6ec,clock)
        if not t.get(live.projectiles+0x118,'<B'):
            completed.append(frame); break
    else:
        raise AssertionError('Original projectile did not complete in bounded frames')
    assert len(positions)>40 and len(set(positions))>40, 'Trajectory did not advance'
    assert positions[0]==(0,467,349), positions[:2]
    assert any(x==815 and y==651 for _,x,y in positions)
    assert not vector(t.get(live.projectileObject+0x30,'<Q'))
assert len(completed)==2
assert t.get(clock+0x18,'<i')<62, 'Original clock did not tick alongside updates'
print('PASS original ARM64: two consecutive shots spawn, follow 43 trajectory frames, remove bullets and clear busy; original clock ticks. Resource/JVM/transport boundaries mocked; no claim of physical-device freeze reproduction.')
