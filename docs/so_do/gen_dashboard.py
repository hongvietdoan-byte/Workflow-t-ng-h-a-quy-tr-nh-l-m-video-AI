"""Sơ đồ thao tác Dashboard: màn → nút → khâu chạy; tô tiện / lỏng / thiếu (mã dashboard/ 17/10)."""
import sys
from xml.sax.saxutils import escape

OUT = sys.argv[1]
G, A, R, C, P, Y = "#4dff6a", "#ffb020", "#ff5a5a", "#22e5ff", "#b388ff", "#ffe14d"
SCREENS = [
    ("① KỊCH BẢN", "dashboard/steps/step1*", "#ff4fd8", [
        (G, "💡 Ý tưởng / 📜 Đây là kịch bản", ["Biên kịch hỏi 3 hướng — giá ước tính trên nút"]),
        (G, "▶ Phân tích (tách cảnh) · 0 USD", ["tách cảnh; có ↩ Hoàn tác"]),
        (G, "🤖 Lập kế hoạch (≈ x USD)", ["MỘT nút: Director → Bible + shot + BYĐ", "+ code kiểm BYĐ, sửa ≤ 2 vòng"]),
        (R, "BYĐ không hiện trên Dashboard", ["không xem / sửa được ý đồ có cấu trúc"]),
        (A, "🩹 Bật cờ sửa lỗi · Bỏ qua có lý do", ["cờ đỏ trước chạy — bỏ qua được"]),
        (A, "🤖 Rà thoại · ↻ Chia shot lại cảnh", ["chỉ theo nút, không phải cổng"]),
        (A, "Nhân vật: duyệt ảnh mốc · Lock · giọng", ["có nút 'Vẫn vẽ theo mô tả chữ —", "bỏ qua ảnh mốc'"]),
        (A, "✔ Duyệt & khóa → Storyboard", ["thiếu ảnh mốc chỉ nhắc 1 dòng,", "KHÔNG chặn"]),
    ]),
    ("② STORYBOARD", "step2 (ảnh + QC) · step3 (motion, giọng)", "#3ca9ff", [
        (R, "Sân khấu 3D: KHÔNG có nút", ["dàn cảnh / giải máy chạy CLI", "tools/stage_auto (Claude chạy tay)"]),
        (G, "↻ Render lại nền 3D shot N · 0 USD", ["vẽ lại nền từ máy đã lưu"]),
        (R, "Xem GÓI trước khi gửi: KHÔNG có", ["chỉ hiện câu sẽ bỏ; prompt cuối +", "ảnh ref + nhãn chỉ có ở CLI replay"]),
        (A, "Cổng trước gen: ⚠ lưu ý (ẩn trong ⓘ)", ["lỗi chặn → ô '☐ Tôi đã xem,", "vẫn gen ảnh' (ghi 📊 Theo dõi)"]),
        (G, "▶ Gen ảnh các cảnh chưa có / đã cũ · $", ["một bấm = xếp hàng + gửi;", "ảnh chờ điều kiện tự gửi sau"]),
        (G, "Thẻ ảnh: ✔ Duyệt · ✖ Loại & gen lại", ["QC chấm điểm · ↩ Bỏ duyệt · ‹ › bản cũ"]),
        (A, "🤖 Viết motion · 🔍 Rà motion", ["rà theo nút, không thấy khung đầu"]),
        (G, "🎙 Tạo giọng · 🎧 Kiểm giọng · 0 USD", ["⏱ thời lượng clip theo giọng thật"]),
        (G, "✔ Duyệt storyboard → gửi video", ["cổng người dùng"]),
    ]),
    ("③ VIDEO", "dashboard/steps/step4.py", "#ff9a3c", [
        (G, "Dùng đề xuất model theo cảnh", ["Seedance / Kling theo từng shot"]),
        (R, "Xem GÓI video trước khi gửi: KHÔNG", ["motion + khung đầu + ref + model"]),
        (A, "Cổng K3: 'Bỏ qua kiểm nền'", ["/ 'Bỏ qua chờ nhóm' — chỉ cần lý do", "≥ 3 ký tự"]),
        (G, "Gen video · ↻ Gửi lại clip lỗi · $$", ["🔎 Tìm task thật (không trả 2 lần)"]),
        (G, "🤖 Kiểm tra N clip · ✔ Duyệt clip", ["↻ Gen lại · ✏ Sửa motion · ⭐ bản tốt"]),
        (G, "✂ Cắt lại · 🎞 Ghép bản nháp · 0 USD", ["xem nhanh cả đoạn"]),
    ]),
    ("④ BẢN GIAO", "dashboard/steps/step5.py", Y, [
        (A, "🤖 Brief nhạc · ✨ Tạo nháp · Chọn", ["chỉ người nghe chọn, không kiểm nhịp"]),
        (A, "✨ Tạo SFX · 🎥 Tiếng video ref → SFX", ["chỉ người"]),
        (A, "📝 Phụ đề · ⬇ .srt/.xlsx · 🔥 In phụ đề", ["chỉ người"]),
        (A, "🤖 AI đề xuất hiệu ứng · ✅ Thêm", ["chỉ người"]),
        (R, "Popup cuối clip: không có kiểm", ["giữ khung cuối — chỉ người nhìn"]),
    ]),
]

