"""C-only Darwin ARM64 fallback check when Xcode/Actions is unavailable.

Usage: test_hud_cross310.py PREVIOUS_AGWHEEL HUD_C_DYLIB TEST_MODULE
Compile unchanged HUD.c with zig0.14.1 cc -target aarch64-macos.12.0 -std=c11
-O1 -dynamiclib -nostdlib -Wl,-undefined,dynamic_lookup. This tests Darwin C
ABI/logic beside the prior framework, not an iPhone IPA or Xcode build.
"""
from pathlib import Path
import sys,struct,runpy
framework,dylib,case=sys.argv[1:]
assert case in ('test_hud_integration310','test_hud309','test_hud_bridges309')
sys.argv=[case+'.py',framework]
import test_inventory_device282 as t
import lief
p=Path(dylib);blob=p.read_bytes();m=lief.MachO.parse(str(p)).at(0);L=t.L+0x1000000
for seg in m.segments:
 if seg.virtual_size:t.u.mem_map(L+seg.virtual_address,(seg.virtual_size+4095)&-4096);t.u.mem_write(L+seg.virtual_address,blob[seg.file_offset:seg.file_offset+seg.file_size])
for r in m.relocations:
 if r.size==64 and int(r.type)==1:t.put(L+r.address,'<Q',t.get(L+r.address,'<Q')+L)
for binding in m.dyld_info.bindings:
 name=binding.symbol.name
 if name in t.names:address=t.names[name]
 elif name in t.symbols:address=t.symbols[name]
 elif name=='dyld_stub_binder':address=t.STOP
 else:
  address=t.F+0x28000+len(t.imports)*16;t.imports[address]=name;t.names[name]=address
 t.put(L+binding.address,'<Q',address)
for name in ('_AGHUDReceive','_AGHUDPaint','_AGHUDCanvasPaint','_AGHUDSkipBar','_AGHUDImage','_AGRankPaintActor'):
 values={s.value for s in m.symbols if s.name==name and s.value};assert len(values)==1,(name,values)
 old=t.symbols[name];new=L+values.pop();delta=new-old;assert delta%4==0 and -(1<<27)<=delta<(1<<27)
 t.u.mem_write(old,struct.pack('<I',0x14000000|((delta//4)&0x3ffffff)));t.symbols[name]=new
print('C-only Darwin ARM64 local cross-check; not an IPA/Xcode/Simulator result.',flush=True)
runpy.run_path(str(Path(__file__).parent/(case+'.py')),run_name='__main__')
