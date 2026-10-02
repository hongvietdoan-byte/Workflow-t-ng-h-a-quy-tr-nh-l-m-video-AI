// Quét tương phản + cỡ chữ của Dashboard đang mở. Dán vào console trình duyệt (F12) hoặc chạy bằng javascript_exec của công cụ trình duyệt.
// In: số phần tử có chữ < 4.5:1 (WCAG 1.4.3) và chữ nhỏ hơn 12.5 px. Mục tiêu: 0, trừ chữ trang trí. Xem docs/THIET_KE_GIAO_DIEN_2026-10-01.md.
// 02/10 (docs/RA_SOAT_UI_V2_SANG_TOI_2026-10-02.md): tính cả độ mờ (opacity của phần tử + cha, alpha của màu chữ) — trước đó chữ bị
// Streamlit đặt opacity .6 vẫn được tính là đạt; quét cả hộp thoại / popover (cổng ngoài .stApp); nền gradient (nút chính, viên chọn) bỏ qua
// vì đã kiểm bằng tokens.promised_pairs. Đổi `ROOT` thành selector (vd. '[data-testid="stDialog"]') để chỉ quét một vùng.
//
// S13.10 (02/10): thêm chế độ TỰ LÁI — đặt `window.AUDIT_MODE` trước khi dán (mặc định 'page' = quét trang hiện tại như cũ):
//   'page'     quét trang đang hiện (cả popover/hộp thoại đang mở)
//   'screens'  bấm lần lượt từng màn của thanh bước (radio `step`), chờ ổn định, quét; mở hết thẻ gập "▸ Mở" của mỗi màn trước khi quét
//   'popovers' mở lần lượt từng popover trên thanh trên (➕ 📥 💵 ⋯ ⚙), quét thân popover, đóng
//   'dialogs'  mở ⚙ rồi bấm từng nút mở hộp thoại (Kho tài nguyên / Kho kiến thức / Bài học / Tính năng thử / Giới hạn / Lịch sử / Phân quyền /
//              Đợt thử & Claude / Bảng giá), quét hộp thoại, đóng
//   'expert'   bật "Chế độ chuyên gia" ở ⚙ rồi chạy 'screens' (panel Chuyên gia ở mọi màn), xong tắt lại
//   'all'      page → screens → popovers → dialogs → expert
// Nền sáng/tối: thêm ?theme=light hoặc ?theme=dark vào địa chỉ (v2 mặc định tối). Độ rộng: đổi cửa sổ (resize_window) rồi chạy lại; cần 1100 px
// cho "mọi màn ở 1100 px". Ca "Tự động đang chạy": seed bằng `py tools/ui_v2_acceptance.py states --out data/demo` (đặt autopilot_state=running
// + > 3 việc ở hộp thư) rồi chạy 'screens'. Kết quả của mọi chế độ: một chuỗi, mỗi dòng "<vùng> | chữ<4.5: N | chữ<12.5px: M" + chi tiết 12 mục đầu.
(async () => {
  const MODE = window.AUDIT_MODE || 'page';
  const ROOT = window.AUDIT_ROOT || null;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const lum = c => { const [r, g, b] = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const parse = s => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(parseFloat); return { c: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 }; };
  const page = parse(getComputedStyle(document.body).backgroundColor);
  const bgOf = e => { let n = e; while (n) { const s = getComputedStyle(n); if (/gradient/.test(s.backgroundImage)) return null;
      // số trên con trượt (stSliderThumbValue) nằm ĐÈ lên trên núm 12 px (top -22 px) → nền thật là nền thẻ, không phải màu núm
      if (n.querySelector && n.querySelector(':scope > [data-testid="stSliderThumbValue"]')) { n = n.parentElement; continue; }
      const p = parse(s.backgroundColor); if (p && p.a > 0.5) return p.c; n = n.parentElement; }
    return (page && page.a > 0.5) ? page.c : [255, 255, 255]; };
  const opacityOf = e => { let o = 1, n = e; while (n) { o *= parseFloat(getComputedStyle(n).opacity); n = n.parentElement; } return o; };

  const scan = (rootEl) => {
    const bad = [], small = [];
    (rootEl || document).querySelectorAll('p,span,label,button,summary,li,div,a,h1,h2,h3,h4,td,th').forEach(e => {
      if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
      if (e.closest('.v2-grad-text, [data-testid="stBaseButton-primary"], [data-testid="stCode"], [data-testid="stIconMaterial"]')) return;
      const r = e.getBoundingClientRect(); if (r.width < 4 || r.height < 4) return;
      const s = getComputedStyle(e); if (s.visibility === 'hidden' || s.display === 'none') return;
      const op = opacityOf(e); if (op < 0.05) return;
      const fg = parse(s.color); if (!fg) return;
      const bg = bgOf(e); if (!bg) return;                                   // chữ trên nền gradient: kiểm bằng token
      const a = fg.a * op, mix = fg.c.map((v, i) => v * a + bg[i] * (1 - a)); // màu chữ thực sự nhìn thấy (đã trộn độ mờ)
      const l1 = lum(mix), l2 = lum(bg);
      const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
      const txt = e.textContent.trim().slice(0, 36);
      if (ratio < 4.5) bad.push(ratio.toFixed(2) + ' | ' + txt + ' | ' + s.color + (op < 0.99 ? ' · opacity ' + op.toFixed(2) : '') + ' trên rgb(' + bg.join(',') + ')');
      if (parseFloat(s.fontSize) < 12.5) small.push(s.fontSize + ' | ' + txt);
    });
    return { bad, small };
  };
  const rootEl = () => (ROOT ? document.querySelector(ROOT) : document);
  const lines = [];
  const record = (name, res) => {
    // "N phần tử" = số khối phần tử Streamlit đang có trên trang — để thấy chế độ chuyên gia / ca "tự động đang chạy" có thật sự mở thêm nội dung
    lines.push(`${name} | chữ<4.5: ${res.bad.length} | chữ<12.5px: ${res.small.length} | ${document.querySelectorAll('[data-testid="stElementContainer"]').length} phần tử`
      + (document.documentElement.scrollWidth > innerWidth + 2 || document.body.scrollWidth > innerWidth + 2 ? ` | ⚠ TRÀN NGANG ${Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)}>${innerWidth}px` : ''));
    res.bad.slice(0, 12).forEach(x => lines.push('    ✗ ' + x));
    res.small.slice(0, 6).forEach(x => lines.push('    ▫ ' + x));
  };

  // ---- trợ giúp tự lái -------------------------------------------------------------------------------------------------------------
  // Streamlit 1.64: [data-testid="stApp"][data-test-script-state=running|notRunning]; phần tử cũ đang chờ thay có data-stale="true" (opacity .33 — KHÔNG đo)
  const busy = () => document.querySelector('[data-testid="stApp"]')?.getAttribute('data-test-script-state') === 'running'
    || !!document.querySelector('[data-stale="true"], [data-testid="stSkeleton"]');
  const settle = async (min = 500) => {
    await sleep(min);
    for (let i = 0, calm = 0; i < 200 && calm < 3; i++) { await sleep(150); calm = busy() ? 0 : calm + 1; }   // 3 lần liền yên = ổn định
  };
  const clickEl = async el => { el.scrollIntoView({ block: 'center' }); el.click(); await settle(); };
  const byText = (re, sel = 'button') => [...document.querySelectorAll(sel)].find(b => re.test((b.textContent || '').trim()) && b.getBoundingClientRect().width > 0);
  const esc = async () => { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27, bubbles: true })); await sleep(350); };
  const closeDialog = async () => {
    const x = document.querySelector('[data-testid="stDialog"] button[aria-label="Close"]');
    if (x) { x.click(); await sleep(450); } else { await esc(); }
  };
  const popTriggers = () => [...document.querySelectorAll('button[data-testid="stPopoverButton"]')]
    .filter(b => b.getBoundingClientRect().width > 0 && !b.closest('[data-testid="stPopoverBody"]') && !b.closest('[data-testid="stDialog"]'));
  const openPopover = async re => {                                          // mở popover trên thanh trên có nhãn khớp `re`
    const t = popTriggers().find(b => re.test(b.textContent || '') || re.test(b.getAttribute('aria-label') || ''));
    if (!t) return null;
    if (t.getAttribute('aria-expanded') !== 'true') await clickEl(t);
    return t;
  };
  const closePopover = async t => { if (t && t.getAttribute('aria-expanded') === 'true') { t.click(); await sleep(400); } };
  const popBody = () => document.querySelector('[data-testid="stPopoverBody"]');
  const openFolds = async () => {                                            // thẻ gập ui.fold: widget bên trong chỉ vẽ khi mở
    for (let i = 0; i < 10; i++) {
      const b = [...document.querySelectorAll('[class*="st-key-fold_"] button, button')].find(x => /^▸\s*Mở/.test((x.textContent || '').trim()) && x.getBoundingClientRect().width > 0);
      if (!b) break; await clickEl(b);
    }
  };

  const doPage = () => record('trang hiện tại' + (ROOT ? ' [' + ROOT + ']' : ''), scan(rootEl()));

  const stepLabels = () => [...document.querySelectorAll('.st-key-step label, [data-testid="stRadio"] label')]
    .filter(l => l.closest('.st-key-step') && l.getBoundingClientRect().width > 0);
  const doScreens = async (tag = '') => {
    const n = stepLabels().length;
    if (!n) { lines.push('!! không thấy thanh bước (radio step)'); return; }
    for (let i = 0; i < n; i++) {
      const lab = stepLabels()[i]; const name = (lab.textContent || '').trim().replace(/\s+/g, ' ');
      await clickEl(lab); await openFolds();
      record(`${tag}màn "${name}" @${innerWidth}px`, scan(rootEl()));
      // các tab con (vd. Storyboard: Ảnh + QC | Motion & giọng): bấm từng tab, quét lại
      const tabs = [...document.querySelectorAll('[role="tab"]')].filter(t => t.getBoundingClientRect().width > 0 && !t.closest('[data-testid="stDialog"]'));
      for (const t of tabs) {
        if (t.getAttribute('aria-selected') === 'true') continue;
        await clickEl(t); await openFolds();
        record(`${tag}màn "${name}" › tab "${(t.textContent || '').trim().slice(0, 28)}" @${innerWidth}px`, scan(rootEl()));
      }
    }
  };
  const doPopovers = async () => {
    for (const [label, re] of [['➕ Dự án mới', /Dự án mới/], ['📥 Việc cần bạn', /Việc cần bạn/], ['💵 Tiền', /💵|Tiền/], ['⋯ Thêm', /⋯|Thêm/], ['⚙ Cài đặt', /⚙|Cài đặt/]]) {
      const t = await openPopover(re);
      if (!t) { lines.push(`popover ${label}: không thấy nút`); continue; }
      const body = popBody();
      record(`popover ${label} @${innerWidth}px`, body ? scan(body) : { bad: ['(thân popover không mở)'], small: [] });
      await closePopover(t);
    }
  };
  // [nhãn, popover chứa nút, nút]. Nút nằm trong các tab của popover (⚙: Dự án | Tài nguyên & kiến thức | Hệ thống) → dò từng tab.
  const DIALOGS = [['Kho tài nguyên', /⚙|Cài đặt/, /Kho tài nguyên/], ['Kho kiến thức', /⚙|Cài đặt/, /Kho kiến thức/], ['Bài học', /⚙|Cài đặt/, /Bài học/],
                   ['Tính năng thử', /⚙|Cài đặt/, /Tính năng thử/], ['Giới hạn hệ thống', /⚙|Cài đặt/, /Giới hạn/], ['Lịch sử & thùng rác', /⚙|Cài đặt/, /Lịch sử/],
                   ['Phân quyền', /⚙|Cài đặt/, /Phân quyền/], ['Đợt thử & Claude', /💵|Tiền/, /Đợt thử/], ['Bảng giá', /💵|Tiền/, /Bảng giá/]];
  const findInPopover = async re => {
    const sel = '[data-testid="stPopoverBody"] button:not([role="tab"])';
    let btn = byText(re, sel);
    if (btn) return btn;
    for (const t of [...document.querySelectorAll('[data-testid="stPopoverBody"] [role="tab"]')]) {
      await clickEl(t); btn = byText(re, sel); if (btn) return btn;
    }
    return null;
  };
  const doDialogs = async () => {
    for (const [label, popRe, re] of DIALOGS) {
      const t = await openPopover(popRe);
      if (!t) { lines.push(`hộp thoại ${label}: không mở được popover ${popRe}`); continue; }
      const btn = await findInPopover(re);
      if (!btn) { lines.push(`hộp thoại ${label}: không thấy nút trong popover (cần quyền / chế độ chuyên gia?)`); await closePopover(t); continue; }
      await clickEl(btn); await sleep(600);
      const dlg = document.querySelector('[data-testid="stDialog"]');
      record(`hộp thoại ${label} @${innerWidth}px`, dlg ? scan(dlg) : { bad: ['(hộp thoại không mở)'], small: [] });
      if (dlg) {                                                              // hộp thoại có tab con (Kho kiến thức, Phân quyền…)
        const tabs = [...dlg.querySelectorAll('[role="tab"]')].filter(x => x.getAttribute('aria-selected') !== 'true' && x.getBoundingClientRect().width > 0);
        for (const x of tabs) { await clickEl(x); record(`hộp thoại ${label} › tab "${(x.textContent || '').trim().slice(0, 24)}"`, scan(document.querySelector('[data-testid="stDialog"]') || dlg)); }
      }
      await closeDialog(); await settle(300);
      const t2 = popTriggers().find(b => b.getAttribute('aria-expanded') === 'true'); if (t2) await closePopover(t2);
    }
  };
  const doExpert = async () => {
    const t = await openPopover(/⚙|Cài đặt/);
    if (!t) { lines.push('chuyên gia: không mở được ⚙'); return; }
    for (const tb of [...document.querySelectorAll('[data-testid="stPopoverBody"] [role="tab"]')]) { await clickEl(tb); if (/Hệ thống/.test(tb.textContent)) break; }
    const tog = [...document.querySelectorAll('[data-testid="stPopoverBody"] label')].find(l => /chuyên gia/i.test(l.textContent || '') && l.getBoundingClientRect().width > 0);
    if (!tog) { lines.push('chuyên gia: không thấy công tắc (đã bật bằng DASHBOARD_EXPERT=1?)'); await closePopover(t); return; }
    (tog.querySelector("input") || tog).click(); await settle(); await closePopover(t); await settle();   // react-aria: bấm <input>, bấm <label> không đổi trạng thái
    await doScreens('[chuyên gia] ');
    const t3 = await openPopover(/⚙|Cài đặt/);
    if (t3) for (const tb of [...document.querySelectorAll('[data-testid="stPopoverBody"] [role="tab"]')]) { await clickEl(tb); if (/Hệ thống/.test(tb.textContent)) break; }
    const tog2 = t3 && [...document.querySelectorAll('[data-testid="stPopoverBody"] label')].find(l => /chuyên gia/i.test(l.textContent || '') && l.getBoundingClientRect().width > 0);
    if (tog2) { (tog2.querySelector("input") || tog2).click(); await settle(); } await closePopover(t3);
  };

  const t0 = Date.now();
  lines.push(`== ui_contrast_audit · chế độ ${MODE} · ${innerWidth}×${innerHeight} · nền ${page ? 'rgb(' + page.c.join(',') + ')' : '?'} ==`);
  if (MODE === 'page' || MODE === 'all') doPage();
  if (MODE === 'screens' || MODE === 'all') await doScreens();
  if (MODE === 'popovers' || MODE === 'all') await doPopovers();
  if (MODE === 'dialogs' || MODE === 'all') await doDialogs();
  if (MODE === 'expert' || MODE === 'all') await doExpert();
  const total = lines.filter(l => !l.startsWith(' ') && !l.startsWith('=='));
  const sumBad = total.reduce((a, l) => a + (parseInt((l.match(/chữ<4\.5: (\d+)/) || [0, 0])[1]) || 0), 0);
  const sumSmall = total.reduce((a, l) => a + (parseInt((l.match(/chữ<12\.5px: (\d+)/) || [0, 0])[1]) || 0), 0);
  lines.push(`TỔNG: ${total.length} vùng · chữ<4.5: ${sumBad} · chữ<12.5px: ${sumSmall} · ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  window.__auditResult = lines.join('\n');       // để nạp bằng <script src> (xem docs) vẫn lấy được kết quả
  return window.__auditResult;
})()
