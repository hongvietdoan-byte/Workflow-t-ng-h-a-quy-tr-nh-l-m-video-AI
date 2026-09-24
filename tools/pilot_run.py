"""Bậc 2A: chạy thử từng bước, có kiểm soát (thay cho autopilot khi trần Claude API rất nhỏ — autopilot chấm QC MỌI ảnh bằng Claude).

Mỗi lệnh làm một bước rồi in trạng thái + tiền đã dùng so với trần đợt thử (core/budget.py). Trần chạm → provider/budget từ chối, lệnh
dừng. Chạy với biến môi trường như Dashboard (IMAGE_PROVIDER=deepix, VIDEO_PROVIDER=clipai, LLM_PROVIDER=anthropic, token ở env).

    py tools/pilot_run.py --project 7 status
    py tools/pilot_run.py --project 7 bible                 # kiểm Bible với ảnh (1 lượt Claude, chỉ nhân vật đổi)
    py tools/pilot_run.py --project 7 images [--only 1,2]   # tạo + gửi job ảnh cho shot chưa có ảnh, rồi chờ xong
    py tools/pilot_run.py --project 7 qc JOB [JOB…]         # QC ảnh bằng Claude (mẫu)
    py tools/pilot_run.py --project 7 approve JOB [JOB…]    # người (phiên vận hành) duyệt sau khi xem ảnh/clip
    py tools/pilot_run.py --project 7 redo JOB "câu sửa tiếng Anh"   # gen lại có chủ đích (≤ 2 lần/shot)
    py tools/pilot_run.py --project 7 motion                # motion prompt mọi shot trong 1 lượt Claude, rồi duyệt
    py tools/pilot_run.py --project 7 voice                 # TTS các câu thoại, chờ xong, kéo dài clip theo giọng thật
    py tools/pilot_run.py --project 7 videos [--only …]     # tạo + gửi job video cho shot sẵn sàng, chờ xong
    py tools/pilot_run.py --project 7 qcvideo JOB [JOB…]    # QC clip bằng Claude (mẫu)
    py tools/pilot_run.py --project 7 render                # dựng + phụ đề (không card cuối), in đường dẫn
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import budget, db, llm_io, llm_runner  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402

SHOT_SENDS = 3          # 1 lần đầu + tối đa 2 lần gen lại (người dùng chốt: gen lại < 3)


def _money(p) -> str:
    s = budget.status(p.conn)
    return (f"đợt thử: ${s['spent']:.2f}/${s['usd']:.0f} · ảnh {s['images']}/{s['image_cap']} · âm thanh {s['audios']}/{s['audio_cap']}"
            f" · Claude ${s['llm_spent']:.3f}/${s['llm_usd']:.2f}")


def _jobs(p, pid, kind):
    return p.conn.execute("SELECT j.id, j.state, j.retry_count, j.retry_reason, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id "
                          "WHERE j.project_id=? AND j.type=? ORDER BY s.idx, j.id", (pid, kind)).fetchall()


def status(p, pid, data_dir):
    for kind in ("image_gen", "video_gen"):
        for j in _jobs(p, pid, kind):
            qc = p.conn.execute("SELECT AVG(score) FROM qc_results WHERE job_id=?", (j["id"],)).fetchone()[0]
            path = (llm_runner.image_path(data_dir, pid, j["id"]) if kind == "image_gen"
                    else os.path.join(data_dir, str(pid), "videos", f"{j['idx']}.mp4"))
            print(f"{kind[:5]} shot {j['idx']:>2} job {j['id']:>4} {j['state']:<15}"
                  + (f" QC {qc:.2f}" if qc is not None else "") + (f" [{str(j['retry_reason'])[:90]}]" if j["retry_reason"] else "")
                  + (f"  {path}" if os.path.exists(path) else ""))
    print(_money(p))


def _sends(p, scene_id, kind) -> int:
    return p.conn.execute("SELECT COUNT(*) FROM jobs WHERE scene_id=? AND type=? AND external_id IS NOT NULL", (scene_id, kind)).fetchone()[0]


def _wait(p, pid, runner, kind, minutes):
    end = time.time() + minutes * 60
    while time.time() < end:
        runner.submit_pending(pid)
        runner.poll_once(pid)
        active = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type=? AND state IN ('queued','running')",
                                (pid, kind)).fetchone()[0]
        print(time.strftime("%H:%M:%S"), f"{kind}: {active} đang chạy", flush=True)
        if not active:
            return
        time.sleep(20)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--data", default=os.environ.get("PIPELINE_DATA", os.path.join("data", "projects")))
    ap.add_argument("--only", default="", help="số shot (idx), cách nhau dấu phẩy")
    ap.add_argument("--minutes", type=float, default=25)
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="*")
    a = ap.parse_args(argv)
    p = Pipeline(db.connect(a.db))
    pid, data_dir = a.project, a.data
    only = {int(x) for x in a.only.split(",") if x.strip()}
    rows = [r for r in p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (pid,)) if not only or r["idx"] in only]
    client = lambda: llm_runner.client_from_env(ledger=a.db)   # noqa: E731

    if a.cmd == "status":
        status(p, pid, data_dir)
    elif a.cmd == "bible":
        from core import claude_tasks
        with llm_runner.tagged("director", pid):
            res = claude_tasks.bible_check(p, pid, client())
        for name, r in res.items():
            print(name, "ĐẠT" if r.get("ok") else "LỆCH", "; ".join(r.get("mismatches") or []))
    elif a.cmd in ("images", "videos"):
        from core.adapters import factory
        from core.runner import ImageRunner, VideoRunner
        kind = "image_gen" if a.cmd == "images" else "video_gen"
        if kind == "image_gen":
            runner = ImageRunner(p, factory.image_provider(), data_dir)
            ready = {r["id"] for r in rows}
        else:
            runner = VideoRunner(p, factory.video_provider(), data_dir)
            ready = {r["scene_id"] for r in llm_io.ready_for_video(p, pid)} & {r["id"] for r in rows}
        for r in rows:
            busy = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE scene_id=? AND type=? AND state NOT IN ('rejected','cancelled')",
                                  (r["id"], kind)).fetchone()[0]
            if r["id"] in ready and not busy:
                p.create_job(r["id"], kind)
        _wait(p, pid, runner, kind, a.minutes)
        status(p, pid, data_dir)
    elif a.cmd == "relink":                               # W12b: jobs written off although ClipAI made them under a new id
        from core.adapters import factory
        from core.runner import VideoRunner
        runner = VideoRunner(p, factory.video_provider(), data_dir)
        for jid in map(int, a.args):
            print(jid, "→", runner.relink_failed(jid))
        _wait(p, pid, runner, "video_gen", a.minutes)
        status(p, pid, data_dir)
    elif a.cmd == "qc":
        for jid in map(int, a.args):
            r = llm_runner.run_qc(p, jid, client(), data_dir)
            print(jid, json.dumps(r, ensure_ascii=False)[:400])
        print(_money(p))
    elif a.cmd == "qcvideo":
        from core import claude_tasks
        for jid in map(int, a.args):
            with llm_runner.tagged("video_qc", pid):
                r = claude_tasks.qc_video(p, jid, client(), data_dir, autofix=False)
            print(jid, json.dumps(r, ensure_ascii=False)[:400])
        print(_money(p))
    elif a.cmd == "approve":
        for jid in map(int, a.args):
            p.approve(jid, "user", "duyệt bởi phiên vận hành chạy thử 2A (đã xem ảnh/clip)")
            print("đã duyệt", jid)
    elif a.cmd == "redo":
        jid, fix = int(a.args[0]), a.args[1]
        job = p.job(jid)
        if _sends(p, job["scene_id"], job["type"]) >= SHOT_SENDS:
            print(f"shot đã gửi {SHOT_SENDS} lần — không gen lại (giới hạn người dùng chốt)")
            return 1
        if job["type"] == "video_gen":
            from core import regen
            new = regen.regenerate_video(p, data_dir, jid, fix)
        elif job["state"] == "failed":
            new = p.resend(jid, fix)                     # the provider refused: same attempt again with the changed input
        else:
            p.reject(jid, "user", "gen lại có chủ đích (phiên vận hành)", fix=fix)
            new = p.conn.execute("SELECT MAX(id) FROM jobs WHERE scene_id=? AND type=?", (job["scene_id"], job["type"])).fetchone()[0]
        print("job mới", new)
    elif a.cmd == "motion":
        r = llm_runner.run_motion(p, pid, client(), data_dir)
        for s in rows:
            m = p.conn.execute("SELECT state FROM motion_prompts WHERE scene_id=?", (s["id"],)).fetchone()
            if m is not None and m["state"] != "approved":
                llm_io.approve_motion_prompt(p, s["id"])
        print(json.dumps(r, ensure_ascii=False)[:300])
        print(_money(p))
    elif a.cmd == "voice":
        from core import audio_lib, music, voice
        prov = music.audio_provider()
        r = voice.generate(p.conn, pid, prov, data_dir)
        print("gửi", r)
        end = time.time() + a.minutes * 60
        while time.time() < end:
            audio_lib.refresh(prov, audio_lib.assets_dir(data_dir, pid))
            st = voice.status(p.conn, pid, data_dir)
            print(time.strftime("%H:%M:%S"), st, flush=True)
            if not st.get("running"):
                break
            time.sleep(15)
        print("kéo dài clip theo giọng:", voice.fit_durations(p.conn, pid, data_dir))
        print(_money(p))
    elif a.cmd == "render":
        from core import delivery
        res = delivery.deliver(p, pid, data_dir, client())
        print(json.dumps({k: v for k, v in res.items() if k != "layers"}, ensure_ascii=False, default=str)[:600])
        print("layers:", res.get("layers"))
        print(_money(p))
    else:
        ap.error("lệnh không rõ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
