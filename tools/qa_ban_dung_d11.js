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
    // Mỗi lỗi có trang riêng để báo đủ một vòng; chỉ fixture offline.
    const regressions=[];
    async function regression(name, fn) {
      const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
      ctx.setDefaultTimeout(2500);
      await ctx.route('**/*', r=>r.request().url().startsWith('file:')?r.continue():r.abort());
      try {const p=await ctx.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto(pathToFileURL(path.join(root,'mockup/ban_dung_3d.html')).href);await fn(p);assert.deepEqual(errors,[]);}
      catch(e){regressions.push(name+': '+e.message);}finally{await ctx.close();}
    }
    await regression('inverse drag actor/camera',async p=>{
      for(const kind of ['actor','camera'])for(const yaw of [0,90])for(const pitch of [30,90])for(const zoom of [.7,1.4]){
        await p.reload();await p.evaluate(({yaw,pitch,zoom,kind})=>{viewers[0]={...viewers[0],yaw,pitch,zoom,pan:30};if(kind==='camera'){cam().x=1;cam().y=-1;}render();},{yaw,pitch,zoom,kind});
        const before=await p.evaluate(kind=>clone(kind==='camera'?cam():p()),kind);
        const mark=p.locator('[data-drag='+kind+'] circle'),box=await mark.boundingBox();
        await p.mouse.move(box.x+box.width/2,box.y+box.height/2);await p.mouse.down();await p.mouse.move(box.x+box.width/2+32,box.y+box.height/2,{steps:3});await p.mouse.up();
        const after=await p.evaluate(kind=>clone(kind==='camera'?cam():p()),kind);
        const projected=await p.evaluate(({before,after})=>{const v=viewers[0],r=v.yaw*Math.PI/180,t=v.pitch*Math.PI/180,s=43*v.zoom;return {dx:((after.x-before.x)*Math.cos(r)-(after.y-before.y)*Math.sin(r))*s,dy:((after.x-before.x)*Math.sin(r)+(after.y-before.y)*Math.cos(r))*Math.sin(t)*s,scale:Math.min(document.querySelector('#preview svg').getBoundingClientRect().width/580,document.querySelector('#preview svg').getBoundingClientRect().height/410)};},{before,after});
        assert(Math.abs(projected.dx*projected.scale-32)<7,'world drag '+kind+' yaw='+yaw+' pitch='+pitch+' zoom='+zoom+' dx='+projected.dx*projected.scale);assert(Math.abs(projected.dy*projected.scale)<7,'world drag lệch trục màn hình');
      }
    });
    await regression('khóa trục + số máy endpoint',async p=>{
      await p.locator('#axis').selectOption('x');const before=await p.evaluate(()=>clone(p()));const circle=p.locator('[data-drag=actor] circle'),b=await circle.boundingBox();await p.mouse.move(b.x+b.width/2,b.y+b.height/2);await p.mouse.down();await p.mouse.move(b.x+b.width/2+30,b.y+b.height/2+15);await p.mouse.up();assert.equal(await p.evaluate(()=>p().y),before.y);assert.notEqual(await p.evaluate(()=>p().x),before.x);
      await p.locator('#selectCamera').click();await p.locator('#cameraPoint').selectOption('end');for(const [id,value] of [['camX','2'],['height','1.2'],['yaw','315'],['pitch','8'],['lens','55']]){const before=await p.evaluate(()=>drawCamera());await p.locator('#'+id).fill(value);await p.locator('#'+id).dispatchEvent('change');assert.notEqual(await p.evaluate(()=>drawCamera()),before,id+' thiếu hiệu ứng tại end');}assert.equal(await p.evaluate(()=>sampleCamera().lens),55);
    });
    await regression('mốc monotonic + chung sampler',async p=>{
      const result=await p.evaluate(()=>{function move(b,value){const e=document.querySelector('[data-keyframe='+b+']');e.value=value;e.dispatchEvent(new Event('input',{bubbles:true}));}move('start','1.9');move('peak','0.1');move('end','2.1');move('peak','3.9');return clone(timing());});
      assert(result.start<result.peak&&result.peak<result.end,'keyframes bị đảo');
      await p.reload();const sample=await p.evaluate(()=>{time=2;beat='start';return {actor:resolved('actor'),frame:window.editor.sampleFrame?window.editor.sampleFrame():null};});assert(sample.frame,'camera và actor thiếu sampler chung');assert.equal(sample.frame.actors.actor.x,sample.actor.x);
      await p.evaluate(()=>{timing().end=3;time=3;render()});assert.equal(await p.evaluate(()=>sampleCamera().x),await p.evaluate(()=>scene().camera.end.x),'máy bỏ mốc end');
      const previewAtPeak=await p.evaluate(()=>{time=2;beat='peak';return drawCamera()});assert.equal(await p.evaluate(()=>{time=2;beat='start';return drawCamera()}),previewAtPeak,'camera preview phụ thuộc beat cũ');
    });
    await regression('diff IDs/revision/approved',async p=>{
      await p.locator('details > summary').first().click();await p.locator('#setupLens').fill('50');await p.locator('#setupApply').click();await p.locator('#setup').selectOption('setup-b');
      assert.equal(await p.locator('#diffPanel').isVisible(),false,'đổi setup vẫn giữ diff');await p.evaluate(()=>$('confirmDiff').click());assert.equal(await p.evaluate(()=>registry.setups['setup-b'].start.lens),50);
      await p.locator('#copyViewer').click();await p.locator('#next').click();assert.equal(await p.locator('#diffPanel').isVisible(),false,'đổi shot vẫn giữ diff');await p.evaluate(()=>$('confirmDiff').click());assert.equal(await p.evaluate(()=>scene().camera.start.yaw),330);
      await p.locator('#prev').click();await p.locator('#copyViewer').click();await p.evaluate(()=>{cam().lens=60;scene().revision++;$('confirmDiff').click()});assert.equal(await p.evaluate(()=>cam().yaw),330,'stale revision vẫn áp');
      await p.locator('#next').click();await p.locator('#next').click();const approved=await p.evaluate(()=>JSON.stringify(scene()));await p.evaluate(()=>$('resetDirector').click());assert.equal(await p.locator('#diffPanel').isVisible(),false);assert.equal(await p.evaluate(()=>JSON.stringify(scene())),approved);
    });
    await regression('target ID resolve',async p=>{
      const before=await p.evaluate(()=>drawCamera());await p.locator('#selectCamera').click();await p.locator('#target').selectOption('actor-kelly');assert.notEqual(await p.evaluate(()=>drawCamera()),before,'target không đổi khung');
      const aimed=await p.evaluate(()=>{const c=sampleCamera(),a=resolved('kelly');return project(c,[a.x,a.y,a.z+registry.actors.kelly.height*.93]);});assert(Math.abs(aimed[0]-.5)<.00001&&Math.abs(aimed[1]-.5)<.00001,'target không ở tâm');
    });
    await regression('nền/đèn/props/baseline fixture',async p=>{
      const approvedBefore=await p.evaluate(()=>{go(2);const svg=drawCamera();go(0);return svg;});await p.locator('details > summary').first().click();assert.equal(await p.locator('#background').count(),1);assert.equal(await p.locator('#lightTime').count(),1);assert.equal(await p.locator('#prop').count(),1);assert.equal(await p.locator('#resetDirector').count(),1);
      const initialSVG=await p.evaluate(()=>drawCamera());await p.locator('#background').selectOption('green');assert.notEqual(await p.evaluate(()=>drawCamera()),initialSVG);assert((await p.locator('#environmentSource').innerText()).includes('fixture'));
      await p.locator('#lightWeather').selectOption('fog');await p.getByText('Ánh sáng nâng cao · minh họa',{exact:true}).click();await p.locator('#lightAzimuth').fill('120');await p.locator('#lightAzimuth').dispatchEvent('change');assert.equal(await p.evaluate(()=>registry.stage.environment.azimuth),120);
      await p.locator('#prop').selectOption('wall');await p.locator('#propX').fill('1');await p.locator('#propX').dispatchEvent('change');assert.equal(await p.evaluate(()=>registry.stage.objects.find(o=>o.object_id==='wall').x),1);await p.locator('#undo').click();assert.equal(await p.evaluate(()=>registry.stage.objects.find(o=>o.object_id==='wall').x),0);
      await p.locator('#prop').selectOption('stand-in');assert.equal(await p.locator('#propX').isDisabled(),true);assert.equal(await p.evaluate(()=>{go(2);const svg=drawCamera();go(0);return svg;}),approvedBefore,'stage sửa lan vào approved');
      await p.locator('#selectCamera').click();await p.locator('#lens').fill('60');await p.locator('#lens').dispatchEvent('change');await p.locator('#resetDirector').click();assert.equal(await p.locator('#diffPanel').isVisible(),true);await p.locator('#confirmDiff').click();assert.equal(await p.evaluate(()=>cam().lens),35);await p.locator('#undo').click();assert.equal(await p.evaluate(()=>cam().lens),60);
    });
    if(regressions.length)throw new Error('Hồi quy Đ11: '+regressions.join('\n'));
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
        await page.locator('details > summary').first().click();currentCount++;
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
      await page.locator('#target').selectOption('actor-kelly');
      assert.equal((await snap()).scenes[0].camera.start.target,'actor-kelly');
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
      await page.locator('#beat').selectOption('end');
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
      await page.locator('details > summary').first().click();
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
    console.log('5 nhóm hồi quy + nền/đèn/props/baseline: PASS');
    console.log('1440+1280: console=0 overflow=0; actor drag/numeric, beat, undo, propagation, approved, camera, fix, compare: PASS');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
