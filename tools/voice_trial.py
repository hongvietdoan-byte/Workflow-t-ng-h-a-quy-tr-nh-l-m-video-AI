"""AU-h — Bộ thử giọng Việt chuẩn: 10 câu mẫu × 2–3 model TTS × các giọng ghi hỗ trợ tiếng Việt → người nghe chấm → chốt cấu hình.

    py tools/voice_trial.py                       (chỉ xem kế hoạch: bao nhiêu lượt TTS, giọng nào, model nào — KHÔNG gửi gì)
    py tools/voice_trial.py --yes                 (gửi thật — tốn credit âm thanh, tính vào trần lượt âm thanh ⚙ → 💵)
    py tools/voice_trial.py --poll <thư mục>      (tải file về, kiểm tự động AU-f, ghi bảng chấm bang_cham.csv)
    py tools/voice_trial.py --summary <thư mục>   (đọc điểm người nghe đã điền → điểm trung bình theo model × giọng)

Tùy chọn: --models eleven_v3,eleven_flash_v2_5  --voices 70,72 (id giọng)  --max-voices 4 (mặc định: 4 giọng clone VN ưu tiên,
data/voices_vi.json; tăng lên để thử thêm giọng official có tiếng Việt).
Chạy ở GĐ-I bậc 0 (xin phép trước khi --yes). Cần CLIPAI_TOKEN như khi chạy Dashboard. Kết quả ở data/voice_trial/<thời điểm>/.
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import audio_lib, music, voice, voice_check  # noqa: E402
from core.db import connect  # noqa: E402
from core.providers import ProviderError  # noqa: E402

# Tên nhân vật (tiếng Anh giữ nguyên), từ game, số, câu cảm xúc — những chỗ giọng Việt hay sai
SENTENCES = [
    ("ten_rieng", "Kelly, Kenta và Maxim, tập trung ở tháp đồng hồ ngay!"),
    ("tu_game", "Loot xong rồi leo rank thôi, trận này phải Booyah!"),
    ("so_va_ma", "Bản cập nhật OB55 có ba nhân vật mới và mười hai skin."),
    ("hanh_dong", "Cẩn thận, bo đang thu nhỏ, chạy vào vòng an toàn đi!"),
    ("hai_huoc", "Ủa, sao ông lại đứng im giữa bãi đất trống thế kia?"),
    ("buon", "Tôi xin lỗi... lẽ ra tôi phải bảo vệ được cậu."),
    ("het_lon", "Không! Đừng bắn nữa, đồng đội của tôi ở đó!"),
    ("thi_tham", "Suỵt, nhỏ tiếng thôi, đội bên kia ở ngay sau bức tường."),
    ("dai", "Nếu hôm nay chúng ta không giữ được điểm này, cả đội sẽ phải bắt đầu lại từ đầu, và tôi không muốn điều đó xảy ra."),
    ("cau_hoi", "Cậu có chắc là Alok đã hồi máu cho cả đội chưa?"),
]
DEFAULT_MODELS = ["eleven_v3", "eleven_flash_v2_5", "eleven_turbo_v2_5"]
ROOT = os.path.join("data", "voice_trial")


def vi_voices(provider, ids=None, limit=3):
    voices = voice.casting_pool(voice.library(provider))     # the 4 preferred team 'VN' voices come first
    if ids:
        voices = [v for v in voices if str(v.get("id")) in ids]
    return voices[:limit] if limit else voices


def plan(args):
    provider = music.audio_provider()
    if provider is None:
        sys.exit("Chưa cấu hình âm thanh (AUDIO_PROVIDER / CLIPAI_TOKEN).")
    models = [m for m in args.models.split(",") if m] if args.models else DEFAULT_MODELS
    bad = [m for m in models if m not in voice.VI_MODELS]
    if bad:
        sys.exit(f"Model không có tiếng Việt: {bad} (dùng trong {voice.VI_MODELS})")
    try:
        voices = vi_voices(provider, set(args.voices.split(",")) if args.voices else None, args.max_voices)
    except ProviderError as e:
        sys.exit(f"Không lấy được danh sách giọng: {e}")
    if not voices:
        sys.exit("Không có giọng nào ghi hỗ trợ tiếng Việt.")
    total = len(SENTENCES) * len(models) * len(voices)
    print(f"{len(SENTENCES)} câu × {len(models)} model × {len(voices)} giọng = {total} lượt TTS")
    print("Model:", ", ".join(models))
    print("Giọng:", ", ".join(("⭐ " if voice.preferred(v) else "") + f"{voice.display_name(v)} (id {v.get('id')}, "
                                f"{voice.voice_gender(v) or '?'})" for v in voices))
    return provider, models, voices, total


def submit(args):
    provider, models, voices, total = plan(args)
    if not args.yes:
        print("\nChỉ xem kế hoạch. Thêm --yes để gửi thật (tốn credit âm thanh).")
        return
    db = os.path.join("data", "manifest.sqlite")
    if not os.path.exists(db):   # the audio cap and the cost ledger live there: never send against a new empty database
        sys.exit(f"Không thấy {db} ở thư mục hiện tại ({os.getcwd()}). Chạy từ thư mục dự án có dữ liệu thật, ví dụ D:\\AI-Video-Pipeline.")
    out = os.path.join(ROOT, datetime.now().strftime("%Y%m%d_%H%M"))
    os.makedirs(out, exist_ok=True)
    conn = connect(db)
    sent = 0
    for m in models:
        for v in voices:
            for key, text in SENTENCES:
                e = audio_lib.submit_tts(provider, out, voice.speakable(text), int(v["id"]), v.get("name", ""), m, None,
                                         ledger=(conn, None), extra={"trial": key, "text": text, "model": m, "voice_id": v["id"],
                                                                     "voice_name": voice.display_name(v)})
                if not e.get("asset_id"):
                    print(f"Dừng: {e.get('message')}")
                    print(f"Đã gửi {sent}/{total}. Thư mục: {out}")
                    return
                sent += 1
    print(f"Đã gửi {sent} lượt. Chạy tiếp: py tools/voice_trial.py --poll {out}")


def poll(args):
    provider = music.audio_provider()
    deadline = time.time() + args.timeout
    while True:
        counts = audio_lib.refresh(provider, args.poll)
        print(f"đang chạy {counts.get('running', 0)} · xong {counts.get('succeeded', 0)} · lỗi {counts.get('failed', 0)}")
        if not counts.get("running") or time.time() > deadline:
            break
        time.sleep(5)
    rows = []
    for e in audio_lib.load(args.poll):
        path = os.path.join(args.poll, e["file"]) if e.get("file") else None
        chk = voice_check.check_line(path, e.get("text") or "") if path and os.path.exists(path) else {"problems": [e.get("message") or "không có file"]}
        rows.append({"model": e.get("model"), "giong": e.get("voice_name"), "cau": e.get("trial"), "noi_dung": e.get("text"),
                     "file": e.get("file") or "", "giay": round(chk.get("seconds") or 0, 2),
                     "kiem_tu_dong": "; ".join(chk.get("problems") or []) or "ok", "nghe_ra": chk.get("heard") or "",
                     "diem_1_5": "", "ghi_chu": ""})
    sheet = os.path.join(args.poll, "bang_cham.csv")
    with open(sheet, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["model"])
        w.writeheader()
        w.writerows(rows)
    print(f"Bảng chấm: {sheet} — nghe từng file, điền cột diem_1_5 (1 tệ … 5 như người Việt nói), rồi chạy --summary.")


def summary(args):
    sheet = os.path.join(args.summary, "bang_cham.csv")
    scores = defaultdict(list)
    flagged = defaultdict(int)
    with open(sheet, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if (r.get("diem_1_5") or "").strip():
                scores[(r["model"], r["giong"])].append(float(r["diem_1_5"]))
            if r.get("kiem_tu_dong") not in ("ok", "", None):
                flagged[(r["model"], r["giong"])] += 1
    if not scores:
        sys.exit("Chưa có điểm nào trong cột diem_1_5.")
    ranked = sorted(scores.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))
    for (m, g), s in ranked:
        print(f"{sum(s) / len(s):.2f}  {m:20s} {g:25s} ({len(s)} câu chấm, {flagged[(m, g)]} câu bị cờ tự động)")
    (m, g), _ = ranked[0]
    print(f"\nĐề xuất: model {m} + giọng {g}. Ghi kết quả vào docs/api_notes.md và chốt ở voice.DEFAULT_MODEL / hồ sơ giọng nhân vật.")
    with open(os.path.join(args.summary, "ket_qua.json"), "w", encoding="utf-8") as f:
        json.dump([{"model": m, "giong": g, "diem": sum(s) / len(s), "so_cau": len(s)} for (m, g), s in ranked], f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true", help="gửi thật (tốn credit)")
    ap.add_argument("--models", help="danh sách model, phân cách bằng dấu phẩy")
    ap.add_argument("--voices", help="id giọng, phân cách bằng dấu phẩy")
    ap.add_argument("--max-voices", type=int, default=4, help="mặc định 4 = 4 giọng clone VN ưu tiên (2 nam, 2 nữ)")
    ap.add_argument("--poll", help="thư mục lượt thử để tải + kiểm + ghi bảng chấm")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--summary", help="thư mục lượt thử có bảng chấm đã điền điểm")
    args = ap.parse_args()
    from core.adapters.check import load_dashboard_env
    load_dashboard_env()          # VIDEO_PROVIDER=clipai etc., like the Dashboard launcher (tokens stay in the user environment)
    if args.poll:
        poll(args)
    elif args.summary:
        summary(args)
    else:
        submit(args)


if __name__ == "__main__":
    main()
