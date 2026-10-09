"""V4 #24 (Sân khấu 3D v2): áp góc máy đã duyệt (9/9) + dàn cảnh mới shot 4–7 (người dùng chốt 09/10) vào kịch bản trong CSDL.

  py tools/experiments/stage_v2_p24/apply_v4.py --db D:/AI-Video-Pipeline/data/manifest.sqlite            # chạy khô: in thay đổi
  py tools/experiments/stage_v2_p24/apply_v4.py --db … --apply                                          # sao lưu rồi ghi

- Mọi shot: `stage_camera` (máy model coords từ data/projects/24/stage_v2/v2.json) — chỉ có tác dụng khi bật cờ `stage_camera`.
- Shot 2: cỡ WS (bộ giải: MS quá chặt). Shot 4–7: cỡ / góc / chuyển động / blocking / image_prompt / motion theo quyết định 09/10
  (4 sau lưng-chéo Kelly ngã ngửa; 5 máy sát đất yêu nữ bám mép gần; 6–7 góc nhìn Kelly bò lùi, máy lùi + rung nhẹ). Trường đã sửa
  được giữ trong `_user_locked` (người dùng quyết → Director về sau không ghi đè). 0 USD; không vẽ gì.
"""
import argparse
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
from core import stage_grid as sg  # noqa: E402

STAGE_DIR = os.path.join(os.path.dirname(ROOT) if ".claude" in ROOT else ROOT, "data", "projects", "24", "stage_v2")
TAIL = "foggy plaza at night, cold moonlight, stylized proportions, moderate texture detail, clear gameplay lighting, everything in focus"
# 10/10 QC: "black-skinned … red tips" ra mặt người da sẫm có mũi + tóc gần đen (shot 5) → câu theo mô tả Kho 418 (người dùng: trang phục
# ma nữ chui khỏi giếng không chuẩn)
CREATURE1 = ("a female creature whose face is a smooth featureless pure-black mask with only two glowing red eyes (no nose, no mouth, no "
             "skin features), long messy black hair whose lower half turns bright red, an off-shoulder torn white dress with a jagged hem "
             "and a red sash at the waist, black arms covered in dark thorny veins with red claws, black stockings fading to red down the "
             "legs, red high heels, constant red glitch noise around her wrists and ankles")

EDITS = {
    2: {"size": "WS"},
    4: {"size": "WS", "angle": "low", "camera_move": "static",
        "action": "Kelly giật mình ngã NGỬA ra sau, xa giếng, hai tay chống xuống đất phía sau, mắt vẫn dán vào miệng giếng (nhìn từ sau lưng hơi chéo)",
        "blocking": ("From behind Kelly, slightly diagonal, camera low near the ground about 1 m behind her: Kelly frame-left seen from "
                     "behind / three-quarter back, just fallen backward onto the ground away from the well, hands braced behind her, eyes "
                     "on the well; the eight-sided stone well looming ahead center-right"),
        "image_prompt": ("Wide shot from behind Kelly, slightly diagonal, low camera close to the ground, Free Fire in-game 3D render style. "
                         "Kelly in her yellow-white-black tracksuit with black spiked choker and short dark bob on the left of the frame seen "
                         "from behind, just fallen backward onto the stone ground away from an ancient eight-sided stone well, upper body "
                         "tipped back, both hands braced on the ground behind her, head turned toward the well; the well looming ahead in "
                         "the center-right of the frame, clean weathered grey stone rim, its dark mouth facing us, " + TAIL),
        "motion_en": {"action": ("KELLY flinches and falls backward away from the well, her hands bracing on the ground behind her, eyes "
                                 "fixed on the well's opening ahead; static low camera behind her")}},
    5: {"size": "MS", "angle": "low", "camera_move": "static",
        "action": "Máy sát đất trước mép gần của giếng: yêu nữ dạng 1 thò tay bám mép giếng, nhô đầu lên rồi trườn qua thành giếng về phía máy",
        "blocking": ("Low camera near the ground (0.5 m) just in front of the well's near rim, looking slightly up at it: the creature's "
                     "clawed hands grip the near rim, her head and shoulders rise over it and she starts to slide over the stone toward "
                     "the camera; Kelly is behind the camera, not in frame"),
        "image_prompt": ("Medium shot, low camera close to the ground in front of the near side of an ancient eight-sided stone well, "
                         "looking slightly up at its rim, Free Fire in-game 3D render style, clawed veined black hands gripping the near "
                         "rim, " + CREATURE1 + ", rising over the rim toward the camera, her head and shoulders above the clean weathered "
                         "stone lip, the rest of her body still inside the well, " + TAIL),
        "motion_en": {"action": ("the demoness in form 1 grips the near rim of the well with clawed hands, her head rises over the edge and "
                                 "she drags her body over the stone toward the camera; static low camera")}},
    6: {"size": "MS", "angle": "low", "camera_move": "pull_out",
        "action": "Góc nhìn Kelly ngồi bệt: yêu nữ trườn ra khỏi giếng, bò về phía cô; Kelly sợ bò lùi → máy lùi chậm ~1 m, rung nhẹ",
        "blocking": ("POV of Kelly sitting on the ground (eye height 0.93 m), looking slightly down toward the well: the creature has slid "
                     "out over the rim and crawls on all fours toward the camera, the well right behind her"),
        "image_prompt": ("Point-of-view shot from Kelly's eyes as she sits on the ground, looking slightly down, Free Fire in-game 3D render "
                         "style, " + CREATURE1 + ", crawling on all fours over the stone ground toward the camera, just out of an ancient "
                         "eight-sided stone well right behind her, " + TAIL),
        "motion_en": {"action": ("the demoness crawls on all fours toward KELLY over the stone ground; point of view of KELLY: the camera "
                                 "slowly dollies back about 1 m with a slight handheld shake as KELLY crawls backward in fear"),
                      "end_state": ("the creature still crawling toward the camera, smaller in the center of the frame, the whole well "
                                    "visible behind her")},
        "end_state": "the creature still crawling toward Kelly, smaller in the center of the frame, the whole well visible behind her"},
    7: {"size": "MLS", "angle": "low", "camera_move": "pull_out",
        "action": ("Góc nhìn Kelly (đã lùi thêm): yêu nữ đứng dậy trước giếng, quay đầu nhìn thẳng Kelly rồi biến hình dạng 1 → dạng 2; "
                   "Kelly tiếp tục bò lùi → máy lùi ~1 m, rung nhẹ"),
        "blocking": ("POV of Kelly sitting on the ground, now 1 m farther back, looking slightly up: the creature rises to stand right in "
                     "front of the well, turns her head to stare at Kelly (the camera), red glitch noise intensifying over her as she "
                     "transforms"),
        "image_prompt": ("Point-of-view shot from Kelly's eyes low on the ground, looking slightly up, Free Fire in-game 3D render style, "
                         "the faceless dark female creature standing in front of an ancient eight-sided stone well in the center of the "
                         "frame, turning her head to stare straight at the camera, engulfed in flickering red digital glitch noise "
                         "mid-transformation, shifting from black-haired tattered-white-dress form into white-haired red-tipped comic-style "
                         "crosshatch form, " + TAIL),
        "motion_en": {"action": ("the demoness stands upright in front of the well, slowly turns her head to stare at KELLY (the camera), "
                                 "then transforms from form 1 to form 2, glitch effect sweeping over her entire body; point of view of "
                                 "KELLY: the camera keeps dollying back about 1 m with a slight handheld shake"),
                      "end_state": ("the figure now in form 2: white hair with red tips, black face with round red eyes, crosshatch "
                                    "linework visible, full body in the center of the frame with the well behind her")}},
}
LOCK = ("size", "angle", "camera_move", "action", "blocking", "image_prompt", "motion_en", "end_state")


