"""S10.8 / S10.9 — thử có trả tiền (người dùng duyệt 30/09, trần 15 USD cho các bài thử; bài này trần riêng CAP_USD):

T4  một clip Kenta + Orion cùng tung kỹ năng, chạy QUA PIPELINE THẬT (model_router → Seedance 2.5, VideoRunner đường kỹ năng: khung đầu +
    ảnh chính diện + bảng nhiều góc + tờ kỹ năng sạch + 2 video kỹ năng, khối vai trò theo mẫu chính thức) — hai hiệu ứng có lẫn nhau không.
T5  cảnh 3 người (Kelly, Kenta, Maxim): khung đầu vẽ đủ người + white-model thô xếp chỗ đứng (core/whitebox) — người thứ ba có giữ chỗ / mặt.

    py tools/experiments/skill_multi_test.py setup                  dự án thử (0 USD) — in mã dự án
    py tools/experiments/skill_multi_test.py --project N frames     vẽ khung đầu các shot (Deepix, qua ImageRunner)
    py tools/experiments/skill_multi_test.py --project N approve 1,2   duyệt khung đầu (sau khi Claude / người dùng xem)
    py tools/experiments/skill_multi_test.py --project N plan       in prompt + tài sản sẽ gửi (0 USD, provider giả)
    py tools/experiments/skill_multi_test.py --project N video 1    gửi clip shot 1 qua VideoRunner (qua trần + sổ chi), chờ, tải về

Chạy từ D:\\AI-Video-Pipeline."""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

NAME = "Thử 2 kỹ năng + 3 người (30/09)"
CAP_USD = 5.0          # T4 + T5 (≈ 3 USD) + vẽ lại ≤ 2 lần — trong 15 USD người dùng duyệt 30/09
ASSETS = (24, 43, 23, 33, 263)          # KENTA, ORION, KELLY, MAXIM, Tháp Đồng Hồ
PLACE = "Quanh Tháp Đồng Hồ (Đảo Quân Sự) — quảng trường trước tháp, ban ngày nắng"
ENV = {"FEATURE_SKILL_DOSSIER": "1", "FEATURE_SEEDANCE_REF_GROUPS": "0", "FEATURE_END_FRAMES": "0", "FEATURE_STORYBOARD_API": "0",
       "FEATURE_SCENE_ESTABLISHING": "0", "FEATURE_PLACE_RENDER_REFS": "0", "FEATURE_LOCATION_PLATES": "0", "FEATURE_LIP_SYNC": "0",
       "FEATURE_DIALOGUE_TAKE": "0"}
SHOTS = [
    {"shot_no": 1, "size": "WS", "angle": "eye", "camera_move": "static", "duration_s": 5.0, "characters": ["KENTA", "ORION"],
     "skill_phase": "KENTA:prepare",                          # the first frame: Kenta ready, Orion still a man (no sphere yet)
     "skill_phase_video": "KENTA:prepare>wind_fly; ORION:activate>drain",
     "image_prompt": ("Wide shot at eye level from behind and a little to the right: Kenta stands on the stone plaza on the left of the frame, "
                      "his back to the camera, facing a white bumpy gloo wall about eight metres ahead of him, a translucent turquoise "
                      "hologram blade in his right hand; Orion stands about four metres to Kenta's right, also facing the wall side, "
                      "relaxed, arms loose; the clock tower and red-roof houses in the background; nobody else"),
     "motion": ("Kenta releases his skill toward the gloo wall. At the same moment Orion, standing apart on the right, turns into his red "
                "sphere where he stands. No enemy is near Orion, so no red cord comes out of the sphere. The two skills stay apart and "
                "never touch. The camera stays still.")},
    {"shot_no": 2, "size": "WS", "angle": "eye", "camera_move": "static", "duration_s": 5.0, "characters": ["KELLY", "KENTA", "MAXIM"],
     "image_prompt": ("Wide shot at eye level on the stone plaza in front of the clock tower: Kenta stands on the left in the foreground, "
                      "Maxim on the right a few metres further back, Kelly further back between them near a low wall; all three are fully "
                      "visible, each clearly apart, facing each other in a loose triangle"),
     "motion": ("Kelly walks a few steps toward the camera and stops; Kenta and Maxim turn their heads to watch her. Everyone stays in their "
                "own place. The camera stays still."),
     "whitebox": {"spot": "plaza_front", "people": [{"name": "KENTA", "at": [7.0, -1.6], "face": "MAXIM"},
                                                   {"name": "MAXIM", "at": [10.5, 1.8], "face": "KENTA"},
                                                   {"name": "KELLY", "at": [13.0, -4.5], "to": [11.5, -3.8], "face": "camera"}]}},
]