W, X0, CW, GAP = 1740, 30, 405, 15
TOP = 250
CH, CG = 74, 10
n_max = max(len(s[3]) for s in SCREENS)
LANE_Y = TOP + 90 + n_max * (CH + CG) + 30
H = LANE_Y + 140 + 40 + 330

o = []
a = o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Segoe UI, Arial, sans-serif">')
a('<defs><filter id="glow" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="4" result="b"/>'
  '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
  '<marker id="aw" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
  '<path d="M0,0 L10,5 L0,10 z" fill="#e6edf3"/></marker></defs>')
a('<style>.b{font-weight:700;font-size:15px;fill:#ffffff}.e{font-size:13px;fill:#b8c2cc}.lg{font-size:14px;fill:#c9d1d9}'
  '.c{font-size:15px;fill:#e6edf3}</style>')
a(f'<rect width="{W}" height="{H}" fill="#12161d"/>')
a(f'<text x="{W // 2}" y="44" text-anchor="middle" font-size="27" font-weight="700" fill="#e6edf3">'
  'Làm phim qua Dashboard — bấm nút nào, khâu nào chạy, chỗ nào tiện / lỏng / thiếu (17/10)</text>')
a(f'<text x="{W // 2}" y="72" text-anchor="middle" font-size="15" fill="#9aa4ae">Nguồn: mã dashboard/ (nhãn nút đúng chữ trên màn) · '
  'cờ máy chính 17/10 · từ 14/10 Claude thao tác Dashboard thay người dùng</text>')
lx = 70
for col, txt in ((G, "tiện / có kiểm"), (A, "lỏng: bỏ qua được, chỉ theo nút, chỉ người"), (R, "thiếu: không có nút / màn / kiểm")):
    a(f'<rect x="{lx}" y="94" width="22" height="16" rx="3" fill="{col}"/><text class="lg" x="{lx + 30}" y="107">{escape(txt)}</text>')
    lx += 470

# làn chế độ tự động
a(f'<rect x="{X0}" y="128" width="{W - 2 * X0}" height="80" rx="10" fill="#111a24" stroke="{P}" stroke-width="2.5" filter="url(#glow)"/>')
a(f'<text x="{X0 + 20}" y="160" font-size="18" font-weight="700" fill="#d3bcff">⚙ CHẾ ĐỘ TỰ ĐỘNG (chạy nối các màn)</text>')
a(f'<text class="c" x="{X0 + 20}" y="188">⏸ Tạm dừng · ■ Dừng hẳn · Nâng trần · ↺ Đặt lại — tự chạy Director → ảnh → video, DỪNG ở cổng gen ảnh và gen video; '
  'mọi lần "vẫn gen" ghi vào 📊 Theo dõi</text>')

for i, (title, src, col, chips) in enumerate(SCREENS):
    x = X0 + i * (CW + GAP)
    a(f'<rect x="{x}" y="{TOP}" width="{CW}" height="70" rx="10" fill="#111a24" stroke="{col}" stroke-width="3" filter="url(#glow)"/>')
    a(f'<text x="{x + CW / 2}" y="{TOP + 32}" text-anchor="middle" font-size="21" font-weight="700" fill="{col}">{escape(title)}</text>')
    a(f'<text x="{x + CW / 2}" y="{TOP + 56}" text-anchor="middle" class="e">{escape(src)}</text>')
    if i:
        px = x - GAP
        a(f'<line x1="{px - 2}" y1="{TOP + 35}" x2="{x - 3}" y2="{TOP + 35}" stroke="#e6edf3" stroke-width="2.5" marker-end="url(#aw)"/>')
    for j, (cc, btn, eff) in enumerate(chips):
        y = TOP + 90 + j * (CH + CG)
        a(f'<rect x="{x}" y="{y}" width="{CW}" height="{CH}" rx="8" fill="{cc}" fill-opacity="0.10" stroke="{cc}" stroke-width="2"/>')
        a(f'<rect x="{x}" y="{y}" width="6" height="{CH}" rx="3" fill="{cc}"/>')
        a(f'<text class="b" x="{x + 16}" y="{y + 24}">{escape(btn)}</text>')
        for k, line in enumerate(eff):
            a(f'<text class="e" x="{x + 16}" y="{y + 46 + k * 18}">{escape(line)}</text>')
        if j < len(chips) - 1:
            a(f'<line x1="{x + CW / 2}" y1="{y + CH}" x2="{x + CW / 2}" y2="{y + CH + CG}" stroke="#5a6672" stroke-width="2"/>')

