"""Render the "who does what in each dashboard step" walkthrough as phone-friendly PNGs (1080 px wide).

    py tools/make_flow_images.py [--out docs/images]

Needs Chrome or Edge (headless screenshot). Text lives in STEPS below: edit it and re-run.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from html import escape

WHO = {"me": ("👤", "Bạn", "#4F46E5", "#EEF0FF"), "sys": ("⚙️", "Hệ thống", "#667085", "#F2F4F7"),
       "ai": ("🤖", "Claude", "#7A5AF8", "#F4F0FF"), "ext": ("🎬", "Dịch vụ ngoài", "#0BA5EC", "#E5F5FD")}

STEPS = [
    ("1", "Kịch bản & phân tích", "Từ file kịch bản đến Character Bible đã khóa", [
        ("me", "Upload kịch bản .docx, bấm “Chạy phân tích”"),
        ("sys", "Tách cảnh + đoán tên nhân vật (theo dòng “Cảnh 1”, “Tên: lời thoại”)"),
        ("ai", "Director: lập Character Bible + thông số từng cảnh (bạn dán JSON, hoặc bấm nút khi có API key)"),
        ("sys", "Kiểm tra JSON, lưu, dò IP so với blocklist → cảnh báo “IP rủi ro”"),
        ("me", "Sửa nhân vật cho hết cảnh báo → bấm “Duyệt & khóa”")]),
    ("2", "Gen ảnh + QC", "Mỗi cảnh một ảnh được duyệt", [
        ("me", "Bấm “Tạo job gen ảnh”"),
        ("ext", "Deepix gen ảnh (hệ thống tự hỏi trạng thái, tự tải về)"),
        ("ai", "Chấm điểm 5 tiêu chí: nhân vật, tay/mặt, bố cục, mood, chi tiết thừa"),
        ("sys", "human_qc: mọi ảnh chờ bạn.  auto: ≥ ngưỡng tự duyệt, thấp hơn tự loại (có vùng chờ bạn ở giữa)"),
        ("me", "Duyệt hoặc Loại (kèm ghi chú lỗi). “Duyệt tất cả” hỏi Có/Không một lần"),
        ("sys", "Điểm quá thấp (mặc định < 0,50) → tự loại ở cả hai chế độ. Bị loại → vào 🗑 Thùng rác (giữ 30 ngày), xếp hàng gen ảnh mới, ghi chú đưa vào prompt. Quá 3 lần → “cần chú ý”")]),
    ("3", "Video Prompt", "Mỗi cảnh một câu lệnh chuyển động", [
        ("ai", "Viết motion prompt cho từng cảnh có ảnh đã duyệt (Seedance: kèm hướng dẫn riêng)"),
        ("sys", "Kiểm tra + lưu, trạng thái “chờ duyệt”"),
        ("me", "Sửa nếu cần → Duyệt (từng cảnh hoặc “Duyệt tất cả”)")]),
    ("4", "Gen video", "Ảnh + motion prompt → clip", [
        ("me", "Chọn model (Kling / Seedance), xem ước tính chi phí, tick xác nhận nếu lô ≥ 10 clip"),
        ("me", "Bấm “Tạo job gen video” (cảnh phải có ảnh VÀ motion prompt đã duyệt)"),
        ("ext", "Clip AI gen video (hệ thống gửi, hỏi trạng thái, tải mp4; lỗi mạng tạm thì tự thử lại)"),
        ("sys", "Bị chặn “risk control” → ghi lại, KHÔNG tự thử lại (tránh tốn credit)"),
        ("me", "Xem clip; bị chặn thì sửa prompt/nhân vật hoặc đổi model rồi Retry")]),
    ("5a", "Nhạc nền & âm thanh", "Chọn nhạc cho video", [
        ("sys", "Gợi ý prompt nhạc từ mood các cảnh + tổng độ dài"),
        ("ext", "Clip AI tạo 3 bản nhạc nháp (tùy chọn thêm SFX, giọng đọc)"),
        ("me", "Nghe, chọn 1 bản (hoặc upload nhạc có sẵn / không dùng)")]),
    ("5b", "Ghép & Render", "Ra video cuối", [
        ("sys", "Nạp clip theo thứ tự cảnh, đo độ dài thật, cảnh báo cảnh thiếu"),
        ("me", "Chọn clip, kiểu chuyển cảnh, âm lượng nhạc → bấm “Render Final”"),
        ("sys", "Ghép bằng ffmpeg (video + nhạc + SFX/giọng đọc) → FINAL_VIDEO.mp4"),
        ("me", "Xem bản cuối, tải về")]),
    ("↺", "Lịch sử", "Truy vết", [
        ("sys", "Tự ghi mọi thay đổi trạng thái của từng job (ai làm: bạn, hệ thống hay AI)"),
        ("me", "Xem và so sánh các lần gen")]),
]

NOTES = [
    "Bạn là người duyệt ở mọi cổng chính: khóa nhân vật, duyệt ảnh, duyệt motion prompt, xác nhận chi phí. Hệ thống không tự nhảy sang bước sau, mỗi bước bạn bấm.",
    "Claude chỉ làm 3 việc: Director, chấm điểm ảnh, viết motion prompt. Hiện bạn dán JSON từ Claude Desktop; có API key thì bấm nút.",
    "Đã chạy thật: ảnh Deepix, video Kling và Seedance, ghép ffmpeg. Chưa chạy thật: nhạc/SFX/giọng đọc, nút Claude API, một cảnh trọn từ Bước 1 đến 5b.",
]

PAGES = [([0, 1], False), ([2, 3, 4], False), ([5, 6], True)]

CSS = """
*{box-sizing:border-box}body{margin:0;width:1080px;background:#F4F5F8;color:#1A1F2B;
font-family:'Segoe UI','Inter',Arial,sans-serif;padding:40px 36px 36px}
h1{font-size:46px;margin:0 0 8px;letter-spacing:-.01em}.sub{font-size:26px;color:#667085;margin:0 0 22px}
.legend{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:26px}
.chip{font-size:24px;font-weight:600;padding:8px 18px;border-radius:30px}
.card{background:#fff;border:2px solid #E2E5EB;border-radius:24px;padding:26px 28px;margin-bottom:26px}
.head{display:flex;align-items:center;gap:18px;margin-bottom:18px}
.num{min-width:74px;height:74px;border-radius:37px;background:#4F46E5;color:#fff;display:grid;place-items:center;
font-size:34px;font-weight:800;padding:0 10px}
.title{font-size:36px;font-weight:800;line-height:1.15}.goal{font-size:24px;color:#667085}
.row{display:flex;gap:16px;align-items:flex-start;padding:14px 16px;border-radius:16px;margin-bottom:10px}
.who{min-width:200px;font-size:23px;font-weight:700;display:flex;gap:8px;align-items:center;padding-top:2px}
.txt{font-size:28px;line-height:1.3}
.note{font-size:27px;line-height:1.35;background:#FFF4E0;border:2px solid #F79009;border-radius:20px;padding:18px 22px;margin-bottom:16px}
.foot{font-size:22px;color:#667085;text-align:center;margin-top:8px}
"""


def page_html(idx: int, step_ids, with_notes: bool, total: int) -> str:
    legend = "".join(f'<span class="chip" style="background:{bg};color:{c}">{ic} {name}</span>'
                     for ic, name, c, bg in WHO.values())
    head = ""
    if idx == 0:
        head = ("<h1>Dashboard chạy thế nào?</h1><div class='sub'>Từng bước, ai làm việc gì</div>")
    body = ""
    for i in step_ids:
        num, title, goal, rows = STEPS[i]
        items = ""
        for who, text in rows:
            ic, name, c, bg = WHO[who]
            items += (f'<div class="row" style="background:{bg}"><div class="who" style="color:{c}">{ic} {name}</div>'
                      f'<div class="txt">{escape(text)}</div></div>')
        body += (f'<div class="card"><div class="head"><div class="num">{num}</div><div><div class="title">'
                 f'{escape(title)}</div><div class="goal">{escape(goal)}</div></div></div>{items}</div>')
    notes = ""
    if with_notes:
        notes = "<h1 style='font-size:36px;margin:8px 0 14px'>Cần biết</h1>" + "".join(
            f'<div class="note">{escape(n)}</div>' for n in NOTES)
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{head}'
            f'<div class="legend">{legend}</div>{body}{notes}<div class="foot">Trang {idx + 1}/{total}</div></body></html>')


def find_browser() -> str:
    for path in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if os.path.exists(path):
            return path
    sys.exit("Cần Chrome hoặc Edge để chụp ảnh.")


def screenshot(browser: str, html_path: str, png_path: str, height: int) -> None:
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--window-size=1080,{height}", f"--screenshot={png_path}",
                    "file:///" + html_path.replace("\\", "/")], check=True, capture_output=True, timeout=120)


def autocrop(png_path: str, margin: int = 36) -> None:
    """Cut the empty page background below the last content row (Pillow)."""
    from PIL import Image, ImageChops
    img = Image.open(png_path).convert("RGB")
    diff = ImageChops.difference(img, Image.new("RGB", img.size, (0xF4, 0xF5, 0xF8)))
    box = diff.getbbox()
    if box:
        img.crop((0, 0, img.width, min(box[3] + margin, img.height))).save(png_path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("docs", "images"))
    ap.add_argument("--height", type=int, default=2400, help="page height in px (content is top-aligned)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    browser = find_browser()
    work = tempfile.mkdtemp()
    for n, (ids, notes) in enumerate(PAGES):
        html = os.path.join(work, f"flow_{n + 1}.html")
        png = os.path.join(work, f"flow_{n + 1}.png")
        with open(html, "w", encoding="utf-8") as f:
            f.write(page_html(n, ids, notes, len(PAGES)))
        screenshot(browser, html, png, args.height)
        autocrop(png)
        shutil.copyfile(png, os.path.join(args.out, f"flow_{n + 1}.png"))
        print("wrote", os.path.join(args.out, f"flow_{n + 1}.png"))


if __name__ == "__main__":
    main()
