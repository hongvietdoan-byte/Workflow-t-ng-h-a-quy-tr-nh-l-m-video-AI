"""Tạo dự án OB55 con rối nhảy (0 USD): dự án + Kho ảnh góc + 5 nhân vật + 6 shot + motion + video ref.
Chạy từ D:/AI-Video-Pipeline:  PYTHONUTF8=1 py <this> """
import json, os, shutil, sqlite3, subprocess, sys
sys.path.insert(0, os.getcwd())
from core.pipeline import Pipeline
from core import assets, llm_io

SRC = r"D:/2026/OB55/Halloween/Duong Tay/clip nhảy"
REF = os.path.join(SRC, "video ref nhảy theo.mp4")
ME = "hongviet.doan@garena.vn"

conn = sqlite3.connect("data/manifest.sqlite"); conn.row_factory = sqlite3.Row
p = Pipeline(conn)
pid = p.create_project("OB55 Halloween — Con rối nhảy Tháp đồng hồ (thế giới song song)", created_by=ME,
                       aspect="9:16", genre="SHORT_FORM", model_priority="balanced", game="FF")
for f, v in (("look", "FF_INGAME"), ("image_model", "gpt-image-2.5-sunburst"), ("shot_mode", "per_shot"), ("test_quality", 1)):
    p.set_project_field(pid, f, v)
conn.execute("UPDATE projects SET paused=1 WHERE id=?", (pid,)); conn.commit()   # không cho tự chạy: cổng ảnh/video do người dùng mở
print("PROJECT", pid)

# --- tư liệu: chép vào dự án (đường dẫn tương đối data/projects/<pid>/...)
base = os.path.join("data", "projects", str(pid))
src_dir = os.path.join(base, "source"); mref = os.path.join(base, "motion_ref")
os.makedirs(src_dir, exist_ok=True); os.makedirs(mref, exist_ok=True)
angles = ["góc 1.png", "goc 2.png", "goc 3.png", "góc 4.png", "goc 5.png", "goc 6.png"]
for f in angles + ["các màu.png", "video ref nhảy theo.mp4"]:
    shutil.copy2(os.path.join(SRC, f), os.path.join(src_dir, f))

# --- Kho: ảnh góc in-game của con rối (riêng dự án). Ảnh có viền vàng chọn trong game -> chỉ lấy HÌNH DÁNG.
files = [(f, open(os.path.join(SRC, f), "rb").read()) for f in angles]
rep = assets.add_reference_images(conn, pid, "FF", "character", "CON RỐI OB55 (ảnh góc in-game)", files, shared=False, created_by=ME)
aid = rep["asset_id"]
conn.execute("UPDATE assets SET description=? WHERE id=?", (
    "[OB55 Halloween, 19/10] Con rối chibi treo dây: đầu to, mặt sứ trắng có đường khâu, mắt đỏ phát sáng, tóc to bồng xoăn, thân nhỏ "
    "khớp gỗ trắng (vai/khuỷu/gối tròn), áo ngắn tay tối + quần yếm, chìa vặn dây cót sau lưng; dây mảnh nối lên tay điều khiển gỗ hình "
    "chữ thập (2 thanh dẹt bắt chéo, núm tròn 4 đầu) lơ lửng trên đầu. Ảnh góc có VIỀN VÀNG = hiệu ứng chọn trong game (phủ cả thanh "
    "điều khiển) — không phải màu thân. Biến thể màu (ảnh 'các màu'): màu nhuộm tóc + viền phát sáng + núm/thanh điều khiển.", aid))
conn.commit()
print("KHO", aid, rep)
for a in (263, 428):                     # Tháp Đồng Hồ (map 3D) + Trời thế giới song song
    assets.attach(conn, pid, a)

LOOK = ("chibi marionette puppet doll exactly like the puppet reference pictures (same shape; ignore the yellow in-game selection glow of those "
        "pictures): oversized head, porcelain-white face with thin dark stitch lines, glowing red eyes, big voluminous wavy hair, small body "
        "with white ball-jointed wooden limbs, dark short-sleeve shirt with suspender shorts, wind-up key on its back, thin strings from its "
        "head, hands and knees up to a flat wooden cross-shaped control bar with round knobs on the four ends floating above it")
