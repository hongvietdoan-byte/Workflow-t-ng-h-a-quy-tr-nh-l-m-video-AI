"""S4.2 + S4.6 phần còn lại — chạy thật có trả tiền (người dùng duyệt 01/10; nhánh A1; trần riêng CAP_USD cho dự án thử này):

S4.2  khớp môi cách (c) QUA LUỒNG CHÍNH: cảnh 6 của #8 (đêm, Tháp Đồng Hồ) — shot 30 (MS qua vai Kenta, KELLY nói) + shot 31 (MCU Kenta
      nghiêng, KENTA nói) = một nhóm tham chiếu Seedance 2.5 (model_router → cờ dialogue_take), MỘT track giọng cả nhóm
      (runner._take_audio), câu thoại + người nói + mốc giây trong prompt (dialogue_take.group_block), cắt clip nhóm → `shift`
      (runner._take_done) → voice.place_on_timeline đặt giọng. Giọng: 2 câu TTS có sẵn của #8 (chép, 0 USD; cùng chữ).
      Mốc so: clip 31 của #8 (khớp môi từng shot (a), đo 29/09 = 0,04–0,18 — không khớp).
S4.6  A/B cận: 2 shot cận không thoại (CU Kelly đêm = shot 32 của #8, CU Kelly ngày = shot 18) × 2 cách:
      ref   = cờ closeup_start_frame TẮT → một shot Seedance chỉ ảnh tham chiếu (P2m, ảnh đánh dấu), như #8
      kling = cờ closeup_start_frame BẬT → Kling từ khung đầu = ảnh storyboard đã duyệt (S4.1)
      Cùng ảnh storyboard đã duyệt của #8 (chép, 0 ảnh mới) và cùng motion prompt đã duyệt của #8 cho cả 2 cách.

    py <worktree>/tools/experiments/s42_s46_take_closeup.py setup               dự án thử mới (0 USD) — chép từ #8, KHÔNG sửa #8
    py <worktree>/tools/experiments/s42_s46_take_closeup.py --project N plan    in model / ảnh / giọng / prompt / giá (0 USD, provider giả)
    py <worktree>/tools/experiments/s42_s46_take_closeup.py --project N take    gửi clip nhóm thoại (trả tiền, trần), chờ, cắt, shift
    py <worktree>/tools/experiments/s42_s46_take_closeup.py --project N closeup ref|kling [idx]   gửi TỪNG clip cận một (trả tiền, trần)
    py <worktree>/tools/experiments/s42_s46_take_closeup.py --project N measure đo khớp môi + mặt cận, xuất so sánh ra OUT

Chạy từ D:\\AI-Video-Pipeline (CSDL thật, token qua group_test.load_env)."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

NAME = "Thử S4.2 khớp môi (c) + S4.6 cận (01/10)"
SOURCE = 8
TAKE = {30: 167, 31: 168}                       # idx in the trial → #8 scene id (the dialogue take, story scene 6, sequence 1)
IMAGES = {167: 374, 168: 348, 169: 370, 155: 366}   # #8 scene → its approved storyboard picture (job id)
CLOSE = {40: (169, "ref"), 41: (169, "kling"), 42: (155, "ref"), 43: (155, "kling")}   # A/B rows: #8 scene, arm
CAP_USD = 4.0                                    # nhánh A1: tiền video + ảnh của dự án thử này
OUT = r"D:\AI-Video-Output\2026-10-01_s4-2_s4-6"
DATA = os.path.join("data", "projects")
BASE_ENV = {"FEATURE_SEEDANCE_REF_GROUPS": "1", "FEATURE_LIP_SYNC": "1", "FEATURE_DIALOGUE_TAKE": "1",
            "FEATURE_CLOSEUP_START_FRAME": "0", "FEATURE_PLACE_RENDER_REFS": "0",
            "FEATURE_SKILL_DOSSIER": "0"}


def _p(extra=None):
    from tools.experiments.group_test import load_env
    load_env(os.getcwd())
    os.environ.update(BASE_ENV)
    os.environ.update(extra or {})
    from core.db import connect
    from core.pipeline import Pipeline
    return Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))


def spent(p, pid):
    from core import project_budget
    return round(sum(project_budget.spent_by_stage(p.conn, pid).values()), 4)


def guard(p, pid, usd, what):
    s = spent(p, pid)
    if s + usd > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN CHẶN ({what}): đã chi ${s:.2f} + ≈ ${usd:.2f} > trần ${CAP_USD:.2f}")
    print(f"trần: đã chi ${s:.2f}, lần này ≈ ${usd:.2f}, còn ${CAP_USD - s - usd:.2f}")


def rows_of(p, pid):
    return [{"id": r["id"], "idx": r["idx"], "data": json.loads(r["data"] or "{}")}
            for r in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]


def by_idx(p, pid):
    return {r["idx"]: r for r in rows_of(p, pid)}


# ---- setup (0 USD) ------------------------------------------------------------------------------------------------------------
def _copy_image(p, pid, sid, src_job):
    jid = p.create_job(sid, "image_gen")
    dest = os.path.join(DATA, str(pid), "images", f"job_{jid}.png")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(os.path.join(DATA, str(SOURCE), "images", f"job_{src_job}.png"), dest)
    p.conn.execute("UPDATE jobs SET state='approved', result_path=? WHERE id=?", (dest, jid))
    p.conn.commit()
    return jid


def setup(p):
    from core import audio_lib, compare
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return
    pid = compare.clone_project(p, SOURCE, NAME)
    p.conn.execute(f"DELETE FROM scenes WHERE project_id=? AND idx NOT IN ({','.join('?' * len(TAKE))})", (pid, *TAKE))
    src = {r["id"]: r for r in rows_of(p, SOURCE)}
    for idx, (sid8, arm) in CLOSE.items():         # each A/B row alone in its own continuity group (never grouped with the take)
        data = dict(src[sid8]["data"], sequence=100 + idx, ab_arm=arm)
        new = p.create_scene(pid, idx, f"A/B cận {arm} · #8 shot {src[sid8]['idx']}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), new))
    p.conn.commit()
    here = by_idx(p, pid)
    for idx, sid8 in TAKE.items():
        _copy_image(p, pid, here[idx]["id"], IMAGES[sid8])
    mp8 = {r["scene_id"]: r for r in p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id IN (169, 155)")}
    for idx, (sid8, _) in CLOSE.items():            # the same approved motion prompt of #8 for both arms (the A/B changes one thing)
        jid = _copy_image(p, pid, here[idx]["id"], IMAGES[sid8])
        m = mp8[sid8]
        p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, camera, duration_sec, negative_prompt, state, image_job_id)"
                       " VALUES (?,?,?,?,?, 'approved', ?)", (here[idx]["id"], m["motion_prompt"], m["camera"], m["duration_sec"],
                                                               m["negative_prompt"], jid))
    p.conn.commit()
    src_dir, dst_dir = audio_lib.assets_dir(DATA, SOURCE), audio_lib.assets_dir(DATA, pid)
    items = []
    for e in audio_lib.load(src_dir):              # the two voiced lines of the take (#8, same words), scene ids remapped
        for idx, sid8 in TAKE.items():
            if e.get("kind") == "tts" and e.get("scene_id") == sid8 and e.get("state") == "succeeded":
                shutil.copyfile(os.path.join(src_dir, e["file"]), os.path.join(dst_dir, e["file"]))
                items.append(dict(e, scene_id=here[idx]["id"], scene_idx=idx, start=None))
    audio_lib._save(dst_dir, items)
    print("dự án thử:", pid, "·", [(r["idx"], r["id"]) for r in rows_of(p, pid)], "· giọng:", [(e["speaker"], e["file"]) for e in items])


# ---- plan (0 USD) -------------------------------------------------------------------------------------------------------------
def _estimate(vr, job):
    args = vr._submit_args(job)
    if not args:
        return None, None
    from core import cost
    usage = vr._usage(args, {"kling_mode": "std"})
    return args, (usage, cost.clip_price(cost.load_pricing(), *usage) if usage else None)


def plan(p, pid, arm="ref"):
    from core import model_router, seedance_refs, shots
    from core.adapters import factory
    from core.providers import MockVideoProvider
    from core.runner import VideoRunner
    n = seedance_refs.code_motion(p, pid)            # the take shots' motion prompts, written by code (no Claude) as the main flow does
    print("motion prompt viết bằng code:", n)
    real = VideoRunner(p, factory.video_provider(), DATA)
    vr = VideoRunner(p, MockVideoProvider(), DATA)
    rows = by_idx(p, pid)
    targets = [30] + [i for i, (_, a) in CLOSE.items() if a == arm]
    for idx in targets:
        r = rows[idx]
        job = {"id": -1, "scene_id": r["id"], "project_id": pid, "retry_reason": None, "type": "video_gen", "group_leader": None}
        print(f"\n=== shot {idx} ({r['data'].get('size')}, {r['data'].get('characters')}) — {model_router.scene_choice(p.conn, r['id'])}")
        print("nhóm:", [g["idx"] for g in (shots.group_of(p.conn, r["id"]) or [])], "· refs:", vr._refs(job),
              "· face_closeup:", seedance_refs.face_closeup(r["data"]))
        args, est = _estimate(real, job)
        if not args:
            print("(chưa gửi được: thiếu motion prompt / ảnh duyệt)")
            continue
        kw = vr._submit_kwargs(job)
        print("GIÂY:", args[3], "MODEL:", args[4], "· ước tính:", est)
        print("ẢNH:", [os.path.basename(x) for x in kw.get("reference_only") or []] or os.path.basename(args[0]))
        print("GIỌNG:", kw.get("reference_audio"))
        print("CHẶN:", vr._blocked(job))
        print(args[1])


# ---- paid runs ----------------------------------------------------------------------------------------------------------------
def _run(p, pid, scene_ids, usd, what, timeout=2700):
    """Create the video jobs, send once (the runner: estimate + global cap + ledger), then only poll until every job is done."""
    from core.adapters import factory
    from core.runner import VideoRunner
    guard(p, pid, usd, what)
    for sid in scene_ids:
        if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state NOT IN ('failed','rejected','cancelled')",
                              (sid,)).fetchone():
            p.create_job(sid, "video_gen")
    vr = VideoRunner(p, factory.video_provider(), DATA)
    before = spent(p, pid)
    t0 = time.time()
    while time.time() - t0 < timeout:
        jobs = [dict(r) for r in p.conn.execute(
            f"SELECT id, scene_id, state, external_id, model FROM jobs WHERE type='video_gen' AND scene_id IN ({','.join('?' * len(scene_ids))})"
            " ORDER BY id", scene_ids)]
        latest = {j["scene_id"]: j for j in jobs}
        if all(j["state"] in ("succeeded", "approved", "pending_review", "failed", "escalated") for j in latest.values()):
            break
        if not any(j["external_id"] for j in latest.values()) and spent(p, pid) <= before + 1e-9:
            if spent(p, pid) + usd > CAP_USD + 1e-9:
                raise SystemExit("TRẦN: dừng gửi")
            vr.submit_pending(pid)
        vr.poll_once(pid)
        print(time.strftime("%H:%M:%S"), [(j["scene_id"], j["state"], j["model"], j["external_id"]) for j in latest.values()],
              "· đã chi", spent(p, pid), flush=True)
        time.sleep(30)
    for r in p.conn.execute(f"SELECT scene_id, severity, code, message FROM diag_events WHERE scene_id IN ({','.join('?' * len(scene_ids))})"
                            " ORDER BY id DESC LIMIT 12", scene_ids):
        print("chẩn đoán:", dict(r))
    print("đã chi:", spent(p, pid))


def take(p, pid):
    from core import lipsync
    from core.adapters import factory
    from core.runner import VideoRunner
    rows = by_idx(p, pid)
    real = VideoRunner(p, factory.video_provider(), DATA)
    job = {"id": -1, "scene_id": rows[30]["id"], "project_id": pid, "retry_reason": None, "type": "video_gen", "group_leader": None}
    args, (usage, usd) = _estimate(real, job)
    if args[4] != "seedance-2.5":
        raise SystemExit(f"model {args[4]} ≠ seedance-2.5 — dừng (khớp môi (c) cần 2.5)")
    print("ước tính:", usage, usd)
    _run(p, pid, [rows[30]["id"], rows[31]["id"]], usd * 1.05, "clip nhóm thoại")
    print("lipsync:", json.dumps(lipsync.index(DATA, pid), ensure_ascii=False))


def closeup(p, pid, arm, only=None):
    from core.adapters import factory
    from core.runner import VideoRunner
    rows = by_idx(p, pid)
    real = VideoRunner(p, factory.video_provider(), DATA)
    for idx, (_, a) in CLOSE.items():
        if a != arm or (only and idx != only):
            continue
        if p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN ('succeeded','approved','pending_review')",
                          (rows[idx]["id"],)).fetchone():
            print("shot", idx, "đã có clip — bỏ qua")
            continue
        job = {"id": -1, "scene_id": rows[idx]["id"], "project_id": pid, "retry_reason": None, "type": "video_gen", "group_leader": None}
        args, (usage, usd) = _estimate(real, job)
        want = "kling" if arm == "kling" else "seedance"
        if want not in str(args[4]):
            raise SystemExit(f"shot {idx}: model {args[4]} không phải cách '{arm}' — kiểm cờ closeup_start_frame")
        print(f"--- shot {idx} ({arm}): {usage} ≈ ${usd}")
        _run(p, pid, [rows[idx]["id"]], usd * 1.05, f"cận {idx} {arm}")      # one clip at a time (ClipAI ~2 in parallel, shared)


# ---- measure (0 USD) ----------------------------------------------------------------------------------------------------------
def _ff():
    from core.ffmpeg_studio import find_ffmpeg
    return find_ffmpeg()


def _mux(video, audio, out):
    subprocess.run([_ff(), "-y", "-loglevel", "error", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a",
                    "aac", "-shortest", out], check=True)


def _voice_at(files_starts, seconds, out):
    """A voice file `seconds` long with each (file, start) laid at its second."""
    cmd = [_ff(), "-y", "-loglevel", "error"]
    for f, _ in files_starts:
        cmd += ["-i", f]
    parts = "".join(f"[{i}:a]adelay={max(int(s * 1000), 0)}|{max(int(s * 1000), 0)},aresample=44100[a{i}];"
                    for i, (_, s) in enumerate(files_starts))
    mix = "".join(f"[a{i}]" for i in range(len(files_starts)))
    cmd += ["-filter_complex", parts + f"{mix}amix=inputs={len(files_starts)}:normalize=0,apad,atrim=0:{seconds:.3f}[o]", "-map", "[o]",
            "-ac", "1", "-ar", "44100", out]
    subprocess.run(cmd, check=True)
    return out


def _sheet(clips, out, n=6, h=320):
    """One row of n frames per clip (frames evenly over the clip) — for the eye."""
    import cv2
    import numpy as np
    rows = []
    for c in clips:
        cap = cv2.VideoCapture(c)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        cells = []
        for k in range(n):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(k * (total - 1) / max(n - 1, 1)))
            ok, f = cap.read()
            if not ok:
                continue
            cells.append(cv2.resize(f, (int(f.shape[1] * h / f.shape[0]), h)))
        cap.release()
        if cells:
            rows.append(np.hstack(cells))
    if rows:
        w = max(r.shape[1] for r in rows)
        cv2.imwrite(out, np.vstack([np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0))) for r in rows]))


def measure(p, pid):
    from core import audio_lib, clip_measure as cm, ffmpeg_studio, lipsync, shots, voice
    os.makedirs(OUT, exist_ok=True)
    rows = by_idx(p, pid)
    vdir = os.path.join(DATA, str(pid), "videos")
    adir = audio_lib.assets_dir(DATA, pid)
    report = {"project": pid, "usd": spent(p, pid)}
    idx = lipsync.index(DATA, pid)
    lines = {e["scene_id"]: e for e in audio_lib.load(adir) if e.get("kind") == "tts"}
    # --- S4.2: the group clip against its dialogue track, then each cut shot with its voice where the timeline puts it
    group_clip = os.path.join(vdir, "30_group.mp4")
    leader = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id DESC LIMIT 1", (rows[30]["id"],)).fetchone()
    track = leader and os.path.join(DATA, str(pid), "lipsync", f"take_{leader['id']}.wav")
    if os.path.exists(group_clip) and track and os.path.exists(track):
        turns = []
        for i in (30, 31):
            rec, e = idx.get(str(rows[i]["id"])) or {}, lines[rows[i]["id"]]
            a = float(rec.get("planned_start") or 0) + (rec.get("offsets") or [voice.LEAD])[0]
            turns.append({"speaker": e["speaker"], "start": round(a, 2), "end": round(a + e["duration_ms"] / 1000.0, 2)})
        res = cm.lip_sync(group_clip, track, turns)
        report["take_group"] = {"clip": group_clip, "turns": turns, **res}
        _mux(group_clip, track, os.path.join(OUT, "s42_take_nhom_co-giong.mp4"))
        _sheet([group_clip], os.path.join(OUT, "s42_take_nhom_khung.jpg"), n=10)
        print("clip nhóm:", json.dumps(report["take_group"], ensure_ascii=False))
    # the timeline of the main flow (voice.place_on_timeline with the lipsync shift) on the two cut clips
    clips = [os.path.join(vdir, f"{i:02d}.mp4") for i in (30, 31)]
    if all(os.path.exists(c) for c in clips):
        from unittest import mock
        durs = [ffmpeg_studio.probe_duration(c) for c in clips]
        fake = [{"scene_id": rows[i]["id"], "path": c, "requested_sec": d} for i, c, d in zip((30, 31), clips, durs)]
        with mock.patch("core.final_cut.collect_clips_for_render", return_value=fake):
            voice.place_on_timeline(p.conn, pid, DATA, durations=durs)
        placed = {e["scene_id"]: e for e in audio_lib.load(adir) if e.get("kind") == "tts"}
        t, cut_rows = 0.0, []
        for i, c, d in zip((30, 31), clips, durs):
            e = placed[rows[i]["id"]]
            local = round(e["start"] - t, 3)
            wav = _voice_at([(os.path.join(adir, e["file"]), local)], d, os.path.join(OUT, f"s42_shot{i}_giong.wav"))
            res = cm.lip_sync(c, wav, [{"speaker": e["speaker"], "start": local, "end": round(local + e["duration_ms"] / 1000.0, 2)}])
            cut_rows.append({"shot": i, "clip": c, "seconds": d, "voice_start_in_clip": local,
                             "shift": (idx.get(str(rows[i]["id"])) or {}).get("shift"), **res})
            _mux(c, wav, os.path.join(OUT, f"s42_shot{i}_co-giong.mp4"))
            t += d
        report["take_cut"] = cut_rows
        film = os.path.join(OUT, "s42_shot30-31_noi.mp4")
        lst = os.path.join(OUT, "_concat.txt")
        with open(lst, "w", encoding="utf-8") as f:
            f.writelines(f"file '{os.path.abspath(c)}'\n" for c in clips)
        subprocess.run([_ff(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-an", "-c:v", "libx264", "-pix_fmt",
                        "yuv420p", film + ".v.mp4"], check=True)
        wav = _voice_at([(os.path.join(adir, placed[rows[i]["id"]]["file"]), placed[rows[i]["id"]]["start"]) for i in (30, 31)],
                        sum(durs), os.path.join(OUT, "s42_noi_giong.wav"))
        _mux(film + ".v.mp4", wav, film)
        os.remove(film + ".v.mp4")
        os.remove(lst)
        for r in cut_rows:
            print("shot cắt:", json.dumps(r, ensure_ascii=False))
    # --- S4.6 close-ups: the look against the approved picture, the reference mark, a frame sheet per arm
    close = []
    for i, (sid8, arm) in CLOSE.items():
        r = rows[i]
        raw = os.path.join(vdir, f"{i:02d}_raw.mp4")
        clip = raw if os.path.exists(raw) else os.path.join(vdir, f"{i:02d}.mp4")
        if not os.path.exists(clip):
            continue
        pic = shots.approved_image_path(p.conn, DATA, pid, r["id"])
        job = p.conn.execute("SELECT model FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id DESC LIMIT 1", (r["id"],)).fetchone()
        row = {"row": i, "src_8": sid8, "arm": arm, "model": job and job["model"], "clip": clip, "seconds": ffmpeg_studio.probe_duration(clip),
               "look": cm.look_drift(clip, pic), "ref_mark": cm.ref_mark(clip), "motion": cm.jerks(clip)}
        row["motion"] = {k: row["motion"].get(k) for k in ("flag", "why", "cuts", "spikes") if k in row["motion"]}
        close.append(row)
        shutil.copyfile(clip, os.path.join(OUT, f"s46_can_{i}_{arm}.mp4"))
        shutil.copyfile(pic, os.path.join(OUT, f"s46_can_{i}_{arm}_khung-duyet.png"))
        print("cận:", json.dumps(row, ensure_ascii=False))
    for sid8 in sorted({v[0] for v in CLOSE.values()}):
        pair = [os.path.join(OUT, f"s46_can_{i}_{a}.mp4") for i, (s, a) in CLOSE.items() if s == sid8]
        if all(os.path.exists(x) for x in pair):
            _sheet(pair, os.path.join(OUT, f"s46_can_8-{sid8}_tren-ref_duoi-kling.jpg"))
    report["closeups"] = close
    with open(os.path.join(OUT, "do_luong.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("ghi:", os.path.join(OUT, "do_luong.json"), "· đã chi", report["usd"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("setup", "plan", "take", "closeup", "measure"))
    ap.add_argument("arm", nargs="?", default="ref", choices=("ref", "kling"))
    ap.add_argument("only", nargs="?", type=int)
    ap.add_argument("--project", type=int)
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    a = ap.parse_args()
    script_cap.require(a, "s42_s46_take_closeup").start()
    extra = {"FEATURE_CLOSEUP_START_FRAME": "1" if a.arm == "kling" and a.step in ("plan", "closeup") else "0"}
    p = _p(extra)
    if a.step == "setup":
        return setup(p)
    if not a.project:
        raise SystemExit("cần --project N")
    if a.step == "plan":
        plan(p, a.project, a.arm)
    elif a.step == "take":
        take(p, a.project)
    elif a.step == "closeup":
        closeup(p, a.project, a.arm, a.only)
    else:
        measure(p, a.project)


if __name__ == "__main__":
    main()
