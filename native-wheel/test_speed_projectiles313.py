"""Compare complete original AOT trajectory under1-step and8-step owners."""
import test_render_projectiles293 as old
from pathlib import Path
import json
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_PC
shots=old.shots;t=old.t;live=old.live
root=Path(__import__('os').environ.get('ARMY2_SPEED_QA',str(Path(__file__).parent/'build/speed313')));report=json.loads((root/'Army2HoangGia-2.4.1-Build313-MaxSpeed-unsigned.validation.json').read_text());j=report['variants'][0];raw=(root/'native313').read_bytes()
trace=[]
def bullet(uc,pc,size,data):
 p=t.reg(1);trace.append((t.get(p+0x48,'<i'),t.get(p+0x7c,'<i'),t.get(p+0x84,'<i')))
t.u.hook_add(UC_HOOK_CODE,bullet,begin=t.MAIN+0x57b638,end=t.MAIN+0x57b638)
t.symbols['_speedStep']=t.MAIN+j['old_update']
def shot():
 global trace
 trace=[];live.dispatch(22,shots.shot);assert t.get(live.projectiles+0x118,'<B')==1
 frames=0
 while t.get(live.projectiles+0x118,'<B'):
  frames+=1;assert frames<=100
  shots.millis+=31;t.call('_speedStep',t.ENV,live.arena)
 assert not shots.vector(t.get(live.projectileObject+0x30,'<Q'))
 return frames,trace.copy()
normal,expected=shot()
# Install exact313 executable bytes, keeping the existing render ownership.
t.u.mem_write(t.MAIN+0x250c000,raw[0x24cc000:0x24d0000]);t.nativeRanges.append((t.MAIN+0x250c000,t.MAIN+0x2510000))
t.u.mem_write(t.MAIN+j['old_update'],raw[j['old_update']-0x40000:j['old_update']-0x40000+4]);t.u.ctl_remove_cache(t.MAIN+j['old_update'],t.MAIN+j['old_update']+8)
t.extraNative[t.MAIN+j['getter']]=lambda:t.ret(10)
fast,actual=shot();assert actual==expected,(len(actual),len(expected));assert fast<normal and fast<=(normal+7)//8+1,(normal,fast)
result={'passed':True,'normal_owner_calls':normal,'max_owner_calls':fast,'identical_original_projectile_updates':len(expected),'busy_cleared':True,'limits':'Actual AOT arena, manager and projectile motion run. Graphics/audio/JVM/transport/actor updates are fixture boundaries. No physical device or server test.'}
(root/'speed313-projectiles.json').write_text(json.dumps(result,indent=2));print('PASS313 original trajectory integration:',result)
