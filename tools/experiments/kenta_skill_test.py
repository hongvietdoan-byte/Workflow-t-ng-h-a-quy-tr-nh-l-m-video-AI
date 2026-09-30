"""Thử hồ sơ kỹ năng (cờ skill_dossier) trên MỘT cảnh ngắn Kenta dùng kỹ năng — người dùng duyệt 2026-09-30, trần cứng $3.
3 shot, mỗi shot một giai đoạn kỹ năng ở khung đầu và một ở khung cuối (skill_phase / skill_phase_end), clip Kling std khung đầu +
khung cuối (cách hiệu ứng vẽ sẵn, S4.6). Không gọi Claude (shot viết tay, đã ghi sẵn giai đoạn) — thử phần ảnh / video của hồ sơ.

    py tools/experiments/kenta_skill_test.py setup            tạo dự án thử (0 USD) — in mã dự án
    py tools/experiments/kenta_skill_test.py --project N frames   vẽ 3 khung đầu (Deepix, ảnh tham chiếu = khung thật của giai đoạn)
    py tools/experiments/kenta_skill_test.py --project N approve 1,2,3   duyệt khung đầu (sau khi xem)
    py tools/experiments/kenta_skill_test.py --project N ends     vẽ 3 khung cuối (giai đoạn cuối)
    py tools/experiments/kenta_skill_test.py --project N plan     in prompt video + giá (không gửi)
    py tools/experiments/kenta_skill_test.py --project N submit   gửi 3 clip Kling (qua trần + sổ chi)
    py tools/experiments/kenta_skill_test.py --project N poll     tải clip về <data>/<pid>/experiments/

Chạy từ D:\\AI-Video-Pipeline. Mọi bước tốn tiền kiểm TRẦN_USD của dự án (sổ chi usage_events) trước khi gửi."""
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

NAME = "Thử hồ sơ kỹ năng Kenta (30/09)"
CAP_USD = 6.6          # người dùng duyệt $3, + $0,6 ("Thử tiếp"), + T1–T3 ≈ $3 ("thử" sau nghiên cứu 30/09 — docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md)
IMAGE_USD = 0.052
ASSETS = (24, 23, 263)          # KENTA, KELLY, Tháp Đồng Hồ (khu nhà dưới chân tháp — giống làng trong video kỹ năng)
PLACE = "Quanh Tháp Đồng Hồ (Đảo Quân Sự) — khu nhà ở dưới chân tháp, ban ngày nắng"
ENV = {"FEATURE_SKILL_DOSSIER": "1", "FEATURE_END_FRAMES": "1", "FEATURE_SEEDANCE_REF_GROUPS": "0",
       "FEATURE_STORYBOARD_API": "0", "FEATURE_SCENE_ESTABLISHING": "0", "FEATURE_PLACE_RENDER_REFS": "0", "FEATURE_LOCATION_PLATES": "0"}
SHOTS = [
    {"shot_no": 1, "size": "MS", "angle": "eye", "camera_move": "static", "duration_s": 3.0, "characters": ["KENTA"],
     "skill_phase": "KENTA:prepare", "skill_phase_end": "KENTA:swing_vortex",
     "image_prompt": "Kenta seen from behind at his right shoulder, standing on a dirt path between wooden houses, facing a white "
                     "bumpy gloo wall about eight metres ahead",
     "action": "Kenta stands still, then sweeps the energy blade in one very fast stroke",
     "end_state": "the stroke has just ended; a transparent blue-white whirlwind column wraps his whole body"},
    {"shot_no": 2, "size": "WS", "angle": "eye", "camera_move": "static", "duration_s": 3.0, "characters": ["KENTA"],
     "skill_phase": "KENTA:ground_rings", "skill_phase_end": "KENTA:wind_fly",
     "image_prompt": "Kenta seen from behind and slightly to his right, whole body small in the frame, on the dirt path between "
                     "wooden houses, the white gloo wall about eight metres ahead of him",
     "action": "the wind rings spread on the ground around his planted feet, then the wind streaks fly straight to the gloo wall",
     "end_state": "thin curved transparent wind streaks are halfway to the gloo wall, low and level; Kenta has not moved"},
    {"shot_no": 3, "size": "MS", "angle": "eye", "camera_move": "static", "duration_s": 3.0, "characters": ["KELLY"],
     "skill_phase": "KENTA:wind_fly", "skill_phase_end": "KENTA:through_gloo",
     "image_prompt": "Kelly crouching behind a white bumpy gloo wall on a dirt path between wooden houses, seen from her side; "
                     "thin transparent wind streaks arriving at the far side of the wall",
     "action": "the wind sweeps through the gloo wall, the wall stays whole, Kelly flinches as she is hit",
     "end_state": "the wind has swept through the wall, which stands whole; Kelly flinches, hurt, still crouching"},
]


