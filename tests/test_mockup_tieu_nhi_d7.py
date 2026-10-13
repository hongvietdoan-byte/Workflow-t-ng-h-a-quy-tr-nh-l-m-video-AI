from pathlib import Path
import re
import subprocess
import pytest
ROOT = Path(__file__).resolve().parents[1]

def test_package_errors_and_repair_controls():
    text = (ROOT / "mockup/tieu_nhi.html").read_text(encoding="utf-8")
    for key in ("packageCheck", "packageList", "addKho", "addPlate", "restorePackage", "generatedHistory", "blockedDemo"):
        assert f'id="{key}"' in text
    assert re.search(r'<input id="distance"[^>]*min="0"[^>]*step="0.01"', text)
    assert "đã gen bản trước" in text and "lần 2" in text
    assert "#24" in text and "Kho 419" in text
    assert 'id="ticketsPanel"' not in text

def test_pet_offline_and_admin_fields():
    text = (ROOT / "mockup/lao_dai_pet.html").read_text(encoding="utf-8")
    for phrase in ("3 ngày", "Nguyên nhân", "Bằng chứng", "Cần gì", "Người làm", "Đã sửa gì", "Test nào", "Mở trên Dashboard", "job kẹt", "gen xong"):
        assert phrase in text
    assert not re.search(r'fetch\(|XMLHttpRequest|https?://', text)
    assert 'id="togglePet"' in text


@pytest.mark.slow
def test_browser_offline_repair_generation_and_pet(tmp_path):
    """Chạy JS thật trong Chrome, không mở phiên trình duyệt người dùng/mạng."""
    runtime = Path("C:/Users/hongviet.doan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node")
    node = runtime / "bin/node.exe"
    chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
    assert node.is_file() and chrome.is_file(), "Cần Node bundled và Chrome để kiểm mockup"
    script = r'''
const { chromium } = require(process.argv[1]);
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
(async () => {
  const browser = await chromium.launch({ executablePath: process.argv[2], headless: true });
  const errors = [], forbidden = [], failures = [];
  try {
    for (const width of [1440, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 1000 } });
      await context.route('**/*', route => {
        if (new URL(route.request().url()).protocol === 'file:') return route.continue();
        forbidden.push('request ngoài file'); return route.abort();
      });
      const page = await context.newPage();
      page.on('console', message => { if(message.type() === 'error') errors.push('console error'); });
      page.on('pageerror', () => errors.push('page error'));
      await page.goto(pathToFileURL(process.argv[3] + '/mockup/tieu_nhi.html').href);
      assert.equal(await page.locator('#distance').getAttribute('min'), '0');
      await page.locator('#packagePreview').click();
      assert.equal(await page.locator('#previewPanel').isVisible(), false);
      await page.locator('#fixBackground').click();
      await page.locator('#fixCharacter').click();
      assert.match(await page.locator('#packageCheck').innerText(), /XANH/);
      await page.locator('#packagePreview').click();
      assert.equal(await page.locator('#previewPanel').isVisible(), true);
      await page.locator('#distance').fill('-0.01');
      assert.equal(await page.locator('#distance').evaluate(input => input.checkValidity()), false);
      await page.locator('#preview').click();
      assert.equal(await page.locator('#previewPanel').isVisible(), false);
      assert.equal(await page.locator('#genPanel').isVisible(), false);
      const generate = async distance => {
        await page.locator('#distance').fill(distance);
        await page.locator('#preview').click();
        await page.locator('#changeConsent').check();
        await page.locator('#apply').click();
        assert.equal(await page.locator('#gen').isEnabled(), false);
        await page.locator('#genConsent').check();
        await page.locator('#gen').click();
        assert.equal(await page.locator('#gen').isEnabled(), false);
      };
      await generate('1.2');
      await page.locator('#preview').click();
      assert.match(await page.locator('#status').innerText(), /đã gen/);
      await generate('1.3');
      await page.locator('#distance').fill('1.2');
      await page.locator('#preview').click();
      if (await page.locator('#previewPanel').isVisible()) failures.push('quay lại 1.2 phải chặn gen trùng');
      await page.locator('#blockedDemo').click();
      assert.equal(await page.locator('#blockedMessage').innerText(), 'đã báo admin, dự án tạm dừng ở shot này');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await page.screenshot({ path: process.argv[4] + '/tieu-nhi-' + width + '.png', fullPage: true });
      await page.goto(pathToFileURL(process.argv[3] + '/mockup/lao_dai_pet.html').href);
      assert.equal(await page.locator('button').filter({hasText: /^Duyệt/}).count(), 0);
      assert.equal(await page.locator('#ticketList article:visible').count(), 3);
      await page.locator('#togglePet').click();
      assert.equal(await page.locator('#petFigure').getAttribute('aria-label'), 'Dáng thường');
      if (await page.locator('#ticketList article:visible').count()) failures.push('dáng thường còn 3 phiếu chờ');
      await page.locator('#togglePet').click();
      assert.equal(await page.locator('#ticketList article:visible').count(), 3);
      await page.locator('.pet .openDashboard').click();
      assert.match(await page.locator('#status').innerText(), /Mô phỏng mở Dashboard/);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await page.screenshot({ path: process.argv[4] + '/lao-dai-' + width + '.png', fullPage: true });
      await context.close();
    }
    assert.deepEqual(errors, [], 'lỗi JS/console');
    assert.deepEqual(forbidden, [], 'mockup không được truy cập mạng');
    assert.deepEqual(failures, []);
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
'''
    # Chỉ môi trường tiến trình cần thiết, không kế thừa khóa User/dashboard.env.
    env = {"SYSTEMROOT": "C:/Windows", "WINDIR": "C:/Windows", "TEMP": str(tmp_path),
           "TMP": str(tmp_path), "PYTHONUTF8": "1"}
    result = subprocess.run(
        [str(node), "-e", script, str(runtime / "node_modules/playwright"), str(chrome), str(ROOT), str(tmp_path)],
        env=env, capture_output=True, text=True, encoding="utf-8", timeout=90,
    )
    assert result.returncode == 0, result.stderr