# làn ngoài Dashboard
a(f'<rect x="{X0}" y="{LANE_Y}" width="{W - 2 * X0}" height="140" rx="10" fill="#111a24" stroke="{R}" stroke-width="2.5" '
  f'stroke-dasharray="10 6" filter="url(#glow)"/>')
a(f'<text x="{X0 + 20}" y="{LANE_Y + 34}" font-size="18" font-weight="700" fill="#ff9a9a">⛔ NGOÀI DASHBOARD — Claude chạy tay '
  '(người dùng không thấy, cờ có thể khác Dashboard)</text>')
outs = ["tools/stage_auto.py — sân khấu 3D chia vai (Đạo diễn / Quay phim), --crew-approve",
        "tools/stage_previs.py — previs Blender làm ref V2V",
        "tools/replay_payload.py — dựng lại GÓI gửi model (chỗ DUY NHẤT thấy đủ prompt + ảnh ref)",
        "sửa thẳng CSDL (byd, time, máy) · py -m devsys … — không hiện ngược lên Dashboard"]
for k, t in enumerate(outs):
    a(f'<text class="c" x="{X0 + 36 + (k % 2) * 830}" y="{LANE_Y + 72 + (k // 2) * 34}">• {escape(t)}</text>')

# tổng kết
yb = LANE_Y + 170
a(f'<rect x="{X0}" y="{yb}" width="{W - 2 * X0}" height="310" rx="12" fill="#111a24" stroke="{C}" stroke-width="2.5" filter="url(#glow)"/>')
a(f'<text x="{X0 + 24}" y="{yb + 38}" font-size="20" font-weight="700" fill="#7af1ff">Đọc sơ đồ: bấm qua Dashboard thì sao?</text>')
rows = [
    ("TIỆN", G, "Một nút chạy Director có ước tính · một bấm gen = xếp hàng + gửi · mọi nút tốn tiền hiện giá ước tính · cắt / ghép / render"),
    ("", G, "nền / kiểm giọng 0 USD · 🔎 Tìm task thật tránh trả 2 lần · chế độ tự động dừng ở 2 cổng gen."),
    ("LỎNG", A, "Cổng chặn gen ảnh có ô 'vẫn gen' · cổng video bỏ qua bằng lý do 3 ký tự · khóa Bible không chặn thiếu ảnh mốc ·"),
    ("", A, "cảnh báo dồn vào ⓘ · rà thoại / motion / storyboard chỉ chạy khi bấm · âm thanh, phụ đề, hiệu ứng chỉ người."),
    ("THIẾU", R, "Không có nút sân khấu 3D · không có màn xem ĐỦ gói ảnh / video trước khi trả tiền · BYĐ không hiện để duyệt ·"),
    ("", R, "việc Claude làm qua CLI không hiện ngược lên Dashboard → hai đường làm lệch nhau (bài học 16/10: cờ test ≠ cờ máy)."),
    ("KẾ HOẠCH", P, "Phần A: BYĐ v2 hiện ở màn Kịch bản (xem / sửa trường). Phần B: thẻ 'Gói sẽ gửi' cạnh nút Gen dùng chung"),
    ("", P, "replay_payload (đủ prompt + ảnh ref + nhãn + VÀNG chữ ↔ trường) → người duyệt nhìn đúng thứ model nhận."),
]
for k, (tag, col, txt) in enumerate(rows):
    yy = yb + 78 + k * 28
    if tag:
        a(f'<rect x="{X0 + 24}" y="{yy - 17}" width="98" height="24" rx="12" fill="{col}"/>'
          f'<text x="{X0 + 73}" y="{yy}" text-anchor="middle" font-size="13" font-weight="700" fill="#12161d">{tag}</text>')
    a(f'<text class="c" x="{X0 + 138}" y="{yy}">{escape(txt)}</text>')
a('</svg>')
open(OUT, "w", encoding="utf-8").write("\n".join(o))
print("ok", H)
