"""Báo cáo bất biến khâu 3D theo GỐC (C-3D-GOC-A, R2 / R3 / R4) cho một dự án — 0 USD, CHỈ ĐỌC (CSDL mở mode=ro, không ghi gì).

    PYTHONUTF8=1 py tools/camera_invariants.py --project 31 [--db D:/AI-Video-Pipeline/data/manifest.sqlite]
        [--stage <thư mục k1>/stage.json] [--ref-word cats] [--json out.json]

Mỗi shot có máy Sân khấu 3D (`stage_camera`): độ nghiêng ↔ angle khai (R2-PITCH); chữ prompt ảnh / blocking / motion ↔ cái máy thấy
(R3: mốc từ --stage `marks` *_chan/*_dinh + khối giữ chỗ của máy); chữ có dấu / chủ thể video mẫu trong motion (R3-VI-TEXT / R3-REF-LEAK);
BYĐ ↔ trường shot (R4) + MỘT dòng cho shot thiếu BYĐ. Tỉ lệ người / sàn (R2-FRAMING / R2-FLOOR) cần chỗ đứng + chiều cao + tia sàn
Blender → chạy ở Sân khấu 3D (core.camera_invariants.shot_report), không đoán ở đây.
Mã thoát: 0 = không có phát hiện; 1 = có phát hiện VÀNG (báo, không chặn gì); 2 = không đọc được CSDL.
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import camera_invariants as ci  # noqa: E402
from core import stage_facts as sf  # noqa: E402
from core import stage_grid as sg  # noqa: E402


def _motion_text(d: dict) -> str:
    m = d.get("motion_en")
    if isinstance(m, dict):
        return " ".join(str(v) for v in m.values() if isinstance(v, str))
    return str(m or d.get("motion") or "")


def landmarks(stage_path: str) -> list:
    if not stage_path:
        return []
    with open(stage_path, encoding="utf-8") as f:
        stage = json.load(f)
    out = []
    for lm in ci.landmarks_from_stage(stage):
        lm = dict(lm, base=list(sg.model_from_rel(stage, lm["base"])), top=list(sg.model_from_rel(stage, lm["top"])) if lm["top"] else None)
        out.append(lm)
    return out


def props_of(d: dict) -> list:
    """Khối giữ chỗ / đạo cụ của máy (tọa độ model) → thứ để kiểm chữ ↔ tầm nhìn (tên = nhãn khối)."""
    st = sf.stage_of(d)
    out = []
    for p in (st or {}).get("props") or []:
        label = str(p.get("label") or p.get("mo_ta_ngan") or p.get("kind") or "")
        if not label or p.get("kind") not in ("block", "well"):
            continue
        at = p["at"]
        out.append({"key": f"prop{p['i']}", "name": label, "words": [label] if p["kind"] == "block" else ["well", "giếng"],
                    "base": at, "top": [at[0], at[1], at[2] + float(p["height"])]})
    return out


def run(conn, pid: int, stage_path: str = "", ref_words=()) -> dict:
    rows = conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    marks = landmarks(stage_path)
    shots, per = [], {}
    for idx, raw in rows:
        try:
            d = json.loads(raw or "{}")
        except ValueError:
            per[idx] = [ci._f("DATA", (), "scenes.data không phải JSON", level=ci.KHONG_RO)]
            continue
        shots.append(dict(d, shot=idx))
        found = ci.byd_vs_fields(d)
        motion = _motion_text(d)
        found += ci.vi_leaks(motion)
        if ref_words:
            found += ci.ref_leaks(motion, ref_words)
        st = sf.stage_of(d)
        if st:
            found += ci.check_pitch(d.get("angle"), ci.pitch_of(st["cam"], st["aim"]), declared=bool(d.get("angle")))
            things = marks + props_of(d)
            if things:
                view = ci.view_of(st["cam"], st["aim"], st["lens"], things)
                for field in sf.PROMPT_FIELDS:
                    if isinstance(d.get(field), str):
                        found += ci.text_vs_view(d[field], view, field)
                found += ci.motion_vs_view(motion, view, d.get("camera_move"))
        if found:
            per[idx] = found
    project = ci.byd_coverage(shots)
    return {"project": pid, "shots": len(rows), "per_shot": per, "project_findings": project,
            "count": sum(len(v) for v in per.values()) + len(project)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bất biến 3D theo gốc R2/R3/R4 (0 USD, chỉ đọc)")
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "manifest.sqlite"))
    ap.add_argument("--stage", default="", help="stage.json của sân khấu (mốc marks *_chan/*_dinh)")
    ap.add_argument("--ref-word", action="append", default=[], help="chủ thể video mẫu (vd cats) — chỉ được nhắc trong câu chặn")
    ap.add_argument("--json", help="ghi kết quả JSON ra file")
    a = ap.parse_args(argv)
    try:
        conn = sqlite3.connect(f"file:{os.path.abspath(a.db)}?mode=ro", uri=True)
        res = run(conn, a.project, a.stage, a.ref_word)
    except (sqlite3.Error, OSError, ValueError) as e:
        print(f"không đọc được {a.db}: {type(e).__name__}: {e}")
        return 2
    print(f"Dự án #{res['project']}: {res['shots']} shot, {res['count']} phát hiện (VÀNG = báo, không chặn)")
    for f in res["project_findings"]:
        print(f"  [dự án] {f['code']} {'/'.join(f['errors'])}: {f['msg']} → {f['fix']}")
    for idx, fs in sorted(res["per_shot"].items()):
        for f in fs:
            print(f"  shot {idx}: {f['code']} {'/'.join(f['errors'])} [{f['level']}] {f['msg']}" + (f" → {f['fix']}" if f["fix"] else ""))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
    return 1 if res["count"] else 0


if __name__ == "__main__":
    sys.exit(main())
