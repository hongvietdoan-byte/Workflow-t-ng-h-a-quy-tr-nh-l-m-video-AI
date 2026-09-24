"""3D place -> empty background plates in the library (GĐ-E0, docs/KE_HOACH_TONG_2026-09-24.md "Dùng bản đồ 3D"; how to test:
docs/HUONG_DAN_3D.md). No AI and no credit: Blender renders on this computer.

  models()        the 3D files in MODEL3D_DIR (default D:\\AI-Video-Pipeline\\model 3D; files never go to GitHub)
  find_blender()  BLENDER_PATH, else the usual install folders (Blender 5.0.1 on the user's PC), else `blender` on PATH
  plan()          the render plan (sky A/B/C, sun, camera presets, real height, decimate) for tools/render_plates.py
  render()        runs Blender in the background (timeout, log file) and returns its manifest (times, triangles, cameras)
  add_sky()       sky C: an in-game sky picture behind a plate rendered with a transparent sky (Pillow, no AI)
  to_library()    the plates go into the library's review box as backgrounds of a place (role from the camera), and their exact
                  camera goes into set_analyses, so no Claude call is needed to read them
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional

from . import assets

MODEL_EXT = (".glb", ".gltf", ".fbx", ".obj", ".blend", ".usd", ".usda", ".usdc", ".usdz", ".stl")
SCRIPT = os.path.join(os.path.dirname(__file__), "..", "tools", "render_plates.py")
PRESETS = {"eye_000": "ngang tầm mắt · hướng 0°", "eye_090": "ngang tầm mắt · hướng 90°", "eye_180": "ngang tầm mắt · hướng 180°",
           "eye_270": "ngang tầm mắt · hướng 270°", "low_000": "góc thấp (ngước lên)", "high_045": "góc cao (nhìn xuống)"}
SKIES = {"A": "A · trời vật lý của Blender (không cần tải, có nắng + bóng)",
         "B": "B · HDRI (ảnh 360°, có mây — cần file .hdr/.exr, ví dụ Poly Haven CC0)",
         "C": "C · ánh sáng như A/B, nền trời trong suốt → ghép ảnh trời in-game"}
ROLE_OF_ANGLE = {"eye_level": "eye_level", "low_angle": "low_angle", "high_angle": "high_angle"}


class Plates3DError(Exception):
    """A message that can be shown to the person."""


def model_dir() -> str:
    return os.environ.get("MODEL3D_DIR") or r"D:\AI-Video-Pipeline\model 3D"


def models(folder: Optional[str] = None) -> List[Dict]:
    """[{path, name, size_mb}] of the 3D files under the folder (two levels deep), biggest last."""
    folder = folder or model_dir()
    if not os.path.isdir(folder):
        return []
    found = []
    for pattern in ("*", os.path.join("*", "*"), os.path.join("*", "*", "*")):
        for path in glob.glob(os.path.join(folder, pattern)):
            if os.path.isfile(path) and path.lower().endswith(MODEL_EXT):
                found.append({"path": path, "name": os.path.relpath(path, folder), "size_mb": round(os.path.getsize(path) / 1e6, 1)})
    return sorted(found, key=lambda m: (m["size_mb"], m["name"]))


def find_blender() -> Optional[str]:
    env = os.environ.get("BLENDER_PATH", "").strip().strip('"')
    if env:
        return env if os.path.exists(env) else None
    candidates = [r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
                  r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
                  r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
                  "/Applications/Blender.app/Contents/MacOS/Blender"]
    candidates += sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe"), reverse=True)
    for c in candidates:
        if os.path.exists(c):
            return c
    return shutil.which("blender")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", assets.fold(name)).strip("_") or "boi_canh"


def plan(model: str, out_dir: str, sky: str = "A", sun_elevation: float = 35, sun_azimuth: float = 140, hdri: Optional[str] = None,
         presets: Optional[List[str]] = None, real_height_m: Optional[float] = None, decimate: float = 1.0,
         resolution=(1280, 720), engine: str = "auto", samples: int = 16, cameras: Optional[List[Dict]] = None,
         ground: bool = True) -> Dict:
    if not os.path.exists(model):
        raise Plates3DError(f"không thấy file 3D: {model}")
    if sky not in SKIES:
        raise Plates3DError("trời phải là A, B hoặc C")
    if sky == "B" and not (hdri and os.path.exists(hdri)):
        raise Plates3DError("cách B cần file HDRI (.hdr/.exr) có thật")
    return {"model": os.path.abspath(model), "out_dir": os.path.abspath(out_dir), "resolution": list(resolution), "engine": engine,
            "samples": int(samples), "real_height_m": real_height_m, "decimate": float(decimate), "ground": bool(ground),
            "presets": list(presets or PRESETS), "cameras": cameras or [], "depth": True,
            "sky": {"mode": sky, "sun_elevation": float(sun_elevation), "sun_azimuth": float(sun_azimuth),
                    "hdri": os.path.abspath(hdri) if hdri else None}}


def out_dir(data_dir: str, place: str) -> str:
    return os.path.join(data_dir, "_plates3d", slug(place), time.strftime("%Y%m%d_%H%M%S"))


def render(cfg: Dict, blender: Optional[str] = None, run: Callable = subprocess.run, timeout: int = 3600) -> Dict:
    """Run tools/render_plates.py in Blender (background) and return its manifest. The whole Blender output is kept in render.log
    next to the plates (the local test reads the times there)."""
    blender = blender or find_blender()
    if not blender:
        raise Plates3DError("không tìm thấy Blender — cài Blender 5.0 hoặc đặt BLENDER_PATH trong dashboard.env")
    os.makedirs(cfg["out_dir"], exist_ok=True)
    plan_path = os.path.join(cfg["out_dir"], "plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    if os.path.basename(blender).lower().startswith("python"):   # a Python with the bpy module (tests / no Blender app)
        cmd = [sys.executable if blender == "python" else blender, os.path.abspath(SCRIPT), "--config", plan_path]
    else:
        cmd = [blender, "-b", "--factory-startup", "-P", os.path.abspath(SCRIPT), "--", "--config", plan_path]
    t0 = time.time()
    try:
        proc = run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Plates3DError(f"Blender chạy quá {timeout // 60} phút — thử giảm lưới (decimate) hoặc cắt khu nhỏ hơn") from None
    except OSError as e:
        raise Plates3DError(f"không chạy được Blender: {e}") from None
    with open(os.path.join(cfg["out_dir"], "render.log"), "w", encoding="utf-8") as f:
        f.write((proc.stdout or "") + "\n--- stderr ---\n" + (proc.stderr or ""))
    manifest_path = os.path.join(cfg["out_dir"], "manifest.json")
    gpu_trouble = re.search(r"EGL|OpenGL|GPU|gpu backend|Vulkan", (proc.stderr or "") + (proc.stdout or ""), re.I)
    if proc.returncode != 0 and cfg.get("engine", "auto") == "auto" and gpu_trouble:
        # EEVEE needs a graphics card context; without one Blender aborts (no Python error to catch) — Cycles on the CPU works
        return render(dict(cfg, engine="cycles"), blender, run, timeout)
    if proc.returncode != 0 or not os.path.exists(manifest_path):
        tail = "\n".join(((proc.stderr or "") + "\n" + (proc.stdout or "")).strip().splitlines()[-8:])
        raise Plates3DError(f"Blender dừng lỗi (mã {proc.returncode}). Cuối log:\n{tail}")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    manifest["total_sec"] = round(time.time() - t0, 1)
    manifest["out_dir"] = cfg["out_dir"]
    return manifest


def add_sky(plate_path: str, sky_path: str, out_path: str) -> str:
    """Sky C: the in-game sky picture, scaled to cover the frame, behind the plate's transparent sky."""
    from PIL import Image
    plate = Image.open(plate_path).convert("RGBA")
    sky = Image.open(sky_path).convert("RGBA")
    scale = max(plate.width / sky.width, plate.height / sky.height)
    sky = sky.resize((max(int(sky.width * scale + 0.5), plate.width), max(int(sky.height * scale + 0.5), plate.height)))
    left, top = (sky.width - plate.width) // 2, 0                       # keep the top of the sky picture (clouds), crop the sides
    sky = sky.crop((left, top, left + plate.width, top + plate.height))
    Image.alpha_composite(sky, plate).convert("RGB").save(out_path)
    return out_path


