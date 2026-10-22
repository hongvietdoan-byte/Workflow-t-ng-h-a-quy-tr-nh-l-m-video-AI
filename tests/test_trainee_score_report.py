"""tools/trainee_score_report (C-QC-BOCUC 22/10): trainee_log qc_team 120 dòng, 0 dòng được chấm — công cụ chấm trên BẢN SAO và nói
vì sao; CSDL thật không đổi."""
import os
import sqlite3

from core import trainee
from core.db import connect
from core.pipeline import Pipeline
from tools import trainee_score_report as tsr


def _db(tmp_path):
    db = str(tmp_path / "manifest.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("hv")
    jobs = []
    for i, (decision, person) in enumerate([("block", "reject"), ("pass", "approve"), ("pass", "reject"), ("flag", "reject"),
                                            ("pass", None)], 1):
        sid = p.create_scene(pid, i, f"s{i}")
        jid = p.create_job(sid, "image_gen")
        trainee.record(p.conn, "qc_team", pid, f"job:{jid}", decision, job_id=jid, at="2026-10-20T01:00:00+00:00")
        if person:
            p.conn.execute("INSERT INTO review_log (job_id, reviewer_type, decision, decided_at) VALUES (?,?,?,?)",
                           (jid, "user", person, f"2026-10-20T02:00:0{i}+00:00"))
        jobs.append(jid)
    p.conn.commit()
    p.conn.close()
    return db, pid


def test_never_scored_is_diagnosed_and_scored_on_the_copy_only(tmp_path):
    db, pid = _db(tmp_path)
    before = os.path.getmtime(db), os.path.getsize(db)
    out = str(tmp_path / "r.md")
    text = tsr.run(db, ["qc_team"], None, out)
    assert "Đã chấm trong CSDL thật: **0**" in text and "Chấm được NGAY (bản sao): **4**" in text
    assert "chưa từng chạy chấm" in text and "job chưa có lần duyệt của người 1" in text
    assert "Khớp gộp **75%** (n=4)" in text                       # block↔reject, pass↔approve, flag↔reject đúng; pass↔reject sai
    assert open(out, encoding="utf-8").read() == text
    assert (os.path.getmtime(db), os.path.getsize(db)) == before
    c = sqlite3.connect(db)
    assert c.execute("SELECT COUNT(*) FROM trainee_log WHERE match IS NOT NULL").fetchone()[0] == 0
    c.close()


def test_main_missing_db_says_so(tmp_path, capsys):
    assert tsr.main(["--db", str(tmp_path / "none.sqlite")]) == 2
    assert "không thấy CSDL" in capsys.readouterr().out
