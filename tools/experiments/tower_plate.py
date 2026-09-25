"""Thử nghiệm "tháp đồng hồ giống FF 90–100%" (2026-09-25) — KHÔNG phải một bước của pipeline, chỉ để đo.

Ba lệnh:
  render   Blender render mô hình 3D tháp đúng góc máy của một shot (9:16). --sky C = trời trong suốt (để tự vẽ trời đêm).
  plate    1 ảnh Deepix: ảnh render làm NỀN + ảnh chuẩn nhân vật; prompt bảo giữ nguyên kiến trúc, chỉ đổi sang đêm.
           Kết quả lần 1: đỉnh tháp giống (~70%) nhưng model tự phóng to tháp, mất thân + cửa vòm, vẽ lại lan can.
  green    1 ảnh Deepix: nhân vật trên phông xanh #00FF00 (bố cục trung cảnh, ánh trăng lạnh) — để ghép lên nền 3D bằng code
           (tools/experiments/composite_plate.py — CHƯA viết), tháp là pixel thật của mô hình.

Mọi lệnh Deepix đều qua budget.check_image + ghi sổ chi (cost.record_usage, stage=plate_test*). Token chỉ đọc từ env User
(DEEPIX_TOKEN), không in ra. Ví dụ (PowerShell, nạp token như tools/pilot_run):
  py tools/experiments/tower_plate.py render --sky C --sun 30
  py tools/experiments/tower_plate.py green --project 7 --ref "D:/AI-Video-Pipeline/data/assets/23/10.png" --out kelly_green.png
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

DATA = r"D:\AI-Video-Pipeline\data"
MODEL = r"D:\AI-Video-Pipeline\model 3D\free_fire_clocktower_3d_model_by_ffxn.glb"
TOWER = [12.68, -31.13, 33.5]      # tọa độ gốc mô hình: tâm thân tháp Object_14; thân z 25,85–44,65; quảng trường trên z ≈ 25,93
# shot 4 kiểu MS: người đứng ~14 m trước tháp trên quảng trường trên, máy sau lưng người 3–4 m, ngang ngực
CAMERAS = [
    {"name": "shot4_ms", "location": [12.68, -12.5, 25.93 + 1.3], "look_at": TOWER, "lens": 32, "model_coords": True},
    {"name": "shot4_ms_wide", "location": [12.68, -8.0, 25.93 + 1.5], "look_at": TOWER, "lens": 26, "model_coords": True},
]
IMAGE_MODEL = "gpt-image-2.5-sunburst"

PLATE_PROMPT = (
    "Image 1 is the EXACT BACKGROUND of this shot, rendered from the game's 3D model: keep its camera, perspective, the clock tower's "
    "shape, proportions, bricks, windows, belfry and spire, the stone terrace and railings EXACTLY as they are — do not redraw, restyle "
    "or move them. Only change the time to night: deep blue night sky with a few stars and a pale moon, cold moonlight on the stone, "
    "a few warm street lamps glowing on the terrace. Image 2 shows KELLY (identity, hair, yellow tracksuit, black choker — copy exactly). "
    "Place KELLY alone in the foreground centre, medium shot from the waist up, facing the camera, lifting her head with wet eyes as if "
    "about to speak, a single soft cold key light on her face; the tower stands behind her, slightly out of focus. One single frame. "
    "Free Fire in-game 3D character art style, cinematic, no text.")
GREEN_PROMPT = (
    "Image 1 shows KELLY — copy her identity, face, bob hair with bangs, yellow track jacket with white star stripes, white crop top, "
    "black O-ring choker exactly. Vertical 9:16 frame, eye-level camera at chest height. KELLY alone, medium shot from the waist up, "
    "centred, her head top at about 35% from the top of the frame, body filling the lower part of the frame, facing the camera, lifting "
    "her head with wet eyes as if about to speak. Night lighting: cool blue moonlight rim light from the upper left, a soft dim cold key "
    "light on her face, darker overall exposure like a night scene. BACKGROUND: a perfectly flat, uniform pure chroma-key green (#00FF00) "
    "studio backdrop filling everything behind her, no shadows, no gradient, no floor, no objects, no green light spilling on her. "
    "Crisp clean hair edges. Free Fire in-game 3D character art style, one single frame, no text.")


def render(args):
    from core import plates3d
    out = plates3d.out_dir(DATA, f"Tháp Đồng Hồ shot4 {args.sky}")
    cams = [c for c in CAMERAS if not args.camera or c["name"] == args.camera]
    cfg = plates3d.plan(MODEL, out, sky=args.sky, sun_elevation=args.sun, sun_azimuth=250, resolution=(1152, 2048), samples=32,
                        presets=["eye_000"], cameras=cams)      # presets=[] would mean ALL presets
    m = plates3d.render(cfg, plates3d.find_blender(), timeout=1200)
    print(plates3d.summary(m))
    print(m["out_dir"])


def generate(args, prompt, refs, stage):
    from core import budget, cost, db
    from core.adapters.deepix import DeepixImageProvider
    conn = db.connect(os.path.join(DATA, "manifest.sqlite"))
    prov = DeepixImageProvider.from_env()
    over = budget.check_image(conn, prov.name)
    if over:
        sys.exit("DỪNG: " + over)
    task = prov.submit(prompt, refs, size="1152x2048", model=IMAGE_MODEL)
    model, tier = prov.usage_info(IMAGE_MODEL)
    cost.record_usage(conn, None, "image", prov.name, model, tier, 1, "image", project_id=args.project, stage=stage)
    end = time.time() + 300
    while time.time() < end:
        st = prov.status(task)
        if st.state != "running":
            break
        time.sleep(10)
    print(st)
    if st.state == "succeeded":
        dest = os.path.join(DATA, "projects", str(args.project), "plate_test", args.out)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print(prov.download(task, dest))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--sky", default="C", choices=["A", "C"])
    r.add_argument("--sun", type=float, default=30)
    r.add_argument("--camera", default="shot4_ms_wide")
    for name in ("plate", "green"):
        g = sub.add_parser(name)
        g.add_argument("--project", type=int, default=7)
        g.add_argument("--ref", required=True, help="ảnh chuẩn nhân vật")
        g.add_argument("--out", required=True)
        if name == "plate":
            g.add_argument("--plate", required=True, help="ảnh render 3D làm nền")
    args = ap.parse_args()
    if args.cmd == "render":
        render(args)
    elif args.cmd == "plate":
        generate(args, PLATE_PROMPT, [args.plate, args.ref], "plate_test")
    else:
        generate(args, GREEN_PROMPT, [args.ref], "plate_test_green")


if __name__ == "__main__":
    main()
