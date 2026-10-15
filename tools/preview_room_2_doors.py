"""Dựng + render xem thử "Phòng 2 cánh cửa" (tools/build_room_2_doors.py) — 0 USD, Blender trên máy (bản Store qua core.plates3d).

    py tools/preview_room_2_doors.py <thư mục ra> [--skip-build] [--engine auto|eevee|cycles]

1) Blender chạy build_room_2_doors.py -> <ra>/glb/phong_2_cua_{A,B,C}.glb (giữ lượt Blender chung: plates3d.blender_turn).
2) Render 9:16 qua ĐÚNG tools/render_plates.py của dây chuyền (đêm, máy trong nhà = INDOOR của chỗ đứng): A từ mọi chỗ đứng,
   B và C từ `goc_nhin_kelly_2_cua` + `can_cua_1`; máy POV = 'at' cao mắt 1,55 m nhìn 'view' ống 16 mm; các chỗ khác = plate_camera.camera_for (MS).
3) plate_env.finish_plate (lớp màu đêm có đèn thật) -> <ra>/<trạng thái>_<chỗ>.png + ảnh tổng hợp <ra>/tong_hop.png.
"""
import importlib.util
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import plate_camera, plate_env, plates3d  # noqa: E402

_spec = importlib.util.spec_from_file_location("room2", os.path.join(ROOT, "tools", "build_room_2_doors.py"))
room = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(room)

RES = (720, 1280)
POV_LENS = 20.0
KELLY_SIZE = {"kelly_giua_phong": "WS"}       # cỡ WS mới thấy cả 2 cửa sau lưng Kelly (MS chỉ 1 cửa + góc phòng)


def cameras_for(spots):
    out = []
    for name in spots:
        sp = room.SPOTS[name]
        if name == "goc_nhin_kelly_2_cua":
            cam = {"name": name, "location": [sp["at"][0], sp["at"][1], room.POV_EYE_M], "look_at": list(sp["view"]),
                   "lens": POV_LENS, "angle": "eye_level"}
        else:
            cam = dict(plate_camera.camera_for({"size": KELLY_SIZE.get(name, "MS")}, sp["at"], sp["facing"], 1.7, RES[0] / RES[1], name=name)["camera"])
        cam["indoor"] = dict(room.INDOOR)
        # đèn bàn thật (đèn trong .glb bị render_plates bỏ) — giống practical_lights lamp warm mà shot đêm sẽ thêm
        x0, x1, y0, y1 = room.FURNITURE["ban_den"]
        cam["lights"] = [{"type": "POINT", "location": [(x0 + x1) / 2, (y0 + y1) / 2, 1.0], "color": [1.0, 0.62, 0.32],
                          "energy": 80, "size": 0.15}]
        cam["model_coords"] = True
        out.append(cam)
    return out


def build(glb_dir):
    blender = plates3d.find_blender()
    if not blender:
        raise SystemExit("không tìm thấy Blender")
    os.makedirs(glb_dir, exist_ok=True)
    args = ["-b", "--factory-startup", "-P", os.path.join(ROOT, "tools", "build_room_2_doors.py"), "--", glb_dir]
    with plates3d.blender_turn(owner="phong_2_cua_build"):
        if blender.startswith(plates3d.STORE):
            proc = plates3d._run_in_store(blender, args, glb_dir, 900)
        else:
            import subprocess
            proc = subprocess.run([blender] + args, capture_output=True, text=True, timeout=900)
    with open(os.path.join(glb_dir, "build.log"), "w", encoding="utf-8") as f:
        f.write(proc.stdout or "")
    missing = [s["file"] for s in room.STATES.values() if not os.path.exists(os.path.join(glb_dir, s["file"]))]
    if proc.returncode != 0 or missing:
        tail = "\n".join((proc.stdout or "").strip().splitlines()[-15:])
        raise SystemExit(f"dựng lỗi (mã {proc.returncode}, thiếu {missing}):\n{tail}")


def render_state(key, glb_dir, out, spots, engine):
    benv = plate_env.blender_env({"time": "night", "weather": "clear"})
    work = os.path.join(out, f"_render_{key}")
    shutil.rmtree(work, ignore_errors=True)
    cfg = plates3d.plan(os.path.join(glb_dir, room.STATES[key]["file"]), work, sky=benv["sky"], sun_elevation=benv["sun_elevation"],
                        sun_azimuth=benv["sun_azimuth"], sky_extra=benv["sky_extra"], resolution=RES, engine=engine, samples=32,
                        cameras=cameras_for(spots), only_cameras=True, ground=False)
    cfg["owner"] = "phong_2_cua_preview"
    man = plates3d.render(cfg)
    env = {"time": "night", "weather": "clear", "practical": True}
    made = {}
    for item in man.get("plates") or man.get("cameras") or []:
        raw = os.path.join(work, item["file"])
        dst = os.path.join(out, f"{key}_{item['name']}.png")
        plate_env.finish_plate(raw, dst, env)
        made[item["name"]] = dst
    with open(os.path.join(work, "manifest_short.json"), "w", encoding="utf-8") as f:
        json.dump({"engine": man.get("engine"), "warnings": man.get("warnings"), "made": made}, f, ensure_ascii=False, indent=1)
    return made, man


def contact_sheet(tiles, path, cell=(360, 640)):
    from PIL import Image, ImageDraw, ImageFont
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    pad, lab = 8, 34
    sheet = Image.new("RGB", (cols * (cell[0] + pad) + pad, rows * (cell[1] + lab + pad) + pad), (18, 18, 20))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    for i, (label, p) in enumerate(tiles):
        c, r = i % cols, i // cols
        x, y = pad + c * (cell[0] + pad), pad + r * (cell[1] + lab + pad)
        with Image.open(p) as im:
            sheet.paste(im.convert("RGB").resize(cell), (x, y + lab))
        draw.text((x + 4, y + 8), label, fill=(235, 235, 235), font=font)
    sheet.save(path)
    return path


def main(argv):
    out = os.path.abspath(argv[0])
    engine = argv[argv.index("--engine") + 1] if "--engine" in argv else "auto"
    glb_dir = os.path.join(out, "glb")
    if "--skip-build" not in argv:
        build(glb_dir)
    all_spots = list(room.SPOTS)
    plan = {"A": all_spots, "B": [room.DEFAULT_SPOT, "can_cua_1"], "C": [room.DEFAULT_SPOT, "can_cua_1"]}
    tiles = []
    for key, spots in plan.items():
        made, man = render_state(key, glb_dir, out, spots, engine)
        print(key, man.get("engine"), made, man.get("warnings"))
        for s in spots:
            if s in made:
                tiles.append((f"{key} · {s}", made[s]))
    print(contact_sheet(tiles, os.path.join(out, "tong_hop.png")))


if __name__ == "__main__":
    main(sys.argv[1:])