def spent(p, pid: int) -> float:
    from core import project_budget
    return round(sum(project_budget.spent_by_stage(p.conn, pid).values()), 4)


def guard(p, pid: int, usd: float, what: str) -> None:
    s = spent(p, pid)
    if s + usd > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN CHẶN ({what}): đã chi ${s:.2f} + lần này ≈ ${usd:.2f} > trần ${CAP_USD:.2f} — dừng, giữ kết quả đã có")
    print(f"trần: đã chi ${s:.2f}, lần này ≈ ${usd:.2f}, còn ${CAP_USD - s - usd:.2f} sau lần này")


def setup(p):
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return row["id"]
    pid = p.create_project(NAME, created_by="claude-code-skill-dossier", game="FF", aspect="9:16")
    p.set_project_field(pid, "shot_mode", "per_shot")
    p.set_project_field(pid, "look", "FF_INGAME")
    for aid in ASSETS:
        p.conn.execute("INSERT OR IGNORE INTO project_assets (project_id, asset_id) VALUES (?, ?)", (pid, aid))
    for n, d in enumerate(SHOTS, 1):
        sid = p.create_scene(pid, n, f"Shot {n}")
        data = dict(d, story_scene=1, sequence=1, location=PLACE, shot=f"S1·{n}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
    p.conn.commit()
    print("dự án thử:", pid)
    return pid


def rows_of(p, pid: int):
    return [{"id": r["id"], "idx": r["idx"], "data": json.loads(r["data"] or "{}")}
            for r in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,))]


def cmd_frames(p, data_dir: str, pid: int) -> None:
    from core.adapters import factory
    from core.runner import ImageRunner
    rows = rows_of(p, pid)
    todo = [r for r in rows if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state NOT IN "
                                                  "('failed','rejected')", (r["id"],)).fetchone()]
    guard(p, pid, IMAGE_USD * len(todo), "khung đầu")
    for r in todo:
        p.create_job(r["id"], "image_gen")
    runner = ImageRunner(p, factory.image_provider(), data_dir)
    ids = {r["id"] for r in rows}
    t0 = time.time()
    while time.time() - t0 < 1800:
        runner.submit_pending(pid)
        runner.poll_once(pid)
        states = {r["id"]: r["state"] for r in p.conn.execute("SELECT scene_id id, state FROM jobs WHERE project_id=? AND type='image_gen'"
                                                              " ORDER BY id", (pid,)) if r["id"] in ids}
        print(time.strftime("%H:%M:%S"), states, flush=True)
        if states and all(s in ("succeeded", "approved", "pending_review", "failed", "escalated") for s in states.values()):
            break
        time.sleep(15)
    for r in p.conn.execute("SELECT j.id, j.scene_id, j.state FROM jobs j WHERE j.project_id=? AND j.type='image_gen' ORDER BY j.id",
                            (pid,)):
        print(r["scene_id"], r["id"], r["state"], os.path.join(data_dir, str(pid), "images", f"job_{r['id']}.png"))
    print("đã chi:", spent(p, pid))


def cmd_approve(p, pid: int, shots) -> None:
    rows = rows_of(p, pid)
    for r in rows:
        if r["data"].get("shot_no") in shots:
            j = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN ('succeeded','pending_review')"
                               " ORDER BY id DESC LIMIT 1", (r["id"],)).fetchone()
            if j:
                p.approve(j["id"], "user", "người dùng duyệt thử hồ sơ kỹ năng — Claude xem ảnh trước khi duyệt")
                print("duyệt shot", r["data"]["shot_no"], "job", j["id"])


