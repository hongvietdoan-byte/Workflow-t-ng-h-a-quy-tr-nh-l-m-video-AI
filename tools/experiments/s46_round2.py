"""S4.6 vòng 2 (người dùng 29/09: "cả 3 mục đều duyệt thử các trường hợp, rút kinh nghiệm cho dự án khác") — trên dự án thử #10.

  1 · dấu đánh dấu ảnh tham chiếu (vòng 1: Seedance 2.0 Fast vẽ dấu chữ thập đỏ lên mặt Kelly) — cùng shot chạy của Kelly, Fast, 3 kiểu dấu
        M_banner   chỉ băng chữ trắng "CHARACTER SHEET REFERENCE", không dấu đỏ
        M_corner   băng chữ + dấu đỏ ở góc ảnh (xa mặt)
        M_none     không đánh dấu (xem bộ lọc người thật có chặn không — bị từ chối lúc tạo thì không mất tiền)
  2 · hiệu ứng kỹ năng Kenta (vòng 1: không model nào tự vẽ vòng gió / vệt gió / vệt chém)
        E_kling_fx       Kling khung đầu ĐÃ VẼ SẴN hiệu ứng
        E_kling_fx_end   Kling khung đầu + khung cuối (vệt gió bay tới tường)
        E_25_timed       Seedance 2.5 tham chiếu + hành động theo mốc giây
        E_fast_fl        Seedance Fast khung đầu + cuối (ảnh không đánh dấu — có thể bị bộ lọc từ chối, không mất tiền)
        E_kling_slash    shot tường: Kling khung đầu (tường trơn) + khung cuối (vệt chém đỏ chéo)
  3 · khớp môi — 3 câu của kịch bản K bản A, 3 người nói
        L_a              (a) mỗi câu một clip cận, Seedance 2.5 + giọng của câu (cách pipeline đang làm)
        L_c_ingame       (c) một clip cả đoạn thoại, Seedance 2.5, track giọng cả đoạn + câu thoại & mốc giây trong prompt, in-game
        L_c_real3d       (c) như trên, phong cách 3D tả thực (mẫu prompt của người dùng)
        L_c_fast         (c) in-game trên Seedance 2.0 Fast (so model)

    py tools/experiments/s46_round2.py setup                 tạo cảnh 2 (hành động) + cảnh 3 (thoại) + giọng nhân vật (miễn phí)
    py tools/experiments/group_test.py --project 10 --scene 2 frames      vẽ khung cảnh 2 (Deepix)
    py tools/experiments/group_test.py --project 10 --scene 3 frames      vẽ khung cảnh 3
    py tools/experiments/s46_round2.py voice                 tạo 3 câu thoại (ClipAI TTS, tính trần âm thanh) + chờ tải
    py tools/experiments/s46_round2.py plan [--cases A,B]    in prompt + giây + giá (không gửi)
    py tools/experiments/s46_round2.py submit [--cases A,B]  gửi (trần + sổ chi); bị từ chối lúc tạo → ghi lại, không gửi lại
    py tools/experiments/group_test.py --project 10 poll     chờ + tải clip

Chạy từ D:\\AI-Video-Pipeline."""
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.experiments import group_test as gt  # noqa: E402

PID = 10
PLACE = "Tháp Đồng Hồ, quảng trường tầng trên, ban ngày"
PLACE_EN = "the upper plaza of the Clock Tower, daytime"
VOICES = {"MAXIM": (72, "voice boy ingame VN"), "KENTA": (69, "voice Hip VN"), "KELLY": (70, "Voice Kelly VN")}
KENTA_TIMED = ("[00:00 - 00:01] a ring of transparent blue-white wind spreads on the stone floor around his feet. "
               "[00:01 - 00:02] his right arm swings the translucent turquoise energy blade from high right down to low left; the katana stays "
               "sheathed at his hip. [00:02 - 00:04] thin transparent wind streaks fly straight forward, low over the ground, and reach the "
               "white gloo wall.")