def _p():
    from tools.experiments.group_test import load_env
    load_env(os.getcwd())
    os.environ.update(ENV)
    from core.db import connect
    from core.pipeline import Pipeline
    return Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))


DATA = os.path.join("data", "projects")


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


def setup(p):
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return
    pid = p.create_project(NAME, created_by="claude-code-s10", game="FF", aspect="9:16")
    p.set_project_field(pid, "shot_mode", "per_shot")
    p.set_project_field(pid, "look", "FF_INGAME")
    p.set_project_field(pid, "image_model", "gpt-image-2.5-sunburst")      # takes the turnaround sheets without copying them
    p.set_project_field(pid, "model_priority", "quality")
    for aid in ASSETS:
        p.conn.execute("INSERT OR IGNORE INTO project_assets (project_id, asset_id) VALUES (?, ?)", (pid, aid))
    for n, d in enumerate(SHOTS, 1):
        sid = p.create_scene(pid, n, f"Shot {n}")
        data = {k: v for k, v in d.items() if k not in ("motion", "whitebox")}
        data.update(story_scene=n, sequence=n, location=PLACE, shot=f"S{n}·1")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
    p.conn.commit()
    print("dự án thử:", pid)


def frames(p, pid, shots):
    from core.adapters import factory
    from core.runner import ImageRunner
    rows = [r for r in rows_of(p, pid) if r["data"]["shot_no"] in shots]
    todo = [r for r in rows if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state NOT IN "
                                                  "('failed','rejected','cancelled')", (r["id"],)).fetchone()]
    guard(p, pid, 0.052 * len(todo), "khung đầu")
    for r in todo:
        p.create_job(r["id"], "image_gen")
    runner = ImageRunner(p, factory.image_provider(), DATA)
    ids = {r["id"] for r in rows}
    t0 = time.time()
    while time.time() - t0 < 1800:
        runner.submit_pending(pid)
        runner.poll_once(pid)
        states = {r["id"]: r["state"] for r in p.conn.execute("SELECT scene_id id, state FROM jobs WHERE project_id=? AND type='image_gen' "
                                                              "ORDER BY id", (pid,)) if r["id"] in ids}
        print(time.strftime("%H:%M:%S"), states, flush=True)
        if states and all(s in ("succeeded", "approved", "pending_review", "failed", "escalated") for s in states.values()):
            break
        time.sleep(15)
    for r in p.conn.execute("SELECT id, scene_id, state FROM jobs WHERE project_id=? AND type='image_gen' ORDER BY id", (pid,)):
        print(r["scene_id"], r["id"], r["state"], os.path.join(DATA, str(pid), "images", f"job_{r['id']}.png"))
    print("đã chi:", spent(p, pid))


def approve(p, pid, shots):
    for r in rows_of(p, pid):
        if r["data"]["shot_no"] in shots:
            j = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN ('succeeded','pending_review') "
                               "ORDER BY id DESC LIMIT 1", (r["id"],)).fetchone()
            if j:
                p.approve(j["id"], "user", "[thử tự động] người dùng duyệt các bài thử 30/09 — Claude xem ảnh trước khi duyệt")
                print("duyệt shot", r["data"]["shot_no"], "job", j["id"])