def cmd_redraw(p, pid: int, shots) -> None:
    """Luật 6: vẽ lại chỉ khi đầu vào đã đổi (hồ sơ 30/09 chiều: mô tả + ảnh cắt cận) — khung đầu đang duyệt bị gỡ, bước frames vẽ mới."""
    for r in rows_of(p, pid):
        if r["data"].get("shot_no") in shots:
            for j in p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'",
                                    (r["id"],)).fetchall():   # the input changed (the dossier): no fix words, the frames step draws anew
                p.reopen_approved(j["id"], "vẽ lại sau khi sửa hồ sơ kỹ năng (lưỡi hologram, katana ngang, lốc màng mờ, gió lưỡi liềm)",
                                  respawn=False, fix="")
                print("gỡ khung đầu shot", r["data"]["shot_no"], "job", j["id"])


def cmd_ends(p, data_dir: str, pid: int) -> None:
    from core import end_frames
    from core.adapters import factory
    queued = end_frames.queue(p, pid)
    guard(p, pid, IMAGE_USD * len(queued), "khung cuối")
    provider = factory.image_provider()
    t0 = time.time()
    while time.time() - t0 < 1800:
        c = end_frames.tick(p, pid, provider, data_dir)
        print(time.strftime("%H:%M:%S"), c, flush=True)
        if not end_frames.pending(p, pid):
            break
        time.sleep(15)
    for r in p.conn.execute("SELECT scene_id, id, state, path, note FROM end_frames WHERE project_id=? ORDER BY id", (pid,)):
        print(dict(r))
    print("đã chi:", spent(p, pid))


def _clip(p, pid: int, row):
    """(start, end, seconds, prompt, negative) of one shot's clip: the look, the action, the skill phases of the dossier."""
    from core import end_frames, looks, skill_dossier
    from core.runner import no_minor_age
    d = row["data"]
    start = end_frames._start_job(p.conn, row["id"])
    start = os.path.join(DATA_DIR, str(pid), "images", f"job_{start['id']}.png") if start else None
    end = end_frames.usable_path(p.conn, row["id"])
    hit = skill_dossier.shot_skill(d)
    look = looks.video_sentence(p.project(pid)).split(" Render style:")[0]
    prompt = no_minor_age(f"{look} Starts on the first image and ends on the last image. {d['action'].strip().rstrip('.')}."
                          + skill_dossier.video_sentence(hit))
    negative = looks.video_negative(p.project(pid), skill_dossier.video_negative(hit, None))
    return start, end, max(3, math.ceil(float(d.get("duration_s") or 3) - 1e-6)), prompt, negative


def cmd_plan(p, pid: int):
    from core import cost
    out = []
    for r in rows_of(p, pid):
        start, end, secs, prompt, negative = _clip(p, pid, r)
        usd = cost.clip_price(cost.load_pricing(), "kling-v3-omni", "std", secs)
        out.append({"row": r, "start": start, "end": end, "seconds": secs, "prompt": prompt, "negative": negative, "usd": usd})
        print(f"shot {r['data']['shot_no']}: {secs} s ≈ ${usd:.2f} · khung đầu {'có' if start else 'THIẾU'} · khung cuối "
              f"{'có' if end else 'THIẾU'} · prompt {len(prompt)} ký tự\n  {prompt}\n  negative: {negative}")
    print(f"Tổng ≈ ${sum(o['usd'] for o in out):.2f}; đã chi ${spent(p, pid):.2f} / trần ${CAP_USD:.2f}")
    return out


REF_CLIP = os.path.join("data", "skills", "KENTA", "clips_local", "release_16.0-19.2.mp4")
REF_NOTE = ("The reference video is the real game footage of this skill: copy ONLY the skill effect's shapes, colours, transparency, "
            "timing and motion from it — not its camera, place, person or on-screen text. ")