S2 = [  # cảnh 2: hành động (một storyboard — kiểm luôn lỗi thừa nhân vật đã sửa)
    {"shot_no": 1, "size": "WS", "angle": "eye", "camera_move": "tracking", "duration_s": 4.0, "characters": ["KELLY"],
     "action": "Kelly sprints across the plaza toward a white gloo wall, hair streaming back, then brakes hard right in front of it",
     "image_prompt": "Kelly mid-sprint on the stone plaza, one foot pushing off the ground, body leaning forward, hair blown back; "
                     "a white bumpy gloo wall a few meters ahead; the clock tower behind",
     "action_peak": "mid-stride, back foot pushing off, body leaning forward"},
    {"shot_no": 2, "size": "MS", "angle": "eye", "camera_move": "static", "duration_s": 2.0, "characters": ["KENTA"],
     "action": "Kenta swings a translucent turquoise energy blade; a ring of transparent wind spreads around his feet; thin wind "
               "streaks fly straight toward the white gloo wall",
     "image_prompt": "Kenta seen from behind at shoulder height, right arm at the top of a swing holding a translucent turquoise energy "
                     "blade, katana sheathed at his hip; a ring of transparent blue-white wind spreading on the stone floor around his "
                     "feet; a white bumpy gloo wall ahead on the plaza",
     "action_peak": "right arm at the top of the swing, wind ring spreading at his feet"},
    {"shot_no": 3, "size": "MS", "angle": "eye", "camera_move": "static", "duration_s": 2.0, "characters": ["KENTA"],
     "action": "end of the swing: thin wind streaks reach the white gloo wall",
     "image_prompt": "The same view from behind Kenta at shoulder height: his right arm followed through low to the left, the "
                     "translucent turquoise energy blade low, katana sheathed; thin transparent wind streaks flying straight forward low "
                     "over the ground and reaching the white bumpy gloo wall",
     "action_peak": "arm followed through low left, wind streaks reaching the wall"},
    {"shot_no": 4, "size": "MCU", "angle": "eye", "camera_move": "static", "duration_s": 2.0, "characters": ["MAXIM"],
     "action": "the white gloo wall stands; Maxim hides behind it",
     "image_prompt": "A white bumpy gloo wall filling the left two thirds of the frame, smooth unmarked surface; Maxim crouches BEHIND "
                     "the wall on the right, only his head and shoulders above it, hugging a steaming bun",
     "action_peak": "Maxim peeking over the wall, bun held close"},
    {"shot_no": 5, "size": "MCU", "angle": "eye", "camera_move": "static", "duration_s": 2.0, "characters": ["MAXIM"],
     "action": "a long red diagonal slash mark appears across the wall; Maxim flinches",
     "image_prompt": "The same white bumpy gloo wall, still standing, now with one long thin red diagonal slash mark across its surface; "
                     "Maxim crouching behind it on the right flinches, shoulders raised, eyes wide, hugging the steaming bun",
     "action_peak": "Maxim flinching, shoulders raised"},
]
S3 = [  # cảnh 3: thoại (kịch bản K bản A — shot 1 và shot 5)
    {"shot_no": 1, "size": "MCU", "angle": "eye", "camera_move": "static", "duration_s": 4.0, "characters": ["MAXIM"],
     "dialogue": [{"speaker": "MAXIM", "text": "Của anh, không ai lấy được!"}], "lip_sync": "generate",
     "action": "Maxim, crouching behind the white gloo wall, hugs the steaming bun and grins smugly while he speaks",
     "image_prompt": "Medium close-up of Maxim crouching behind a white bumpy gloo wall, hugging a steaming bun, smug grin, face to camera"},
    {"shot_no": 2, "size": "MCU", "angle": "eye", "camera_move": "static", "duration_s": 4.0, "characters": ["KENTA"],
     "dialogue": [{"speaker": "KENTA", "text": "Chia đôi."}], "lip_sync": "generate",
     "action": "Kenta holds up one half of a cleanly cut bun and says it calmly, straight face",
     "image_prompt": "Medium close-up of Kenta facing the camera, calm straight face, holding up one half of a cleanly cut steamed bun"},
    {"shot_no": 3, "size": "MCU", "angle": "eye", "camera_move": "static", "duration_s": 4.0, "characters": ["KELLY"],
     "dialogue": [{"speaker": "KELLY", "text": "…Còn em?"}], "lip_sync": "generate",
     "action": "Kelly, bent over with hands on her knees, catches her breath and looks up to ask",
     "image_prompt": "Medium close-up of Kelly bent over, hands on her knees, out of breath, looking up toward the camera"},
    {"shot_no": 4, "size": "MS", "angle": "eye", "camera_move": "static", "duration_s": 6.0, "characters": ["KELLY", "KENTA", "MAXIM"],
     "action": "the three of them by the white gloo wall after the bun was cut in two",
     "image_prompt": "Medium shot of three people by a white bumpy gloo wall, all faces toward the camera: Kelly on the left bent over "
                     "with hands on her knees, panting; Kenta in the centre standing calm, holding up one half of a cleanly cut steamed "
                     "bun; Maxim on the right crouching behind the low end of the wall, holding the other half of the bun"},
]
TAKE_CAST = [{"name": "MAXIM", "where": "right, crouching behind the low end of the gloo wall", "pose": "holding one half of the bun"},
             {"name": "KENTA", "where": "centre, standing", "pose": "holding up the other half, calm straight face"},
             {"name": "KELLY", "where": "left", "pose": "bent over, hands on her knees, panting"}]
