"""S4.6 — A/B hành động (người dùng 29/09: "hành động thì cho phép thử"): 3 shot hành động của kịch bản K bản A "Chia đôi"
(docs/KICH_BAN_KIEM_K1_2026-09-29.md) × 3 cách làm video, mỗi shot một clip:
  P2m    Seedance 2.0 Fast — chỉ ảnh tham chiếu đánh dấu (cách đang dùng ở #8)
  P2m25  Seedance 2.5      — cùng cách gửi, model mới (đọc mốc giây, chuyển động tốt hơn theo tài liệu ClipAI)
  S2     Kling 3.0 Omni    — khung đầu = ảnh storyboard của shot

    py tools/experiments/action_ab.py setup        tạo dự án thử (không tốn tiền, không gọi Claude) — in mã dự án
    py tools/experiments/group_test.py --project N --scene 1 frames                               vẽ 3 khung đầu (Deepix)
    py tools/experiments/group_test.py --project N --scene 1 --single --methods P2m,P2m25,S2 plan    in prompt + giá, không gửi
    py tools/experiments/group_test.py --project N --scene 1 --single --methods P2m,P2m25,S2 submit  gửi (qua trần + sổ chi)
    py tools/experiments/group_test.py --project N poll

Chạy từ D:\\AI-Video-Pipeline. Mỗi shot dài 4 s (Seedance tính tối thiểu 4 s) để ba cách so trên cùng độ dài."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

NAME = "A/B hành động S4.6 · Chia đôi (29/09)"
ASSETS = (23, 377, 33, 263)          # KELLY, Kenta ở OB55, MAXIM, Tháp Đồng Hồ
PLACE = "Tháp Đồng Hồ, quảng trường tầng trên, ban ngày"
SHOTS = [
    {"shot_no": 1, "size": "WS", "angle": "eye", "camera_move": "tracking", "duration_s": 4.0, "characters": ["KELLY"],
     "action": "Kelly sprints across the plaza toward a white gloo wall, hair streaming back, then brakes hard right in front of it",
     "image_prompt": "Kelly mid-sprint on the stone plaza, one foot pushing off the ground, body leaning forward, hair blown back; "
                     "a white bumpy gloo wall a few meters ahead; the clock tower behind",
     "action_peak": "mid-stride, back foot pushing off, body leaning forward"},
    {"shot_no": 2, "size": "MS", "angle": "eye", "camera_move": "static", "duration_s": 4.0, "characters": ["KENTA"],
     "action": "Seen from behind at shoulder height, Kenta swings a translucent turquoise energy blade with his right hand while his "
               "katana stays sheathed at his hip; transparent blue-white wind rings spread on the ground around his feet, then thin "
               "streaks of wind fly straight forward toward the white gloo wall",
     "image_prompt": "Kenta seen from behind at shoulder height, right arm raised holding a translucent turquoise energy blade, katana "
                     "sheathed at his hip, a white gloo wall ahead on the plaza",
     "action_peak": "right arm at the top of the swing, energy blade raised"},
    {"shot_no": 3, "size": "MCU", "angle": "eye", "camera_move": "static", "duration_s": 4.0, "characters": ["MAXIM"],
     "action": "Thin wind streaks pass straight through the white gloo wall; a long red diagonal slash mark appears across the wall's "
               "surface while the wall stays standing; behind it Maxim, crouching and hugging a steamed bun, flinches",
     "image_prompt": "A white bumpy gloo wall in the foreground; Maxim crouching behind it on the side, hugging a steaming bun, looking "
                     "startled",
     "action_peak": "Maxim flinching, shoulders raised"},
]


def setup():
    from core.db import connect
    from core.pipeline import Pipeline
    from tools.experiments.group_test import load_env
    load_env(os.getcwd())
    p = Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return row["id"]
    pid = p.create_project(NAME, created_by="claude-code-s4.6", game="FF", aspect="9:16")
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


if __name__ == "__main__":
    if sys.argv[1:] == ["setup"]:
        setup()
    else:
        print(__doc__)