def cmd_submit(p, pid: int, shots=None, refvideo: bool = False) -> None:
    from core import budget, experiments, formats
    from core.adapters import factory
    from core.cost import record_usage
    from core.providers import ProviderError
    provider = factory.video_provider()
    aspect = formats.spec(formats.project_aspect(p.project(pid)) or "9:16")["clip"]
    items = experiments.load(DATA_DIR, pid)
    method = "SKILLV" if refvideo else "SKILL2" if shots else "SKILL"
    done = {e.get("group") for e in items if e.get("kind") == "group_test" and e.get("method") == method and e.get("state") != "failed"}
    for o in cmd_plan(p, pid):
        n = o["row"]["data"]["shot_no"]
        if shots and n not in shots:
            continue
        if refvideo:
            o["prompt"] = REF_NOTE + o["prompt"]
        if n in done:
            print("đã gửi trước đó: shot", n)
            continue
        if refvideo:                               # 30/09: the reference video carries the effect; no drifting end frame to morph into
            o["end"] = None
            o["prompt"] = o["prompt"].replace(" Starts on the first image and ends on the last image.", " Starts on the first image, same camera and place throughout.")
        if not (o["start"] and (o["end"] or refvideo)):
            print("bỏ qua shot", n, "— thiếu khung đầu / cuối")
            continue
        if len(o["prompt"]) > 2500:              # core/adapters/clipai.py PROMPT_LIMITS["kling"] (500 = one shot of a multi-shot)
            raise SystemExit(f"prompt shot {n} dài {len(o['prompt'])} > 2500 ký tự Kling — rút gọn trước khi gửi")
        guard(p, pid, o["usd"], f"clip shot {n}")
        entry = {"kind": "group_test", "scene": 1, "method": method, "group": n, "shots": [n], "seconds": o["seconds"],
                 "film_s": o["seconds"], "model": "kling-v3-omni", "tier": "std", "usd": o["usd"], "prompt": o["prompt"],
                 "external_id": None, "state": "running", "file": None, "sequence": 1, "scenes": [n],
                 "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        with budget.SPEND_LOCK:
            over = budget.check_video(p.conn, provider.name, "kling-v3-omni", "std", o["seconds"])
            if over:
                raise SystemExit("TRẦN CHUNG CHẶN: " + over)
            try:
                entry["external_id"] = provider.submit(o["start"], o["prompt"], o["negative"], o["seconds"], "kling",
                                                       aspect_ratio=aspect, kling_mode="std", last_frame=o["end"],
                                                       **({"reference_video": {"path": REF_CLIP, "refer_type": "feature"}}
                                                          if refvideo else {}))
                record_usage(p.conn, None, "video", provider.name, "kling-v3-omni", "std", o["seconds"], "second", pid)
            except ProviderError as e:
                entry.update(state="failed", message=f"[{e.code}] {e}"[:400], usd=0.0)
        items.append(entry)
        experiments._save(DATA_DIR, pid, items)
        print("shot", n, entry["state"], entry["external_id"] or entry.get("message", "")[:160])
    print("đã chi:", spent(p, pid))


# Nghiên cứu 30/09 (docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md): prompts written to the official templates — every asset named, one
# job each, what NOT to take said; the video carries the effect so the effect is not described again in detail.
KENTA_FRONT = os.path.join("data", "assets", "24", "7.png")
T1_PROMPT = (
    "[Goal] Kenta, a Free Fire in-game 3D character, releases his skill on a dirt path between wooden houses: a translucent hologram blade "
    "in his right hand is swept, a faint see-through whirlwind wraps his whole body, sinks into wind rings on the ground, and crescent wind "
    "arcs fly toward the white gloo wall ahead.\n"
    "[Asset roles]\n"
    "@Image 1 is the first frame. It sets the dirt path, the wooden houses, the clock tower, where the gloo wall stands, Kenta standing with "
    "his back to the camera, his pose, and the fixed medium-shot camera.\n"
    "@Image 2 is Kenta: use only his face, hair, blue hooded cloak, and the red-hilted katana worn horizontally across the back of his waist; "
    "not the grey background.\n"
    "@Video 1 is used only for the skill effect: its shape, colour, transparency, size against the body, order and rhythm (hologram blade "
    "swept, then a see-through whirlwind wrapping the whole body, then wind rings on the ground, then crescent wind arcs flying forward at "
    "shoulder height). Do not take the person, clothes, place, camera or on-screen text of @Video 1.\n"
    "[Event] At the start Kenta stands still holding the hologram blade, as in @Image 1. He releases the skill with the timing of @Video 1. "
    "At the end the crescent wind arcs reach the gloo wall; Kenta's feet have not moved.\n"
    "[Keep] Kenta's identity and clothes, the katana in its scabbard across his back, the fixed camera, the gloo wall standing whole, the "
    "Free Fire in-game 3D render style. No subtitles, no on-screen text.")
T2_PROMPT = (
    "Take <<<image_1>>> as the start frame. <<<image_2>>> is Kenta: keep his face, hair, blue hooded cloak and the red-hilted katana worn "
    "across the back of his waist. Animate Kenta in <<<image_1>>> releasing his skill with the same motion and the same skill effect as in "
    "<<<video_1>>>: the hologram blade is swept, a faint see-through whirlwind wraps his whole body, sinks into wind rings on the ground, and "
    "crescent wind arcs fly at shoulder height toward the white gloo wall. Take only the motion and the effect from <<<video_1>>>, not its "
    "person, place, camera or on-screen text. The camera stays fixed; Kenta's feet do not move.")


T3_ASSETS = [os.path.join("data", "assets", "263", "5.png"), os.path.join("data", "assets", "23", "10.png"), KENTA_FRONT,
             os.path.join("data", "assets", "33", "7.png")]
T3_PROMPT = (
    "[Goal] Three Free Fire in-game characters in one continuous shot on a street of red-roof houses below the clock tower: Kenta releases "
    "his skill toward a white gloo wall, Kelly crouches behind the wall and flinches when the wind reaches her, Maxim watches from a house "
    "doorway.\n"
    "[Asset roles]\n"
    "@Image 1 is the place: use only the street, the red-roof houses, the clock tower and the midday light; not its camera.\n"
    "@Image 2 is Kelly: use only her face, hair and yellow tracksuit; not the grey background.\n"
    "@Image 3 is Kenta: use only his face, hair, blue hooded cloak and the red-hilted katana worn horizontally across the back of his waist; "
    "not the grey background.\n"
    "@Image 4 is Maxim: use only his face, hair and clothes; not the grey background.\n"
    "The three people never swap faces, hair, clothes, places or actions.\n"
    "@Video 1 is used only for Kenta's skill effect: its shape, colour, transparency, order and rhythm. Do not take the person, clothes, "
    "place, camera or on-screen text of @Video 1.\n"
    "[People and places] A white bumpy gloo wall stands in the middle of the street. Kelly crouches behind the wall, on the side away from "
    "Kenta. Kenta stands on the street about eight metres from the wall, facing it. Maxim stands in the doorway of the red-roof house next "
    "to the wall.\n"
    "[Event] At the start Kenta holds a translucent turquoise hologram blade in his right hand. He releases the skill with the timing of "
    "@Video 1; the crescent wind arcs pass through the gloo wall, which stays whole; Kelly flinches but keeps crouching; Maxim steps back "
    "inside the doorway. At the end all three are still in their own places.\n"
    "[Camera] Fixed wide shot from the side at eye level; all three people stay visible.\n"
    "[Keep] The three identities and clothes, the katana in its scabbard across Kenta's back, the gloo wall standing whole, the Free Fire "
    "in-game 3D render style. Nobody speaks; mouths closed. No subtitles, no on-screen text.")


def cmd_research_test(p, pid: int, which: str) -> None:
    """T1: Seedance 2.5 reference mode (first frame by role sentence + Kenta + skill video). T2: Kling with the assets named."""
    from core import budget, cost, end_frames, experiments, formats
    from core.adapters import factory
    from core.cost import record_usage
    from core.providers import ProviderError
    row = rows_of(p, pid)[0]                                   # shot 1: prepare → release
    start = end_frames._start_job(p.conn, row["id"])
    start = os.path.join(DATA_DIR, str(pid), "images", f"job_{start['id']}.png")
    for f in (start, KENTA_FRONT, REF_CLIP):
        if not os.path.exists(f):
            raise SystemExit("thiếu tài sản: " + f)
    provider = factory.video_provider()
    aspect = formats.spec(formats.project_aspect(p.project(pid)) or "9:16")["clip"]
    if which == "t3":                                          # 3 people, no first frame: the place picture + one picture per person
        for f in T3_ASSETS:
            if not os.path.exists(f):
                raise SystemExit("thiếu tài sản: " + f)
        model, canonical, tier, secs, prompt = "seedance-2.5", "dreamina-seedance-2-5-260628", "720p", 5, T3_PROMPT
        usd = cost.clip_price(cost.load_pricing(), canonical, tier, secs) * 1.25
        kwargs = {"reference_only": T3_ASSETS, "resolution": tier}
    elif which == "t1":
        model, canonical, tier, secs, prompt = "seedance-2.5", "dreamina-seedance-2-5-260628", "720p", 5, T1_PROMPT
        usd = cost.clip_price(cost.load_pricing(), canonical, tier, secs) * 1.25          # no exact price source (× UNVERIFIED_MARGIN)
        kwargs = {"reference_only": [start, KENTA_FRONT], "resolution": tier}
    else:
        model, canonical, tier, secs, prompt = "kling", "kling-v3-omni", "std", 3, T2_PROMPT
        usd = cost.clip_price(cost.load_pricing(), canonical, tier, secs) * 1.5 / 1.33    # measured: cost 27 with a video (≈ $0,27)
        kwargs = {"kling_mode": tier, "image_references": [{"path": KENTA_FRONT, "label": "KENTA"}], "kling_image_refs": True}
    items = experiments.load(DATA_DIR, pid)
    if any(e.get("method") == which.upper() and e.get("state") != "failed" for e in items):
        print("đã gửi trước đó:", which)
        return
    print(prompt, len(prompt), "ký tự")
    guard(p, pid, usd, which)
    entry = {"kind": "group_test", "scene": 1, "method": which.upper(), "group": 1, "shots": [1], "seconds": secs, "film_s": secs,
             "model": canonical, "tier": tier, "usd": round(usd, 3), "prompt": prompt, "external_id": None, "state": "running",
             "file": None, "sequence": 1, "scenes": [1], "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with budget.SPEND_LOCK:
        over = budget.check_video(p.conn, provider.name, canonical, tier, secs)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        try:
            entry["external_id"] = provider.submit(start, prompt, None, secs, model, aspect_ratio=aspect,
                                                   reference_video={"path": REF_CLIP, "refer_type": "feature"}, **kwargs)
            record_usage(p.conn, None, "video", provider.name, canonical, tier, secs, "second", pid)
        except ProviderError as e:
            entry.update(state="failed", message=f"[{e.code}] {e}"[:400], usd=0.0)
    items.append(entry)
    experiments._save(DATA_DIR, pid, items)
    print(which, entry["state"], entry["external_id"] or entry.get("message"), "· đã chi:", spent(p, pid))


DATA_DIR = os.path.join("data", "projects")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int)
    ap.add_argument("step", choices=("setup", "frames", "approve", "redraw", "ends", "plan", "submit", "poll", "t1", "t2", "t3"))
    ap.add_argument("shots", nargs="?", default="")
    ap.add_argument("--refvideo", action="store_true", help="gửi kèm đoạn video kỹ năng thật làm tham chiếu chuyển động (Kling video_list)")
    a = ap.parse_args()
    from tools.experiments.group_test import cmd_poll, load_env
    load_env(os.getcwd())
    os.environ.update(ENV)
    global DATA_DIR
    DATA_DIR = os.environ.get("PIPELINE_DATA") or DATA_DIR
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))
    if a.step == "setup":
        setup(p)
        return
    {"frames": lambda: cmd_frames(p, DATA_DIR, a.project),
     "approve": lambda: cmd_approve(p, a.project, {int(x) for x in a.shots.split(",") if x}),
     "ends": lambda: cmd_ends(p, DATA_DIR, a.project),
     "plan": lambda: cmd_plan(p, a.project),
     "redraw": lambda: cmd_redraw(p, a.project, {int(x) for x in a.shots.split(",") if x}),
     "submit": lambda: cmd_submit(p, a.project, {int(x) for x in a.shots.split(",") if x} or None, a.refvideo),
     "t1": lambda: cmd_research_test(p, a.project, "t1"),
     "t2": lambda: cmd_research_test(p, a.project, "t2"),
     "t3": lambda: cmd_research_test(p, a.project, "t3"),
     "poll": lambda: cmd_poll(p, DATA_DIR, a.project)}[a.step]()


if __name__ == "__main__":
    main()
