'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('playwright'),{ArmyWriter}=require('./viewer/market.js'),{readGearAtlas}=require('./viewer/battlefield.js');
const bytes=fs.readFileSync(path.join(__dirname,'fixtures/equip306.bin')),atlas=readGearAtlas(bytes);
assert.equal(atlas.frames.size,1556,'The original APK cache has six geometry poses and ten attribute bytes per template');
const visual=Array.from({length:5},(_,s)=>Number([...atlas.frames.keys()].find(k=>k.startsWith('0:'+s+':')).split(':')[2]));
const worn=[54,52,53,55,56],encode=b=>Buffer.from(b).toString('base64');
function board(){const rows=[1,2,3,78,79,80,81,82,83,84,85,86,87],w=new ArmyWriter().int(1129591862).byte(1).int(1).int(88).int(99).byte(rows.length);
 for(const rank of rows)w.int(rank).int(rank+100).utf('fixture-'+rank).int(rank<4?999:1);
 for(const rank of rows){w.byte(0);visual.forEach(id=>w.short(id));w.byte(46).int(0);}
 w.int(1397050438).int(88).int(99).utf('self-fixture').int(146).byte(0);visual.forEach(id=>w.short(id));return w.byte(55).int(0).bytes;}
function profile(){const w=new ArmyWriter().int(1129591862).byte(2).int(2).int(1).utf('fixture-1').int(999).utf('Gunner').byte(5);
 [193585,571,14306,15097,14337].forEach(n=>w.int(n));worn.forEach((id,s)=>w.short(id).utf('fixture item '+s).byte(16).byte(3).byte(0));
 w.byte(0);visual.forEach(id=>w.short(id));return w.byte(1).byte(46).long(42327685480).long(46042461728).int(0).byte(0).bytes;}
(async()=>{
 const root=path.join(__dirname,'viewer'),server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+new URL(req.url,'http://127.0.0.1').pathname);if(!p.startsWith(root+path.sep)){res.writeHead(404);res.end();return;}fs.readFile(p,(err,b)=>{if(err){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.html')?'text/html':'image/png');res.end(b);});});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;
 try{
  browser=await chromium.launch({args:['--no-sandbox'],executablePath:process.env.ARMY2_CHROMIUM});const page=await browser.newPage({viewport:{width:432,height:626}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{window.messages=[];window.webkit={messageHandlers:{lobby:{postMessage:m=>messages.push(m)}}};});
  await page.goto('http://127.0.0.1:'+server.address().port+'/lobby.html');await page.evaluate(()=>{lobbyViewport(432,[432,0,0,0,0,0,0],602);openTab('field',0);});await page.evaluate(b=>receiveFrame(-120,b),encode(board()));
  assert.deepEqual(await page.evaluate(()=>{const p=fieldLayout(432,602);return[p.rowH,p.top,p.bottom,p.footerY,p.rows[3],p.rows.length];}),[50,72,512,567,null,14]);
  await page.evaluate(()=>{for(let i=0;i<9;i++)lobbyKey(-2);});await page.waitForTimeout(70);
  assert.ok(await page.evaluate(()=>scroll>0&&fieldPane.top-scroll<fieldPane.top),'Top-three cards scroll together with the rest, as in the supplied video');
  const selected=await page.evaluate(()=>focus);await page.mouse.move(150,350);await page.mouse.down();await page.mouse.move(150,170,{steps:8});await page.mouse.up();assert.equal(await page.evaluate(()=>focus),selected,'Dragging the list must not activate a row');
  await page.evaluate(()=>{focus=0;fieldAutoFocus=true;profile();});await page.evaluate(b=>receiveFrame(-120,b),encode(profile()));await page.evaluate(b=>lobbyGearAtlas(b),encode(bytes));
  await page.waitForFunction(()=>PixelUI.serverGearIconMetadata(reply.avatar.character,0,reply.items[0].id).kind===2);
  const seen=await page.evaluate(()=>{
   const calls=[],frames=[],gear=PixelUI.gearIcon,frame=PixelUI.equipmentFrame,item=PixelUI.equipmentItem;
   PixelUI.gearIcon=(...args)=>{calls.push(args.slice(0,3));return gear(...args);};PixelUI.equipmentFrame=(...args)=>{frames.push(args);return frame(...args);};
   PixelUI.equipmentItem=(...args)=>{calls.push(args.slice(0,3));return item(...args);};
   drawProfile();PixelUI.gearIcon=gear;PixelUI.equipmentFrame=frame;PixelUI.equipmentItem=item;
   return {calls,frame:frames.at(-1),expectedY:Math.floor((Math.round(PixelUI.height*432/320)-35-170)/2)};
  });
  assert.deepEqual(seen.calls.slice(0,5),visual.map((id,s)=>[0,s,id]),'Upper slots use the selected account appearance IDs');
  assert.deepEqual(seen.calls.slice(5,9),worn.slice(0,4).map((id,s)=>[0,s,id]),'Lower item grid uses the worn stat-bearing items');
  assert.deepEqual(seen.frame,[124,seen.expectedY]);
  const native=await page.evaluate(async()=>{
   lobbyAvatarNeeded(reply.avatar.character,reply.avatar.parts);const c=document.createElement('canvas');c.width=240;c.height=80;const g=c.getContext('2d');['#ff1234','#1456ff','#24bb67'].forEach((color,i)=>{g.fillStyle=color;g.fillRect(i*80,0,80,80);});
   lobbyNativeAvatar({hero:reply.avatar.character,parts:reply.avatar.parts,status:0,png:c.toDataURL().split(',')[1]});await new Promise(r=>setTimeout(r,100));
   const dst=PixelUI.g;dst.save();dst.setTransform(1,0,0,1,0,0);const result=[];
   for(const preview of [false,true]){dst.clearRect(20,20,80,80);PixelUI.avatar({...reply.avatar,preview,aura:0},60,84,1);result.push([...dst.getImageData(50,50,1,1).data]);}dst.restore();
   return {pixels:result,preview:Math.floor(PixelUI.frame*42/200)%5<=2?1:2};
  });
  assert.deepEqual(native.pixels[0],[255,18,52,255]);assert.deepEqual(native.pixels[1],native.preview===1?[20,86,255,255]:[36,187,103,255]);assert.deepEqual(errors,[]);
  console.log('PASS APK306 reference: parses all1556 actual templates and the real icon PNG; native432 board/scroll/gap/self-card geometry and touch drag; separate appearance/item icon IDs; APK-centered184x170 profile, real atlas icons, right-facing rank pose and alternating profile poses');
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exit(1);});
