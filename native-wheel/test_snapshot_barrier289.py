"""Delayed snapshot replay and automatic native scene restoration.

Run the compiled iPhone ARM64 adapter. The server trace is replayed without
SP7, with delayed HP/status packets; no live account/device is used.
"""
import base64
import test_native_watch as t
for v in range(6):
 a,c,g,cam,back,oldMap,oldTiles=t.objects[v]
 t.stillWatching=True
 for cmd,encoded in t.trace:
  p=base64.b64decode(encoded)
  if cmd==-102 and p[3] in (3,4,5):assert t.packet(v,p)==1
  elif cmd==8:t.observe(v,cmd,p)
 assert not t.call('_AGNativeWatchRunning',v)
 # Receiving SP5 is not completion. Even after a slow frame, an early
 # completion attempt must not change wait policy for subsequent HP replay.
 for delay in (.41,1,4):
  t.now+=delay
  assert not t.call('_AGNativeWatchTryFinishSnapshot',t.ENV,v),'Partial snapshot became live by elapsed time'
  t.snapshotSync=True;t.put(c+0x13c,'<B',1);before=t.waitCalls
  for kind in range(4):t.call('_AGBattleAwait',t.ENV,c,v,kind,0)
  assert t.waitCalls==before
 t.snapshotSync=False
 assert t.packet(v,next(p for p in t.sp if p[3]==7))==1
 assert t.call('_AGNativeWatchRunning',v)
 assert t.get(c+0x13c,'<B')==0,'Snapshot flash blocks live frames'
 # Force/message dialog must not leak over the area list on match end.
 t.put(c+0x108,'<Q',t.alloc(0x40));t.stillWatching=False
 assert t.call('_AGNativeWatchTryEnd',t.ENV,v)==1
 assert t.get(c+0xb8,'<Q')==back
 assert t.get(c+0x108,'<Q')==0
 assert t.get(a+0xc8,'<Q')==oldMap and t.get(g+0xb8,'<Q')==oldTiles
 assert not t.call('_AGNativeWatchRunning',v)
 assert all(n==0 for n in t.pins.values())
print('PASS delayed snapshot barrier: six PBs, no early live state at .41/1/4 seconds, no HP wait, SP7 completes, native end restores area screen and clears dialogs/roots')