TAKE_BEATS = {0: "Maxim clutches his half, smug", 1: "Kenta lifts his half slightly; Maxim's grin drops",
              2: "Kelly straightens up a little, looking from one half to the other", "end": "Maxim hugs his half closer"}

CASES = ("M_banner", "M_corner", "M_none", "E_kling_fx", "E_kling_fx_end", "E_25_timed", "E_fast_fl", "E_kling_slash",
         "L_a", "L_c_ingame", "L_c_real3d", "L_c_fast")
SCENE_OF = {c: (3 if c.startswith("L_") else 2) for c in CASES}


def _pipeline():
    gt.load_env(os.getcwd())
    from core.db import connect
    from core.pipeline import Pipeline
    return Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite"))), \
        os.environ.get("PIPELINE_DATA") or os.path.join("data", "projects")


def setup():
    from core import voice
    p, _ = _pipeline()
    have = {json.loads(r["data"] or "{}").get("story_scene") for r in p.conn.execute("SELECT data FROM scenes WHERE project_id=?", (PID,))}
    idx = p.conn.execute("SELECT COALESCE(MAX(idx), 0) m FROM scenes WHERE project_id=?", (PID,)).fetchone()["m"]
    for story, shots, title in ((2, S2, "R2 hành động"), (4, S3[:3], "R2 câu thoại"), (3, S3[3:], "R2 thoại")):
        if story in have:
            print("đã có cảnh", story)
            continue
        for d in shots:
            idx += 1
            sid = p.create_scene(PID, idx, f"{title} · shot {d['shot_no']}")
            data = dict(d, story_scene=story, sequence=story, location=PLACE, shot=f"S{story}·{d['shot_no']}")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
    for name, (vid, vname) in VOICES.items():
        if not p.conn.execute("SELECT 1 FROM characters WHERE project_id=? AND name=?", (PID, name)).fetchone():
            p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, ?, ?)", (PID, name, name))
        voice.set_profile(p.conn, PID, name, {"voice_id": vid, "voice_name": vname})
    p.conn.commit()
    print("xong: cảnh 2 (5 shot), cảnh 3 (4 shot), giọng", ", ".join(VOICES))


def rows(p, story):
    return gt.shots_of_scene(p, PID, story)


def cmd_voice():
    from core import audio_lib, voice
    from core.adapters.clipai_audio import ClipAIAudioProvider
    p, data_dir = _pipeline()
    ids = [r["id"] for r in rows(p, 4) if r["data"].get("dialogue")]
    prov = ClipAIAudioProvider.from_env()
    print(voice.generate(p.conn, PID, prov, data_dir, scene_ids=ids))
    d = audio_lib.assets_dir(data_dir, PID)
    for _ in range(40):
        c = audio_lib.refresh(prov, d)
        print(time.strftime("%H:%M:%S"), c, flush=True)
        if not c.get("running"):
            break
        time.sleep(10)
    for e in audio_lib.load(d):
        if e.get("kind") == "tts":
            print(e.get("speaker"), e.get("text"), e["state"], e.get("duration_ms"), e.get("file") or e.get("message"))


def _lines(p, data_dir):
    from core import audio_lib
    items = audio_lib.load(audio_lib.assets_dir(data_dir, PID))
    out = []
    for r in rows(p, 4):
        for e in items:
            if e.get("kind") == "tts" and e.get("scene_id") == r["id"] and e.get("state") == "succeeded":
                out.append({"speaker": e["speaker"], "text": e["text"], "file": e["file"], "duration_ms": e["duration_ms"], "scene_id": r["id"]})
    return out


def _marked(paths, data_dir, style):
    out_dir = os.path.join(data_dir, str(PID), "experiments", "marked")
    return [gt.mark_reference(x, out_dir, style) for x in paths]


