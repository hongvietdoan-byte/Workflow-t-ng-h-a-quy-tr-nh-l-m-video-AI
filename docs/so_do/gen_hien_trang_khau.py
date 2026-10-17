"""Sinh sơ đồ hiện trạng các khâu (swimlane) — dữ liệu từ devsys/stages.json + cờ máy chính 17/10 + lỗi 15–17/10."""
import sys
from xml.sax.saxutils import escape

OUT = sys.argv[1]
G, A, R, C, P = "#4dff6a", "#ffb020", "#ff5a5a", "#22e5ff", "#b388ff"
# (id, ten [dòng], tốn tiền, trước (màu, [dòng]), sau (màu, [dòng]), đọc từ (màu, chữ), lỗi ([dòng]), kế hoạch)
ROWS = [
    ("L1", ["Ý tưởng → kịch bản", "Biên kịch Claude · chat"], "$", (G, ["dựng được (nơi có trong Kho)", "IP / tên bị chặn"]),
     (A, ["chỉ người duyệt từng lượt"]), (G, "kết quả"), [], ""),
    ("L2", ["Bảng kê tài nguyên", "asset_checklist"], "$", (G, ["đối chiếu bảng kê với Kho"]), (R, ["không có"]), (G, "kết quả"), [], ""),
    ("L5", ["Hồ sơ nhân vật · Bible · ảnh mẫu Kho", "dạng nhân vật khai bằng dòng chữ"], "$", (R, ["KHÔNG CÓ"]),
     (A, ["chỉ người duyệt Kho"]), (R, "chữ mô tả Kho"),
     ["5 — dạng / khóa áo đoán từ chữ", "(character_forms: never, tóc, không dấu)"], "A2a · Q3"),
    ("L3", ["Đạo diễn: chia shot · prompt · BYĐ", "BYĐ #31 có 36/36 — khâu sau không đọc"], "$",
     (G, ["chuẩn hóa shot · cấu trúc prompt", "câu trái hình học — KHÔNG ai kiểm NGHĨA"]), (R, ["không có"]), (R, "chữ tự do"),
     ["2 — _POST_ONLY: 'overlay' chưa bao giờ", "khớp (ký tự backspace thay \\b)"], "A1"),
    ("L4", ["Thoại · chọn giọng", ""], "$", (A, ["rà thoại TẮT — chỉ theo nút"]), (R, ["không có"]), (R, "chữ tự do"), [], ""),
    ("L6", ["Sân khấu 3D: dàn cảnh · máy · nền", "#31 chạy tay bằng tools/stage_auto"], "$",
     (G, ["kiểm dàn cảnh · kiểm yêu cầu khung"]), (G, ["Đạo diễn duyệt render nền"]), (G, "BYĐ / shot_specs"),
     ["1 — POV đặt máy quay ngược 180°", "(plate_camera) · mốc nền suy từ chữ 'why'"], "A2d"),
    ("L7", ["Storyboard · ảnh neo", "scene_storyboard"], "$", (A, ["cờ rủi ro (môi, cast)", "— không xem gói"]),
     (A, ["rà storyboard theo nút + người"]), (R, "chữ tự do"), ["1 — _USES_HELD: shot sau 'fires it'", "mất ảnh súng"], "A2b"),
    ("L8", ["Lắp GÓI ẢNH: prompt cuối + ảnh ref", "runner._submit_args — dẫn thẳng tới tiền"], "→$",
     (R, ["KHÔNG CÓ (17/10 mới thêm VÀNG", "chữ ↔ cast / giờ)"]), (R, ["không có"]), (R, "chữ tự do"),
     ["≈ 12 — tên bối cảnh Việt 4 · trăng trong", "nhà 2 · đạo cụ 2 · cúi/cũi 1 · báo nhầm 3"], "A2c·e·f + B"),
    ("L9", ["Gen ẢNH khung đầu", "ClipAI"], "$", (R, ["KHÔNG lớp nào xem gói"]),
     (G, ["QC lớp 0 · QC Claude · bố cục/render", "Tổ QC học việc · người duyệt"]), (G, "kết quả"), [], ""),
    ("L10", ["Gen lại ảnh", "Đạo diễn viết lại prompt"], "$", (A, ["chỉ kiểm cấu trúc prompt"]), (R, ["không có"]),
     (R, "chữ tự do"), [], ""),
    ("L11", ["Motion prompt + dịch", ""], "$", (A, ["lint motion · rà motion (nút)", "— không thấy khung đầu"]), (R, ["không có"]),
     (R, "chữ tự do"), [], ""),
    ("L12", ["Lắp GÓI VIDEO", "motion + khung đầu + ref + model"], "→$$", (R, ["KHÔNG CÓ ở bước lắp", "(kiểm thật dồn về L13)"]),
     (R, ["không có"]), (R, "chữ tự do"), ["2 — dạng gom cả clip · ảnh OUTFIT vẫn", "gửi khi đổi dạng (seedance_refs)"], "A2a + B"),
    ("L13", ["Gen VIDEO (nháp → cao)", "Seedance / Kling"], "$$", (G, ["K3 kiểm gói trước gen", "(video_pregen)"]),
     (G, ["đo clip · QC clip · chọn ⭐ · người"]), (G, "kết quả"), [], ""),
    ("L14", ["TTS · nhạc · SFX · phụ đề", ""], "$", (R, ["không có"]), (A, ["chỉ TTS có kiểm code", "còn lại chỉ người"]),
     (A, "chữ / kết quả"), [], ""),
    ("L15", ["Dựng · bản thô · popup cuối", "ffmpeg — 0 USD"], "", (R, ["không có"]),
     (G, ["duyệt bản thô Claude", "popup: chỉ người"]), (G, "kết quả"), [], ""),
    ("L16", ["Thay đổi giữa chừng", "sửa shot / Kho"], "", (G, ["bộ kiểm tác động + Tổ rà soát", "— không xem gói, không xem ảnh"]),
     (R, ["không có"]), (R, "chữ tự do"), [], "B"),
]

