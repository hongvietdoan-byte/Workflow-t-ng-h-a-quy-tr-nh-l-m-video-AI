"""Tạo dự án OB55 "Mèo nhảy tập 2" (0 USD): 2 con rối (TÍM nhảy, ĐỎ ngồi cầm điện thoại quay) theo video TikTok 2 con mèo
phông xanh, nền Cổng Trời thế giới song song (Kho 265 + 450), 1 shot 12,6 s = trọn ref (ref là MỘT cú máy tĩnh, không cắt cảnh).
Cách làm theo tools/experiments/ob55_con_roi_create.py (#33); tái dùng ảnh mẫu con rối đã duyệt Kho 452 (ĐỎ) / 454 (TÍM).
Chạy từ D:/AI-Video-Pipeline:  PYTHONUTF8=1 py <this> --tiktok <file mp4 tải về>"""
import argparse, json, os, shutil, sqlite3, subprocess, sys
sys.path.insert(0, os.getcwd())
from core.pipeline import Pipeline
from core import assets, llm_io, llm_provider

ap = argparse.ArgumentParser()
ap.add_argument("--tiktok", required=True)
args = ap.parse_args()
SRC = r"D:/2026/OB55/Halloween/Duong Tay/clip nhảy"
ME = "hongviet.doan@garena.vn"
DUR = 12.6                                    # ref 12,60 s (tiếng 12,585 s), 129 BPM

conn = sqlite3.connect("data/manifest.sqlite"); conn.row_factory = sqlite3.Row
p = Pipeline(conn)
pid = p.create_project("OB55 Halloween — Mèo nhảy tập 2: con rối nhảy theo 2 con mèo (Cổng Trời thế giới song song)", created_by=ME,
                       aspect="9:16", genre="SHORT_FORM", model_priority="balanced", game="FF")
for f, v in (("look", "FF_INGAME"), ("image_model", "gpt-image-2.5-sunburst"), ("shot_mode", "per_shot"), ("test_quality", 1)):
    p.set_project_field(pid, f, v)
conn.execute("UPDATE projects SET paused=1 WHERE id=?", (pid,)); conn.commit()   # cổng ảnh / video do người dùng mở
llm_provider.set_project_provider(conn, pid, "claude_cli")    # bỏ Anthropic API (quyết định 19/10); lỗi A2 tập 1
print("PROJECT", pid)

base = os.path.join("data", "projects", str(pid))
src_dir = os.path.join(base, "source"); mref = os.path.join(base, "motion_ref")
os.makedirs(src_dir, exist_ok=True); os.makedirs(mref, exist_ok=True)
for f in ("video ref nhảy tập 2.mp4", "các màu.png"):
    shutil.copy2(os.path.join(SRC, f), os.path.join(src_dir, f))
shutil.copy2(args.tiktok, os.path.join(src_dir, "tiktok_baloosilly_7683219461792337183.mp4"))   # bản 1080p, có nhạc dùng khi dựng

# Kho: ảnh mẫu đã duyệt ở #33 (ĐỎ 452, TÍM 454) + Cổng Trời (3D 265, trời/không khí 450) + Trời thế giới song song 428
for a in (452, 454, 265, 450, 428):
    assets.attach(conn, pid, a)

src_chars = {r["name"]: r for r in conn.execute("SELECT * FROM characters WHERE project_id=33 AND name IN ('RỐI TÍM','RỐI ĐỎ A')")}
CAST = [("RỐI TÍM", src_chars["RỐI TÍM"], 454), ("RỐI ĐỎ", src_chars["RỐI ĐỎ A"], 452)]
for name, row, aid in CAST:
    llm_io.add_character(p, pid, name, row["description"], wardrobe=row["wardrobe"])
    conn.execute("UPDATE characters SET lock_rules=? WHERE project_id=? AND name=?", (row["lock_rules"], pid, name))
    assets.set_character_link(conn, pid, name, aid)
conn.commit()

