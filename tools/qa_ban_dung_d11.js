// Kiểm tương tác thật: tuyệt đối không truy cập HTTP hoặc profile người dùng.
const fs = require('fs'), path = require('path'), assert = require('assert');
const {pathToFileURL} = require('url');
const root = path.resolve(__dirname, '..');
let pw;
try { pw = require('playwright'); } catch (_) {
  const mod = process.env.PLAYWRIGHT_MODULE_PATH || path.join(process.env.USERPROFILE || process.env.HOME || '', '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
  try { pw = require(mod); } catch (_) { console.log('Không có runtime Playwright; bỏ kiểm trình duyệt'); process.exit(77); }
}
(async () => {
  const executablePath = [process.env.D11_BROWSER_PATH, 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => p && fs.existsSync(p));
  if (!executablePath) { console.log('Không có Chrome/Edge cục bộ; bỏ kiểm trình duyệt'); process.exitCode=77; return; }
  const browser = await pw.chromium.launch({executablePath, headless:true});
  try {
    for (const width of [1440,1280]) {
      const context = await browser.newContext({viewport:{width,height:1000}});
      await context.route('**/*', route => route.request().url().startsWith('file:') ? route.continue() : route.abort());
      const page = await context.newPage(), errors=[];
      page.on('pageerror', e => errors.push(e.message));
      page.on('console', m => {if(m.type()==='error') errors.push(m.text());});
      await page.goto(pathToFileURL(path.join(root,'mockup/ban_dung_3d.html')).href);
      const snap=()=>page.evaluate(()=>window.editor.snapshot());
      if(width===1440){
        const out=process.env.D11_SHOT_DIR||path.join(root,'docs/images/d11');fs.mkdirSync(out,{recursive:true});
        const baselineFile=path.join(out,'baseline.html');
        const baseline=require('child_process').execFileSync('C:/Program Files/Git/cmd/git.exe',['show','c5544891:mockup/ban_dung_3d.html'],{cwd:root,encoding:'utf8'});
        fs.writeFileSync(baselineFile,baseline);
        const bp=await context.newPage();await bp.goto(pathToFileURL(baselineFile).href);
        let baselineCount=0,currentCount=0;
        await bp.locator('#lens').fill('50');await bp.locator('#lens').dispatchEvent('change');baselineCount++;
        await bp.locator('#next').click();baselineCount++;
        await bp.locator('#lens').fill('50');await bp.locator('#lens').dispatchEvent('change');baselineCount++;
        await bp.locator('#prev').click();baselineCount++;await bp.locator('#viewCamera').click();baselineCount++;
        await page.locator('details summary').click();currentCount++;
        await page.locator('#setupLens').fill('50');await page.locator('#setupLens').dispatchEvent('change');currentCount++;
        await page.locator('#setupApply').click();currentCount++;await page.locator('#confirmDiff').click();currentCount++;
        await page.locator('#viewCamera').click();currentCount++;
        for(const tab of [bp,page])assert.equal(await tab.evaluate(()=>window.editor.snapshot().scenes[1].camera.start.lens),50);
        console.log('Đo fixture 2 shot sửa lens + xem máy: baseline='+baselineCount+' current='+currentCount+' thao tác (fill/change tính một); chưa chứng minh giảm bấm');
        await bp.close();fs.unlinkSync(baselineFile);await page.reload();
      }

      assert.equal((await snap()).scene,0);
      assert.equal((await snap()).registry.stage.id,'stage-well');
      assert.equal(await page.locator('#actorControls').isVisible(),false);
      await page.locator('[data-drag=actor] circle').click();
      assert.equal(await page.evaluate(()=>window.editor.cell(0,0)),'K11');
      const shared=await snap();
      assert.equal(shared.registry.shots.length,3);
      assert.equal(Object.keys(shared.registry.setups).length,2);
      const cameraBefore=JSON.stringify(shared.scenes[0].camera);
      for(const id of ['orbit','pan','zoom','top','perspective','frame']) await page.locator('#'+id).click();
      assert.equal(JSON.stringify((await snap()).scenes[0].camera),cameraBefore);
      const exported=await page.evaluate(()=>window.editor.exportSVG());
      await page.locator('#hideActor').click();
      assert.equal(await page.evaluate(()=>window.editor.exportSVG()),exported);
      await page.locator('#hideActor').click();
      await page.locator('#copyViewer').click();
      assert.equal(await page.locator('#diffPanel').isVisible(),true);
      assert.equal(JSON.stringify((await snap()).scenes[0].camera),cameraBefore);
      await page.locator('#cancelDiff').click();
      await page.locator('#selectCamera').click();
      await page.locator('#sensor').fill('36');await page.locator('#sensor').dispatchEvent('change');
      await page.locator('#fov').fill('60');await page.locator('#fov').dispatchEvent('change');
      assert(Math.abs((await snap()).scenes[0].camera.start.lens-31.1769)<.01);
      await page.locator('#undo').click();
      await page.locator('#target').selectOption('kelly');
      assert.equal((await snap()).scenes[0].camera.start.target,'kelly');
      const viewerBeforeInput=JSON.stringify((await snap()).viewers[0]);
      await page.locator('#reason').focus();await page.keyboard.press('q');
      assert.equal(JSON.stringify((await snap()).viewers[0]),viewerBeforeInput);
      await page.locator('#reason').fill('Kiểm nhập chữ');
      await page.locator('#timeline').fill('2');await page.locator('#timeline').dispatchEvent('input');
      assert.equal((await snap()).time,2);
      await page.locator('[data-keyframe=peak]').fill('2.5');await page.locator('[data-keyframe=peak]').dispatchEvent('input');
      await page.locator('#beat').selectOption('peak');assert.equal((await snap()).time,2.5);
      await page.locator('#play').click();await page.waitForTimeout(120);await page.locator('#play').click();
      assert.notEqual((await snap()).time,2.5);
      await page.locator('[data-drag=actor] circle').click();

      assert.equal(await page.evaluate(()=>window.editor.cell(-.01,-.01)),'J10');
      await page.locator('#beat').selectOption('end');
      await page.locator('#actorX').fill('1.9'); await page.locator('#actorX').dispatchEvent('change');
      assert.equal((await snap()).scenes[0].beats.end.actor.x,1.9);
      assert.equal((await snap()).registry.states['state-0-end'].actors.actor.x,1.9);
      assert.equal((await snap()).scenes[0].manual_lock,true);
      await page.locator('#undo').click(); assert.equal((await snap()).scenes[0].beats.end.actor.x,1.25); assert.equal((await snap()).registry.states['state-0-end'].actors.actor.x,1.25);
      await page.locator('#actorX').fill('1.8'); await page.locator('#actorX').dispatchEvent('change');
      const pending = JSON.stringify((await snap()).scenes[1]);
      const approved = JSON.stringify((await snap()).scenes[2]);
      await page.locator('[data-reject="1"]').click();
      assert.equal(JSON.stringify((await snap()).scenes[1]),pending);
      assert.equal(JSON.stringify((await snap()).scenes[2]),approved);
      assert.equal(await page.locator('[data-accept="1"]').isDisabled(),true);
      assert.equal(await page.locator('[data-reject="1"]').isDisabled(),true);
      await page.locator('#undo').click();
      assert.equal(await page.locator('[data-accept="1"]').isDisabled(),false);
      await page.locator('[data-accept="1"]').click();
      assert.equal((await snap()).scenes[1].beats.start.actor.x,1.8);
      assert.equal(await page.locator('[data-reject="1"]').isDisabled(),true);
      await page.evaluate(()=>document.querySelector('[data-reject="1"]').dispatchEvent(new MouseEvent('click',{bubbles:true})));
      assert.equal((await snap()).proposalState[1],'Đã nhận · chỉ đầu cảnh');
      assert.equal((await snap()).scenes[1].beats.start.actor.x,1.8);
      assert.equal(JSON.stringify((await snap()).scenes[2]),approved);
      await page.locator('#beat').selectOption('start');
      await page.locator('#selectCamera').click();
      await page.locator('#viewCamera').click();
      const before = await page.locator('#preview').innerHTML();
      await page.locator('#lens').fill('55'); await page.locator('#lens').dispatchEvent('change');
      assert.notEqual(await page.locator('#preview').innerHTML(),before);
      await page.locator('#viewDirector').click();
      await page.locator('#beat').selectOption('end');
      const target=page.locator('[data-drag="actor"] circle'); const box=await target.boundingBox();
      const x=(await snap()).scenes[0].beats.end.actor.x;
      await page.mouse.move(box.x+box.width/2,box.y+box.height/2); await page.mouse.down();
      await page.mouse.move(box.x+box.width/2+28,box.y+box.height/2,{steps:4}); await page.mouse.up();
      assert.notEqual((await snap()).scenes[0].beats.end.actor.x,x);
      const camera=page.locator('[data-drag="camera"] circle'), cb=await camera.boundingBox();
      const cx=(await snap()).scenes[0].camera.start.x;
      await page.mouse.move(cb.x+10,cb.y+10); await page.mouse.down();
      await page.mouse.move(cb.x+30,cb.y+10,{steps:4}); await page.mouse.up();
      assert.notEqual((await snap()).scenes[0].camera.start.x,cx);
      await page.locator('[data-drag=actor] circle').click();
      await page.locator('#actorCell').fill('K11'); await page.locator('#actorCell').dispatchEvent('change');
      assert.equal((await snap()).scenes[0].beats.end.actor.x,.5);
      await page.locator('#reason').fill(''); await page.locator('#save').click();
      assert.equal((await snap()).versions.length,0);
      await page.locator('#reason').fill('Kiểm lưu bản giả'); await page.locator('#save').click();
      assert.equal((await snap()).versions.length,1);
      await page.locator('#selectCamera').click();
      await page.locator('#height').fill('0.1'); await page.locator('#height').dispatchEvent('change');
      await page.locator('#fixHeight').click(); assert.equal((await snap()).scenes[0].camera.start.height,0.6);
      await page.locator('#next').click(); await page.locator('#next').click();
      assert.equal(await page.locator('#actorX').isDisabled(),true);
      await page.locator('#prev').click(); await page.locator('#prev').click();
      await page.locator('#compare').click(); assert.equal(await page.locator('#comparePanel').isVisible(),true);
      await page.locator('details summary').click();
      await page.locator('#setupLens').fill('50');await page.locator('#setupLens').dispatchEvent('change');
      await page.locator('#setupApply').click();await page.locator('#confirmDiff').click();
      assert.equal((await snap()).scenes[0].camera.start.lens,50);assert.equal((await snap()).scenes[1].camera.start.lens,50);
      const approvedSetup=JSON.stringify((await snap()).scenes[2]);
      await page.locator('#setup').selectOption('setup-b');await page.locator('#setupApply').click();
      assert((await page.locator('#diffText').innerText()).includes('VÀNG'));
      await page.locator('#confirmDiff').click();
      assert.equal(JSON.stringify((await snap()).scenes[2]),approvedSetup);
      for(const layer of ['map','source','clay']){await page.locator('#layer').selectOption(layer);assert((await page.locator('#layers').innerText()).includes(layer==='clay'?'preview_only':'UNKNOWN'));}

      await page.locator('#viewDirector').click();
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      const out=process.env.D11_SHOT_DIR||path.join(root,'docs/images/d11');  // hộp thư 12/10 21:05: test ghi thư mục tạm, không sửa ảnh tài liệu
      fs.mkdirSync(out,{recursive:true});
      await page.reload();
      await page.screenshot({path:path.join(out,`ban_dung_${width}_director.png`),fullPage:true});
      await page.locator('#viewCamera').click();
      await page.screenshot({path:path.join(out,`ban_dung_${width}_camera.png`),fullPage:true});
      assert.deepEqual(errors,[]); await context.close();
    }
    console.log('1440+1280: console=0 overflow=0; actor drag/numeric, beat, undo, propagation, approved, camera, fix, compare: PASS');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
