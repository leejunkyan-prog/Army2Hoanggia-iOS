'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const zlib=require('node:zlib');
const http=require('node:http');
const {chromium}=require('playwright');
const {ArmyWriter}=require('./viewer/market.js');
const {ArmyBattlefield}=require('./viewer/battlefield.js');
const Profile=require('./viewer/profile.js');
const w=()=>new ArmyWriter();
// Deliberately synthetic, flat-color PNGs make wrong-image substitution
// measurable. They are not photographs or captured server item artwork.
function testPng(colors){
 const crc=bytes=>{let c=0xffffffff;for(const b of bytes){c^=b;for(let i=0;i<8;i++)c=c&1?0xedb88320^(c>>>1):c>>>1;}return(c^0xffffffff)>>>0;};
 const chunk=(name,bytes)=>{const type=Buffer.from(name),out=Buffer.alloc(bytes.length+12);out.writeUInt32BE(bytes.length);type.copy(out,4);bytes.copy(out,8);out.writeUInt32BE(crc(Buffer.concat([type,bytes])),bytes.length+8);return out;};
 const ihdr=Buffer.alloc(13);ihdr.writeUInt32BE(16);ihdr.writeUInt32BE(16*colors.length,4);ihdr[8]=8;ihdr[9]=6;
 const rows=[];for(const rgb of colors)for(let y=0;y<16;y++)rows.push(Buffer.concat([Buffer.from([0]),Buffer.concat(Array.from({length:16},()=>Buffer.from([...rgb,255])))]));
 return Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',ihdr),chunk('IDAT',zlib.deflateSync(Buffer.concat(rows))),chunk('IEND',Buffer.alloc(0))]);
}
const diamondColor=[80,180,255],platinumColor=[220,220,230],diamondPng=testPng([diamondColor]),platinumPng=testPng([platinumColor]);
const rows=[{rank:1,id:41,name:'top-magenta',hero:0},{rank:2,id:52,name:'other-account',hero:1}];
function board(serial){
 const p=w().int(1129591862).byte(1).int(serial).int(90).int(700).byte(rows.length);
 for(const r of rows)p.int(r.rank).int(r.id).utf(r.name).int(999);
 for(const r of rows){p.byte(r.hero);for(let i=0;i<5;i++)p.short(0);p.byte(99).int(0);}
 return Uint8Array.from(p.bytes);
}
const magentaIds=[56,54,55,57,58];
function profile(serial,row,{hero=9,upgrade=16,health=1935000000,costume=true,details=true,icons=true}={}){
 const ids=hero===9?magentaIds:[54,52,53,55,56];
 const p=w().int(1129591862).byte(2).int(serial).int(row.rank).utf(row.name).int(999).utf(hero===9?'Magenta':'Miss 6').byte(5);
 for(const value of [health,9274,14632,14679,14569])p.int(value);
 for(let i=0;i<5;i++)p.short(ids[i]).utf(['súng','nón','áo','quần','kính'][i]+(hero===9?' kim cương 3':' bạch kim')).byte(upgrade).byte(hero===9?7:6).byte(0);
 p.byte(hero);for(const id of ids)p.short(id);
 p.byte(1).byte(98).long(493166945541).long(2000).int(240).byte(costume?1:0);
 if(costume)p.short(2999).utf('Bộ trang phục của top 1').byte(12).byte(7).byte(0);
 if(details){
  p.int(0x44455448).byte(6);
  for(let i=0;i<6;i++){
   p.byte(i<5||costume?1:0);if(i===5&&!costume)continue;
   p.byte(5);for(const v of i===5?[999,888,777,666,555]:[115+i,181,95,96,91])p.int(v);
   p.byte(5);for(const v of [54,60,44,43,43])p.int(v);
   p.int(20+i).byte(i===5?2:0);
  }
  p.int(0x47454d49).byte(6);
  for(let i=0;i<6;i++){p.byte(i<5||costume?1:0);if(i<5||costume)p.utf('Ngọc của '+row.name+' ô '+i).utf('Sinh lực +7%. Sức mạnh +8%.');}
 }
 if(icons){p.int(0x49434f4e).byte(6);for(let i=0;i<6;i++){const png=i<5||costume?(hero===9?diamondPng:platinumPng):Buffer.alloc(0);p.short(png.length);for(const b of png)p.byte(b);}}
 return Uint8Array.from(p.bytes);
}
function encoded(p){return Buffer.from(p).toString('base64');}
// Protocol/model: the selected account is sealed into this request. A fresh
// profile may have changed hero since the ranking list was received.
const f=new ArmyBattlefield();f.request(1);f.receive(board(1));f.request(2,f.board[0]);
const data=f.receive(profile(2,rows[0]));
assert.equal(data.id,41);assert.equal(data.avatar.character,9);assert.equal(data.character,'Magenta');
assert.deepEqual(data.items.map(p=>[p.id,p.upgrade]),magentaIds.map(id=>[id,16]));
assert.equal(data.abilities[0],1935000000);assert.deepEqual(Profile.slots(data),[0,1,2,3,4,5]);
assert.match(Profile.details(data,0),/Sinh lực \+115/);assert.match(Profile.details(data,0),/Sức mạnh \+60%/);
assert.match(Profile.details(data,5),/Sinh lực \+999/);assert.match(Profile.details(data,5),/Ngọc của top-magenta ô 5/);
const wire=f.request(2,f.board[1]);assert.equal(new DataView(Uint8Array.from(wire).buffer).getInt32(13),52);
assert.equal(f.receive(profile(2,rows[0])).type,'stale');
assert.throws(()=>f.receive(profile(3,rows[0])),/Hạng đã thay đổi/);
const other=f.receive(profile(3,rows[1],{hero:1,upgrade:0,costume:false,health:1234}));assert.equal(other.id,52);
assert.equal(other.abilities[0],1234);assert.ok(other.items.every(p=>p.upgrade===0));
f.request(2,f.board[0]);const missing=f.receive(profile(4,rows[0],{details:false}));
assert.match(Profile.details(missing,0),/Chưa nhận được/);
assert.doesNotMatch(Profile.details(missing,0),/Sinh lực \+115/,'Missing metadata must not reuse a previous item');
const sparse={...data,items:data.items.map((p,i)=>i===1?{...p,id:-1}:p),display:{...data.display,outfit:null}};
assert.deepEqual(Profile.slots(sparse),[0,2,3,4]);assert.equal(Profile.move(sparse,0,1),2);

