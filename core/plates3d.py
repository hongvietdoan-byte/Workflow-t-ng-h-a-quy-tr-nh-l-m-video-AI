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
import contextlib
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from typing import Callable, Dict, List, Optional

from . import assets

MODEL_EXT = (".glb", ".gltf", ".fbx", ".obj", ".blend", ".usd", ".usda", ".usdc", ".usdz", ".stl")
MODEL_DEPTH = 6   # folders below MODEL3D_DIR still searched (a zip unpacked into a folder of its own name adds two)
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
    """[{path, name, size_mb}] of the 3D files under the folder (up to MODEL_DEPTH folders deep), biggest last.
    2026-09-29: the official in-game export sits at <zip name>/<zip name>/ClockTower/T_30_XH_PCMAP_P16/asset.fbx — 4 folders down;
    the old 3-level glob never listed it."""
    folder = folder or model_dir()
    if not os.path.isdir(folder):
        return []
    found = []
    base = os.path.normpath(folder).count(os.sep)
    for root, dirs, files in os.walk(folder):
        if os.path.normpath(root).count(os.sep) - base >= MODEL_DEPTH:
            dirs[:] = []
        for f in files:
            if f.lower().endswith(MODEL_EXT):
                path = os.path.join(root, f)
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
    return shutil.which("blender") or store_blender()


STORE = "store:"


_STORE_CACHE: dict = {}


def store_blender() -> Optional[str]:
    """Remembered per process (an answer is kept for good, "not installed" for 5 minutes): the PowerShell query takes ~1 s and the Dashboard
    asked on every redraw of the library dialog (02/10).""" 
    import time
    hit = _STORE_CACHE.get("v")
    if hit and (hit[0] is not None or time.time() - hit[1] < 300):
        return hit[0]
    value = _store_blender()
    _STORE_CACHE["v"] = (value, time.time())
    return value


def _store_blender() -> Optional[str]:
    """Blender installed from the Microsoft Store (2026-09-25, this machine: 5.0.1). Its folder under WindowsApps is hidden from file
    search and its blender.exe cannot be started directly ("Access is denied"); the Store alias blender-launcher.exe drops every
    argument. It runs headless only inside its package context (Invoke-CommandInDesktopPackage). Returns "store:<family>|<exe>"."""
    if os.name != "nt":
        return None
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-AppxPackage BlenderFoundation.Blender | Select-Object -First 1 | "
                              "ForEach-Object { $_.PackageFamilyName + '|' + $_.InstallLocation }"],
                             capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    if "|" not in out:
        return None
    family, loc = out.split("|", 1)
    return f"{STORE}{family}|{os.path.join(loc, 'Blender', 'blender.exe')}"


class _Done:
    def __init__(self, returncode: int, stdout: str):
        self.returncode, self.stdout, self.stderr = returncode, stdout, ""


def _run_in_store(blender: str, args: List[str], work: str, timeout: int):
    """Run Store Blender headless: a .cmd file (Blender + args, output to render.log, exit code to rc.txt) started inside the package
    context, then wait for rc.txt."""
    family, exe = blender[len(STORE):].split("|", 1)
    stamp = time.strftime("%H%M%S") + "_" + uuid.uuid4().hex[:6]     # a retry within the same second must not read the old rc file
    log, rc, bat = (os.path.join(work, f"store_{stamp}.{x}") for x in ("log", "rc", "cmd"))
    quoted = " ".join(f'"{a}"' for a in args)
    with open(bat, "w", encoding="ascii", errors="replace") as f:
        f.write(f'@echo off\r\n"{exe}" {quoted} > "{log}" 2>&1\r\necho %errorlevel% > "{rc}"\r\n')
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"Invoke-CommandInDesktopPackage -PackageFamilyName '{family}' -AppId 'BLENDER' "
                    f"-Command 'C:\\Windows\\System32\\cmd.exe' -Args '/c \"{bat}\"' -PreventBreakaway"],
                   capture_output=True, text=True, timeout=120)
    end = time.time() + timeout
    while time.time() < end and not os.path.exists(rc):
        time.sleep(2)
    if not os.path.exists(rc):
        raise subprocess.TimeoutExpired(exe, timeout)
    time.sleep(0.5)
    with open(rc, encoding="ascii", errors="replace") as f:
        code = int((f.read().strip() or "1").split()[0])
    with open(log, encoding="utf-8", errors="replace") as f:
        return _Done(code, f.read())


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", assets.fold(name)).strip("_") or "boi_canh"


