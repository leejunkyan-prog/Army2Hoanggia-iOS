'use strict';
// A profile is one server reply for one requested account. Never combine it
// with the logged-in account, a ranking avatar or a previously opened profile.
const ArmyProfile=(()=>{
 const stats=['Sinh lực','Sức mạnh','Phòng thủ','May mắn','Đồng đội'];
 function item(profile,slot){return slot===5?profile?.display?.outfit:profile?.items?.[slot];}
 function slots(profile){return Array.from({length:6},(_,i)=>i).filter(i=>{const p=item(profile,i);return p&&Number.isInteger(p.id)&&p.id>=0;});}
 function move(profile,selected,delta){const all=slots(profile);if(!all.length)return -1;const index=Math.max(0,all.indexOf(selected));return all[(index+delta%all.length+all.length)%all.length];}
 function title(profile,slot){const p=item(profile,slot);return p?p.name+(p.upgrade?' +'+p.upgrade:''):'';}
 function details(profile,slot){
  const p=item(profile,slot);if(!p||p.id<0)return '';
  const d=profile.details?.[slot],gems=profile.gems?.[slot]||[];
  if(!d)return title(profile,slot)+'. Chưa nhận được chỉ số chi tiết của món này từ máy chủ.';
  const format=(values,unit)=>stats.flatMap((name,i)=>values[i]?[name+' '+(values[i]>0?'+':'')+values[i]+unit]:[]);
  return [...format(d.flat,''),...format(d.percent,'%'),'Ngày hết hạn: '+d.days,'Slot trống '+d.slots].join('. ')+'.'+
   (gems.length?'\n'+gems.flatMap(gem=>[gem.name,gem.detail]).filter(Boolean).join('\n'):'');
 }
 function values(profile){return [profile.name+' - '+profile.character,...stats.map((name,i)=>name+': '+profile.abilities[i])].join('\n');}
 return {item,slots,move,title,details,values};
})();
if(typeof module!=='undefined')module.exports=ArmyProfile;
