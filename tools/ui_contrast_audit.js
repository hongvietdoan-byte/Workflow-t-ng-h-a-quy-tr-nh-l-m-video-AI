// Quét tương phản + cỡ chữ của trang Dashboard đang mở. Dán vào console trình duyệt (F12) hoặc chạy bằng javascript_exec của công cụ trình duyệt.
// In: số phần tử có chữ < 4.5:1 (WCAG 1.4.3) và chữ nhỏ hơn 12.5 px. Mục tiêu: 0, trừ chữ trang trí. Xem docs/THIET_KE_GIAO_DIEN_2026-10-01.md.
// 02/10 (docs/RA_SOAT_UI_V2_SANG_TOI_2026-10-02.md): tính cả độ mờ (opacity của phần tử + cha, alpha của màu chữ) — trước đó chữ bị
// Streamlit đặt opacity .6 vẫn được tính là đạt; quét cả hộp thoại / popover (cổng ngoài .stApp); nền gradient (nút chính, viên chọn) bỏ qua
// vì đã kiểm bằng tokens.promised_pairs. Đổi `ROOT` thành selector (vd. '[data-testid="stDialog"]') để chỉ quét một vùng.
(() => {
  const ROOT = null;
  const lum = c => { const [r, g, b] = c.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const parse = s => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(parseFloat); return { c: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 }; };
  const page = parse(getComputedStyle(document.body).backgroundColor);
  const bgOf = e => { let n = e; while (n) { const s = getComputedStyle(n); if (/gradient/.test(s.backgroundImage)) return null;
      const p = parse(s.backgroundColor); if (p && p.a > 0.5) return p.c; n = n.parentElement; }
    return (page && page.a > 0.5) ? page.c : [255, 255, 255]; };
  const opacityOf = e => { let o = 1, n = e; while (n) { o *= parseFloat(getComputedStyle(n).opacity); n = n.parentElement; } return o; };
  const bad = [], small = [];
  (ROOT ? document.querySelector(ROOT) : document).querySelectorAll('p,span,label,button,summary,li,div,a,h1,h2,h3,h4,td,th').forEach(e => {
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
  return 'CHỮ TƯƠNG PHẢN < 4.5: ' + bad.length + '\n' + bad.slice(0, 25).join('\n') + '\nCHỮ < 12.5px: ' + small.length + '\n' + small.slice(0, 25).join('\n');
})()