def to_library(conn, manifest: Dict, game: str, place: str, sky_picture: Optional[str] = None, look: Optional[str] = None) -> Dict:
    """Put the rendered plates in the library as backgrounds of `place` (created if new), waiting for a person (G2). Each plate's
    role comes from its camera (eye level / low / high) and its exact camera goes to set_analyses (no paid reading)."""
    import hashlib
    row = conn.execute("SELECT id FROM assets WHERE game=? AND kind='location' AND lower(name)=lower(?) AND project_id IS NULL",
                       (game, place)).fetchone()
    aid = row["id"] if row else assets.create(conn, game, "location", place, "Bối cảnh dựng từ file 3D (render nền trống người).",
                                              created_by="3d")
    added, skipped = [], []
    for p in manifest.get("plates") or []:
        src = os.path.join(manifest["out_dir"], p["file"])
        if sky_picture and manifest.get("sky", {}).get("mode") == "C":
            src = add_sky(src, sky_picture, src.replace(".png", "_sky.png"))
        try:
            with open(src, "rb") as f:
                data = f.read()
            assets.add_image(conn, aid, f"3d_{p['name']}.png", data, src_path=src, status="pending",
                             role=ROLE_OF_ANGLE.get(p.get("angle")), look=look, variant="3D",
                             limit=assets.PLATES_PER_LOCATION)
        except (OSError, assets.AssetError) as e:
            skipped.append(f"{p['name']}: {e}")
            continue
        stored = conn.execute("SELECT path FROM asset_images WHERE asset_id=? ORDER BY id DESC LIMIT 1", (aid,)).fetchone()["path"]
        with open(assets.resolve(stored), "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        if p.get("set_analysis"):
            conn.execute("INSERT OR REPLACE INTO set_analyses (sha256, data, created_at) VALUES (?,?,datetime('now'))",
                         (sha, json.dumps(p["set_analysis"], ensure_ascii=False)))
        added.append(p["name"])
    conn.commit()
    return {"asset_id": aid, "added": added, "skipped": skipped}


def summary(manifest: Dict) -> str:
    """One line for the person (and for docs/RESEARCH_3D_PREVIZ.md): what the local test must record."""
    m = manifest.get("model") or {}
    times = [p["render_sec"] for p in manifest.get("plates") or []]
    return (f"{m.get('size_mb', '?')} MB · {m.get('triangles', 0):,} tam giác · nhập {m.get('import_sec', '?')} s · "
            f"{len(times)} ảnh nền, render {min(times, default=0):.1f}–{max(times, default=0):.1f} s/ảnh · engine "
            f"{manifest.get('engine')} · tổng {manifest.get('total_sec', '?')} s · tỉ lệ ×{manifest.get('scale_factor')}")