# video ref: trọn clip TikTok, h264 720x1280 30 fps, SAR 1:1 (phông xanh giữ nguyên — prompt cấm lấy nền)
ref = os.path.join(mref, f"shot_1_meo_0.00-{DUR:.2f}.mp4")
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", args.tiktok, "-t", str(DUR),
                "-vf", "scale=720:1280,fps=30,setsar=1", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", ref],
               check=True)

LOOK = src_chars["RỐI TÍM"]["description"].split("(cùng hình dáng ảnh góc). ", 1)[1].split("; colour variant", 1)[0]
BG = ("in the grass clearing at the centre of the hedge maze at Cổng Trời: tall trimmed dark-green hedges on dark stone base walls around the "
      "clearing, grey paved stone paths, tall dark trees beyond; behind the hedges the villa — a two-storey building with pale blue-grey walls, "
      "columns and an orange-red clay-tile roof with three dormer windows — exactly as in the 3D render picture")
SKY = ("PARALLEL WORLD night at Cổng Trời, matching the in-game look: thick dark purple-grey storm clouds fill the sky above a deep navy-blue "
       "horizon; inside the clouds looms ONE giant dark shadow ghost figure — a dark head with two small glowing white eyes and two huge hands "
       "raised as if pressed against glass — faint and smoky, part of the sky (no vortex, no red lightning). Everything stays clearly readable — "
       "a dim, desaturated blue-grey night, never pitch black")
LOCK = ("BACKGROUND LOCK: the PLACE render picture decides the hedges, paths and villa exactly, in the same places; the Cổng Trời sky picture "
        "decides only the sky and the light. Do NOT add a green screen, a plain studio backdrop, a room, a clock tower or a floating car")
STRINGS = ("Each puppet hangs from its own floating cross-shaped control bar by thin taut strings; the bar tilts, bobs and swings with each move "
           "as if moved by an invisible puppeteer, the strings pulling the head, hands and knees")
COMP = ("Vertical 9:16 layout kept for the edit: both puppets with full bodies in the middle band of the frame (their feet about two-thirds of "
        "the way down); the top fifth of the frame is open night sky with the ghost figure (room for a caption) and the bottom quarter is plain "
        "empty grass and paved stone in front of them (room for an overlay) — nothing important in those two bands")
IMG = ("eye-level wide shot of two chibi marionette puppets in the same place: RỐI TÍM (purple) frame-left of centre, standing and dancing, "
       "full body facing the camera, both wooden arms flung straight out to the sides, one knee lifted, head tilted; RỐI ĐỎ (red) frame-right, "
       "sitting upright on the grass turned three-quarters toward RỐI TÍM, holding a black smartphone in a blue case up in both wooden hands "
       "in front of its face, filming RỐI TÍM")
ACT = ("RỐI TÍM nhảy y hệt mèo cam trong ref theo từng nhịp (129 BPM): 0–0,5 s dang tay chữ T → 0,5–3,8 s nhảy lò cò, đá chân, đấm tay lùi "
       "sang trái → 3,8–4,7 s nghiêng người nhảy ngang → 5–9 s dang tay lắc hông qua lại, sát lại RỐI ĐỎ → 9–10 s vẫy tay, bước → 10,5 s giơ "
       "cao hai tay → 11–12,6 s nhún nảy, hai tay lên mặt, xoay hông kết. RỐI ĐỎ ngồi suốt clip, hai tay giơ điện thoại quay RỐI TÍM, xoay "
       "máy theo bạn, nhún nhẹ (như mèo xám).")