COL = {"ĐỎ": ("crimson red", "đỏ thẫm"), "XANH LƠ": ("bright cyan", "xanh lơ"), "TÍM": ("violet purple", "tím")}
CAST = [("RỐI ĐỎ A", "ĐỎ"), ("RỐI XANH LƠ A", "XANH LƠ"), ("RỐI TÍM", "TÍM"), ("RỐI XANH LƠ B", "XANH LƠ"), ("RỐI ĐỎ B", "ĐỎ")]
for name, c in CAST:
    en, vi = COL[c]
    llm_io.add_character(p, pid, name,
        f"Con rối chibi treo dây OB55 bản màu {vi} (cùng hình dáng ảnh góc). {LOOK}; colour variant: {en} streaks in the dark hair, "
        f"a soft {en} glowing rim around the whole puppet, {en} knobs and edges on the dark control bar; face stays white, eyes red.",
        wardrobe=f"áo tối + quần yếm, khớp gỗ trắng; điểm màu {vi} ở tóc, viền sáng và tay điều khiển")
    assets.set_character_link(conn, pid, name, aid)

# --- video ref: cắt theo đúng điểm cắt cảnh của clip mèo (ffmpeg scene > 0.12), SAR 1:1, giữ 768x576
SEG = [(0.0, 2.95), (2.96, 6.33), (6.33, 9.54), (9.54, 17.67), (17.67, 25.0), (25.0, 30.07)]
for i, (a, b) in enumerate(SEG, 1):
    out = os.path.join(mref, f"shot_{i}_meo_{a:.2f}-{b:.2f}.mp4")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(a), "-to", str(b), "-i", REF,
                    "-vf", "setsar=1", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", out], check=True)

BG = ("they stand on the paved stone landing at the foot of ONE broad flight of stone steps of the Clock Tower (Tháp Đồng Hồ): the wide "
      "staircase rises straight up behind them with a stone side wall on its right, the tall stone clock tower stands at the top of the stairs "
      "left of centre and the grey gable and slate roof of the house peeks above the right-hand side wall, exactly as in the 3D render picture")
SKY = ("PARALLEL WORLD night (Free Fire OB55 Other World, as the parallel-world sky picture): a huge dark grey storm-cloud vortex covers the sky "
       "above the tower with only a faint dim orange-red glow at its centre; cars, vans and crates float around the tower with faint red light "
       "streaks under them; thin white wind streaks across the sky; the scene is grey-blue and dim but CLEARLY VISIBLE — tower, stairs and house "
       "readable, never pitch black; a small red demon-claw mark on the house roof. No rain, no lightning, no fire")
LOCK = ("BACKGROUND LOCK: the PLACE render picture decides the staircase, side walls, clock tower and house exactly, in the same places; the "
        "parallel-world sky picture decides only the sky and the light. Do NOT add palm trees, grass fields, red-roof houses, a flat open plaza, "
        "the room or curtains of the reference video")
STRINGS = ("Every puppet hangs from its own floating cross-shaped control bar by thin taut strings; the bar tilts, bobs and swings with each "
           "dance move as if moved by an invisible puppeteer, the strings pulling the head, hands and knees; feet touch the stone and push off it")
REFV = ("Dance exactly the moves of the reference video, beat by beat. The cats in the reference video only give the motion, the formation and "
        "the camera — never take their fur, faces, room, curtains or sunlight. Fast, continuous motion the whole clip: nobody freezes or holds "
        "a pose longer than half a second.")

