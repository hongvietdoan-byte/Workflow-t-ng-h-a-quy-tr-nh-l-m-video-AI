"""M2.10 SHADOW chạy tay: gói gửi TỐI GIẢN dựng bên cạnh mọi gói ĐÃ gửi của một dự án (jobs.sent_package) — 0 USD, CSDL mở CHỈ ĐỌC.

    PYTHONUTF8=1 py tools/lean_package_shadow.py --db D:/AI-Video-Pipeline/data/pipeline.db --project 31 --out <thư mục ngoài data/>

Ghi <out>/job_<id>.json (báo cáo core/lean_package.shadow) + tong_hop.json + tong_hop.md (TB độ dài / số ref thật → tối giản theo loại job,
ref bỏ theo mã lý do, loại shot, trường BYĐ không còn nói). Không gửi, không ghi CSDL; không cần cờ lean_package (cờ chỉ điều khiển runner).
docs/KE_HOACH_GOI_GUI_TOI_GIAN_2026-10-21.md."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import lean_package as L  # noqa: E402

TYPES = ("image_gen", "video_gen")


def _load(raw):
    try:
        d = json.loads(raw) if raw else {}
    except ValueError:
        d = {}
    return d if isinstance(d, dict) else {}


def run(db: str, project: int, out: str, jobs=None, limit: int = 0) -> dict:
    os.makedirs(out, exist_ok=True)
    reports = []
    with closing(sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        scenes = {r[0]: (r[1], _load(r[2])) for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=?", (project,))}
        by_idx = sorted((idx, sid) for sid, (idx, _) in scenes.items())
        prev_of = {sid: (by_idx[n - 1][1] if n else None) for n, (_, sid) in enumerate(by_idx)}
        q = ("SELECT id, scene_id, type, sent_package FROM jobs WHERE project_id=? AND type IN ('image_gen','video_gen') "
             "AND sent_package IS NOT NULL AND sent_package != '' ORDER BY id")
        for jid, sid, jtype, pkg in conn.execute(q, (project,)).fetchall():
            if jobs and jid not in jobs:
                continue
            data = scenes.get(sid, (None, {}))[1]
            prev = scenes.get(prev_of.get(sid), (None, None))[1] if prev_of.get(sid) else None
            rep = L.shadow(pkg, data, kind="image" if jtype == "image_gen" else "video", job_id=jid, prev_data=prev)
            rep["type"], rep["scene_id"] = jtype, sid
            L.write(rep, os.path.join(out, f"job_{jid}.json"))
            reports.append(rep)
            if limit and len(reports) >= limit:
                break
    summary = summarize(reports, project)
    with open(os.path.join(out, "tong_hop.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "tong_hop.md"), "w", encoding="utf-8") as f:
        f.write(markdown(summary))
    return summary


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def summarize(reports, project) -> dict:
    out = {"project": project, "so_goi": {}, "loi": [], "tb": {}, "ref_bo": {}, "loai": {}, "khong_con_noi": {}, "canh_bao": {}}
    for t in TYPES:
        rs = [r for r in reports if r.get("type") == t and not r.get("loi")]
        if not rs and not any(r.get("type") == t for r in reports):
            continue
        out["so_goi"][t] = len([r for r in reports if r.get("type") == t])
        out["tb"][t] = {"chars_that": _avg([r["that"]["chars"] for r in rs]), "chars_gon": _avg([r["gon"]["chars"] for r in rs]),
                        "refs_that": _avg([r["that"]["refs"] for r in rs]), "refs_gon": _avg([r["gon"]["refs"] for r in rs]),
                        "ty_le_chars": _avg([r.get("ty_le_chars") for r in rs])}
        for key, items in (("ref_bo", lambda r: [x["ly_do"] for x in r["ref_bo"]]), ("loai", lambda r: [r["loai"]]),
                           ("khong_con_noi", lambda r: [x["truong"] for x in r["phu_byd"]["khong_con_noi"]]),
                           ("canh_bao", lambda r: [w["ma"] for w in r["canh_bao"]])):
            bucket = out[key].setdefault(t, {})
            for r in rs:
                for k in items(r):
                    bucket[k] = bucket.get(k, 0) + 1
    out["loi"] = [{"job_id": r.get("job_id"), "loi": r["loi"]} for r in reports if r.get("loi")]
    return out


def markdown(s) -> str:
    lines = [f"# Gói tối giản SHADOW — dự án #{s['project']} (KHÔNG gửi, 0 USD)", "",
             "| loại job | số gói | ký tự TB thật → gọn (tỉ lệ) | ref TB thật → gọn |", "|---|---|---|---|"]
    for t, tb in s["tb"].items():
        lines.append(f"| {t} | {s['so_goi'][t]} | {tb['chars_that']} → {tb['chars_gon']} ({tb['ty_le_chars']}) | "
                     f"{tb['refs_that']} → {tb['refs_gon']} |")
    for key, title in (("loai", "Loại shot"), ("ref_bo", "Ref bỏ theo mã"), ("khong_con_noi", "Trường BYĐ không còn nói"),
                       ("canh_bao", "Cảnh báo")):
        lines += ["", f"## {title}"]
        for t, b in s[key].items():
            lines.append(f"- {t}: " + (", ".join(f"{k} ×{n}" for k, n in sorted(b.items(), key=lambda x: -x[1])) or "—"))
    if s["loi"]:
        lines += ["", "## Gói không dựng được"] + [f"- job {x['job_id']}: {x['loi']}" for x in s["loi"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gói gửi tối giản SHADOW trên gói đã gửi (0 USD, CSDL chỉ đọc)")
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB"), help="tệp CSDL (mặc định PIPELINE_DB)")
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--out", required=True, help="thư mục ghi báo cáo (ngoài data/ thật)")
    ap.add_argument("--job", type=int, action="append", help="chỉ job này (lặp được)")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    if not a.db or not os.path.exists(a.db):
        print(f"Không thấy CSDL: {a.db!r} (--db hoặc PIPELINE_DB)", file=sys.stderr)
        return 2
    s = run(a.db, a.project, a.out, jobs=set(a.job or []), limit=a.limit)
    print(markdown(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
