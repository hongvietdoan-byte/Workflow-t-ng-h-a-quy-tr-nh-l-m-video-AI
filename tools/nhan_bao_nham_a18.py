"""Bảng GÁN NHÃN báo nhầm cho khóa nhận diện A18 (thẩm định 4 lỗ hổng #1) — 0 USD, không gọi model, CHỈ ĐỌC CSDL bản chính.

Chạy lại khóa nhận diện (core.identity_declare) trên prompt thật #24 như chạy khô K0b (tools/dryrun_k0b_p24.py — cùng hàm
identity_rows) hai lần: KHÔNG lọc (như summary.json cũ) và LỌC theo BYĐ (data_out/k0b_p24/byd_shot*.json: cỡ cảnh, mặt/lưng, có trong
khung). Mục còn bị báo sau lọc (thieu / thieu_mau / sai_mau) → bảng cho người dùng gán "đúng lỗi / báo nhầm" (≤ 30 mục). Ghi
docs/NHAN_BAO_NHAM_A18_2026-10-10.md (đường dẫn neo theo repo, không theo cwd):

    PYTHONUTF8=1 py tools/nhan_bao_nham_a18.py [--main D:/AI-Video-Pipeline] [--max 30]

#22: repo chưa có dữ liệu chạy khô (data_out/) → bảng ghi rõ "chưa có", không im lặng bỏ.
"""
import argparse
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import identity_declare as idd  # noqa: E402

DATA = os.path.join(ROOT, "data_out", "k0b_p24")
OUT = os.path.join(ROOT, "docs", "NHAN_BAO_NHAM_A18_2026-10-10.md")
BAO = ("thieu", "thieu_mau", "sai_mau")
NGUONG = ("Mục 9 kế hoạch chỉ có ngưỡng cho LỚP CLAUDE: báo nhầm ≤ 10 % trước khi chặn, cỡ mẫu ≥ 50 mục trên ≥ 2 dự án. Lớp CODE A18 "
          "chưa có ngưỡng riêng → tạm dùng ≤ 10 % (thẩm định 4 đề n ≥ 30) — **chờ người dùng chốt**. Chưa đạt → `CHAN_DO = False` "
          "(thiếu chữ = VÀNG, không chặn).")


