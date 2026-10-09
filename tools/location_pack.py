r"""Gói bối cảnh (kế hoạch V4 mục 1): gắn mô hình 3D cho một khu vực trong Kho, dò chỗ đứng, xem / render nền theo góc máy các shot.

    py tools/location_pack.py probe  --model "D:\...\x.glb"                       dò mặt phẳng đi được (Blender, miễn phí)
    py tools/location_pack.py register --asset 263 --model "D:\...\asset.fbx" --anchor -217.07 132.04 30 [--spot tên x y z hướng]
                                                                                   gắn mô hình + chỗ đứng (tự đề xuất từ dò nếu không đưa)
    py tools/location_pack.py plan   --project 6                                     góc máy + ô nhân vật của từng shot (không render)
    py tools/location_pack.py render --project 6                                     render nền còn thiếu (Blender, bộ nhớ đệm dùng chung)
    py tools/location_pack.py topview --project 6 [--out sodo.png]                    sơ đồ máy nhìn từ trên (miễn phí, không Blender)
    py tools/location_pack.py script-view --asset 263 --spot-name lower_yard --spot-name level_22_4 [--landmark "the clock tower"]
                                                                                   S5.7: chỗ đứng không có hướng cố định (tùy kịch bản)
    py tools/location_pack.py preview --asset 263 --spot-name lower_yard --view away --time night \
        --lights '[{"kind":"lamp","where":"behind_left","color":"warm","why":"..."}]' --out DIR
                                                                                   S5.7: render thử MỘT nền theo hướng + đèn đã chọn
                                                                                   (đọc CSDL chỉ-đọc, không ghi gì)
    py tools/location_pack.py camera-plan --project 24 [--yes] [--review] [--force]
                                                                                   G0 (cờ director_camera_plan): Đạo diễn lập sơ đồ
                                                                                   cảnh + bộ góc máy; --review: render rồi Đạo diễn
                                                                                   xem render từng góc. Không --yes: chỉ in ước tính

Không tốn tiền. Ghi CSDL chỉ ở lệnh register và script-view (hồ sơ khu vực → mục model3d).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import location_pack, plates3d  # noqa: E402
from core.db import connect  # noqa: E402

DATA = os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))


def run_probe(model: str, step: float) -> dict:
    cfg = plates3d.plan(model, plates3d.out_dir(os.path.dirname(os.path.abspath(DATA)), "probe " + os.path.basename(model)),
                        only_cameras=True, probe={"step": step})
    return plates3d.render(cfg, plates3d.find_blender(), timeout=1800)["probe"]


def run_preview(a) -> dict:
    """S5.7 evidence: one plate of a spot with the direction + lights given on the command line, rendered and finished (sky, grade)
    exactly as a shot's plate is (same plan, same finish). The database is opened read-only."""
    import sqlite3
    from core import plate_camera, plate_choice, plate_env
    uri = "file:" + os.path.abspath(a.db).replace("\\", "/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT profile FROM assets WHERE id=?", (a.asset,)).fetchone()
    entry = (json.loads(row["profile"] or "{}") if row else {}).get("model3d")
    if not entry:
        raise SystemExit(f"khu vực {a.asset} chưa gắn mô hình 3D")
    if a.landmark:
        entry = dict(entry, landmark=a.landmark)
    spot_name = (a.spot_name or [entry.get("default_spot")])[0]
    data = {"size": a.size, "time": a.time, "weather": a.weather, "plate_spot": spot_name}
    if a.view:
        data["plate_view"] = {"background": a.view, "why": a.why}
    if a.lights is not None:
        data["practical_lights"] = json.loads(a.lights)
    sp = location_pack.spot_for(entry, data)
    view = plate_choice.view_of(entry, sp, data)
    env = plate_env.env_of(data)
    lit = plate_choice.lights_of(data, env)
    if view["needs"]:
        return {"needs": view["needs"]}
    res = (720, 1280)
    cam = plate_camera.camera_for(data, sp["at"], view["facing_deg"], 1.75, res[0] / res[1], name="preview")
    camera = dict(cam["camera"], model_coords=True, subject={"location": sp["at"], "height_m": 1.75})
    if lit["lights"]:
        camera["lights"] = plate_choice.light_rigs(lit["lights"], sp["at"], camera["location"], 1.75)
        env = dict(env, practical=True)
    benv = plate_env.blender_env(env, entry.get("sun_azimuth", 250.0))
    out = os.path.abspath(a.out or ".")
    os.makedirs(out, exist_ok=True)
    tag = f"{spot_name}_{(view['view'] or 'mac_dinh').replace(':', '-')}_{env['time']}_{'den' if lit['lights'] else 'khong_den'}"
    cfg = plates3d.plan(entry["path"], os.path.join(out, "_render_" + tag), sky=benv["sky"], sun_elevation=benv["sun_elevation"],
                        sun_azimuth=benv["sun_azimuth"], resolution=res, samples=a.samples, cameras=[camera], only_cameras=True,
                        weather=benv["weather"], sky_extra=benv["sky_extra"], real_height_m=entry.get("real_height_m"))
    man = plates3d.render(cfg, plates3d.find_blender(), timeout=3600)
    p = next((x for x in man.get("plates", []) if x["name"] == "preview"), None)
    if p is None:
        return {"error": "Blender không trả về ảnh", "manifest_error": man.get("error")}
    final = plate_env.finish_plate(os.path.join(man["out_dir"], p["file"]), os.path.join(out, tag + ".png"), env,
                                   depth_path=os.path.join(man["out_dir"], p["depth_file"]) if p.get("depth_file") else None,
                                   depth_range=p.get("depth_range_m"))
    it = {"spot": sp["name"], "view": view, "env": env, "lights": lit["lights"], "lights_decided": lit["decided"]}
    return {"plate": final, "layout_vi": location_pack.layout_words(it), "view_problem": view["problem"],
            "light_problem": lit["problem"], "camera": camera, "render_sec": p.get("render_sec"), "lights_rendered": p.get("lights"),
            "cache_key": location_pack.cache_key(entry, camera, env, res)}


