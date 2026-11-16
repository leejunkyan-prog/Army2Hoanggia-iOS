'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),zlib=require('node:zlib');
const {chromium}=require('playwright');
const {ArmyWriter}=require('./viewer/market.js');
const captured=require('./profile304-captured.json');
function png(color){
 const crc=b=>{let v=0xffffffff;for(const x of b){v^=x;for(let j=0;j<8;j++)v=v&1?0xedb88320^(v>>>1):v>>>1;}return(v^0xffffffff)>>>0;};
 const chunk=(name,b)=>{const t=Buffer.from(name),out=Buffer.alloc(b.length+12);out.writeUInt32BE(b.length);t.copy(out,4);b.copy(out,8);out.writeUInt32BE(crc(Buffer.concat([t,b])),b.length+8);return out;};
 const hdr=Buffer.alloc(13);hdr.writeUInt32BE(16);hdr.writeUInt32BE(16,4);hdr[8]=8;hdr[9]=6;
 const rows=Buffer.concat(Array.from({length:16},()=>Buffer.concat([Buffer.from([0]),Buffer.from(Array.from({length:16},()=>color).flat())])));
 return Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',hdr),chunk('IDAT',zlib.deflateSync(rows)),chunk('IEND',Buffer.alloc(0))]).toString('base64');
}
function board(serial){
 const w=new ArmyWriter().int(1129591862).byte(1).int(serial).int(90).int(700).byte(1).int(1).int(41).utf('captured-profile').int(999).byte(6);
 for(let j=0;j<5;j++)w.short(0);return w.byte(46).int(240).bytes;
}
function profile(serial){
 const r=captured,w=new ArmyWriter().int(1129591862).byte(2).int(serial).int(1).utf('captured-profile').int(999).utf('Trường Lục').byte(5);
 r.abilities.forEach(v=>w.int(v));
 for(let s=0;s<5;s++)w.short(r.item_ids[s]).utf(['súng','nón','giáp','giày','cánh'][s]+' kim cương').byte(r.upgrades[s]).byte(r.tiers[s]).byte(0);
 w.byte(6);for(let s=0;s<5;s++)w.short(0);
 w.byte(1).byte(46).long(42327685480).long(46042461728).int(240).byte(1).short(2046).utf('Batman 2.0').byte(0).byte(0).byte(0);
 w.int(0x44455448).byte(6);for(let s=0;s<6;s++){w.byte(1).byte(5);r.flat[s].forEach(v=>w.int(v));w.byte(5);r.percent[s].forEach(v=>w.int(v));w.int(s===5?0:22).byte(0);}
 return w.bytes; // Reproduce the supplied diagnostic: no ICON image data.
}
const b64=bytes=>Buffer.from(bytes).toString('base64');
(async()=>{
 const root=path.join(__dirname,'viewer'),server=http.createServer((req,res)=>{
  const file=path.resolve(root,'.'+new URL(req.url,'http://127.0.0.1').pathname);
  if(!file.startsWith(root+path.sep)){res.writeHead(404);res.end();return;}
  fs.readFile(file,(error,bytes)=>{if(error){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':'image/png');res.end(bytes);});
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({args:['--no-sandbox'],executablePath:process.env.ARMY2_CHROMIUM});
 const page=await browser.newPage({viewport:{width:432,height:626},deviceScaleFactor:2});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.sent=[];window.requests=[];window.logs=[];window.webkit={messageHandlers:{lobby:{postMessage:([kind,data])=>{if(kind==='profileIcons')requests.push(data);else if(kind==='profileDiagnostic')logs.push(data);else if(kind!=='avatar')sent.push([kind,data]);}}}};});
 await page.goto('http://127.0.0.1:'+server.address().port+'/lobby.html');
 await page.evaluate(()=>{lobbyViewport(432,[432,0,0,0,0,0,0],602);openTab('field',0);});
 await page.evaluate(b=>receiveFrame(-120,b),b64(board(1)));await page.evaluate(()=>profile());
 await page.evaluate(b=>receiveFrame(-120,b),b64(profile(2)));
 assert.deepEqual(await page.evaluate(()=>reply.abilities),captured.abilities);
 assert.deepEqual(await page.evaluate(()=>reply.items.map(i=>i.id)),captured.item_ids.slice(0,5));
 assert.deepEqual(await page.evaluate(()=>logs.at(-1).icon_sources),[0,0,0,0,0,0]);
 const request=await page.evaluate(()=>requests.at(-1));assert.equal(request.hero,6);assert.deepEqual(request.ids,captured.item_ids);
 const colors=Array.from({length:6},(_,i)=>[40+i*30,180-i*15,240-i*20,255]);
 const response={...request,png:colors.map(png),status:[0,0,0,0,0,0],icon_ids:[211,212,213,214,215,-1]};
 // A reply for a previous account/selection cannot populate this profile.
 await page.evaluate(d=>lobbyNativeProfileIcons(d),{...response,requested_id:52});
 assert.deepEqual(await page.evaluate(()=>logs.at(-1).icon_sources),[0,0,0,0,0,0]);
 await page.evaluate(d=>lobbyNativeProfileIcons(d),response);
 await page.waitForFunction(()=>logs.at(-1).icon_sources.every(n=>n===5));
 const sampled=await page.evaluate(()=>{
  const cv=document.createElement('canvas');cv.width=450;cv.height=450;
  const g=PixelUI.g;g.save();g.setTransform(1,0,0,1,0,0);const samples=[];
  for(let s=0;s<6;s++){g.clearRect(20,20,24,24);PixelUI.gearIcon(reply.avatar.character,s,ArmyProfile.item(reply,s).id,32,32,16,null,true);samples.push(Array.from(g.getImageData(32,32,1,1).data));}
  g.restore();return samples;
 });
 assert.deepEqual(sampled,colors,'Every physical slot, including the costume, must paint its exact native-cache image');
 await page.evaluate(()=>{profileFocus=0;profileDetails();});
 assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Sinh lực \+182/);assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Sức mạnh \+55%/);
 await page.evaluate(()=>{lobbyKey(-7);profileFocus=5;profileDetails();});
 assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Sức mạnh \+63/);assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Sinh lực \+6%/);
 await page.evaluate(()=>{lobbyKey(-7);profileStats();});
 assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Sinh lực: 193585/);assert.match(await page.evaluate(()=>modal.lines.join(' ')),/Sức mạnh: 571/);
 await page.evaluate(()=>{lobbyKey(-7);const note=document.createElement('div');note.textContent='LOG 303 — ICON KIỂM THỬ, KHÔNG PHẢI ẢNH ACC THẬT';note.style.cssText='position:fixed;top:0;background:#173b58;color:white;font:10px sans-serif;padding:5px';document.body.append(note);});
 fs.mkdirSync(path.join(__dirname,'build'),{recursive:true});await page.screenshot({path:path.join(__dirname,'build/profile304-recorded.png')});
 await page.evaluate(()=>fieldBack());await page.evaluate(d=>lobbyNativeProfileIcons(d),response);
 assert.equal(await page.evaluate(()=>view),'board');assert.deepEqual(errors,[]);
 await browser.close();await new Promise(r=>server.close(r));
 console.log('PASS recorded profile304: supplied hero6/IDs/upgrades/totals/details without ICON or atlas, native icon request and six-slot response including Batman, exact decoded pixels, wrong-account/closed-profile rejection, every detail and full stat retained; screenshot labels its test icons');
})().catch(e=>{console.error(e);process.exit(1);});