def stage_cameras(stage_dir):
    st = json.load(open(os.path.join(stage_dir, "stage.json"), encoding="utf-8"))
    v2 = json.load(open(os.path.join(stage_dir, "v2.json"), encoding="utf-8"))
    out = {}
    for s in v2["shots"]:
        b = s["best"]
        if not b or not b["ok"]:
            raise SystemExit(f"shot {s['shot']}: phương án chưa đạt — không áp")
        m, sp = b["m"], s["spec"]
        cam = {"location": [round(v, 3) for v in sg.model_from_rel(st, m["at"])],
               "look_at": [round(v, 3) for v in sg.model_from_rel(st, m["aim"])], "lens": m["lens"],
               "source": f"Sân khấu 3D v2 #24 shot {s['shot']} ({b['tag']}), duyệt 09/10", "cell": m["cell"]}
        w = (s.get("objs") or {}).get("gieng")
        if w:                                                   # khối giếng thay thế trong nền (mô hình 3D không có giếng) — 10/10
            cam["props"] = [{"kind": "well", "at": [round(v, 3) for v in sg.model_from_rel(st, [w["xy"][0], w["xy"][1], w.get("z", 0.0)])],
                             "radius": w["r"], "height": w["h"], "hollow": True, "sides": 8, "tone": "da_toi"}]
        if sp.get("pov"):
            cam["pov"] = sp["pov"]
        if sp.get("may") and b.get("end"):
            e = b["end"]["m"]
            cam["move"] = {"kieu": sp["may"]["kieu"], "m": sp["may"]["m"], "rung": sp["may"].get("rung"),
                           "end_location": [round(v, 3) for v in sg.model_from_rel(st, e["at"])],
                           "end_look_at": [round(v, 3) for v in sg.model_from_rel(st, e["aim"])]}
        out[s["shot"]] = cam
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--stage-dir", default=STAGE_DIR)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    cams = stage_cameras(a.stage_dir)
    conn = sqlite3.connect(a.db if a.apply else f"file:{os.path.abspath(a.db)}?mode=ro", uri=not a.apply)
    rows = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=24 ORDER BY idx").fetchall()
    backup, new = {}, {}
    for sid, idx, data in rows:
        d = json.loads(data)
        backup[sid] = d
        nd = dict(d, stage_camera=cams[idx])
        ed = EDITS.get(idx, {})
        for k, v in ed.items():
            nd[k] = dict(d.get(k) or {}, **v) if k == "motion_en" and isinstance(d.get(k), dict) else v
        if ed:
            nd["_user_locked"] = sorted(set(d.get("_user_locked") or []) | {k for k in ed if k in LOCK})
        new[sid] = nd
        ch = [k for k in nd if nd.get(k) != d.get(k)]
        print(f"shot {idx}: đổi {ch} · máy ô {cams[idx]['cell']} {cams[idx]['location']}"
              + (f" · {cams[idx].get('pov') and 'POV'} {cams[idx].get('move', {}).get('kieu', '')}" if cams[idx].get("pov") else ""))
    if not a.apply:
        print("(chạy khô — thêm --apply để sao lưu + ghi)")
        return
    bfile = os.path.join(a.stage_dir, f"scenes_backup_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(bfile, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=1)
    for sid, nd in new.items():
        conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(nd, ensure_ascii=False), sid))
    conn.commit()
    print(f"đã ghi {len(new)} shot; sao lưu: {bfile}")


if __name__ == "__main__":
    main()