def plan(model: str, out_dir: str, sky: str = "A", sun_elevation: float = 35, sun_azimuth: float = 140, hdri: Optional[str] = None,
         presets: Optional[List[str]] = None, real_height_m: Optional[float] = None, decimate: float = 1.0,
         resolution=(1280, 720), engine: str = "auto", samples: int = 16, cameras: Optional[List[Dict]] = None,
         ground: bool = True, weather: Optional[Dict] = None, sky_extra: Optional[Dict] = None, only_cameras: bool = False,
         probe: Optional[Dict] = None, heights: Optional[List] = None, rooms: Optional[List] = None) -> Dict:
    """only_cameras: render just `cameras` (the shot cameras of a location pack), no preset views. weather: {"snow","wet","fog"}
    0..1 on the geometry. sky_extra: more sky keys for tools/render_plates.py (sun_strength, sun_color, strength, exposure)."""
    if not os.path.exists(model):
        raise Plates3DError(f"không thấy file 3D: {model}")
    if sky not in SKIES:
        raise Plates3DError("trời phải là A, B hoặc C")
    if sky == "B" and not (hdri and os.path.exists(hdri)):
        raise Plates3DError("cách B cần file HDRI (.hdr/.exr) có thật")
    return {"model": os.path.abspath(model), "out_dir": os.path.abspath(out_dir), "resolution": list(resolution), "engine": engine,
            "samples": int(samples), "real_height_m": real_height_m, "decimate": float(decimate), "ground": bool(ground),
            "presets": [] if only_cameras else list(presets or PRESETS), "cameras": cameras or [], "depth": True,
            "weather": dict(weather or {}), **({"probe": probe} if probe else {}), **({"heights": heights} if heights else {}), **({"rooms": rooms} if rooms else {}),
            "sky": {"mode": sky, "sun_elevation": float(sun_elevation), "sun_azimuth": float(sun_azimuth),
                    "hdri": os.path.abspath(hdri) if hdri else None, **(sky_extra or {})}}


def out_dir(data_dir: str, place: str) -> str:
    """One folder per render; the short random tail keeps two renders of the same place in the same second apart (two projects)."""
    return os.path.join(data_dir, "_plates3d", slug(place), time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:4])


LOCK_STALE_SEC = 3600       # a lock older than this was left by a Blender that died; it is taken over
LOCK_WAIT_SEC = 1800        # how long a render waits for its turn before giving up with a clear message


def lock_path() -> str:
    """One Blender at a time on this computer (it uses the whole graphics card), whatever data folder the caller uses — so the
    lock lives in the system temp folder unless PLATES3D_LOCK names another file."""
    return os.environ.get("PLATES3D_LOCK") or os.path.join(tempfile.gettempdir(), "ai_video_pipeline_blender.lock")


def queue_length() -> int:
    """Renders waiting for their turn right now (shown on the dashboard)."""
    return len(glob.glob(lock_path() + ".wait.*"))


def pid_alive(pid: int) -> bool:
    """Is process `pid` still running on this computer? (Windows: OpenProcess + exit code; elsewhere: signal 0.)"""
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = ctypes.c_void_p
        k32.GetExitCodeProcess.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
        k32.CloseHandle.argtypes = (ctypes.c_void_p,)
        handle = k32.OpenProcess(0x1000, False, int(pid))        # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5                  # 5 = access denied: it exists (another user's process)
        try:
            code = ctypes.c_ulong()
            if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == 259                            # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_lock(path: str) -> Optional[Dict]:
    """The lock's content: {pid, owner, since_ts}. Reads the older 'PID date' text too (owner unknown, time = file time)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read().strip()
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    try:
        d = json.loads(raw)
        if not isinstance(d, dict):
            raise ValueError
    except ValueError:
        first = raw.split()[0] if raw.split() else ""
        d = {"pid": int(first) if first.isdigit() else 0, "owner": ""}
    try:
        pid = int(d.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    return {"pid": pid, "owner": str(d.get("owner") or ""), "since_ts": float(d.get("since_ts") or mtime)}


def holder() -> Optional[Dict]:
    """Who holds this computer's Blender turn right now: {pid, owner, since_ts, held_sec, alive}; None = free."""
    h = _read_lock(lock_path())
    if h is None:
        return None
    h["held_sec"] = max(0.0, time.time() - h["since_ts"])
    h["alive"] = pid_alive(h["pid"])
    return h


def waiters() -> List[Dict]:
    """Renders waiting for their turn: [{owner, waited_sec}] (the ticket file says who; its time says since when)."""
    out = []
    for t in glob.glob(lock_path() + ".wait.*"):
        try:
            with open(t, encoding="utf-8", errors="replace") as fh:
                owner = fh.read().strip()
            out.append({"owner": owner, "waited_sec": max(0.0, time.time() - os.path.getmtime(t))})
        except OSError:
            continue
    return sorted(out, key=lambda w: -w["waited_sec"])


def _minutes(sec: float) -> str:
    return f"{int(sec // 60)} phút" if sec >= 60 else f"{int(sec)} giây"


def status_text() -> str:
    """One line for the dashboard: who holds Blender, for how long, who waits and since when; '' when Blender is free."""
    h = holder()
    if h is None:
        return ""
    who = h["owner"] or f"tiến trình {h['pid'] or '?'}"
    text = f"🏗 Blender đang bận: {who} giữ khóa {_minutes(h['held_sec'])}"
    if not h["alive"]:
        text += " (tiến trình đã tắt — lượt render kế tiếp sẽ tự gỡ khóa)"
    w = waiters()
    if w:
        text += " · chờ: " + ", ".join(f"{x['owner'] or '?'} {_minutes(x['waited_sec'])}" for x in w)
    return text


