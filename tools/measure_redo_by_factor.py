"""Đo số lần gen lại video trung bình mỗi shot theo yếu tố độ khó / nhãn (N2, người dùng chốt 08/10 mục 5a.7: số đo thật để Đạo diễn /
hệ thống rút kinh nghiệm phân loại dễ / phức tạp).

CHỈ ĐỌC: không bao giờ mở CSDL thật để ghi — mặc định chép một bản sao (sqlite backup, đọc chế độ ro) ra thư mục tạm rồi đo trên bản sao.

Mỗi lần gen lại (job video_gen thứ 2 trở đi của một shot, bỏ job đã hủy / còn chờ) được gán MỘT nguồn theo bằng chứng của job trước nó:
  ncc    lỗi nhà cung cấp (job trước 'failed', lý do ghi lỗi nhà cung cấp / rate-limit) — BỎ khỏi r̂ (không phải do shot khó)
  nguoi  người dùng loại job trước (review_log user reject)
  qc     QC / Tổ QC loại (review_log ai_agent reject, qc_results 'fail', lý do 'QC …')
  khac   còn lại (gen lại không ghi lý do, autopilot thử lại, thử nghiệm)
r̂ = (nguoi + qc + khac) / số shot của nhóm.

Dùng:
  py tools/measure_redo_by_factor.py [--db PATH] [--project 8 --project 22] [--record PATH_DB_GHI]
--record ghi mỗi nhóm thành một ca trong sổ kinh nghiệm (core/experience.record, stage "video_tier") vào CSDL chỉ định (bản sao /
CSDL thử) — công cụ không tự ghi vào CSDL thật.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import tempfile
from collections import defaultdict
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import shot_complexity  # noqa: E402

DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "manifest.sqlite")
SOURCES = ("nguoi", "qc", "khac", "ncc")
SOURCE_VI = {"nguoi": "người loại", "qc": "QC loại", "khac": "khác", "ncc": "lỗi NCC (bỏ)"}
_NCC = re.compile(r"nhà cung cấp|rate.?limit|\b1130\b|timeout|provider|server error|5\d\d\b", re.I)
SKIP_STATES = ("cancelled", "queued")
HIGH_REDO = 0.8          # 5a: r > 0,8 → bản cao 720p một lượt đã đắt hơn nháp trước (mục 2 công thức ngưỡng)


def snapshot(src: str) -> str:
    """A read-only copy of `src` (WAL included) in a temp folder; the original is opened mode=ro and never written."""
    out = os.path.join(tempfile.mkdtemp(prefix="redo_measure_"), "manifest.sqlite")
    s = sqlite3.connect(f"file:{os.path.abspath(src)}?mode=ro", uri=True)
    d = sqlite3.connect(out)
    s.backup(d)
    d.close()
    s.close()
    return out


def _cols(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def classify(prev: Dict, cur: Dict, reviews: Dict[int, List], qc_fail: set) -> str:
    reason = cur.get("retry_reason") or ""
    if prev["state"] == "failed" or _NCC.search(reason):
        return "ncc"
    decided = reviews.get(prev["id"], [])
    if ("user", "reject") in decided:
        return "nguoi"
    if ("ai_agent", "reject") in decided or prev["id"] in qc_fail or reason.startswith("QC "):
        return "qc"
    return "khac"


def measure(conn, projects: Optional[List[int]] = None) -> Dict:
    """{"shots": [{project_id, scene_id, redo: {source: n}, factors, suggest, label}], "groups": {name: {shots, nguoi, qc, khac, ncc, r}}}"""
    conn.row_factory = sqlite3.Row
    where, args = "type='video_gen' AND state NOT IN (?,?)", list(SKIP_STATES)
    if projects:
        where += " AND project_id IN (" + ",".join("?" * len(projects)) + ")"
        args += list(projects)
    jobs = defaultdict(list)
    for r in conn.execute(f"SELECT id, project_id, scene_id, state, retry_reason FROM jobs WHERE {where} ORDER BY id", args):
        jobs[r["scene_id"]].append(dict(r))
    reviews = defaultdict(list)
    for r in conn.execute("SELECT job_id, reviewer_type, decision FROM review_log"):
        reviews[r["job_id"]].append((r["reviewer_type"], r["decision"]))
    qc_fail = {r[0] for r in conn.execute("SELECT DISTINCT job_id FROM qc_results WHERE auto_decision='fail'")}
    ref = set()
    if "ref_video_path" in _cols(conn, "motion_prompts"):
        ref = {r[0] for r in conn.execute("SELECT scene_id FROM motion_prompts WHERE ref_video_path IS NOT NULL AND ref_video_path!=''")}
    shots = []
    for scene_id, js in jobs.items():
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
        data = json.loads(row["data"] or "{}") if row else {}
        redo = {s: 0 for s in SOURCES}
        for prev, cur in zip(js, js[1:]):
            redo[classify(prev, cur, reviews, qc_fail)] += 1
        sc = shot_complexity.score(data, ref_video=scene_id in ref)
        shots.append({"project_id": js[0]["project_id"], "scene_id": scene_id, "redo": redo,
                      "factors": [f["key"] for f in sc["factors"]],
                      "factor_vi": {f["key"]: f["label"].split(" (")[0] for f in sc["factors"]},
                      "suggest": sc["suggest"], "label": data.get("difficulty")})
    return {"shots": shots, "groups": group(shots)}


def group(shots: List[Dict]) -> Dict[str, Dict]:
    names = {"people": "≥ 2 người", "dance": "nhảy / múa", "fight": "đánh / bắn", "motion": "chuyển động lớn", "hands": "tay",
             "skill_words": "kỹ năng (từ khóa)", "skill": "kỹ năng (hồ sơ)", "lip_sync": "khớp môi", "dialogue": "có thoại (không khớp môi)",
             "camera_big": "máy di chuyển lớn", "ref_video": "video tham chiếu", "place_3d": "nền 3D"}
    buckets = defaultdict(list)
    for s in shots:
        buckets["tất cả"].append(s)
        buckets[f"dự án #{s['project_id']}"].append(s)
        if not s["factors"]:
            buckets["yếu tố: không có"].append(s)
        for f in s["factors"]:
            buckets[f"yếu tố: {names.get(f, f)}"].append(s)
        buckets[f"gợi ý code: {s['suggest']}"].append(s)
        if s["label"]:
            buckets[f"nhãn Đạo diễn: {s['label']}"].append(s)
    out = {}
    for name, ss in buckets.items():
        g = {"shots": len(ss), **{src: sum(s["redo"][src] for s in ss) for src in SOURCES}}
        g["r"] = round((g["nguoi"] + g["qc"] + g["khac"]) / len(ss), 2) if ss else 0.0
        out[name] = g
    return out


def table(groups: Dict[str, Dict]) -> str:
    order = sorted(groups, key=lambda n: (0 if n == "tất cả" else 1 if n.startswith("dự án") else 2 if n.startswith("gợi ý") else
                                          3 if n.startswith("nhãn") else 4, -groups[n]["r"], n))
    lines = ["| Nhóm | Shot | Người loại | QC loại | Khác | Lỗi NCC (bỏ) | r̂ |", "|---|---|---|---|---|---|---|"]
    for n in order:
        g = groups[n]
        r = f"{g['r']:.2f}".replace(".", ",")
        lines.append(f"| {n} | {g['shots']} | {g['nguoi']} | {g['qc']} | {g['khac']} | {g['ncc']} | {r} |")
    return "\n".join(lines)


def record(db_path: str, groups: Dict[str, Dict]) -> int:
    """One experience case per group (stage "video_tier", key per group, replaced at each run) in `db_path` — never the live database."""
    if os.path.abspath(db_path) == os.path.abspath(DEFAULT_DB):
        raise SystemExit("Không ghi vào CSDL thật — chỉ ghi vào bản sao / CSDL thử.")
    from core import experience
    conn = sqlite3.connect(db_path)
    n = 0
    for name, g in groups.items():
        if not g["shots"]:
            continue
        r = f"{g['r']:.2f}".replace(".", ",")
        note = (f"Đo gen lại video theo nhóm '{name}': {g['shots']} shot, r̂ = {r} lần/shot (người {g['nguoi']}, QC {g['qc']}, "
                f"khác {g['khac']}; bỏ {g['ncc']} lần lỗi nhà cung cấp). r̂ > 0,8 → nên nháp trước.")
        n += experience.record(conn, key=f"redo_by_factor:{name}", stage="video_tier",
                               outcome="failure" if g["r"] > HIGH_REDO else "success", note=note,
                               source="tools/measure_redo_by_factor.py", kind="redo_rate", replace=True)
    conn.close()
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=DEFAULT_DB, help="CSDL nguồn (chỉ đọc, đo trên bản sao)")
    ap.add_argument("--no-copy", action="store_true", help="--db đã là bản sao: đọc thẳng (vẫn chế độ ro)")
    ap.add_argument("--project", type=int, action="append")
    ap.add_argument("--record", help="CSDL (bản sao / thử) để ghi các ca vào sổ kinh nghiệm")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    path = a.db if a.no_copy else snapshot(a.db)
    conn = sqlite3.connect(f"file:{os.path.abspath(path)}?mode=ro", uri=True)
    res = measure(conn, a.project)
    conn.close()
    print(json.dumps(res["groups"], ensure_ascii=False, indent=1) if a.json else table(res["groups"]))
    if a.record:
        print(f"\nĐã ghi {record(a.record, res['groups'])} ca mới vào sổ kinh nghiệm (stage video_tier) của {a.record}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
