'use strict';
const ui=PixelUI;
const send=value=>window.webkit.messageHandlers.viewer.postMessage(value);
const aliases={[-22]:-7,[-11]:-7,27:-7,35:-7,82:-7,114:-7,[-21]:-6,76:-6,108:-6,10:-5,13:-5,53:-5,70:-5,102:-5,50:-1,56:-2,52:-3,54:-4};
let phase=-1,message='',free=false,menu=null,selection=0,awaiting=false,nativeMenu=false,angle=-1;
let drag=null,dragCode=0,pbs=false,variant=1;
function stopDrag(){
 if(dragCode)send(['key',1,dragCode]);
 drag=null;dragCode=0;
}
function openMenu(value){
 stopDrag();
 menu=value;selection=0;
 send(value?'menuOpen':'menuClosed');
}
function answer(accept){
 if(phase!==0||awaiting)return;
 awaiting=true;
 send(accept?'accept':'decline');
}
function nativeAction(action){openMenu(null);send(['option',action]);}
const main=[
 ['TIẾP TỤC',()=>openMenu(null)],
 ['LỰC MAX',()=>nativeAction(1)],
 ['V9 MENU',()=>openMenu('v9')],
 ['BẬT/TẮT ICON ĐỘI',()=>nativeAction(3)],
 ['BẠN BÈ',()=>nativeAction(4)],
 ['TIN NHẮN',()=>nativeAction(5)],
 ['RỜI TRẬN CHIẾN',()=>{openMenu(null);send('leave');}],
];
const v9=[
 ['CAMERA',()=>{openMenu(null);send('camera');}],
 ['TRỞ RA',()=>openMenu('main')],
];
const options=()=>menu==='v9'?v9:main;
window.watchCameraMode=flag=>{free=!!flag;if(!free)stopDrag();};
window.watchNativeMenu=flag=>{nativeMenu=!!flag;};
window.watchVariant=number=>{variant=number;};
window.watchAngle=value=>{if(Number.isInteger(value)&&value>=0&&value<360)angle=value;};
window.setWatchPhase=(next,question)=>{
 if(next!==phase){awaiting=false;menu=null;nativeMenu=false;pbs=false;free=false;angle=-1;stopDrag();}
 phase=next;message=question||'';
};
window.watchKey=key=>{
 const code=aliases[key]??key;
 if(phase===0){
  if(code===-6||code===-5)answer(true);
  else if(code===-7)answer(false);
  return;
 }
 if(phase===1&&code===-7){send('leave');return;}
 if(phase!==2||nativeMenu)return;
 if(key===-6&&!menu){send('camera');return;}
 if(menu){
  const list=options();
  if(code===-1||code===-3)selection=(selection+list.length-1)%list.length;
  else if(code===-2||code===-4)selection=(selection+1)%list.length;
  else if(code===-5||code===-6)list[selection][1]();
  else if(code===-7)openMenu(menu==='v9'?'main':null);
 }else if(code===-6)openMenu('main');
 else if(code===-7)send('camera');
};
const desktop={ArrowUp:-1,ArrowDown:-2,ArrowLeft:-3,ArrowRight:-4,Enter:-5,Escape:-7,F1:-6,F2:-7,ContextMenu:-21};
for(const type of ['keydown','keyup'])addEventListener(type,event=>{
 const code=desktop[event.key];if(!code)return;
 event.preventDefault();
 if(type==='keydown'&&!event.repeat)watchKey(code);
 if(code>=-4&&(type==='keyup'||(phase===2&&free&&!menu)))send(['key',type==='keyup'?1:0,code]);
});
function paintMenu(){
 const list=options(),w=136,h=18+list.length*22,x=92,y=Math.max(7,Math.floor((ui.height-h)/2));
 ui.zone(0,0,320,ui.height,()=>openMenu(null));
 ui.stripedBox(x,y,w,h);
 list.forEach(([label,action],i)=>{
  const row=y+17+i*22;
  if(i===selection)ui.rect(x+5,row,w-10,19,'#ffdf4e');
  ui.text(label,160,row+3,{title:true,align:'center',max:w-12});
  ui.zone(x+5,row,w-10,19,action);
 });
}
function cameraControls(){
 const x=20,y=ui.height-45;
 for(const [code,dx,dy,rotation] of [[-1,0,-12,-Math.PI/2],[-2,0,12,Math.PI/2],[-3,-12,0,Math.PI],[-4,12,0,0]]){
  ui.g.save();ui.g.translate(x+dx,y+dy);ui.g.rotate(rotation);
  ui.g.lineJoin='round';ui.g.lineWidth=1.2;ui.g.strokeStyle='#214247';ui.g.fillStyle='#ffdb56';
  ui.g.beginPath();ui.g.moveTo(-4,-4);ui.g.lineTo(4,0);ui.g.lineTo(-4,4);
  ui.g.closePath();ui.g.fill();ui.g.stroke();ui.g.restore();
  ui.zone(x+dx-6,y+dy-6,12,12,()=>{send(['nudge',code]);});
 }
}
ui.start(()=>{
 if(phase<0)return;
 if(phase===2){
  if(nativeMenu)return;
  ui.text('Đang xem',5,15,{max:100});
  if(angle>=0){
   ui.text('Góc: '+angle,160,27,{align:'center',color:'#fff',outline:true,max:54});
  }
  if(free&&!menu)cameraControls();
  ui.zone(0,0,44,40,()=>openMenu('main'));
  ui.zone(45,0,24,38,()=>nativeAction(5));
  ui.zone(280,0,40,42,()=>{pbs=!pbs;});
  if(pbs)for(let pb=1;pb<=6;pb++){
   const x=72+(pb-1)*30,y=39;
   ui.g.save();ui.g.translate(x,y+28);ui.g.scale(1,-1);ui.sprite('pb'+pb,0,0,27,27);ui.g.restore();
   ui.zone(x,y,27,28,()=>{pbs=false;if(pb!==variant)send(['pb',pb]);});
  }
  if(menu)paintMenu();
  return;
 }
 const title=phase===0?message:phase===3?message||'Đang rời trận…':'Đang tải trận đấu…';
 ui.bottomDialog(ui.wrapText(title,290));
 ui.footer(phase===0?'Có':'','',phase===0?'Không':phase===1?'Hủy':'',
  ()=>answer(true),()=>answer(true),()=>phase===0?answer(false):phase===1&&send('leave'));
},{transparent:true});
ui.canvas.addEventListener('pointerdown',e=>{
 if(phase!==2||!free||menu||nativeMenu||e.clientY<40)return;
 const rect=ui.canvas.getBoundingClientRect(),x=(e.clientX-rect.left)*320/rect.width,y=(e.clientY-rect.top)*ui.height/rect.height;
 if(x<39&&y>ui.height-65)return;
 drag=[e.clientX,e.clientY];ui.canvas.setPointerCapture(e.pointerId);
});
ui.canvas.addEventListener('pointermove',e=>{
 if(!drag)return;
 const dx=e.clientX-drag[0],dy=e.clientY-drag[1];
 if(Math.max(Math.abs(dx),Math.abs(dy))<3)return;
 const code=Math.abs(dx)>Math.abs(dy)?(dx>0?-3:-4):(dy>0?-1:-2);
 if(code!==dragCode){
  if(dragCode)send(['key',1,dragCode]);
  dragCode=code;send(['key',0,code]);
 }
 drag=[e.clientX,e.clientY];
});
for(const type of ['pointerup','pointercancel','lostpointercapture'])ui.canvas.addEventListener(type,stopDrag);
send('ready');