def _ready_for_video(p, pid, row):
    """The shot as the video step sees it: the video skill phases, and an approved motion prompt (hand-written, no Claude)."""
    spec = SHOTS[row["data"]["shot_no"] - 1]
    data = dict(row["data"])
    if spec.get("skill_phase_video"):
        data["skill_phase"] = spec["skill_phase_video"]
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row["id"]))
    p.conn.execute("DELETE FROM motion_prompts WHERE scene_id=?", (row["id"],))
    p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, camera, duration_sec, negative_prompt, state) "
                   "VALUES (?,?,?,?,?, 'approved')", (row["id"], spec["motion"], "static", float(spec["duration_s"]), ""))
    p.conn.commit()


def plan(p, pid, shot):
    from core import model_router
    from core.providers import MockVideoProvider
    from core.runner import VideoRunner
    row = next(r for r in rows_of(p, pid) if r["data"]["shot_no"] == shot)
    _ready_for_video(p, pid, row)
    print("model:", model_router.scene_choice(p.conn, row["id"]))
    vr = VideoRunner(p, MockVideoProvider(), DATA)
    job = {"id": -1, "scene_id": row["id"], "project_id": pid, "retry_reason": None, "type": "video_gen"}
    kw = vr._submit_kwargs(job)
    args = vr._submit_args(job)
    print("ẢNH:", [os.path.basename(x) for x in kw.get("reference_only") or []])
    print("VIDEO:", [os.path.basename(v["path"]) for v in kw.get("reference_video") or []])
    print("GIÂY:", args[3], "MODEL:", args[4])
    print(args[1])


def video(p, pid, shot):
    from core import cost
    from core.adapters import factory
    from core.runner import VideoRunner
    row = next(r for r in rows_of(p, pid) if r["data"]["shot_no"] == shot)
    _ready_for_video(p, pid, row)
    usd = cost.clip_price(cost.load_pricing(), "dreamina-seedance-2-5-260628", "720p", 5) * 1.25
    guard(p, pid, usd, f"clip shot {shot}")
    if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state NOT IN ('failed','rejected','cancelled')",
                          (row["id"],)).fetchone():
        p.create_job(row["id"], "video_gen")
    vr = VideoRunner(p, factory.video_provider(), DATA)
    t0 = time.time()
    while time.time() - t0 < 2400:
        vr.submit_pending(pid)
        vr.poll_once(pid)
        st = [dict(r) for r in p.conn.execute("SELECT id, state FROM jobs WHERE scene_id=? AND type='video_gen' ORDER BY id", (row["id"],))]
        print(time.strftime("%H:%M:%S"), st, flush=True)
        if st and st[-1]["state"] in ("succeeded", "approved", "pending_review", "failed", "escalated"):
            break
        time.sleep(30)
    for r in p.conn.execute("SELECT d.severity, d.code, d.message FROM diag_events d WHERE d.scene_id=? ORDER BY d.id DESC LIMIT 6", (row["id"],)):
        print("chẩn đoán:", dict(r))
    print("đã chi:", spent(p, pid))