(async()=>{
 // A same-origin HTTP fixture is required for exact canvas pixel reads.
 // Chromium treats independent file:// images as opaque origins.
 let server,viewerURL=process.env.ARMY2_VIEWER_URL;
 if(!viewerURL){
  const root=path.join(__dirname,'viewer');
  server=http.createServer((req,res)=>{
   const file=path.resolve(root,'.'+new URL(req.url,'http://127.0.0.1').pathname);
   if(!file.startsWith(root+path.sep)){res.writeHead(404);res.end();return;}
   fs.readFile(file,(error,bytes)=>{if(error){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':file.endsWith('.png')?'image/png':'application/octet-stream');res.end(bytes);});
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));viewerURL='http://127.0.0.1:'+server.address().port+'/lobby.html';
 }
 const browser=await chromium.launch({args:['--no-sandbox'],executablePath:process.env.ARMY2_CHROMIUM});
 const page=await browser.newPage({viewport:{width:432,height:660},deviceScaleFactor:2});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.sent=[];window.profileDiagnostics=[];window.webkit={messageHandlers:{lobby:{postMessage:a=>a[0]==='profileDiagnostic'?profileDiagnostics.push(a[1]):sent.push(a)}}};});
 await page.goto(viewerURL);
 await page.evaluate(()=>{const note=document.createElement('div');note.textContent='DỮ LIỆU KIỂM THỬ — KHÔNG PHẢI ACC THẬT';note.style.cssText='position:fixed;top:0;left:0;right:0;background:#173b58;color:white;text-align:center;font:12px sans-serif;padding:6px;pointer-events:none';document.body.append(note);});
 await page.evaluate(()=>{lobbyViewport(432,[432,0,0,0,0,0,0],602);openTab('field',0);});
 await page.evaluate(b=>receiveFrame(-120,b),encoded(board(1)));
 await page.evaluate(()=>{
  window.drawn=[];window.frames=[];
  const draw=PixelUI.equipmentItem,frame=PixelUI.equipmentFrame;
  PixelUI.equipmentItem=(...args)=>{drawn.push(args.slice(0,7));if(drawn.length>100)drawn.splice(0,50);return draw(...args);};
  PixelUI.equipmentFrame=(...args)=>{frames.push([...args,PixelUI.g.getTransform().a]);if(frames.length>20)frames.shift();return frame(...args);};
  profile();
 });
 await page.evaluate(b=>receiveFrame(-120,b),encoded(profile(2,rows[0])));
 await page.waitForFunction(()=>drawn.length>=4);
 assert.deepEqual(await page.evaluate(()=>[view,reply.id,reply.avatar.character,character]),['profile',41,9,0]);
 assert.deepEqual(await page.evaluate(()=>drawn.slice(-4).map(a=>[a[0],a[1],a[2],a[5]])),magentaIds.slice(0,4).map((id,i)=>[9,i,id,16]));
 const geometry=await page.evaluate(()=>frames.at(-1));assert.deepEqual(geometry.slice(0,2),[124,259]);
 assert.ok(Math.abs(geometry[2]-450/432)<1e-6,'Profile must use the same432-pixel grid as the outside screen: '+JSON.stringify(geometry));
 await page.waitForFunction(()=>PixelUI.serverGearIconMetadata(reply.avatar.character,0,reply.items[0].id,reply.icons[0]).kind===1);
 const iconPixel=()=>page.evaluate(()=>{const g=PixelUI.g;g.save();g.setTransform(1,0,0,1,0,0);g.clearRect(24,24,16,16);PixelUI.equipmentItem(reply.avatar.character,0,reply.items[0].id,32,32,16,reply.icons[0],true);const color=Array.from(g.getImageData(32,32,1,1).data);g.restore();return color;});
 assert.deepEqual(await iconPixel(),[...diamondColor,255],'The equipped item must paint its exact server PNG');
 assert.equal(await page.evaluate(()=>profileDiagnostics.at(-1).hero),9);
 assert.ok(await page.evaluate(()=>profileDiagnostics.at(-1).icon_sources.every(s=>s===1)));
 assert.ok(await page.evaluate(()=>!JSON.stringify(profileDiagnostics).includes('top-magenta')&&!JSON.stringify(profileDiagnostics).includes('Ngọc')),'Diagnostic metadata must omit names/gem text and PNG payloads');
 await page.waitForTimeout(300);
 const out=path.join(__dirname,'build');fs.mkdirSync(out,{recursive:true});
 await page.screenshot({path:path.join(out,'profile303-magenta.png')});
 await page.evaluate(()=>profileDetails());
 assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Sinh lực \+115/);
 assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Ngày hết hạn: 20/);
 await page.screenshot({path:path.join(out,'profile303-details.png')});
 await page.evaluate(()=>{lobbyKey(-7);profileStats();});
 assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Sinh lực: 1935000000/,'Full HP must remain readable without truncation');
 await page.evaluate(()=>{lobbyKey(-7);profileFocus=5;profileDetails();});
 assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Sinh lực \+999/,'Costume detail must use slot5, not a worn item from another slot');
 await page.evaluate(()=>{lobbyKey(-7);refreshProfile();fieldBack();});
 await page.evaluate(b=>receiveFrame(-120,b),encoded(profile(3,rows[0])));
 assert.deepEqual(await page.evaluate(()=>[view,waiting]),['board',false],'A late refresh must not reopen a closed profile');
 await page.evaluate(()=>{focus=1;profile();});
 await page.evaluate(b=>receiveFrame(-120,b),encoded(profile(4,rows[1],{hero:1,upgrade:16,costume:false,health:1234})));
 assert.deepEqual(await page.evaluate(()=>[reply.id,reply.avatar.character,reply.abilities[0],...reply.items.map(p=>p.upgrade)]),[52,1,1234,16,16,16,16,16]);
 await page.waitForFunction(()=>PixelUI.serverGearIconMetadata(reply.avatar.character,0,reply.items[0].id,reply.icons[0]).kind===1);
 assert.deepEqual(await iconPixel(),[...platinumColor,255],'The same+16 level must not change platinum into the previous diamond icon');
 await page.evaluate(()=>{fieldBack();focus=0;profile();});
 await page.evaluate(b=>receiveFrame(-120,b),encoded(profile(5,rows[0],{upgrade:15,health:139028})));
 assert.deepEqual(await page.evaluate(()=>[reply.id,reply.abilities[0],...reply.items.map(p=>p.upgrade)]),[41,139028,15,15,15,15,15]);
 assert.equal(await page.evaluate(()=>sent.filter(a=>a[0]===-120&&atob(a[1]).charCodeAt(4)===2).length),4,'Each open/refresh must request that account again');
 for(const viewport of [{width:390,height:592},{width:946,height:1370}]){
  await page.setViewportSize(viewport);await page.waitForTimeout(100);
  await page.evaluate(()=>profileDetails());assert.ok(await page.evaluate(()=>modal.lines.length>0));
  await page.evaluate(()=>lobbyKey(-7));
 }
 // Exercise the live catalog path independently of per-profile PNGs.
 const strip=testPng([diamondColor,platinumColor]),catalog=w().byte(1).byte(9).short(999).byte(1).byte(0).byte(2);
 for(const [id,frame]of [[56,0],[43,1]]){catalog.short(id).byte(13).short(frame);for(let i=0;i<49;i++)catalog.byte(0);}
 catalog.short(strip.length);for(const b of strip)catalog.byte(b);
 await page.evaluate(b=>lobbyGearAtlas(b),encoded(catalog.bytes));
 await page.waitForFunction(()=>PixelUI.serverGearIconMetadata(9,0,56).kind===2);
 const catalogPixels=await page.evaluate(()=>{
  const g=PixelUI.g;g.save();g.setTransform(1,0,0,1,0,0);const colors=[];
  for(const id of [56,43]){g.clearRect(24,24,16,16);PixelUI.equipmentItem(9,0,id,32,32,16,null,true);colors.push(Array.from(g.getImageData(32,32,1,1).data));}
  const missing=PixelUI.gearIcon(9,0,48,32,32,16,null,true);g.restore();return {colors,missing};
 });
 assert.deepEqual(catalogPixels.colors,[[...diamondColor,255],[...platinumColor,255]],'Catalog item IDs must select different server frames even at the same+16 level');
 assert.equal(catalogPixels.missing,false,'Missing catalog entries must not be replaced by avatar-body crops');
 assert.deepEqual(errors,[]);await browser.close();if(server)await new Promise(resolve=>server.close(resolve));
 console.log('PASS profile303: fresh targeted replies, synthetic Magenta+16 fixture, distinct diamond/platinum server PNGs and catalog frames at identical+16, no avatar-crop icon fallback, six worn/costume details/gems, full HP, native432 geometry, stale/wrong-account rejection, numeric-only icon diagnostics, changed gear, missing details and multiple viewport sizes; screenshots clearly marked TEST DATA');
})().catch(e=>{console.error(e);process.exit(1);});