def _dryrun():
    spec = importlib.util.spec_from_file_location("dryrun_k0b_p24", os.path.join(ROOT, "tools", "dryrun_k0b_p24.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def excerpt(text: str, item: str, n: int = 15) -> str:
    """≤ n từ của đoạn prompt nói về nhân vật: quanh chỗ nhắc món (nếu có), không thì đầu đoạn."""
    words = str(text or "").split()
    if not words:
        return "(đoạn prompt của nhân vật rỗng)"
    keys = [idd.fold(w) for w in idd.ITEMS.get(item, ((item,),))[0]]
    at = next((i for i, w in enumerate(words) if any(re.sub(r"[^\w-]", "", idd.fold(w)).startswith(k.split()[0]) for k in keys)), None)
    start = 0 if at is None else max(0, at - n // 2)
    part = words[start:start + n]
    return ("… " if start else "") + " ".join(part) + (" …" if start + n < len(words) else "")


def _count(rows, states):
    return sum(1 for n in rows for m in n["mon"] if m["trang_thai"] in states)


def build(main: str, max_rows: int = 30):
    mod = _dryrun()
    summary = json.load(open(os.path.join(DATA, "summary.json"), encoding="utf-8"))
    conn = mod.ro(main)
    scenes = {r[0]: json.loads(r[1]) for r in conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (mod.PID,))}
    shots = []
    for s in summary["shots"]:
        idx = s["shot"]
        data = scenes.get(idx)
        if data is None:
            raise SystemExit(f"shot {idx}: không có trong CSDL {main} (project {mod.PID}) — không tạo bảng thiếu shot")
        path = os.path.join(DATA, f"byd_shot{idx}.json")
        byd = json.load(open(path, encoding="utf-8")).get("byd")
        if byd is None:
            raise SystemExit(f"{path}: không có BYĐ — không lọc được")
        prompt, chars, people = data.get("image_prompt") or "", data.get("characters") or [], set(s["nguoi_trong_khung"])
        before = mod.identity_rows(conn, chars, prompt, people)
        after = mod.identity_rows(conn, chars, prompt, people, byd=byd)
        seg = idd.segment(prompt, {c: mod.MARKERS.get(c, [c.lower()]) for c in chars if mod.STAGE_KEY.get(c) in people})
        shots.append({"shot": idx, "co": byd["may"]["co"], "before": before, "after": after, "seg": seg,
                      "summary_thieu": sum(n["tong"].get("thieu", 0) for n in s["nhan_dien"])})
    return shots


def render(shots, max_rows: int = 30) -> str:
    b_thieu = sum(_count(s["before"], ("thieu",)) for s in shots)
    b_bao = sum(_count(s["before"], BAO) for s in shots)
    a_thieu = sum(_count(s["after"], ("thieu",)) for s in shots)
    a_bao = sum(_count(s["after"], BAO) for s in shots)
    a_can = sum(_count(s["after"], ("khong_can",)) for s in shots)
    sum_thieu = sum(s["summary_thieu"] for s in shots)
    b_shots = sum(1 for s in shots if _count(s["before"], BAO))
    a_shots = sum(1 for s in shots if _count(s["after"], BAO))
    items, filtered = [], []
    for s in shots:
        for n in s["after"]:
            for m in n["mon"]:
                if m["trang_thai"] in BAO:
                    items.append((s, n, m))
                elif m["trang_thai"] == "khong_can":
                    filtered.append((s, n, m))
    lines = [
        "# Bảng gán nhãn báo nhầm — khóa nhận diện A18 (10/10)",
        "",
        "Thẩm định 4 lỗ hổng #1: luật A18 \"mọi món must_keep phải có chữ trong prompt\" chưa đo báo nhầm. Bảng này lấy từ chạy khô #24",
        "(prompt ảnh thật trong CSDL, BYĐ `data_out/k0b_p24/byd_shot*.json`), sinh bằng `tools/nhan_bao_nham_a18.py` — chạy lại ra đúng bảng.",
        "",
        f"**Ngưỡng nhận:** {NGUONG}",
        "",
        "## Số đo trước / sau lọc theo BYĐ (#24, 9 shot)",
        "",
        "| | Trước lọc | Sau lọc |",
        "|---|---|---|",
        f"| món `thieu` | {b_thieu} | {a_thieu} |",
        f"| món bị báo (thieu + thieu_mau + sai_mau) | {b_bao} | {a_bao} |",
        f"| shot có món bị báo | {b_shots} | {a_shots} |",
        f"| món `khong_can` (lọc, có lý do) | 0 | {a_can} |",
        "",
        f"(summary.json cũ ghi {sum_thieu} món `thieu` — số \"trước lọc\" ở đây chạy lại cùng hàm trên CSDL hiện tại.)",
        "",
        "## Gán nhãn (mỗi mục một chạm)",
        "",
        "Cột cuối: ghi **đúng lỗi** (prompt thật sự thiếu / sai món đó, ảnh dễ vẽ sai) hoặc **báo nhầm** (món có trong khung đúng hoặc không",
        "cần chữ ở shot này). Kết quả code: `thieu` = không có chữ món; `thieu_mau` = có món, thiếu màu chính; `sai_mau` = màu ngược khóa.",
        "",
        "| # | Shot (cỡ) | Nhân vật | Món (màu khóa) | Kết quả code | Mức | Trích prompt (≤ 15 từ) | Người dùng: đúng lỗi / báo nhầm |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, (s, n, m) in enumerate(items[:max_rows], 1):
        mau = "/".join(m.get("mau_chinh") or []) or "—"
        ex = excerpt(s["seg"].get(n["nhan_vat"], ""), m["mon"]).replace("|", "/")
        lines.append(f"| {i} | {s['shot']} ({s['co']}) | {n['nhan_vat']} | {m['mon']} ({mau}) | {m['trang_thai']} | "
                     f"{'ĐỎ' if m['muc'] == 'do' else 'VÀNG'} | {ex} | |")
    if len(items) > max_rows:
        lines.append(f"\n{len(items) - max_rows} mục sau mục {max_rows} chưa đưa vào bảng (giới hạn ≤ {max_rows}).")
    if not items:
        lines.append("| — | — | — | — | không còn mục bị báo | — | — | — |")
    lines += ["", "## Món bị lọc (`khong_can`) — để người dùng xem lọc có che lỗi thật không", "",
              "| Shot (cỡ) | Nhân vật | Món | Lý do |", "|---|---|---|---|"]
    for s, n, m in filtered:
        lines.append(f"| {s['shot']} ({s['co']}) | {n['nhan_vat']} | {m['mon']} | {m['ly_do']} |")
    lines += ["", "## Chưa có",
              "- #22: repo chưa có dữ liệu chạy khô (không có `data_out/` cho #22) — chưa đưa vào bảng; cỡ mẫu hiện < 30 / 1 dự án, chưa",
              "  đủ mẫu số mục 9 (≥ 50 mục, ≥ 2 dự án).",
              "- Lọc chưa chỉnh theo tư thế (ngồi / quỳ / bò đổi phần thân trong khung) và chưa thấy vật che (bàn, thành giếng) — K1a.",
              "- Mục có trích \"(đoạn prompt của nhân vật rỗng)\": `segment` chia prompt theo từ đánh dấu; hai dạng yêu nữ dùng chung",
              "  'creature' nên chữ thuộc dạng nhắc trước — 'thieu' ở dạng kia có thể là báo nhầm do tách đoạn (người dùng gán để đo).", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default="D:/AI-Video-Pipeline")
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    shots = build(a.main, a.max)
    text = render(shots, a.max)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    for s in shots:
        print(f"S{s['shot']} {s['co']}: thieu {_count(s['before'], ('thieu',))} -> {_count(s['after'], ('thieu',))}, "
              f"bao {_count(s['before'], BAO)} -> {_count(s['after'], BAO)}, khong_can {_count(s['after'], ('khong_can',))}")
    print("ghi", a.out)


if __name__ == "__main__":
    main()
