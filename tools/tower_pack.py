"""Standard picture set + camera-move videos of a 3D place (kế hoạch sau #8, S5.1 + S5.6 — người dùng 2026-09-29: "tự làm bộ ảnh bối
cảnh chuẩn kèm video từ file 3D của Tháp").

    py tools/tower_pack.py [--asset 263] [--out DIR] [--test] [--no-night] [--no-video]

#8's tower frames came out as stacked terraces (lỗi 1.4): the only references were renders taken right at the tower's foot. This set is
taken where a person stands: every measured flat spot of the model (location_pack spots, eye height 1.6 m) looking at the tower, a few
reverse views (the plaza without the tower), day and night; plus three camera moves (walk in, arc round the tower, crane up), each as a
textured video and a white-model (clay) video — the reference Seedance 2.5 takes for movement and layout (ClipAI Update Log 16/09).
0 USD: Blender on this computer. Output: plates (png) + depth + mp4 + contact sheet; nothing is written to the Kho until a person approves."""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import plates3d  # noqa: E402
from core.ffmpeg_studio import find_ffmpeg  # noqa: E402

EYE = 1.6
RES = (720, 1280)                         # 9:16, the projects' frame
# spots checked by eye on the first render (29/09): these two lie UNDER the upper plaza (a covered yard) — looking up at the tower the
# camera saw a concrete ceiling. Người dùng 29/09: keep them — the character stands on the ground below, the camera at eye level, level
# (never tilted up into the ceiling), and a few directions give different uses (looking out towards the tower side, into the yard, across).
COVERED = {"lower_yard", "level_22_4"}
COVER_CAM_M = 4.0                         # camera this far from the character's spot
FIGURE_M = 1.7                            # height of the person drawn on the check copy


def covered_cameras(m3d):
    """The covered spots: the character on the ground of the spot, the camera COVER_CAM_M away at eye height, looking level at the
    character's chest. Directions: 'ra' (camera behind the character, background = the side towards the tower), 'vao' (the reverse),
    'ngang' (across). Each keeps where the character stands (`spot`) so a check copy can draw a 1.7 m figure there."""
    ax, ay, _ = m3d["anchor"]
    out = []
    for name in sorted(COVERED):
        if name not in m3d["spots"]:
            continue
        x, y, z = m3d["spots"][name]["at"]
        dx, dy = ax - x, ay - y
        n = max(math.hypot(dx, dy), 1e-6)
        ux, uy = dx / n, dy / n                                    # towards the tower, on the ground plane
        for tag, (cx, cy) in (("ra", (-ux, -uy)), ("vao", (ux, uy)), ("ngang", (-uy, ux))):
            out.append({"name": f"eye_{name}_{tag}", "location": [x + cx * COVER_CAM_M, y + cy * COVER_CAM_M, z + EYE],
                        "look_at": [x, y, z + 1.3], "lens": 35, "model_coords": True, "angle": "eye_level",
                        "spot": [x, y, z]})
    return out


def spots_of(asset_id: int, db: str):
    import sqlite3
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    prof = json.loads(c.execute("SELECT profile FROM assets WHERE id=?", (asset_id,)).fetchone()["profile"] or "{}")
    return prof["model3d"]


def cameras(m3d):
    ax, ay, az = m3d["anchor"]
    out = []
    for name, s in m3d["spots"].items():
        if name in COVERED or s.get("indoor"):                          # a room does not see the landmark
            continue
        x, y, z = s["at"]
        eye = z + EYE
        dist = math.hypot(x - ax, y - ay)
        out.append({"name": f"eye_{name}_thap", "location": [x, y, eye], "look_at": [ax, ay, max(eye + 2.0, az - 3.5)], "lens": 28 if dist < 20 else 35,
                    "model_coords": True, "angle": "eye_level"})
    # reverse views: the plaza / houses / sea behind the camera line — from the default spot and the next two spots (29/09: the names
    # used to be the FFXN model's own; the official export has other spots)
    others = [n for n in m3d["spots"] if n != m3d.get("default_spot") and n not in COVERED and not m3d["spots"][n].get("indoor")][:2]
    for name in [m3d.get("default_spot", "plaza_front")] + others:
        if name in m3d["spots"]:
            x, y, z = m3d["spots"][name]["at"]
            dx, dy = x - ax, y - ay
            k = 20.0 / max(math.hypot(dx, dy), 1e-6)
            out.append({"name": f"eye_{name}_nguoc", "location": [x, y, z + EYE], "look_at": [x + dx * k, y + dy * k, z + EYE - 0.5],
                        "lens": 28, "model_coords": True, "angle": "eye_level"})
    out += indoor_cameras(m3d)
    for name, s in m3d["spots"].items():                             # surroundings (29/09): the view this spot was chosen for
        if s.get("view") and not s.get("indoor"):
            x, y, z = s["at"]
            out.append({"name": f"eye_{name}_canh", "location": [x, y, z + EYE], "look_at": list(s["view"]), "lens": 28,
                        "model_coords": True, "angle": "eye_level"})
    return out + covered_cameras(m3d)


