'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const http=require('node:http');
const {chromium}=require('playwright');
(async()=>{
 const root=path.join(__dirname,'viewer');
 const server=http.createServer((request,response)=>{
  const name=path.resolve(root,'.'+new URL(request.url,'http://localhost').pathname);
  if(!name.startsWith(root+path.sep)){response.writeHead(403);response.end();return;}
  fs.readFile(name,(error,data)=>{
   if(error){response.writeHead(404);response.end();return;}
   const mime={'.html':'text/html','.js':'text/javascript','.png':'image/png'}[path.extname(name)]||'application/octet-stream';
   response.writeHead(200,{'Content-Type':mime});response.end(data);
  });
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 let browser;
 try{
  browser=await chromium.launch({args:['--no-sandbox'],executablePath:process.env.ARMY2_CHROMIUM});
  const page=await browser.newPage({viewport:{width:390,height:590}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{window.sent=[];window.webkit={messageHandlers:{viewer:{postMessage:value=>sent.push(value)}}};});
  await page.goto('http://127.0.0.1:'+server.address().port+'/native-watch.html');
  const setPhase=(p,text='')=>page.evaluate(([p,text])=>setWatchPhase(p,text),[p,text]);
  const press=k=>page.evaluate(k=>watchKey(k),k);
  const last=()=>page.evaluate(()=>sent.at(-1));
  await setPhase(0,'Khu vực đang chiến đấu bạn có muốn xem');
  await page.waitForTimeout(100);
  assert.equal(await page.evaluate(()=>PixelUI.g.getImageData(100,100,1,1).data[3]),0,'Area list remains visible');
  assert.equal(await page.evaluate(()=>PixelUI.g.getImageData(100,PixelUI.canvas.height-58,1,1).data[3]),255,'Dialog is at the bottom');
  await press(-22);assert.equal(await last(),'decline');
  await setPhase(-1);await setPhase(0);
  await press(13);assert.equal(await last(),'accept');
  await press(-6);assert.equal(await page.evaluate(()=>sent.filter(x=>x==='accept').length),1);
  await setPhase(1);await press(-22);assert.equal(await last(),'leave');
  await setPhase(2);await press(-6);assert.equal(await last(),'menuOpen','Native F1 opens the spectator menu');
  assert.deepEqual(await page.evaluate(()=>options().map(x=>x[0])),[
   'TIẾP TỤC','LỰC MAX','V9 MENU','BẬT/TẮT ICON ĐỘI','BẠN BÈ','TIN NHẮN','RỜI TRẬN CHIẾN']);
  assert.equal(await page.evaluate(()=>sent.filter(x=>x==='leave').length),1);
  await press(13);assert.equal(await last(),'menuClosed');
  assert.equal(await page.evaluate(()=>sent.filter(x=>x==='camera').length),0,'F1 must never toggle camera');
  await press(-7);assert.equal(await last(),'camera','Native F2 toggles the spectator camera');
  await press(-21);assert.equal(await last(),'menuOpen','Hardware F1 alias opens the same menu');
  await press(-22);assert.equal(await last(),'menuClosed','F2 closes an open menu without switching camera');
  assert.equal(await page.evaluate(()=>sent.filter(x=>x==='camera').length),1);
  await press(-22);assert.equal(await last(),'camera','Hardware F2 alias toggles camera outside a menu');
  await page.keyboard.press('F1');assert.equal(await last(),'menuOpen','Desktop F1 uses the same route as the native pad');
  await page.keyboard.press('F2');assert.equal(await last(),'menuClosed');
  await page.keyboard.press('F2');assert.equal(await last(),'camera','Desktop F2 toggles camera');
  await page.evaluate(()=>{
   window.angleLabels=[];const text=PixelUI.text;
   PixelUI.text=(label,...args)=>{if(label.startsWith('Góc:'))angleLabels.push(label);return text(label,...args);};
   watchCameraMode(true);watchAngle(247);
  });
  await page.waitForTimeout(60);
  assert.deepEqual(await page.evaluate(()=>angleLabels),[],'Overlay must not duplicate the native angle label');
  await page.keyboard.down('ArrowRight');
  assert.deepEqual(await last(),['key',0,-4]);
  await page.keyboard.up('ArrowRight');
  assert.deepEqual(await last(),['key',1,-4]);
  await press(-21);await press(-1);await press(-5);assert.equal(await last(),'leave');
  await setPhase(-1);await setPhase(2);await page.waitForTimeout(100);
  await page.mouse.click(360,16);assert.equal(await page.evaluate(()=>pbs),true);
  await page.waitForTimeout(70);await page.mouse.click(72*390/320+44,60);
  assert.deepEqual(await last(),['pb',2]);
  assert.deepEqual(errors,[]);
  console.log('PASS spectator controls: native/desktop F1 Menu and F2 Camera, hardware aliases, menu select/back, transparent confirmation, free-camera directions, leave and PB selector.');
 }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
