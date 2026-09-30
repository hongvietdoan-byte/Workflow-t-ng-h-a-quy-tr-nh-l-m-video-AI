"""S5.5' — thử có trả tiền cờ `place_render_refs` trên 1 cảnh (người dùng duyệt 30/09; trần riêng CAP_USD):

Cảnh "khu nhà dưới chân tháp" của #8 (shot 20–24, ban ngày, Tháp Đồng Hồ #263) chép sang một dự án thử (không đụng #8 đã giao).
Mỗi shot được render 3D đúng góc máy làm ảnh tham chiếu nơi chốn + câu số đo; vẽ khung bằng model ảnh của #8 qua ImageRunner (trần +
sổ chi); rồi đo độ khớp nền (`place_refs.background_match`) so với số gốc 0,073 của các khung #8 cũ.

    py tools/experiments/place_refs_trial.py setup                  dự án thử (0 USD) — in mã dự án
    py tools/experiments/place_refs_trial.py --project N plates     render 3D các shot (Blender, 0 USD)
    py tools/experiments/place_refs_trial.py --project N plan       in ảnh tham chiếu + prompt sẽ gửi (0 USD, provider giả)
    py tools/experiments/place_refs_trial.py --project N frames     vẽ ảnh toàn cảnh + khung các shot (trả tiền, trần CAP_USD)
    py tools/experiments/place_refs_trial.py --project N measure    độ khớp nền từng shot, so với khung #8 cùng shot

Chạy từ D:\\AI-Video-Pipeline."""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

NAME = "Thử place_render_refs 1 cảnh (30/09)"
SOURCE, KEEP = 8, range(20, 25)        # #8, shots 20–24: "khu nhà dưới chân tháp", day
CAP_USD = 1.0                          # 5 shots + 1 establishing ≈ 0,31 USD; ≤ 2 redraws each — người dùng duyệt 30/09
BASELINE = 0.073                       # mean background match of the 19 measurable #8 frames (docs/THU_PLACE_RENDER_REFS_2026-09-30.md)
ENV = {"FEATURE_PLACE_RENDER_REFS": "1", "FEATURE_STORYBOARD_API": "0", "FEATURE_LOCATION_PLATES": "0"}
DATA = os.path.join("data", "projects")


def _p():
    from tools.experiments.group_test import load_env
    load_env(os.getcwd())
    os.environ.update(ENV)
    from core.db import connect
    from core.pipeline import Pipeline
    return Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))


def spent(p, pid):
    from core import project_budget
    return round(sum(project_budget.spent_by_stage(p.conn, pid).values()), 4)


def rows_of(p, pid):
    return [{"id": r["id"], "idx": r["idx"], "data": json.loads(r["data"] or "{}")}
            for r in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]


def setup(p):
    from core import compare
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return
    pid = compare.clone_project(p, SOURCE, NAME)
    p.conn.execute(f"DELETE FROM scenes WHERE project_id=? AND idx NOT IN ({','.join('?' * len(KEEP))})", (pid, *KEEP))
    p.conn.commit()
    print("dự án thử:", pid, "·", len(rows_of(p, pid)), "shot")


def plates(p, pid):
    from core import location_pack, place_refs
    idx = location_pack.ensure_plates(p.conn, pid, DATA, os.getcwd(), place_refs.resolution_of(p.project(pid)), log=print)
    for r in rows_of(p, pid):
        rec = location_pack.plate_of(DATA, pid, r["id"])
        print(r["idx"], r["data"].get("shot"), "→", rec and rec.get("plate"))
    return idx


def plan(p, pid):
    from core.providers import MockImageProvider
    from core.runner import ImageRunner
    runner = ImageRunner(p, MockImageProvider(), DATA)
    for r in rows_of(p, pid):
        job = {"id": -1, "scene_id": r["id"], "project_id": pid, "retry_reason": None, "type": "image_gen"}
        kw = runner._submit_kwargs(job)
        args = runner._submit_args(job)
        print(f"--- shot {r['idx']} ({r['data'].get('shot')})")
        if not args:
            print("(không gửi)")
            continue
        print("ẢNH:", [os.path.relpath(str(x)) for x in (args[1] if len(args) > 1 else [])], kw or "")
        print(args[0])