def build_case(p, data_dir, case, look):
    """[(label, kwargs, seconds, prompt, model key, tier)] — one or more sends of the case."""
    from core import dialogue_take, ffmpeg_studio, lipsync
    s2, s3 = rows(p, 2), rows(p, 4) + rows(p, 3)   # cảnh 4 = 3 câu thoại (nguồn giọng, không vẽ khung); cảnh 3 = khung cả đoạn
    fr = lambda r: gt.frame_path(p, data_dir, PID, r["id"])  # noqa: E731
    out = []
    if case.startswith("M_"):
        kw, secs, prompt = gt.build(p, data_dir, PID, [s2[0]], "P2", look)
        style = {"M_banner": "banner", "M_corner": "corner_plus", "M_none": "none"}[case]
        kw["reference_only"] = _marked(kw["reference_only"], data_dir, style)
        out.append((case, kw, secs, prompt, "seedance-fast", "720p"))
    elif case == "E_kling_fx":
        kw, secs, prompt = gt.build(p, data_dir, PID, [s2[1]], "S2", look)
        out.append((case, kw, 4, prompt, "kling", "std"))
    elif case in ("E_kling_fx_end", "E_kling_slash"):
        pair = [s2[1], s2[2]] if case == "E_kling_fx_end" else [s2[3], s2[4]]
        kw, secs, prompt = gt.build(p, data_dir, PID, pair, "P4", look.split(" Render style:")[0])
        if case == "E_kling_slash":           # 29/09: the end frame came back mirrored (wall right, Maxim left) — flipped to match
            from PIL import Image, ImageOps
            flipped = os.path.join(data_dir, str(PID), "experiments", "slash_end_flipped.png")
            ImageOps.mirror(Image.open(kw["last_frame"]).convert("RGB")).save(flipped)
            kw["last_frame"] = flipped
        out.append((case, kw, 4, prompt, "kling", "std"))
    elif case == "E_25_timed":
        kw, secs, prompt = gt.build(p, data_dir, PID, [s2[1]], "P2m25", look)
        prompt = prompt + "\nTiming of Shot 1 (whole seconds): " + KENTA_TIMED
        out.append((case, kw, 4, prompt, "seedance-2.5", "720p"))
    elif case == "E_fast_fl":
        if not (fr(s2[1]) and fr(s2[2])):
            raise SystemExit("thiếu ảnh khung shot 2–3 cảnh 2")
        prompt = (look.split(" Render style:")[0] + " One continuous shot, no cut; starts exactly on the first image and ends exactly on "
                  "the last image. " + KENTA_TIMED)
        out.append((case, {"image_path": fr(s2[1]), "last_frame": fr(s2[2])}, 4, prompt, "seedance-fast", "720p"))
    elif case == "L_a":
        ff = ffmpeg_studio.find_ffmpeg()
        for r in s3[:3]:
            kw, secs, prompt = gt.build(p, data_dir, PID, [r], "P2m25", look)
            who = r["data"]["dialogue"][0]["speaker"]
            seg = lipsync.shot_audio(data_dir, PID, r["id"], 4.0, ff) if _lines(p, data_dir) else None
            if seg:
                kw["reference_audio"] = [seg["path"]]
            prompt += (f"\n{who} speaks the Vietnamese line of Audio1 (\"{r['data']['dialogue'][0]['text']}\"): mouth, jaw and teeth in "
                       "sync with every syllable; the mouth closes in the silence before and after.")
            out.append((f"L_a_{who}", kw, 4, prompt, "seedance-2.5", "720p"))
    elif case.startswith("L_c_"):
        style = "real3d" if case == "L_c_real3d" else "ingame"
        lines = _lines(p, data_dir)
        segs = dialogue_take.segments(lines) if lines else dialogue_take.segments(
            [{"speaker": d["dialogue"][0]["speaker"], "text": d["dialogue"][0]["text"], "duration_ms": 1500} for d in (r["data"] for r in s3[:3])])
        from core import assets
        take = s3[3]
        if not fr(take):
            raise SystemExit("thiếu ảnh khung shot 4 cảnh 3 — chạy bước 'frames' cảnh 3 trước")
        links = assets.link_characters(p.conn, PID, [c["name"] for c in TAKE_CAST])
        ids = [links[c["name"]]["ref"]["path"] for c in TAKE_CAST]
        refs = _marked([fr(take)] + ids, data_dir, "eye_plus")
        kw = {"image_path": fr(take), "reference_only": refs}
        if lines:
            track = os.path.join(data_dir, str(PID), "lipsync", "take_s3.wav")
            os.makedirs(os.path.dirname(track), exist_ok=True)
            kw["reference_audio"] = [dialogue_take.mix(segs, _audio_dir(data_dir), track, ffmpeg_studio.find_ffmpeg())]
        prompt = dialogue_take.prompt(TAKE_CAST, segs, style, place=PLACE_EN, beats=TAKE_BEATS)
        model = "seedance-fast" if case == "L_c_fast" else "seedance-2.5"
        out.append((case, kw, dialogue_take.billed_seconds(segs), prompt, model, "720p"))
    return out