def indoor_cameras(m3d):
    """Rooms (29/09, user: "bổ sung cả những góc cảnh trong nhà"): `_trong` looks into the room, `_ra` out through its door / window;
    wide lens, the spot's own brighter view + fill lamp (render_plates camera.indoor)."""
    out = []
    for name, s in m3d["spots"].items():
        if not s.get("indoor"):
            continue
        x, y, z = s["at"]
        for tag, target, lens, light in (("trong", s.get("view"), 18, s["indoor"]),
                                         ("ra", s.get("view_out"), 22, dict(s["indoor"], exposure=max(float(s["indoor"].get("exposure", 1.5)) - 0.5, 0)))):
            if target:
                out.append({"name": f"eye_{name}_{tag}", "location": [x, y, z + EYE], "look_at": list(target), "lens": lens,
                            "model_coords": True, "angle": "eye_level", "indoor": light})
    return out


def animations(m3d, white: bool):
    ax, ay, az = m3d["anchor"]
    sp = m3d["spots"]
    front = sp.get(m3d.get("default_spot")) or sp.get("plaza_front") or next(iter(sp.values()))
    fx, fy, fz = front["at"]
    ux, uy, uz = sp.get("level_26_0", front)["at"]
    tower_mid = [ax, ay, az - 1.5]                    # heights from the anchor (FFXN: anchor 33,5 → 32 / 34 / 36 as before)
    r = math.hypot(fx - ax, fy - ay) + 1.0
    base = math.atan2(fy - ay, fx - ax)
    orbit = [{"t": i / 4, "location": [ax + r * math.cos(base + math.radians(-60 + 30 * i)), ay + r * math.sin(base + math.radians(-60 + 30 * i)),
                                       fz + EYE], "look_at": tower_mid} for i in range(5)]
    tag = "_white" if white else ""
    # walk in on ONE floor: the first try went from the lower yard (22,4 m) up to the plaza (26 m) in a straight line and passed
    # through the retaining wall for 1,5 s — the start is now further out on the upper plaza itself
    dx, dy = ux - ax, uy - ay
    k = 6.0 / max(math.hypot(dx, dy), 1e-6)
    start = [ux + dx * k, uy + dy * k, uz + EYE]
    return [
        {"name": "di_bo_vao" + tag, "seconds": 6, "fps": 24, "model_coords": True, "white": white, "lens": 28,
         "keys": [{"t": 0, "location": start, "look_at": tower_mid}, {"t": 0.5, "location": [ux, uy, uz + EYE], "look_at": tower_mid},
                  {"t": 1, "location": [fx, fy, fz + EYE], "look_at": [ax, ay, az + 0.5]}]},
        {"name": "vong_quanh_thap" + tag, "seconds": 6, "fps": 24, "model_coords": True, "white": white, "lens": 28, "keys": orbit},
        {"name": "can_cau_len" + tag, "seconds": 5, "fps": 24, "model_coords": True, "white": white, "lens": 28,
         "keys": [{"t": 0, "location": [fx, fy, fz + EYE], "look_at": tower_mid}, {"t": 1, "location": [fx, fy + 4, fz + 12.0],
                                                                                    "look_at": [ax, ay, az + 2.5]}]},
    ]