SHOTS = [
 dict(t="toàn từ trên xuống — 5 con rối đứng vòng tròn ngước nhìn lên", chars=[n for n, _ in CAST], size="WS", angle="overhead", move="static",
      dur=2.95, act="Nhìn thẳng từ trên xuống: 5 con rối đứng thành vòng tròn trên thềm đá, ngước mặt nhìn lên máy, đầu lắc lư theo nhịp, tay điều khiển chữ thập lơ lửng ngay dưới máy.",
      img="top-down high-angle wide shot looking straight down on five marionette puppets standing in a loose circle on the paved stone landing, all looking up at the camera, their cross-shaped control bars floating just under the camera above their heads; clockwise from top-left: RỐI ĐỎ A (red), RỐI XANH LƠ A (cyan), RỐI TÍM (purple, centre), RỐI XANH LƠ B (cyan), RỐI ĐỎ B (red)",
      cam="Top-down, almost static, tiny slow rotation."),
 dict(t="máy thấp len giữa nhóm — các con rối nhún lắc quay sang máy", chars=["RỐI ĐỎ A", "RỐI TÍM", "RỐI XANH LƠ A"], size="MS", angle="low", move="push_in",
      dur=3.37, act="Máy thấp lách giữa nhóm: RỐI ĐỎ A tiền cảnh trái, RỐI TÍM giữa quay sang máy, RỐI XANH LƠ A phải; cả nhóm nhún vai lắc đầu theo nhịp, dây kéo tay lên xuống.",
      img="low-angle medium shot from among the group: RỐI ĐỎ A large in the left foreground, RỐI TÍM in the middle turning toward the camera, RỐI XANH LƠ A on the right, all bouncing to the beat; the clock tower rises behind them under the storm vortex",
      cam="Low, slow push-in between the puppets."),
 dict(t="cận RỐI TÍM giơ tay vẫy", chars=["RỐI TÍM"], size="MCU", angle="low", move="static",
      dur=3.21, act="Cận RỐI TÍM: giơ một tay lên vẫy rồi chỉ về máy, đầu nghiêng theo nhịp; thanh điều khiển nghiêng theo tay, dây tay căng lên.",
      img="low-angle medium close-up of RỐI TÍM raising one wooden hand high in a wave, head tilted, its control bar tilted above following the raised hand, string to that hand pulled taut; the clock tower and storm vortex behind",
      cam="Near static, slight handheld sway."),
 dict(t="trung cảnh hàng 3 con rối nhảy đồng đều", chars=["RỐI XANH LƠ A", "RỐI TÍM", "RỐI XANH LƠ B"], size="MS", angle="eye", move="push_in",
      dur=8.13, act="Ba con rối đứng hàng ngang (XANH LƠ A trái, TÍM giữa, XANH LƠ B phải) nhảy đồng đều: dang tay, lắc hông, giậm chân; máy chậm tiến lại rồi lượn nhẹ.",
      img="eye-level medium-wide shot of three marionette puppets in a row dancing in sync — RỐI XANH LƠ A frame-left, RỐI TÍM centre, RỐI XANH LƠ B frame-right — arms swinging out, knees bent, full bodies with feet on the stone landing, control bars above each",
      cam="Slow push-in then a gentle arc to the right."),
 dict(t="cận solo RỐI ĐỎ A → lia nhanh sang RỐI XANH LƠ A dang tay", chars=["RỐI ĐỎ A", "RỐI XANH LƠ A"], size="MCU", angle="eye", move="whip",
      dur=7.33, act="Cận RỐI ĐỎ A nhảy solo (vung tay, xoay vai) ~3,5 s; máy lia nhanh sang RỐI XANH LƠ A đang dang hai tay nhún nhảy toàn thân.",
      img="eye-level medium close-up of RỐI ĐỎ A dancing solo, both wooden arms swinging across its chest, hair bouncing, control bar swinging above; RỐI XANH LƠ A slightly out of frame to the right",
      cam="Follows the red puppet, then a fast whip pan right to the cyan puppet."),
 dict(t="toàn hàng ngang 5 con rối nhảy kết", chars=[n for n, _ in CAST], size="WS", angle="eye", move="pull_out",
      dur=5.07, act="Cả 5 con rối đứng hàng ngang (ĐỎ A, XANH LƠ A, TÍM, XANH LƠ B, ĐỎ B) nhảy đồng đều theo nhịp rồi kết bằng một tư thế chung; máy lùi nhẹ cho thấy cả tháp.",
      img="eye-level wide shot of all five marionette puppets in one row dancing in sync, left to right RỐI ĐỎ A (red), RỐI XANH LƠ A (cyan), RỐI TÍM (purple, centre), RỐI XANH LƠ B (cyan), RỐI ĐỎ B (red), full bodies on the stone landing at the foot of the stairs, five control bars floating above them, the clock tower under the storm vortex behind",
      cam="Slow pull-out revealing the whole tower."),
]