W = 1720
TOP = 200
RH = 96
X_ID, X_K, W_K = 30, 96, 470
X_T, W_T = 590, 330
X_S, W_S = 940, 300
X_D, W_D = 1255, 125
X_L, W_L = 1395, 300
H = TOP + RH * len(ROWS) + 330

o = []
a = o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Segoe UI, Arial, sans-serif">')
a('<defs><filter id="glow" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="4" result="b"/>'
  '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
  '<marker id="aw" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
  '<path d="M0,0 L10,5 L0,10 z" fill="#c9d1d9"/></marker></defs>')
a('<style>.h{font-weight:700;font-size:16px;fill:#e6edf3}.k{font-weight:700;font-size:17px;fill:#ffffff}'
  '.ks{font-size:13px;fill:#9aa4ae}.c{font-size:14px;fill:#e6edf3}.id{font-weight:700;font-size:15px;text-anchor:middle}'
  '.lg{font-size:14px;fill:#c9d1d9}</style>')
a(f'<rect width="{W}" height="{H}" fill="#12161d"/>')
a(f'<text x="{W//2}" y="44" text-anchor="middle" font-size="27" font-weight="700" fill="#e6edf3">'
  'Hiện trạng các khâu dây chuyền video AI — chỗ nào yếu, thiếu, sai (17/10)</text>')
a(f'<text x="{W//2}" y="72" text-anchor="middle" font-size="15" fill="#9aa4ae">Nguồn: sổ khâu devsys/stages.json · trạng thái '
  'theo cờ máy chính 17/10 (devsys.stages.effective) · lỗi: rà quy ước 7 + commit 15–17/10 (#31)</text>')
# chú giải
lx = 60
for col, txt in ((G, "có kiểm, đang chạy"), (A, "chỉ người / theo nút / chỉ cấu trúc"), (R, "KHÔNG CÓ kiểm · đọc chữ tự do"),
                 (P, "phần kế hoạch sửa")):
    a(f'<rect x="{lx}" y="96" width="22" height="16" rx="3" fill="{col}"/><text class="lg" x="{lx + 30}" y="109">{escape(txt)}</text>')
    lx += 330
a(f'<text class="lg" x="{W - 60}" y="109" text-anchor="end">$ tốn tiền · →$ dẫn thẳng tới lời gọi tốn tiền</text>')
# đầu cột
for x, w, t in ((X_K, W_K, "KHÂU (theo thứ tự chạy)"), (X_T, W_T, "KIỂM TRƯỚC KHI TRẢ TIỀN"), (X_S, W_S, "KIỂM SAU"),
                (X_D, W_D, "KẾT LUẬN TỪ"), (X_L, W_L, "LỖI 15–17/10 · KẾ HOẠCH")):
    a(f'<text class="h" x="{x + w / 2}" y="{TOP - 34}" text-anchor="middle">{t}</text>')
    a(f'<line x1="{x}" y1="{TOP - 24}" x2="{x + w}" y2="{TOP - 24}" stroke="#3a4450" stroke-width="2"/>')


def cell(x, y, w, h, col, lines, cls="c"):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{col}" fill-opacity="0.10" stroke="{col}" stroke-width="2"/>')
    n = len([l for l in lines if l])
    y0 = y + h / 2 - (n - 1) * 10 + 5
    for i, l in enumerate([l for l in lines if l]):
        a(f'<text class="{cls}" x="{x + 12}" y="{y0 + i * 20}">{escape(l)}</text>')