def _audio_dir(data_dir):
    from core import audio_lib
    return audio_lib.assets_dir(data_dir, PID)


def cmd_plan(cases):
    from core import budget, cost, looks
    p, data_dir = _pipeline()
    look = (looks.video_sentence(p.project(PID)) + " " + looks.image_sentence(p.project(PID))).strip()
    out = []
    for c in cases:
        try:
            sends = build_case(p, data_dir, c, look)
        except SystemExit as e:
            print(c, "CHƯA ĐỦ ĐẦU VÀO:", e)
            continue
        for label, kw, secs, prompt, model, tier in sends:
            canonical = gt.CANONICAL[model]
            usd = cost.clip_price(cost.load_pricing(), canonical, tier, secs)
            audio = " + giọng" if kw.get("reference_audio") else ""
            print(f"{label}: {gt.CANONICAL[model]} {tier} {secs} s ≈ ${usd:.2f}{audio} ({len(prompt)} ký tự)")
            out.append({"case": c, "label": label, "kw": kw, "seconds": secs, "prompt": prompt, "model": model, "tier": tier,
                        "canonical": canonical, "usd": usd})
    s = budget.status(p.conn)
    print(f"Tổng ≈ ${sum(o['usd'] or 0 for o in out):.2f}; trần còn {s['left']} USD, ảnh {s['images']}/{s['image_cap']}, "
          f"âm thanh {s['audios']}/{s['audio_cap']}")
    return p, data_dir, out


def cmd_submit(cases):
    from core import budget, experiments, formats
    from core.adapters import factory
    from core.cost import record_usage
    from core.providers import ProviderError
    p, data_dir, plan = cmd_plan(cases)
    provider = factory.video_provider()
    aspect = formats.spec(formats.project_aspect(p.project(PID)) or "9:16")["clip"]
    items = experiments.load(data_dir, PID)
    done = {e.get("method") for e in items if e.get("kind") == "group_test"}
    for o in plan:
        if o["label"] in done:
            print("đã gửi trước đó:", o["label"])
            continue
        kw = dict(o["kw"])
        image = kw.pop("image_path")
        extra = {"kling_mode": o["tier"]} if o["model"] == "kling" else {"resolution": o["tier"]}
        story = SCENE_OF[o["case"]]
        entry = {"kind": "group_test", "scene": story, "method": o["label"], "group": 1, "shots": [], "seconds": o["seconds"],
                 "film_s": o["seconds"], "model": o["canonical"], "tier": o["tier"], "usd": o["usd"], "prompt": o["prompt"],
                 "external_id": None, "state": "running", "file": None, "sequence": story, "scenes": [],
                 "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "round": "s46_r2"}
        with budget.SPEND_LOCK:
            over = budget.check_video(p.conn, provider.name, o["canonical"], o["tier"], o["seconds"])
            if over:
                print("TRẦN CHẶN:", over)
                return
            try:
                entry["external_id"] = provider.submit(image, o["prompt"], None, o["seconds"], o["model"], aspect_ratio=aspect,
                                                       **extra, **kw)
                record_usage(p.conn, None, "video", provider.name, o["canonical"], o["tier"], o["seconds"], "second", PID)
            except ProviderError as e:          # refused at creation: nothing billed — a result of the test, not retried
                entry.update(state="failed", message=f"[{e.code}] {e}"[:400], usd=0.0)
        items.append(entry)
        experiments._save(data_dir, PID, items)
        print(o["label"], entry["state"], entry["external_id"] or entry.get("message", "")[:200])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("setup", "voice", "plan", "submit"))
    ap.add_argument("--cases", default=",".join(CASES))
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    a = ap.parse_args()
    script_cap.require(a, "s46_round2").start()
    cases = [c.strip() for c in a.cases.split(",") if c.strip()]
    bad = [c for c in cases if c not in CASES]
    if bad:
        raise SystemExit(f"không có trường hợp: {bad}")
    {"setup": setup, "voice": cmd_voice, "plan": lambda: cmd_plan(cases), "submit": lambda: cmd_submit(cases)}[a.step]()


if __name__ == "__main__":
    main()