def run_camera_plan(conn, a) -> None:
    """G0: the Director's scene map + camera set-ups (paid: Claude, estimate printed first; runs only with --yes and the flag on)."""
    from core import camera_plan, cost
    if not camera_plan.enabled():
        print("Cờ director_camera_plan đang TẮT — bật ở 🧪 hoặc FEATURE_DIRECTOR_CAMERA_PLAN=1 rồi chạy lại")
        return
    todo = [g for g in camera_plan.groups(conn, a.project)
            if a.force or g["key"] not in camera_plan.load_plans(DATA, a.project)]
    one = cost.llm_estimate(conn, camera_plan.STAGE, 1, images=1)
    look = cost.llm_estimate(conn, camera_plan.REVIEW_STAGE, 1, images=2)
    print(f"{len(todo)} cảnh cần sơ đồ · Claude ≈ {(one or 0) * cost.LLM_MARGIN * len(todo):.3f} USD"
          + (f" · duyệt render ≈ {(look or 0) * cost.LLM_MARGIN:.3f} USD / góc máy (×3 nếu phải sửa 2 vòng)" if a.review else ""))
    if not a.yes:
        print("Chưa chạy (thêm --yes để đồng ý chi tiền)")
        return
    res = camera_plan.before_plates(conn, a.project, DATA, force=a.force, log=print)
    print(json.dumps(res, ensure_ascii=False))
    if a.review:
        root = os.path.dirname(os.path.abspath(DATA))
        location_pack.ensure_plates(conn, a.project, DATA, root, log=print)
        print(json.dumps(camera_plan.after_plates(conn, a.project, DATA, root, log=print), ensure_ascii=False, indent=1))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("probe", "register", "plan", "render", "topview", "script-view", "preview", "camera-plan"))
    ap.add_argument("--yes", action="store_true", help="camera-plan: đồng ý chi tiền Claude (không có: chỉ in ước tính)")
    ap.add_argument("--review", action="store_true", help="camera-plan: render nền rồi Đạo diễn xem render từng góc máy")
    ap.add_argument("--force", action="store_true", help="camera-plan: lập lại sơ đồ dù đã có")
    ap.add_argument("--spot-name", action="append", help="tên chỗ đứng (script-view / preview)")
    ap.add_argument("--off", action="store_true", help="script-view: bỏ đánh dấu")
    ap.add_argument("--landmark", help="tên mốc bằng tiếng Anh cho prompt, vd 'the clock tower'")
    ap.add_argument("--view", help="preview: landmark|away|left|right|spot:<tên>|số độ")
    ap.add_argument("--why", default="", help="preview: lý do hướng máy")
    ap.add_argument("--time", default="day", help="preview: dawn|day|dusk|night")
    ap.add_argument("--weather", default="clear")
    ap.add_argument("--size", default="MS", help="preview: cỡ cảnh (MS, WS, CU…)")
    ap.add_argument("--lights", help="preview: JSON danh sách đèn ([] = không thêm đèn)")
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--fresh-shot", type=int, action="append",
                    help="render: render lại shot số này (idx) dù đã có trong cache — vd sau khi sửa kiểm tia Blender (P24)")
    ap.add_argument("--out")
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--model")
    ap.add_argument("--asset", type=int)
    ap.add_argument("--project", type=int)
    ap.add_argument("--anchor", type=float, nargs=3)
    ap.add_argument("--spot", nargs=5, action="append", metavar=("NAME", "X", "Y", "Z", "FACING"))
    ap.add_argument("--default-spot")
    ap.add_argument("--step", type=float, default=1.5)
    ap.add_argument("--min-level", type=float, help="bỏ các mặt phẳng thấp hơn độ cao này (địa hình xa)")
    a = ap.parse_args()
    if a.cmd == "probe":
        p = run_probe(a.model, a.step)
        print(json.dumps(p["areas"][:15], ensure_ascii=False, indent=1))
        print(json.dumps(location_pack.propose_spots(p, a.anchor, ignore_below_m=a.min_level), ensure_ascii=False, indent=1))
        return
    if a.cmd == "preview":
        print(json.dumps(run_preview(a), ensure_ascii=False, indent=1))
        return
    conn = connect(a.db)
    if a.cmd == "script-view":
        entry = location_pack.set_script_view(conn, a.asset, a.spot_name or [], on=not a.off, landmark=a.landmark)
        print(json.dumps({k: v for k, v in entry["spots"].items() if (k in (a.spot_name or []))}, ensure_ascii=False, indent=1))
        return
    if a.cmd == "register":
        spots = {s[0]: {"at": [float(s[1]), float(s[2]), float(s[3])], "facing": float(s[4]), "label": s[0]} for s in (a.spot or [])}
        if a.model and (not spots or a.min_level is not None):
            spots.update(location_pack.propose_spots(run_probe(a.model, a.step), a.anchor, ignore_below_m=a.min_level))
        entry = location_pack.set_model3d(conn, a.asset, a.model, spots, a.default_spot, a.anchor)
        print(json.dumps(entry, ensure_ascii=False, indent=1))
        return
    if a.cmd == "plan":
        for it in location_pack.plan(conn, a.project):
            print(f"shot {it['idx']:>3} · {it['place']} · {location_pack.layout_words(it)} · "
                  f"cách {it['distance_m']} m · ống {it['camera']['lens']} mm · ô nhân vật {it['subject_box']}"
                  + "".join(f" · ⚠ {it[k]}" for k in ("weather_problem", "spot_problem", "view_problem", "light_problem") if it.get(k))
                  + (f" · ⛔ {it['needs']}" if it.get("needs") else ""))
        return
    if a.cmd == "camera-plan":
        run_camera_plan(conn, a)
        return
    if a.cmd == "topview":
        res = location_pack.top_view(conn, a.project, a.out or os.path.join(DATA, str(a.project), "plates", "top_view.png"))
        print(f"{res['shots']} shot → {res['path']}" + ("".join(f" · ⚠ shot {x} và {y}: máy hai phía đối diện nhân vật — kiểm lại nếu không phải shot ngược / qua vai"
                                                             for x, y in res["opposite"])))
        return
    idx = location_pack.ensure_plates(conn, a.project, DATA, os.path.dirname(os.path.abspath(DATA)), log=print,
                                      fresh=a.fresh_shot or ())
    failed = [k for k, v in idx.items() if v.get("failed")]
    print(f"{len(idx) - len(failed)} shot có nền 3D → {os.path.join(DATA, str(a.project), 'plates', 'index.json')}"
          + (f" · ⚠ {len(failed)} shot Blender không trả về góc máy (vẽ ảnh thường)" if failed else ""))


if __name__ == "__main__":
    main()