def frames(p, pid):
    from core.adapters import factory
    from core.runner import ImageRunner
    rows = rows_of(p, pid)
    todo = [r for r in rows if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state NOT IN "
                                                  "('failed','rejected','cancelled')", (r["id"],)).fetchone()]
    usd = 0.052 * (len(todo) + 1)                 # + the scene's establishing picture
    s = spent(p, pid)
    if s + usd > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN CHẶN: đã chi ${s:.2f} + ≈ ${usd:.2f} > trần ${CAP_USD:.2f}")
    print(f"trần: đã chi ${s:.2f}, lần này ≈ ${usd:.2f}, còn ${CAP_USD - s - usd:.2f}")
    for r in todo:
        p.create_job(r["id"], "image_gen")
    runner = ImageRunner(p, factory.image_provider(), DATA)
    ids = {r["id"] for r in rows}
    t0 = time.time()
    while time.time() - t0 < 2400:
        if spent(p, pid) > CAP_USD + 1e-9:
            print("TRẦN: dừng gửi thêm")
            break
        runner.submit_pending(pid)
        runner.poll_once(pid)
        states = {r["id"]: r["state"] for r in p.conn.execute("SELECT scene_id id, state FROM jobs WHERE project_id=? AND type='image_gen' "
                                                              "ORDER BY id", (pid,)) if r["id"] in ids}
        print(time.strftime("%H:%M:%S"), states, "· đã chi", spent(p, pid), flush=True)
        if len(states) == len(ids) and all(s in ("succeeded", "approved", "pending_review", "failed", "escalated") for s in states.values()):
            break
        time.sleep(15)
    print("đã chi:", spent(p, pid))


def _latest_image(p, pid, scene_id):
    j = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN ('succeeded','approved','pending_review') "
                       "ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()
    path = j and os.path.join(DATA, str(pid), "images", f"job_{j['id']}.png")
    return path if path and os.path.exists(path) else None


def measure(p, pid):
    from core import location_pack, place_refs
    old = {r["idx"]: r["id"] for r in rows_of(p, SOURCE)}
    out, new_s, old_s = [], [], []
    for r in rows_of(p, pid):
        rec = location_pack.plate_of(DATA, pid, r["id"])
        plate = rec and rec.get("plate")
        new = _latest_image(p, pid, r["id"])
        before = _latest_image(p, SOURCE, old.get(r["idx"])) if old.get(r["idx"]) else None
        a = place_refs.background_match(new, plate) if new and plate else None
        b = place_refs.background_match(before, plate) if before and plate else None
        new_s += [a] if a is not None else []
        old_s += [b] if b is not None else []
        out.append({"shot": r["idx"], "size": r["data"].get("shot"), "new": a, "old_8": b, "image": new, "plate": plate})
        print(f"shot {r['idx']:>2} {str(r['data'].get('shot'))[:28]:<28} mới {a}  ·  #8 cũ {b}")
    avg = lambda v: round(sum(v) / len(v), 3) if v else None  # noqa: E731
    print(f"TRUNG BÌNH mới {avg(new_s)} (n={len(new_s)}) · #8 cũ cùng shot {avg(old_s)} (n={len(old_s)}) · số gốc 19 khung #8 {BASELINE}")
    dest = os.path.join(DATA, str(pid), "place_refs_measure.json")
    json.dump({"rows": out, "mean_new": avg(new_s), "mean_old": avg(old_s), "baseline": BASELINE, "usd": spent(p, pid)},
              open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ghi:", dest)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("setup", "plates", "plan", "frames", "measure"))
    ap.add_argument("--project", type=int)
    a = ap.parse_args(argv)
    p = _p()
    if a.step == "setup":
        return setup(p)
    if not a.project:
        raise SystemExit("cần --project N")
    {"plates": plates, "plan": plan, "frames": frames, "measure": measure}[a.step](p, a.project)


if __name__ == "__main__":
    main()