def _log_lock_event(code: str, msg: str) -> None:
    """Keep the last lock takeovers next to the lock (any data folder / tool sees them), newest last, at most 50 lines."""
    log = lock_path() + ".log"
    try:
        lines = []
        if os.path.exists(log):
            with open(log, encoding="utf-8") as fh:
                lines = fh.read().splitlines()[-49:]
        lines.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {code} {msg}")
        with open(log, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass


_REPORTER: Optional[Callable[[str, str, str], None]] = None


def set_reporter(fn: Optional[Callable[[str, str, str], None]]) -> None:
    """The dashboard hands a function(msg, code, owner) that writes the diag table (plates3d itself has no database)."""
    global _REPORTER
    _REPORTER = fn


@contextlib.contextmanager
def blender_turn(wait: float = LOCK_WAIT_SEC, sleep: Callable[[float], None] = time.sleep, owner: str = "",
                 report: Optional[Callable[[str, str, str], None]] = None):
    """Wait for this computer's Blender turn (file lock, so it also holds across dashboard windows and tools), then hold it.
    The lock names its process and project (`owner`); a lock whose process is gone (a render stopped by closing the dashboard /
    a crash) or older than LOCK_STALE_SEC is removed at once and reported (`report`, else the dashboard's reporter, + lock .log)."""
    path = lock_path()
    report = report or _REPORTER
    ticket = f"{path}.wait.{os.getpid()}_{uuid.uuid4().hex[:6]}"
    with open(ticket, "w", encoding="utf-8") as f:
        f.write(owner)
    end = time.time() + wait
    try:
        while True:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                h = _read_lock(path)
                if h is None:
                    continue                                  # freed meanwhile: try again at once
                age = time.time() - h["since_ts"]
                dead = h["pid"] != 0 and not pid_alive(h["pid"])
                if age > LOCK_STALE_SEC or dead:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    why = f"tiến trình {h['pid']} không còn chạy" if dead else f"quá {LOCK_STALE_SEC // 60} phút"
                    msg = (f"Gỡ khóa Blender cũ của {h['owner'] or 'không rõ dự án'} (PID {h['pid']}, giữ {_minutes(age)}): {why} — "
                           f"lượt render trước bị ngắt; {owner or 'lượt mới'} nhận lượt.")
                    _log_lock_event("blender_lock_stale", msg)
                    if report:
                        try:
                            report(msg, "blender_lock_stale", h["owner"])
                        except Exception:  # noqa: BLE001 - a diag write must never stop the render
                            pass
                    continue
                if time.time() > end:
                    raise Plates3DError(f"Blender đang bận với lượt render khác quá {int(wait // 60)} phút — thử lại sau. Nếu chắc chắn "
                                        f"không còn Blender nào chạy, xóa file {path}.") from None
                sleep(1.0)
    finally:
        try:
            os.remove(ticket)
        except OSError:
            pass
    os.write(fd, json.dumps({"pid": os.getpid(), "owner": owner, "since_ts": time.time(),
                             "since": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False).encode("utf-8"))
    os.close(fd)
    try:
        yield
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def render(cfg: Dict, blender: Optional[str] = None, run: Callable = subprocess.run, timeout: int = 3600) -> Dict:
    """Run tools/render_plates.py in Blender (background) and return its manifest. The whole Blender output is kept in render.log
    next to the plates (the local test reads the times there). Renders from several projects wait in line (`blender_turn`)."""
    with blender_turn(owner=str(cfg.get("owner") or "")):
        return _render(cfg, blender, run, timeout)


def _render(cfg: Dict, blender: Optional[str], run: Callable, timeout: int) -> Dict:
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
        if blender.startswith(STORE):
            proc = _run_in_store(blender, cmd[1:], cfg["out_dir"], timeout)
        else:
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
        return _render(dict(cfg, engine="cycles"), blender, run, timeout)     # still our turn: no second wait
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
    row = row or assets.find_same(conn, game, "location", place)     # S14.43B: 'Thap Dong Ho' / an alias = the same place, never a twin
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


def ground_heights(model: str, points: List, out: str, real_height_m: Optional[float] = None, blender: Optional[str] = None) -> List[Dict]:
    """Ground height (raw model frame) under each [x, y], plants skipped — Blender, no render (tools/render_plates.py `heights`)."""
    cfg = plan(model, out, only_cameras=True, real_height_m=real_height_m, heights=[list(p[:3]) for p in points])
    return render(cfg, blender, timeout=1800)["heights"]


def room_cameras(model: str, boxes: List[Dict], out: str, real_height_m: Optional[float] = None, blender: Optional[str] = None) -> List[Dict]:
    """Camera spot + view inside each house box ({"name", "lo", "hi", "floor_z"}, raw model frame) — Blender, no render
    (tools/render_plates.py `rooms`)."""
    cfg = plan(model, out, only_cameras=True, real_height_m=real_height_m, rooms=list(boxes))
    return render(cfg, blender, timeout=1800)["rooms"]