MOTION = ("ROI TIM (purple) and ROI DO (red): chibi marionette puppets exactly as in the reference pictures (very short cute chibi body about "
          "1.8 heads tall: big head, tiny torso, short stubby legs), colours fixed (purple / red accents, no other colour). ROI TIM dances "
          "exactly the moves of the dancer on the left of the reference video, beat by beat: hops and kicks with boxing arms, a sideways lean "
          "and hop, side-to-side sways with both arms out, a wave, both arms thrown up high near the end, then bouncy hands-to-face moves and a "
          "hip twist to finish. ROI DO copies the filmer on the right of the reference video: it stays sitting on the grass the whole clip, "
          "holding the black smartphone up in both hands and filming ROI TIM, turning the phone to follow it, with small bobs on the beat. "
          "The animals in the reference video only give the motion, the positions and the camera — never take their fur, faces or the green "
          "screen. Fast, continuous motion the whole clip: the dancer never freezes or holds a pose longer than half a second. "
          f"{STRINGS}; feet touch the ground and push off it. Camera: locked static eye-level as in the reference, tiny handheld sway only. "
          "The clip starts exactly on the first image. Background (fixed, do not change): the grass clearing at the centre of the hedge maze "
          "at Cong Troi with dark hedges on stone base walls and the pale villa with the orange-red tile roof behind, exactly as in the first "
          "image; parallel-world night sky with dark purple-grey storm clouds and the faint giant shadow ghost figure with white eyes and two "
          "hands in the clouds. Keep the same hedges and villa in every frame; never turn into another place, never show a green background.")

sid = p.create_scene(pid, 1, "CẢNH 1 - ĐÊM, THẾ GIỚI SONG SONG, TRUNG TÂM MÊ CUNG CỔNG TRỜI · shot 1 — RỐI TÍM nhảy, RỐI ĐỎ ngồi cầm điện thoại quay")
data = {
    "location": "Cổng Trời — trung tâm mê cung, thế giới song song", "time": "night", "weather": "fog",
    "mood": "vui nhộn, khoe khoang (meme 'cốt var cực mạnh'), năng lượng nhảy cao",
    "lighting": "đêm thế giới song song Cổng Trời: ánh xanh xám dịu từ trời mây giông tím xám; tối nhưng nhìn rõ, không đen kịt",
    "location_asset": 265, "story_scene": 1, "shot_no": 1, "sequence": 1, "characters": [c[0] for c in CAST],
    "image_prompt": (f"Free Fire in-game 3D render, vertical frame, {IMG}; each puppet: {LOOK}. They are {BG}. {SKY}. {LOCK}. {COMP}. "
                     "stylized proportions, moderate texture detail, clear gameplay lighting, everything in focus, not a movie still, no text"),
    "shot": "WS, eye, static", "size": "WS", "angle": "eye", "camera_move": "static",
    "role": "payoff", "action": ACT, "text": ACT, "end_state": None, "continuous_with_next": False, "dialogue": [],
    "on_screen_text": [],      # chữ 2 dòng chèn ở HẬU KỲ (như #33), không cho model ảnh/video vẽ chữ
    "duration_s": DUR, "camera_complexity": "simple", "shot_role": "hero",
    "plate_spot": "trung_tam_me_cung",
    "plate_view": {"background": "landmark", "why": "thấy biệt thự mái ngói đỏ cam sau hàng rào (đúng ảnh Kho 450/2) — một cú máy tĩnh như ref"},
    "video_route": "single",
    "performance": {"intensity": 4, "body": "fast continuous puppet dance (purple) + seated filming with a phone (red), strings driving the limbs",
                    "timing": "on every beat of the reference video (129 BPM), no pause", "eyes": "red eyes; the filmer looks at its phone screen"},
    "sound": {"music": "in", "why": "nhạc gốc video TikTok phủ cả clip (cách #22/#33)"},
    "why": f"bám trọn video ref 0–{DUR:.2f} s: MỘT cú máy tĩnh, mèo cam trái nhảy, mèo xám phải ngồi cầm điện thoại quay",
    "_user_locked": ["characters", "image_prompt", "video_route", "plate_spot", "plate_view", "duration_s"],
}
conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, camera, duration_sec, negative_prompt, state, ref_video_path, ref_video_type, video_model)"
             " VALUES (?,?,?,?,?,?,?,?,?)",
             (sid, MOTION, "Locked static eye-level, tiny handheld sway.", DUR,
              "no frozen poses, no strings breaking, no cats, no fur, no green screen, no studio backdrop, no text, no pitch-black night, no rain",
              "pending", ref, "feature", "seedance-2.5"))
conn.commit()
print("SCENE", sid, "REF", ref)
