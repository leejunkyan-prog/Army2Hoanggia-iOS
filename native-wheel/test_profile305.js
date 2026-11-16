'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require('playwright');
(async()=>{
 const root=path.join(__dirname,'viewer'),server=http.createServer((req,res)=>{
  const file=path.resolve(root,'.'+new URL(req.url,'http://127.0.0.1').pathname);
  if(!file.startsWith(root+path.sep)){res.writeHead(404);res.end();return;}
  fs.readFile(file,(err,data)=>{if(err){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':'image/png');res.end(data);});
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({args:['--no-sandbox'],executablePath:process.env.ARMY2_CHROMIUM});
 const page=await browser.newPage({viewport:{width:432,height:626},deviceScaleFactor:1});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.messages=[];window.webkit={messageHandlers:{lobby:{postMessage:m=>messages.push(m)}}};});
 await page.goto('http://127.0.0.1:'+server.address().port+'/lobby.html');
 const result=await page.evaluate(async()=>{
  // Asymmetric fixture proves that the complete native pose is displayed once
  // at its anchor, without applying another flip or unrelated clothing crops.
  const fixture=document.createElement('canvas');fixture.width=fixture.height=80;const x=fixture.getContext('2d');
  x.fillStyle='#24ade5';x.fillRect(37,40,8,24);x.fillStyle='#ff0044';x.fillRect(45,42,16,5);x.fillStyle='#13c142';x.fillRect(32,59,5,5);
  const pixels=Array.from(x.getImageData(0,0,80,80).data).map((n,i)=>i%4===3?255:n),png=fixture.toDataURL().split(',')[1];
  const rows=Array.from({length:10},(_,hero)=>({character:hero,parts:[300,301,302,303,304].map(p=>p+hero*5),aura:0}));
  for(const row of rows){lobbyAvatarNeeded(row.character,row.parts);lobbyAvatarNeeded(row.character,row.parts);}
  const requests=messages.filter(m=>m[0]==='avatar').map(m=>m[1]);
  const wrong={hero:0,parts:[999,999,999,999,999],status:0,png};lobbyNativeAvatar(wrong);
  const before=avatarStatuses.has('0:999,999,999,999,999');
  for(const r of requests)lobbyNativeAvatar({...r,status:0,png});
  await new Promise(r=>setTimeout(r,100));
  const g=PixelUI.g;g.save();g.setTransform(1,0,0,1,0,0);g.imageSmoothingEnabled=false;
  const samples=rows.map(row=>{g.clearRect(20,20,80,80);PixelUI.avatar(row,60,84,1);return Array.from(g.getImageData(20,20,80,80).data);});g.restore();
  // Same template ID for two characters must not share a gear icon cache key.
  function icon(color){x.clearRect(0,0,80,80);x.fillStyle=color;x.fillRect(0,0,80,80);return fixture.toDataURL().split(',')[1];}
  PixelUI.setNativeProfileIcons(0,[56],[icon('#ff1234')]);PixelUI.setNativeProfileIcons(1,[56],[icon('#1456ff')]);
  await new Promise(r=>setTimeout(r,100));g.save();g.setTransform(1,0,0,1,0,0);
  const gear=[0,1].map(hero=>{g.clearRect(20,20,24,24);PixelUI.gearIcon(hero,0,56,32,32,16,null,true);return Array.from(g.getImageData(32,32,1,1).data);});g.restore();
  return {requests,before,samples,pixels,gear};
 });
 assert.equal(result.requests.length,10);assert.equal(result.before,false);
 for(let hero=0;hero<10;hero++){assert.equal(result.requests[hero].hero,hero);assert.equal(Buffer.compare(Buffer.from(result.samples[hero]),Buffer.from(result.pixels)),0,'Native pose must retain every decoded pixel, its right facing weapon and foot anchor');}
 assert.deepEqual(result.gear,[[255,18,52,255],[20,86,255,255]]);
 assert.deepEqual(errors,[]);await browser.close();await new Promise(r=>server.close(r));
 console.log('PASS profile305 browser: ten character/appearance requests, duplicate throttling, unknown appearance response rejected, exact complete right-facing native PNG/anchor, Gun and AK with same template ID retain distinct gear icons');
})().catch(e=>{console.error(e);process.exit(1);});
