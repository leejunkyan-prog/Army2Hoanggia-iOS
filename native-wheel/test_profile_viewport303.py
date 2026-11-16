"""Read the real PB canvas dimensions without borrowing profile item/stat data."""
import test_inventory_device282 as t
from unicorn import UC_HOOK_CODE
getters=(0x56ff3c,0x65a4f0,0x73f1b4,0x823e78,0x908b3c,0x9ed800)
players={}
def hook(u,pc,size,_):
    if pc in players:t.ret(players[pc])
t.u.hook_add(UC_HOOK_CODE,hook)
for v in range(6):
    canvas=t.alloc(0x180);player=t.alloc(0xe0)
    t.put(t.B+t.canvases[v],'<Q',canvas);t.put(canvas+0x130,'<i',432+v);t.put(canvas+0x128,'<i',602+v)
    t.put(player+0xd9,'<B',v);t.put(player+0xa8,'<q',493166945541);t.put(player+0xb0,'<q',2000)
    players[t.B+getters[v]]=player
    out=t.alloc(56);assert t.call('_AGLobbyReadAccount',t.E,v,out)==1
    assert (t.get(out,'<i'),t.get(out+4,'<i'),t.get(out+8,'<i'))==(v,432+v,602+v)
    assert t.get(out+40,'<q')==493166945541 and t.get(out+48,'<q')==2000
    # A temporarily missing local player cannot fabricate a remote profile.
    players[t.B+getters[v]]=0;out=t.alloc(56)
    assert t.call('_AGLobbyReadAccount',t.E,v,out)==0
    assert t.get(out+4,'<i')==432+v and t.get(out+8,'<i')==602+v
print('PASS compiled six-PB profile viewport: exact native width/height, independent PBs, 64-bit wallet ABI retained, no remote gear/stat synthesis when local player is absent')
