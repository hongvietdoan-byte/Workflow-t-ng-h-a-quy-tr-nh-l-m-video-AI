r"""Gói bối cảnh (kế hoạch V4 mục 1): gắn mô hình 3D cho một khu vực trong Kho, dò chỗ đứng, xem / render nền theo góc máy các shot.

    py tools/location_pack.py probe  --model "D:\...\x.glb"                       dò mặt phẳng đi được (Blender, miễn phí)
    py tools/location_pack.py register --asset 263 --model "D:\...\x.glb" --anchor 12.68 -31.13 33.5 [--spot tên x y z hướng]
                                                                                   gắn mô hình + chỗ đứng (tự đề xuất từ dò nếu không đưa)
    py tools/location_pack.py plan   --project 6                                     góc máy + ô nhân vật của từng shot (không render)
    py tools/location_pack.py render --project 6                                     render nền còn thiếu (Blender, bộ nhớ đệm dùng chung)
    py tools/location_pack.py topview --project 6 [--out sodo.png]                    sơ đồ máy nhìn từ trên (miễn phí, không Blender)

Không tốn tiền. Ghi CSDL chỉ ở lệnh register (hồ sơ khu vực → mục model3d).
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


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("probe", "register", "plan", "render", "topview"))
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
    conn = connect(a.db)
    if a.cmd == "register":
        spots = {s[0]: {"at": [float(s[1]), float(s[2]), float(s[3])], "facing": float(s[4]), "label": s[0]} for s in (a.spot or [])}
        if a.model and (not spots or a.min_level is not None):
            spots.update(location_pack.propose_spots(run_probe(a.model, a.step), a.anchor, ignore_below_m=a.min_level))
        entry = location_pack.set_model3d(conn, a.asset, a.model, spots, a.default_spot, a.anchor)
        print(json.dumps(entry, ensure_ascii=False, indent=1))
        return
    if a.cmd == "plan":
        for it in location_pack.plan(conn, a.project):
            print(f"shot {it['idx']:>3} · {it['place']} · spot {it['spot']} · {it['env']['time']}/{it['env']['weather']} · "
                  f"cách {it['distance_m']} m · ống {it['camera']['lens']} mm · ô nhân vật {it['subject_box']}"
                  + (f" · ⚠ {it['weather_problem']}" if it["weather_problem"] else ""))
        return
    if a.cmd == "topview":
        res = location_pack.top_view(conn, a.project, a.out or os.path.join(DATA, str(a.project), "plates", "top_view.png"))
        print(f"{res['shots']} shot → {res['path']}" + ("".join(f" · ⚠ shot {x} và {y}: máy hai phía đối diện nhân vật — kiểm lại nếu không phải shot ngược / qua vai"
                                                             for x, y in res["opposite"])))
        return
    idx = location_pack.ensure_plates(conn, a.project, DATA, os.path.dirname(os.path.abspath(DATA)), log=print)
    print(f"{len(idx)} shot có nền 3D → {os.path.join(DATA, str(a.project), 'plates', 'index.json')}")


if __name__ == "__main__":
    main()