refs = sorted(os.listdir(mref))
for i, s in enumerate(SHOTS, 1):
    sid = p.create_scene(pid, i, f"CẢNH 1 - ĐÊM, THẾ GIỚI SONG SONG, CHÂN CẦU THANG THÁP ĐỒNG HỒ · shot {i} — {s['t']}")
    data = {
        "location": "Chân cầu thang Tháp Đồng Hồ (thế giới song song)", "time": "night", "weather": "cloudy",
        "mood": "ma mị nhưng vui nhộn, năng lượng nhảy cao",
        "lighting": "đêm thế giới song song: ánh xanh xám dịu từ trời mây giông, đốm cam đỏ mờ giữa xoáy mây; tối nhưng nhìn rõ, không đen kịt",
        "location_asset": 263, "story_scene": 1, "shot_no": i, "sequence": 1, "characters": s["chars"],
        "image_prompt": (f"Free Fire in-game 3D render, vertical frame, {s['img']}; each puppet: {LOOK}. {BG}. {SKY}. {LOCK}. "
                         "stylized proportions, moderate texture detail, clear gameplay lighting, everything in focus, not a movie still"),
        "shot": f"{s['size']}, {s['angle']}, {s['move']}", "size": s["size"], "angle": s["angle"], "camera_move": s["move"],
        "role": "setup" if i == 1 else ("payoff" if i == len(SHOTS) else "development"),
        "action": s["act"], "text": s["act"], "end_state": None, "continuous_with_next": False, "dialogue": [], "on_screen_text": [],
        "duration_s": s["dur"], "camera_complexity": "simple", "shot_role": "hero" if i == len(SHOTS) else "normal",
        "plate_spot": "bac_thang_giua",
        "plate_view": {"background": 124, "why": "giống #22: chân cầu thang, tháp đồng hồ bên trái, đầu hồi nhà bên phải — trùng góc ảnh in-game thế giới song song (Kho 428/1); mọi shot nhảy cùng một chỗ đứng"},
        "video_route": "single",
        "performance": {"intensity": 4, "body": "fast continuous puppet dance, jerky-cute marionette bounce, strings driving the limbs",
                        "timing": "on every beat of the reference video, no pause", "eyes": "red eyes toward camera"},
        "sound": {"music": "in", "why": "nhạc gốc của video ref phủ cả clip (cách #22)"},
        "why": f"bám video ref đoạn {SEG[i-1][0]:.2f}–{SEG[i-1][1]:.2f} s (đội hình + góc máy + nhịp)",
        "_user_locked": ["characters", "image_prompt", "video_route", "plate_spot", "plate_view", "duration_s"],
    }
    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
    names = ", ".join(s["chars"])
    motion = (f"{names}: chibi marionette puppets exactly as in the reference pictures, colours fixed (red / cyan / purple accents, no other colour). "
              f"{s['act_en'] if 'act_en' in s else s['img']}. {REFV} {STRINGS}. Camera: {s['cam']} The clip starts exactly on the first image. "
              f"Background (fixed, do not change): {BG}; {SKY}. Keep the same staircase, tower and house in every frame; never turn into another place.")
    conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, camera, duration_sec, negative_prompt, state, ref_video_path, ref_video_type, video_model)"
                 " VALUES (?,?,?,?,?,?,?,?,?)",
                 (sid, motion, s["cam"], s["dur"], "no frozen poses, no strings breaking, no cats, no fur, no curtains, no pitch-black night, no rain",
                  "pending", os.path.join(mref, refs[i-1]), "feature", "seedance-2.5"))
conn.commit()
print("SCENES", len(SHOTS), "refs", refs)
