"""Bậc 2A (kế hoạch 2026-09-25): dựng dự án chạy thử từ một dự án chia shot — giữ N phần đầu của kịch bản, áp bộ chuẩn hóa shot lên
câu trả lời Director đã có (không gọi Claude), tắt card cuối và nhạc trả tiền, rồi đặt trần đợt thử. KHÔNG gửi lời gọi trả tiền nào.

    py tools/pilot_setup.py --project 6 --sections 2 --usd 8 --llm-usd 1 --images 32 --audio 25 [--dry-run]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import budget, compare, db, director_report, llm_io, music, script_parser  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402


def trimmed_script(script: str, sections: int) -> str:
    """The preamble + the first `sections` script sections (the rest of the script is not part of the trial)."""
    rows, out, seen = script.splitlines(), [], 0
    for r in rows:
        if r.strip() and script_parser.is_heading(r.strip()):
            seen += 1
            if seen > sections:
                break
        out.append(r)
    return "\n".join(out).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--sections", type=int, default=2)
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--usd", type=float, default=8.0, help="trần tiền có giá của đợt thử (video + Claude theo sổ)")
    ap.add_argument("--llm-usd", type=float, default=1.0, help="trần Claude API của đợt thử")
    ap.add_argument("--images", type=int, default=32)
    ap.add_argument("--audio", type=int, default=25)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    p = Pipeline(db.connect(a.db))
    src = p.project(a.project)
    raw = json.loads(src["director_raw"])
    keep = set(range(1, a.sections + 1))
    obj = {**raw, "scenes": [s for s in raw["scenes"] if s["idx"] in keep]}
    obj.pop("dropped_lines", None)
    obj.pop("normalized", None)
    script = trimmed_script(src["script_text"], a.sections)
    rep = director_report.report(obj, script)
    print(f"Phần giữ: {sorted(keep)} · {rep['shots']} shot · {rep['total_s']:g}s · video trả tiền từng shot ~{rep['paid_s']['per_shot']:g}s")
    if a.dry_run:
        return 0
    new = compare.clone_project(p, a.project, f"{src['name']} · thử 0–{int(rep['total_s'] + 0.5)}s", with_rows=False)
    p.conn.execute("DELETE FROM story_scenes WHERE project_id=? AND idx>?", (new, a.sections))
    p.conn.execute("DELETE FROM scenes WHERE project_id=? AND idx>?", (new, a.sections))
    p.conn.commit()
    p.set_script_text(new, script)
    settings = json.loads(src["render_settings"] or "{}")
    settings["end_card"] = {**(settings.get("end_card") or {}), "enabled": False}      # the end card belongs to the full film
    p.set_project_field(new, "render_settings", json.dumps(settings, ensure_ascii=False))
    music.set_off(p, new, True)                                                          # no paid music in the trial
    stored = llm_io.store_scene_analysis(p, new, obj)                                    # normaliser runs here (H1)
    p.set_project_field(new, "director_raw", json.dumps(stored, ensure_ascii=False))
    print(f"Dự án thử #{new}: {len(stored.get('normalized') or [])} chỗ chuẩn hóa")
    for c in stored.get("normalized") or []:
        print("  •", c)
    print(director_report.text(director_report.report(stored, script)))
    b = budget.restart(p.conn, a.usd)
    budget.save(p.conn, image_cap=a.images, audio_cap=a.audio)
    budget.restart_llm(p.conn, a.llm_usd)
    print("Trần đợt thử:", json.dumps(budget.status(p.conn), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
