"""D6 thí điểm (docs/DANH_GIA_VAI_DAO_DIEN_2026-10-14.md mục 3b–3c): so prompt CŨ (bản code ghép) ↔ prompt D6 (Claude nhìn đúng các ảnh sẽ
gửi viết lại) trên vài shot của một dự án — 0 USD video, KHÔNG ghi CSDL thật (chạy trên một bản sao tạm).

    PYTHONUTF8=1 py tools/d6_pilot.py --project 27 --shots 3,11,17                 # chỉ BÁO GIÁ (không gọi Claude)
    PYTHONUTF8=1 py tools/d6_pilot.py --project 27 --shots 3,11,17 --kind video --yes   # gọi Claude (qua sổ chi), ghi bảng so

Mặc định --db = PIPELINE_DB hoặc data/manifest.sqlite; --data = PIPELINE_DATA hoặc data/projects; bảng so ghi vào --out (mặc định
data/d6_pilot/d6_<dự án>_<giờ>.md). Mỗi shot: ảnh = job ảnh đã duyệt mới nhất; video = job video mới nhất (cần motion prompt đã duyệt).
Sổ chi: lượt Claude được ghi vào bản sao (thí điểm) — số tiền in ra cuối bảng để người dùng ghi nhận.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chat_prompt  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402


def _copy(src: str) -> str:
    """A temporary copy of the database (sqlite backup: consistent even while the Dashboard writes)."""
    d = tempfile.mkdtemp(prefix="d6_pilot_")
    dst = os.path.join(d, "copy.sqlite")
    a = sqlite3.connect(f"file:{os.path.abspath(src)}?mode=ro", uri=True)
    b = sqlite3.connect(dst)
    a.backup(b)
    a.close()
    b.close()
    return dst


def capture(runner, job) -> dict:
    """The assembled prompt + the (label, path) pictures the runner would send — taken where D6 plugs in (`runner.chat_rewrite`), D6 itself
    kept off so the old prompt is what comes back."""
    seen = {}

    def grab(runner_, job_, kind, assembled, images, model, limit=4000):
        seen.update(kind=kind, assembled=assembled, images=list(images), model=model, limit=limit)
        return assembled

    from core import runner as R
    with mock.patch.object(R, "chat_rewrite", grab):
        runner._submit_args(job)
    return seen


def pick_job(conn, pid: int, idx: int, kind: str):
    typ = "image_gen" if kind == "image" else "video_gen"
    state = " AND j.state='approved'" if kind == "image" else ""
    return conn.execute(f"SELECT j.* FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE s.project_id=? AND s.idx=? AND j.type=?{state} "
                        "ORDER BY j.id DESC LIMIT 1", (pid, idx, typ)).fetchone()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D6 thí điểm: prompt cũ ↔ prompt Claude nhìn ảnh viết (0 USD video, chạy trên bản sao CSDL)")
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--shots", required=True, help="số shot, cách nhau dấu phẩy (vd 3,11,17)")
    ap.add_argument("--kind", choices=("image", "video", "both"), default="both")
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--data", default=os.environ.get("PIPELINE_DATA", os.path.join("data", "projects")))
    ap.add_argument("--out", default=None)
    ap.add_argument("--yes", action="store_true", help="gọi Claude thật (không có cờ này: chỉ báo giá)")
    a = ap.parse_args(argv)
    copy = _copy(a.db)
    p = None
    try:
        p = Pipeline(connect(copy))
        from core.providers import MockImageProvider, MockVideoProvider
        from core.runner import ImageRunner, VideoRunner
        runners = {"image": ImageRunner(p, MockImageProvider(), a.data), "video": VideoRunner(p, MockVideoProvider(), a.data)}
        kinds = ("image", "video") if a.kind == "both" else (a.kind,)
        rows, total_est = [], 0.0
        for idx in [int(x) for x in a.shots.split(",") if x.strip()]:
            for kind in kinds:
                job = pick_job(p.conn, a.project, idx, kind)
                if job is None:
                    rows.append({"shot": idx, "kind": kind, "skip": "không có job phù hợp"})
                    continue
                try:
                    got = capture(runners[kind], job)
                except Exception as e:  # noqa: BLE001 - one shot that cannot be built is said, the others go on
                    rows.append({"shot": idx, "kind": kind, "skip": f"không dựng được prompt cũ: {str(e)[:200]}"})
                    continue
                if not got:
                    rows.append({"shot": idx, "kind": kind, "skip": "runner không dựng prompt (thiếu ảnh duyệt / motion?)"})
                    continue
                est = chat_prompt.estimate(p.conn, min(len(got["images"]), chat_prompt.MAX_IMAGES)) or 0.0
                total_est += est
                row = {"shot": idx, "kind": kind, "job": job["id"], "old": got["assembled"], "images": [lab for lab, _ in got["images"]],
                       "est": est}
                if a.yes:
                    said = []
                    with mock.patch.object(chat_prompt, "enabled", return_value=True):
                        row["new"] = chat_prompt.rewrite(p, job, kind, got["assembled"], got["images"], model=got["model"],
                                                         limit=got["limit"], say=lambda lv, code, msg: said.append(f"{lv} {code}: {msg}"))
                    row["said"] = said
                rows.append(row)
        print(f"Ước tính Claude: {total_est:.3f} USD cho {sum(1 for r in rows if 'old' in r)} prompt"
              + ("" if a.yes else " — chưa gọi (thêm --yes để chạy)"))
        out = a.out or os.path.join("data", "d6_pilot", f"d6_{a.project}_{time.strftime('%Y%m%d_%H%M')}.md")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"# D6 thí điểm — dự án #{a.project}, shot {a.shots} ({time.strftime('%d/%m %H:%M')})\n\n"
                    f"Ước tính Claude: {total_est:.3f} USD · {'ĐÃ gọi' if a.yes else 'chưa gọi (chỉ báo giá)'}\n\n")
            for r in rows:
                f.write(f"## Shot {r['shot']} · {r['kind']}" + (f" · job {r['job']}" if r.get("job") else "") + "\n\n")
                if "skip" in r:
                    f.write(f"⚠ {r['skip']}\n\n")
                    continue
                f.write("Ảnh Claude nhìn: " + "; ".join(r["images"]) + f"\n\n**CŨ (code ghép, {len(r['old'])} ký tự)**\n\n```\n{r['old']}\n```\n\n")
                if "new" in r:
                    f.write(f"**D6 ({len(r['new'])} ký tự)**\n\n```\n{r['new']}\n```\n\n" + "".join(f"- {s}\n" for s in r["said"]) + "\n")
        print(f"Bảng so: {out}")
        return 0
    finally:
        if p is not None:
            p.conn.close()
        shutil.rmtree(os.path.dirname(copy), ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
