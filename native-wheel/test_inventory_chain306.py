"""Actual C6 update/grid callbacks across 7->8->9 and a new login."""
import test_inventory_pipeline305 as p
t=p.t
for v in range(6):
 clazz=t.alloc(0x180);pool=t.alloc(0xc0);canvas=t.alloc(0x180);screen=t.alloc(0xe0);serviceClass=t.alloc(0xb0);service=t.alloc(0x30)
 t.put(t.B+t.classes[v],'<Q',clazz);t.put(t.B+t.pools[v],'<Q',pool);t.put(t.B+t.canvases[v],'<Q',canvas)
 t.put(screen,'<Q',clazz);t.put(clazz+0xa0,'<Q',screen);t.put(canvas+0xb8,'<Q',screen);t.put(canvas+0x130,'<i',432);t.put(canvas+0x128,'<i',602)
 connection=(0x207b870,0x20ab650,0x20d9350,0x2107040,0x2134d30,0x2162a20)[v]
 t.put(t.B+connection,'<Q',serviceClass);t.put(serviceClass+0xa0,'<Q',service);t.put(service+0x10,'<Q',12300+v)
 gear=t.item(70001,equipment=True);seven=t.item(7,2595);stone=t.item(103,40)
 def set_source(items):
  vec=t.vector(items);t.put(pool+0xa8,'<Q',vec);t.put(screen+0x70,'<Q',vec);return vec
 vec=set_source([gear,seven,stone]);t.call('_AGInventoryTick',t.E,v)
 eight=t.item(8,347);t.put(seven+0x90,'<q',4);vec=set_source([gear,seven,stone,eight]);t.call('_AGInventoryTick',t.E,v)
 assert t.displayed(screen)[0]==8 and t.get(screen+0x90,'<Q')==eight
 nine=t.item(9,43);t.put(eight+0x90,'<q',4);vec=set_source([gear,seven,stone,eight,nine]);t.call('_AGInventoryTick',t.E,v)
 assert t.displayed(screen)[:2]==[9,8] and t.get(screen+0x90,'<Q')==nine
 t.call('_AGInventoryOrder',t.E,v,canvas,0,0);t.call('_AGInventoryTick',t.E,v);assert t.displayed(screen)[0]==9
 t.put(service+0x10,'<Q',0);t.call('_AGInventoryTick',t.E,v);t.put(service+0x10,'<Q',45600+v);t.call('_AGInventoryTick',t.E,v)
 assert t.displayed(screen)==[70001,7,8,9,103]
 assert t.ids(vec)==[70001,7,103,8,9]
 t.call('_AGInventoryOrder',t.E,v,canvas,0,0)
print('PASS APK video gem chain306: 2595 level7 ->347 level8 ->43 level9; newest first/selected, reopening retains order, logout/login groups gear/gems/stones, all six PBs and unchanged server quantities/order')
