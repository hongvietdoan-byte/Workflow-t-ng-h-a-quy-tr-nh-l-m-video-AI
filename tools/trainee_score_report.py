"""Vì sao vai 🎓 học việc chưa được chấm + khớp thật nếu chấm bây giờ (C-QC-BOCUC, người dùng 22/10). 0 USD, chỉ đọc.

    py tools/trainee_score_report.py                       mọi vai, mọi dự án có dòng học việc
    py tools/trainee_score_report.py --feature qc_team --project 31 --project 33

Chạy trainee.score_project trên BẢN SAO CSDL (sqlite backup vào thư mục tạm) — CSDL thật không đổi, kể cả cột truth/match. In mỗi vai:
số dòng, đã chấm TRƯỚC (trong CSDL thật), chấm được NGAY (trên bản sao), người duyệt trước vai, chờ người duyệt (kèm lý do), khớp gộp /
cân bằng và các điều kiện còn thiếu (trainee.agreement). Lưu data/trainee_score_report.md.
"""
import argparse
import os
import shutil
import sqlite3
import sys
import tempfile
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import trainee  # noqa: E402
from core.db import connect  # noqa: E402


def _utf8_console() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _waiting_reasons(conn, feature: str, pids: List[int]) -> Dict[str, int]:
    """Dòng còn chờ (match NULL, không phải người-duyệt-trước): vì sao — không job / job không có lần duyệt của người / chỉ có xóa."""
    out = {"không ghi job_id": 0, "job chưa có lần duyệt của người": 0, "chỉ có lần xóa 'không phải lỗi'": 0, "khác": 0}
    q = ("SELECT id, job_id FROM trainee_log WHERE feature=? AND match IS NULL AND COALESCE(truth_source,'') != 'human_first'"
         f" AND project_id IN ({','.join('?' * len(pids)) or 'NULL'})")
    for r in conn.execute(q, [feature] + pids).fetchall():
        if r["job_id"] is None:
            out["không ghi job_id"] += 1
            continue
        revs = conn.execute("SELECT COALESCE(reason,'') AS reason FROM review_log WHERE job_id=? AND reviewer_type='user'",
                            (r["job_id"],)).fetchall()
        if not revs:
            out["job chưa có lần duyệt của người"] += 1
        elif all(v["reason"] == "khong_phai_loi" for v in revs):
            out["chỉ có lần xóa 'không phải lỗi'"] += 1
        else:
            out["khác"] += 1
    return {k: v for k, v in out.items() if v}


def _count(conn, feature: str, pids: List[int], where: str) -> int:
    q = f"SELECT COUNT(*) FROM trainee_log WHERE feature=? AND {where} AND project_id IN ({','.join('?' * len(pids)) or 'NULL'})"
    return conn.execute(q, [feature] + pids).fetchone()[0]


def report(conn, features: Optional[List[str]] = None, projects: Optional[List[int]] = None) -> str:
    """Chấm trên `conn` (đã là bản sao) và trả bảng markdown."""
    feats = features or [f for f in trainee.RULES if trainee.RULES[f].get("truth") == "review"]
    lines = ["# Học việc — vì sao chưa chấm + khớp nếu chấm bây giờ (0 USD, bản sao CSDL)", ""]
    for feat in feats:
        pids = projects or [r[0] for r in conn.execute("SELECT DISTINCT project_id FROM trainee_log WHERE feature=?", (feat,))]
        total = _count(conn, feat, pids, "1=1")
        if not total:
            lines += [f"## {feat}", "", "Không có dòng học việc nào.", ""]
            continue
        before = _count(conn, feat, pids, "match IS NOT NULL")
        never = _count(conn, feat, pids, "scored_at IS NULL")
        stats = {pid: trainee.score_project(conn, pid, [feat]).get(feat, {}) for pid in pids}
        after = _count(conn, feat, pids, "match IS NOT NULL")
        a = trainee.agreement(conn, feat, pids)
        lines += [f"## {feat}", "",
                  f"- Dòng học việc: **{total}** ({len(pids)} dự án: {', '.join('#' + str(p) for p in sorted(pids))})",
                  f"- Đã chấm trong CSDL thật: **{before}** · chưa từng chạy chấm (scored_at trống): **{never}**",
                  f"- Chấm được NGAY (bản sao): **{after}** · người duyệt trước vai: {a['n_human_first']} · còn chờ: {a['n_waiting']}"
                  f" · 'Duyệt tất cả' (gate_bulk): {a['n_bulk']}"]
        why = _waiting_reasons(conn, feat, pids)
        if why:
            lines.append("- Còn chờ vì: " + "; ".join(f"{k} {v}" for k, v in why.items()))
        if before == 0 and after > 0:
            lines.append("- **Nguyên nhân 0 dòng được chấm: chưa từng chạy chấm** — trainee.score_project chỉ chạy lúc Xuất bản (Bước 5) "
                         "và khi bấm '↻ Chấm lại' ở 🧪; dữ liệu đủ để chấm.")
        rate = "—" if a["rate"] is None else f"{a['rate']:.0%}"
        bal = "—" if a["balanced"] is None else f"{a['balanced']:.0%}"
        lines += [f"- Khớp gộp **{rate}** (n={a['n']}) · khớp cân bằng **{bal}** (ngưỡng bật lại qc_team: ≥ 75 %) · "
                  f"quá chặt {a['too_strict']} · quá lỏng {a['too_loose']}",
                  "- Theo dự án: " + ("; ".join(f"#{p} {d['matched']}/{d['n']}" for p, d in sorted(a["per_project"].items())) or "—"),
                  "- Còn thiếu để '🎓 đủ chuẩn': " + ("; ".join(a["missing"]) or "không"), ""]
        lines.append("  " + " · ".join(f"#{p}: chấm {s.get('scored', 0)}, trước {s.get('human_first', 0)}, chờ {s.get('waiting', 0)}"
                                        for p, s in sorted(stats.items())))
        lines.append("")
    return "\n".join(lines)


def run(db: str, features: Optional[List[str]] = None, projects: Optional[List[int]] = None, out: str = "") -> str:
    tmp = tempfile.mkdtemp(prefix="trainee_report_")
    try:
        copy = os.path.join(tmp, "manifest.sqlite")
        src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        dst = sqlite3.connect(copy)
        src.backup(dst)
        src.close()
        dst.close()
        conn = connect(copy)
        try:
            text = report(conn, features, projects)
        finally:
            conn.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def main(argv=None) -> int:
    _utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join(ROOT, "data", "manifest.sqlite")))
    ap.add_argument("--feature", action="append", default=None)
    ap.add_argument("--project", action="append", type=int, default=None)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "trainee_score_report.md"))
    a = ap.parse_args(argv)
    if not os.path.exists(a.db):
        print(f"không thấy CSDL {a.db}")
        return 2
    print(run(a.db, a.feature, a.project, a.out))
    print(f"(đã lưu: {a.out})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