def t5(p, pid):
    """T5: the first frame with all three drawn + a coarse white model locking where each stands (core/whitebox, official 粗粒度白模)."""
    from core import budget, cost, formats, location_pack, looks, seedance_refs, shots, whitebox
    from core.adapters import factory
    from core.cost import record_usage
    from core.providers import ProviderError
    row = next(r for r in rows_of(p, pid) if r["data"]["shot_no"] == 2)
    spec = SHOTS[1]
    first = shots.approved_image_path(p.conn, DATA, pid, row["id"])
    if not first:
        raise SystemExit("shot 2 chưa có khung đầu đã duyệt")
    m3d = location_pack.model3d(p.conn, 263)
    wb = spec["whitebox"]
    anim = whitebox.plan(m3d, wb["spot"], wb["people"], seconds=4.0, name="t5_whitebox")
    out = os.path.join(DATA, str(pid), "whitebox")
    os.makedirs(out, exist_ok=True)
    mp4 = os.path.join(out, "t5_whitebox.mp4")
    if not os.path.exists(mp4):
        mp4 = whitebox.render(m3d, anim, out)
    people = seedance_refs.identity_pictures(p.conn, pid, [row], 8)
    lines = ["[Asset roles]", "@Image 1 is the first frame. It sets the place, where each person stands and faces, their poses, and the camera."]
    for k, (n, _) in enumerate(people, 2):
        lines.append(f"@Image {k} is {n}: use only {n}'s face, hair and clothes; not its background.")
    lines.append("The people never swap faces, hair, clothes, places or actions.")
    lines.append(whitebox.role_line(anim, 1))
    look = looks.video_sentence(p.project(pid))
    prompt = "\n".join(lines) + "\n[Event] " + (look + " " if look else "") + spec["motion"]
    print(prompt)
    usd = cost.clip_price(cost.load_pricing(), "dreamina-seedance-2-5-260628", "720p", 5) * 1.25
    guard(p, pid, usd, "T5")
    provider = factory.video_provider()
    aspect = formats.spec(formats.project_aspect(p.project(pid)) or "9:16")["clip"]
    with budget.SPEND_LOCK:
        over = budget.check_video(p.conn, provider.name, "dreamina-seedance-2-5-260628", "720p", 5)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        try:
            ext = provider.submit(first, prompt, None, 5, "seedance-2.5", aspect_ratio=aspect, resolution="720p",
                                  reference_only=[first] + [path for _, path in people],
                                  reference_video=[{"path": mp4, "refer_type": "feature"}])
        except ProviderError as e:
            raise SystemExit(f"ClipAI từ chối: [{e.code}] {e}")
        record_usage(p.conn, None, "video", provider.name, "dreamina-seedance-2-5-260628", "720p", 5, "second", pid)
    print("đã gửi:", ext)
    t0 = time.time()
    dest = os.path.join(DATA, str(pid), "videos", "t5.mp4")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    while time.time() - t0 < 2400:
        st = provider.status(ext)
        print(time.strftime("%H:%M:%S"), st.state, flush=True)
        if st.state == "succeeded":
            provider.download(ext, dest)
            print("tải về:", dest)
            break
        if st.state == "failed":
            print("thất bại:", getattr(st, "message", ""))
            break
        time.sleep(30)
    print("đã chi:", spent(p, pid))


T6_KEYS = [os.path.join("data", "projects", "11", "images", "job_470.png"),
           r"D:\AI-Video-Output\2026-09-30_tai_san_toi_uu\t6_ground_rings_2.png",
           r"D:\AI-Video-Output\2026-09-30_tai_san_toi_uu\t6_wind_fly_1.png"]