def to_mp4(folder: str, fps: int, dst: str) -> str:
    subprocess.run([find_ffmpeg(), "-y", "-v", "error", "-framerate", str(fps), "-i", os.path.join(folder, "f_%04d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", dst], check=True, capture_output=True)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", type=int, default=263)
    ap.add_argument("--db", default=r"D:\AI-Video-Pipeline\data\manifest.sqlite")
    ap.add_argument("--out", default=r"D:\AI-Video-Output\2026-09-29_bo-boi-canh-thap-dong-ho")
    ap.add_argument("--test", action="store_true", help="one still + 12 frames: measure the speed first")
    ap.add_argument("--no-night", action="store_true")
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--only-video", default="", help="render just these videos (comma list of names, e.g. di_bo_vao), no stills")
    ap.add_argument("--only-covered", action="store_true", help="just the covered spots' views (day + night), no video")
    ap.add_argument("--only-indoor", action="store_true", help="just the rooms' views (day + night), no video")
    a = ap.parse_args()
    if a.only_video:
        a.no_night = True
    if a.only_covered or a.only_indoor:
        a.no_video = True
    m3d = spots_of(a.asset, a.db)
    os.makedirs(a.out, exist_ok=True)
    day = dict((m3d.get("light") or {}).get("day") or {})           # the place's own daylight look (official FF export 29/09)
    passes = [("ngay", {"sun_elevation": day.pop("sun_elevation", 35), "sun_azimuth": m3d.get("sun_azimuth", 250.0)}, day or None)]
    if not a.no_night and not a.test:
        passes.append(("dem", {"sun_elevation": 20, "sun_azimuth": 60.0},
                       {"strength": 0.04, "sun_strength": 0.5, "sun_color": [0.55, 0.65, 1.0], "exposure": -0.3}))
    report = {"asset": a.asset, "passes": []}
    for tag, sun, extra in passes:
        cams = cameras(m3d)[:1] if a.test or a.only_video else (covered_cameras(m3d) if a.only_covered else
                                                              indoor_cameras(m3d) if a.only_indoor else cameras(m3d))
        cfg = plates3d.plan(m3d["path"], os.path.join(a.out, "_render_" + tag), sky="A", sun_elevation=sun["sun_elevation"],
                            sun_azimuth=sun["sun_azimuth"], resolution=RES, cameras=cams, only_cameras=True, sky_extra=extra,
                            real_height_m=m3d.get("real_height_m"), samples=16)
        if tag == "ngay" and not a.no_video:
            anims = animations(m3d, False) + animations(m3d, True)
            if a.test:
                anims = [dict(anims[0], seconds=0.5)]
            if a.only_video:
                want = {x.strip() for x in a.only_video.split(",")}
                anims = [x for x in anims if x["name"].replace("_white", "") in want]
            cfg["animations"] = anims
        man = plates3d.render(cfg, timeout=4 * 3600)
        for p in ([] if a.only_video else man["plates"]):
            shutil.copyfile(os.path.join(cfg["out_dir"], p["file"]), os.path.join(a.out, f"{tag}_{p['name']}.png"))
        vids = []
        for an in man.get("animations") or []:
            dst = os.path.join(a.out, f"{tag}_{an['name']}.mp4")
            to_mp4(os.path.join(cfg["out_dir"], an["folder"]), an["fps"], dst)
            vids.append({"file": os.path.basename(dst), "frames": an["frames"], "render_sec": an["render_sec"], "white": an["white"]})
        report["passes"].append({"pass": tag, "engine": man.get("engine"), "total_sec": man.get("total_sec"),
                                 "plates": [{"file": f"{tag}_{p['name']}.png", "render_sec": p["render_sec"]} for p in man["plates"]],
                                 "videos": vids, "warnings": man.get("warnings")})
    if a.only_covered:
        report["covered_spots"] = {c["name"]: {"spot": c["spot"], "camera": c["location"]} for c in covered_cameras(m3d)}
    with open(os.path.join(a.out, "report_video.json" if a.only_video else ("report_covered.json" if a.only_covered else
                                                                           "report_indoor.json" if a.only_indoor else "report.json")),
              "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