for i, (sid, ten, money, (tc, tl), (sc, sl), (dc, dt), loi, plan) in enumerate(ROWS):
    y = TOP + i * RH
    h = RH - 16
    worst = R if (tc == R and money) or dc == R else (A if A in (tc, dc) else C)
    if i:
        a(f'<line x1="{X_K + 40}" y1="{y - 16}" x2="{X_K + 40}" y2="{y - 2}" stroke="#c9d1d9" stroke-width="2" marker-end="url(#aw)"/>')
    a(f'<circle cx="{X_ID + 26}" cy="{y + h / 2}" r="24" fill="#111a24" stroke="{worst}" stroke-width="2.5"/>')
    a(f'<text class="id" x="{X_ID + 26}" y="{y + h / 2 + 5}" fill="{worst}">{sid}</text>')
    a(f'<rect x="{X_K}" y="{y}" width="{W_K}" height="{h}" rx="10" fill="#111a24" stroke="{worst}" stroke-width="3" filter="url(#glow)"/>')
    a(f'<text class="k" x="{X_K + 16}" y="{y + (32 if ten[1] else 46)}">{escape(ten[0])}</text>')
    if ten[1]:
        a(f'<text class="ks" x="{X_K + 16}" y="{y + 56}">{escape(ten[1])}</text>')
    if money:
        a(f'<text x="{X_K + W_K - 14}" y="{y + 30}" text-anchor="end" font-size="16" font-weight="700" fill="#ffe14d">{money}</text>')
    cell(X_T, y, W_T, h, tc, tl)
    cell(X_S, y, W_S, h, sc, sl)
    cell(X_D, y, W_D, h, dc, [dt])
    if loi:
        cell(X_L, y, W_L, h, R, loi)
    else:
        a(f'<text class="lg" x="{X_L + 12}" y="{y + h / 2 + 5}">—</text>')
    if plan:
        a(f'<rect x="{X_K + W_K - 122}" y="{y + h - 26}" width="112" height="20" rx="10" fill="{P}"/>'
          f'<text x="{X_K + W_K - 66}" y="{y + h - 11}" text-anchor="middle" font-size="12" font-weight="700" fill="#12161d">'
          f'{escape(plan)}</text>')

# vùng tô: lỗi dồn ở gói
yb = TOP + RH * len(ROWS) + 10
a(f'<rect x="30" y="{yb}" width="{W - 60}" height="300" rx="12" fill="#111a24" stroke="{C}" stroke-width="2.5" filter="url(#glow)"/>')
a(f'<text x="56" y="{yb + 38}" font-size="20" font-weight="700" fill="#7af1ff">Đọc sơ đồ: khâu yếu · thiếu · sai</text>')
notes = [
    ("SAI", R, "L8 + L12 (lắp gói ảnh / video) là chỗ code ĐOÁN Ý TỪ CHỮ để chọn ảnh, khóa áo, câu nền, câu sáng: ≈ 14/22 lỗi 15–17/10 nằm ở đây."),
    ("THIẾU", R, "L8 và L12 không có lớp kiểm nào trước tiền và không có test trên gói thật: lỗi chỉ lộ khi chạy replay_payload bằng tay → Phần B."),
    ("YẾU", A, "L3 có BYĐ có cấu trúc (36/36 shot #31) nhưng L5 · L7 · L8 · L12 không đọc, mà đọc lại chữ → hai nguồn lệch (dạng: 24 vs 21 shot) → Phần A."),
    ("THIẾU", R, "L5 Kho (dạng nhân vật, tên bối cảnh Anh) không có kiểm trước: khai dạng bằng dòng chữ, tên Việt lọt prompt (sửa 4 lần)."),
    ("YẾU", A, "L3 · L10 · L11 chỉ kiểm CẤU TRÚC prompt — không ai kiểm NGHĨA prompt ↔ ý đồ; L4 · L14 · L15 (âm thanh, popup) chỉ có người."),
    ("ĐO", P, "Phần C: đếm lỗi lọt cổng mỗi dự án (/10 shot) + số shot có gói trái trường (0 USD) trước/sau khi bật byd_fields."),
]
for j, (tag, col, txt) in enumerate(notes):
    yy = yb + 76 + j * 37
    a(f'<rect x="56" y="{yy - 17}" width="74" height="24" rx="12" fill="{col}"/>'
      f'<text x="93" y="{yy}" text-anchor="middle" font-size="13" font-weight="700" fill="#12161d">{tag}</text>')
    a(f'<text class="c" x="146" y="{yy}" font-size="15">{escape(txt)}</text>')
a('</svg>')
open(OUT, "w", encoding="utf-8").write("\n".join(o))
print("ok", H)