def t6(p, pid):
    """T6: the phases in order as keyframes (official Seedance 2.5 多关键帧顺序控制: "以@图片1至@图片N的顺序作为关键帧") — T1 swapped two
    phases; drawn keyframes fix the order, the skill video still carries the motion."""
    from core import budget, cost, formats, looks, skill_dossier
    from core.adapters import factory
    from core.cost import record_usage
    from core.providers import ProviderError
    d = skill_dossier.load("KENTA")
    front = os.path.join("data", "assets", "24", "7.png")
    sheet = os.path.join(d["_dir"], d["skill_sheet"])
    video_path = os.path.join(d["_dir"], d["video_ref"]["release"])
    for f in T6_KEYS + [front, sheet, video_path]:
        if not os.path.exists(f):
            raise SystemExit("thiếu: " + f)
    look = looks.video_sentence(p.project(pid))
    prompt = "\n".join([
        "Use @Image 1 to @Image 3 in this order as keyframes.",
        "@Image 1 is the first frame. It sets the dirt path, the wooden houses, the clock tower, the white gloo wall, Kenta standing with his "
        "back to the camera, his pose, and the fixed camera.",
        "@Image 2 is the second keyframe: the blade has been swept, thin see-through circles lie on the ground around his planted feet and the "
        "first crescent arc of wind is leaving at shoulder height.",
        "@Image 3 is the third keyframe: crescent arcs of wind are halfway to the gloo wall at shoulder height.",
        "@Image 4 is KENTA: use only his face, hair and clothes; not its background.",
        "@Image 5 shows the phases of KENTA's skill in order, left to right (numbered panels): use only the skill effect's shape, colour and "
        "transparency; not the panels, the numbers, the people, the place or the camera.",
        "@Video 1 is used only for KENTA's skill effect: its shape, colour, transparency, order and rhythm. Do not take the person, clothes, "
        "place, camera or on-screen text of @Video 1.",
        "The picture goes through the states of @Image 1, @Image 2 and @Image 3 in this order, with continuous motion between them; the "
        "keyframes are states to reach, not still pauses.",
        "[Event] " + (look + " " if look else "") + "Kenta sweeps the translucent hologram blade once; a faint see-through whirlwind wraps his "
        "body for an instant, sinks into rings on the ground, and crescent arcs of wind fly straight to the gloo wall, which stays whole. His "
        "feet do not move; his katana stays in its scabbard across the back of his waist. The camera stays still."])
    print(prompt)
    usd = cost.clip_price(cost.load_pricing(), "dreamina-seedance-2-5-260628", "720p", 5) * 1.25
    guard(p, pid, usd, "T6")
    provider = factory.video_provider()
    aspect = formats.spec(formats.project_aspect(p.project(pid)) or "9:16")["clip"]
    with budget.SPEND_LOCK:
        over = budget.check_video(p.conn, provider.name, "dreamina-seedance-2-5-260628", "720p", 5)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        try:
            ext = provider.submit(T6_KEYS[0], prompt, None, 5, "seedance-2.5", aspect_ratio=aspect, resolution="720p",
                                  reference_only=T6_KEYS + [front, sheet], reference_video=[{"path": video_path, "refer_type": "feature"}])
        except ProviderError as e:
            raise SystemExit(f"ClipAI từ chối: [{e.code}] {e}")
        record_usage(p.conn, None, "video", provider.name, "dreamina-seedance-2-5-260628", "720p", 5, "second", pid)
    print("đã gửi:", ext)
    dest = os.path.join(DATA, str(pid), "videos", "t6.mp4")
    t0 = time.time()
    while time.time() - t0 < 2400:
        st = provider.status(ext)
        print(time.strftime("%H:%M:%S"), st.state, flush=True)
        if st.state == "succeeded":
            provider.download(ext, dest)
            print("tải về:", dest)
            break
        if st.state == "failed":
            print("thất bại:", getattr(st, "message", ""))
            break
        time.sleep(30)
    print("đã chi:", spent(p, pid))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int)
    ap.add_argument("step", choices=("setup", "frames", "approve", "plan", "video", "t5", "t6"))
    ap.add_argument("shots", nargs="?", default="1")
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    a = ap.parse_args()
    script_cap.require(a, "skill_multi_test").start()
    p = _p()
    shots = {int(x) for x in a.shots.split(",") if x}
    if a.step == "setup":
        setup(p)
    elif a.step == "frames":
        frames(p, a.project, shots)
    elif a.step == "approve":
        approve(p, a.project, shots)
    elif a.step == "t6":
        t6(p, a.project)
    elif a.step == "t5":
        t5(p, a.project)
    elif a.step == "plan":
        plan(p, a.project, min(shots))
    else:
        video(p, a.project, min(shots))


if __name__ == "__main__":
    main()
