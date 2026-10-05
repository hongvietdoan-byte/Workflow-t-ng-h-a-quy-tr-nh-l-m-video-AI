"""G2 (S13.3) — bộ ảnh chụp giao diện v2 trên DỮ LIỆU MẪU gần thật, bằng chính Dashboard thật + Chrome headless (giao thức CDP).

    py tools/ui_snapshot.py --subset                 # nhanh: 1 độ rộng (1440) × sáng/tối × 100 %, các màn chính
    py tools/ui_snapshot.py                          # đủ: 4 độ rộng × sáng/tối × phóng 100/80 % (+ các trạng thái trống/đang chạy/lỗi/xong)
    py tools/ui_snapshot.py --only storyboard,home --widths 1280,1920 --themes dark

Việc làm: (1) dựng CSDL mẫu bằng API Pipeline thật (không gọi dịch vụ ngoài, 0 USD): 50 dự án đủ trạng thái, tên dài, dự án chính có 30 khung
storyboard; (2) chạy `streamlit run dashboard/app.py` cổng 8525 với PIPELINE_DB/PIPELINE_DATA trỏ vào dữ liệu mẫu và nhà cung cấp giả;
(3) mở Chrome headless, đổi nền sáng/tối bằng công tắc 🌙 trong ⚙ (không dùng ?theme= vì phiên nhớ), bấm từng màn trên thanh bước, chụp
WebP vào docs/ui_snapshots/<ngày>/ kèm index.md. Không cài thêm gói: dùng `websockets` + Chrome/Edge có sẵn trong máy.

Phần logic không cần trình duyệt (ma trận chụp, tên file, index.md, dựng CSDL mẫu) nằm ở các hàm thuần để test (tests/test_ui_snapshot.py).
"""
import argparse
import base64
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from typing import Dict, List, NamedTuple, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))

PORT = 8525
CDP_PORT = 9225
WIDTHS = (1280, 1440, 1630, 1920)
THEMES = ("dark", "light")                      # v2 mở ở nền tối; "light" = bấm công tắc 🌙
ZOOMS = (100, 80)
STATES = ("rich", "empty", "running", "error", "done")       # trạng thái của DỰ ÁN CHÍNH (project #1, màn nào cũng mở nó)
SCREENS = {                                      # tên file -> chữ nhận nút trên thanh bước (radio)
    "home": "Tất cả dự án", "script": "Kịch bản", "storyboard": "Storyboard", "video": "Video",
    "deliver": "Bản giao", "team": "Nhóm", "monitor": "Theo dõi"}
OVERLAYS = {"settings": "⚙", "inbox": "📥", "money": "💵"}   # popover trên thanh trên: chụp khi mở, trên màn ⌂
PROJECT_SCREENS = ("script", "storyboard", "video", "deliver")
SUBSET_SCREENS = ("home", "storyboard", "deliver", "settings")
MAX_HEIGHT = 3000                                # px của ảnh; trang dài hơn bị cắt (ghi trong index)
BASE_STATE_COMBO = (1440, "dark", 100)           # các trạng thái phụ chỉ chụp ở tổ hợp này

LONG_NAME = ("Trailer Free Fire — Mùa hè rực lửa: Kelly đối đầu Maxim ở thành phố Bermuda, bản dựng dài để thử cắt chữ "
             "và xuống dòng của tên dự án trên thanh trên, thẻ dự án và hộp thoại")
KINDS = ("idle", "running", "error", "waiting", "done", "paused", "empty")   # vòng lặp trạng thái cho 49 dự án còn lại
NAMES = ("Trailer Ep.", "Cinematic mùa giải", "Teaser nhân vật", "Quảng cáo sự kiện", "Video giới thiệu skin", "Highlight giải đấu")


class Shot(NamedTuple):
    state: str
    screen: str
    theme: str
    width: int
    zoom: int


def shot_name(s: Shot, ext: str = "webp") -> str:
    """Tên file có hệ: <state>__<screen>__<theme>__<width>__z<zoom>.<ext> — sắp xếp theo tên là nhóm được theo màn / theo độ rộng."""
    return f"{s.state}__{s.screen}__{s.theme}__{s.width}__z{s.zoom}.{ext}"


def parse_name(name: str) -> Optional[Shot]:
    base = name.rsplit(".", 1)[0]
    parts = base.split("__")
    if len(parts) != 5 or not parts[4].startswith("z"):
        return None
    try:
        return Shot(parts[0], parts[1], parts[2], int(parts[3]), int(parts[4][1:]))
    except ValueError:
        return None


def _csv(value: Optional[str], allowed, cast=str) -> list:
    if not value:
        return list(allowed)
    out = [cast(x.strip()) for x in value.split(",") if x.strip()]
    bad = [x for x in out if x not in allowed]
    if bad:
        raise ValueError(f"giá trị không hợp lệ {bad}; chọn trong {list(allowed)}")
    return out


def build_matrix(subset: bool = False, widths: Optional[str] = None, themes: Optional[str] = None, zooms: Optional[str] = None,
                 only: Optional[str] = None, states: Optional[str] = None) -> List[Shot]:
    """Danh sách ảnh cần chụp. Trạng thái 'rich' = ma trận đầy đủ; trạng thái phụ chỉ chụp màn của dự án ở BASE_STATE_COMBO.
    --subset: 1 độ rộng (1440), phóng 100 %, vài màn chính — để chạy nhanh."""
    ws = _csv(widths, WIDTHS, int) if widths else ([1440] if subset else list(WIDTHS))
    ths = _csv(themes, THEMES)
    zs = _csv(zooms, ZOOMS, int) if zooms else ([100] if subset else list(ZOOMS))
    allowed = list(SCREENS) + list(OVERLAYS)
    scr = _csv(only, allowed) if only else (list(SUBSET_SCREENS) if subset else allowed)
    sts = _csv(states, STATES) if states else (["rich"] if subset else list(STATES))
    out = []
    for state in sts:
        for theme in ths:
            for w in ws:
                for z in zs:
                    for s in scr:
                        if state != "rich":
                            if (w, theme, z) != BASE_STATE_COMBO or s not in PROJECT_SCREENS + ("home",):
                                continue
                        out.append(Shot(state, s, theme, w, z))
    return out


def viewport(width: int, zoom: int, height: int) -> Dict:
    """Số liệu Emulation: phóng 80 % = trang rộng width/0.8 px CSS, ảnh vẫn rộng đúng `width` px thiết bị."""
    f = zoom / 100.0
    return {"width": round(width / f), "height": round(height / f), "deviceScaleFactor": f, "mobile": False}


def index_markdown(date: str, shots: List[Dict], total_bytes: int, notes: Optional[List[str]] = None) -> str:
    """index.md: bảng theo (trạng thái, màn) × (nền, rộng, phóng) với liên kết ảnh; cuối trang là tổng dung lượng + cách sinh lại."""
    lines = [f"# Ảnh chụp giao diện v2 — {date}", "",
             "Sinh bằng `py tools/ui_snapshot.py` trên dữ liệu mẫu (50 dự án, dự án chính 30 khung), nhà cung cấp giả, 0 USD. "
             "Tên file: `<trạng thái>__<màn>__<nền>__<rộng>__z<phóng %>.webp`.", ""]
    for n in notes or []:
        lines.append(f"- {n}")
    if notes:
        lines.append("")
    by_state: Dict[str, List[Dict]] = {}
    for s in shots:
        by_state.setdefault(s["state"], []).append(s)
    for state, items in by_state.items():
        lines += [f"## Trạng thái dự án chính: {state}", "", "| Màn | Nền | Rộng | Phóng | Cao (px) | Ảnh | KB |", "|---|---|---|---|---|---|---|"]
        for s in sorted(items, key=lambda x: (x["screen"], x["theme"], x["width"], -x["zoom"])):
            cut = " ⚠ cắt" if s.get("cut") else ""
            lines.append(f"| {s['screen']} | {s['theme']} | {s['width']} | {s['zoom']} % | {s['height']}{cut} | [{s['file']}]({s['file']}) | {s['bytes'] // 1024} |")
        lines.append("")
    lines += [f"**Tổng: {len(shots)} ảnh, {total_bytes / 1048576:.1f} MB.**", ""]
    return "\n".join(lines)


# ---- dữ liệu mẫu ---------------------------------------------------------------------------------------------------------------
def build_sample_data(out_dir: str, primary: str = "rich", n_projects: int = 50, scenes_primary: int = 30, images: bool = True) -> Dict:
    """Dựng CSDL + ảnh mẫu bằng API Pipeline thật. Dự án #1 (mở mặc định) có trạng thái `primary`; #2.. xoay vòng các trạng thái, vài
    cái tên dài. Trả {"db", "data", "projects": [(id, name, kind)]}. Xóa dựng cũ trong out_dir."""
    from core.db import connect
    from core.llm_io import approve_motion_prompt, lock_character_bible, store_motion_prompts, store_scene_analysis
    from core.pipeline import Pipeline
    from seed_demo import COLORS, CRITERIA, SCENES, draw

    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    db = os.path.join(out_dir, "manifest.sqlite")
    data = os.path.join(out_dir, "projects")
    p = Pipeline(connect(db))
    made = []

    def make(kind: str, name: str, n_scenes: int, rich: bool) -> int:
        pid = p.create_project(name, created_by=None)
        if kind == "empty":
            return pid
        for i in range(1, n_scenes + 1):
            loc, t, ch, mood, shot = SCENES[(i - 1) % len(SCENES)]
            sid = p.create_scene(pid, i, f"CẢNH {i}")
            text = (f"CẢNH {i}. {t.upper()} — {loc.upper()}\n{', '.join(ch)} xuất hiện trong khung cảnh {mood}. Camera {shot}. "
                    f"(Đoạn kịch bản mẫu số {i} để thử giao diện.)\n{ch[0]}: Chúng ta phải đi tiếp trước khi trời sáng.")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"text": text}, ensure_ascii=False), sid))
        p.conn.commit()
        store_scene_analysis(p, pid, {
            "characters": [{"name": "Lyra", "description": "Nữ, 25 tuổi, tóc bạc dài, giáp xanh cobalt, sẹo mắt trái"},
                           {"name": "Kael", "description": "Nam, 35, râu ngắn, áo choàng đen, kiếm rune"},
                           {"name": "Nữ chiến binh Amazon", "description": "Nữ, 30, giáp vàng, khiên tròn", "wardrobe": "vòng tay bạc"},
                           {"name": "Ông lão Orin", "description": "Nam, 70, râu bạc, gậy gỗ, áo len xám"}],
            "scenes": [{"idx": i, "location": SCENES[(i - 1) % len(SCENES)][0], "time": SCENES[(i - 1) % len(SCENES)][1],
                        "characters": SCENES[(i - 1) % len(SCENES)][2], "mood": SCENES[(i - 1) % len(SCENES)][3], "lighting": "tự nhiên",
                        "shot": SCENES[(i - 1) % len(SCENES)][4], "image_prompt": f"{SCENES[(i - 1) % len(SCENES)][0]}, cảnh {i}"}
                       for i in range(1, n_scenes + 1)]})
        lock_character_bible(p, pid)
        imgdir = os.path.join(data, str(pid), "images")
        # trạng thái ảnh theo cảnh: dự án chính 'rich' có đủ loại; các dự án khác theo `kind`
        for i in range(1, n_scenes + 1):
            sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (pid, i)).fetchone()["id"]
            if kind == "idle" and not rich and i > 2:
                break
            job = p.create_job(sid)
            plan = _image_plan(kind, i, n_scenes, rich)
            if plan == "queued":
                continue
            p.start(job)
            if plan == "running":
                continue
            if plan == "failed":
                p.fail(job, "risk control")
                continue
            p.succeed(job)
            if images:
                draw(os.path.join(imgdir, f"job_{job}.png"), *COLORS[i % len(COLORS)], f"S{i:02d}")
            if plan == "ok":
                continue
            base = {"approved": .92, "review_high": .90, "review_low": .61, "auto_rejected": .30}[plan]
            vals = ([base + d for d in (0.03, -0.08, 0.02, -0.02, 0.05)] if plan in ("approved", "review_high")
                    else ([.78, .42, .71, .55, .60] if plan == "review_low" else [.35, .20, .30, .25, .40]))
            p.apply_qc(job, dict(zip(CRITERIA, vals)), issues="tay trái 6 ngón, sai màu áo" if plan == "auto_rejected" else None)
            if plan == "approved":
                p.approve(job)
        if rich or kind in ("running", "done", "error"):
            ok = [r["idx"] for r in p.conn.execute(      # motion prompt chỉ nhận cảnh đã có ảnh được duyệt
                "SELECT DISTINCT s.idx FROM scenes s JOIN jobs j ON j.scene_id=s.id WHERE s.project_id=? AND j.type='image_gen' AND j.state='approved'"
                " ORDER BY s.idx", (pid,)).fetchall()][:12]
            if ok:
                store_motion_prompts(p, pid, {"scenes": [{"idx": i, "motion_prompt": f"Slow push-in cảnh {i}, sương mù trôi ngang", "duration_sec": 5}
                                                          for i in ok]})
                for i in ok[:8]:
                    row = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (pid, i)).fetchone()
                    try:
                        approve_motion_prompt(p, row["id"])
                    except Exception:  # noqa: BLE001 - mẫu: một cảnh không duyệt được thì bỏ qua
                        pass
        if kind in ("running", "done", "rich"):
            for i in range(1, min(n_scenes, 4) + 1):
                row = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (pid, i)).fetchone()
                job = p.create_job(row["id"], "video_gen")
                p.start(job)
                if i < 3 or kind == "done":
                    p.succeed(job)
        if kind == "running":
            p.conn.execute("UPDATE projects SET autopilot_state='running', autopilot_note=? WHERE id=?", ("Đang gen ảnh cảnh 12/30", pid))
        elif kind == "error":
            p.conn.execute("UPDATE projects SET autopilot_state='error', autopilot_note=? WHERE id=?",
                           ("Ảnh cảnh 7 bị risk control 3 lần — cần bạn đổi đầu vào", pid))
        elif kind == "waiting":
            p.conn.execute("UPDATE projects SET autopilot_state='waiting', autopilot_note=? WHERE id=?", ("Chờ bạn duyệt storyboard", pid))
        elif kind == "paused":
            p.conn.execute("UPDATE projects SET paused=1 WHERE id=?", (pid,))
        elif kind == "done":
            out = os.path.join(data, str(pid), "output")
            os.makedirs(out, exist_ok=True)
            with open(os.path.join(out, "FINAL_VIDEO.mp4"), "wb") as f:
                f.write(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64)       # đủ để "có bản giao" — không phải video thật
            from core import delivered                                         # S14.30: "Xong" = đã xuất bản giao
            delivered.mark(p.conn, pid, os.path.join(out, "FINAL_VIDEO.mp4"), source="deliver")
        p.conn.commit()
        return pid

    first_kind = {"rich": "idle", "empty": "empty"}.get(primary, primary)
    pid = make(first_kind, LONG_NAME, 0 if first_kind == "empty" else scenes_primary, rich=(primary == "rich"))
    made.append((pid, LONG_NAME, first_kind))
    for n in range(2, n_projects + 1):
        kind = KINDS[(n - 2) % len(KINDS)]
        name = f"{NAMES[n % len(NAMES)]}{n}" + (" — " + LONG_NAME[:70] if n % 7 == 0 else "")
        pid = make(kind, name, 0 if kind == "empty" else 3 + n % 5, rich=False)
        made.append((pid, name, kind))
    p.conn.close()                                # Windows: không đóng thì không xóa được thư mục tạm
    return {"db": db, "data": data, "projects": made}


def _image_plan(kind: str, i: int, n: int, rich: bool) -> str:
    """Trạng thái ảnh của cảnh i (1..n) trong dự án loại `kind`."""
    if rich:
        cycle = ["approved"] * 14 + ["review_low", "review_high", "ok", "auto_rejected", "failed", "running", "queued"]
        return cycle[(i - 1) % len(cycle)]
    if kind in ("done", "waiting"):
        return "approved" if kind == "done" else ("review_low" if i % 2 else "approved")
    if kind == "error":
        return "failed" if i % 3 == 0 else "approved"
    if kind == "running":
        return "approved" if i < n // 2 else ("running" if i == n // 2 else "queued")
    return "ok" if i % 2 else "queued"


# ---- Chrome DevTools Protocol (websockets, không cài thêm) ----------------------------------------------------------------------
def find_browser() -> Optional[str]:
    cands = [os.environ.get("CHROME_PATH", ""),
             r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
             shutil.which("chrome") or "", shutil.which("google-chrome") or "", shutil.which("chromium") or ""]
    return next((c for c in cands if c and os.path.exists(c)), None)


class CDP:
    def __init__(self, ws_url: str):
        from websockets.sync.client import connect
        self.ws = connect(ws_url, max_size=64 * 1024 * 1024, open_timeout=20)
        self.n = 0

    def call(self, method: str, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv(timeout=90))
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expr: str):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description", "js error"))
        return r.get("result", {}).get("value")

    def close(self):
        self.ws.close()


JS_SETTLE = """(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  let last = -1, same = 0;
  for (let i = 0; i < 80; i++) {
    const busy = !!document.querySelector('[data-testid="stStatusWidget"]') || !!document.querySelector('[data-testid="stAppViewContainer"][data-test-script-state="running"]')
      || document.querySelector('.stApp')?.getAttribute('data-test-script-state') === 'running';
    const h = (document.querySelector('[data-testid="stMain"]') || document.body).scrollHeight;
    same = (!busy && h === last) ? same + 1 : 0; last = h;
    if (same >= 3) break;
    await sleep(250);
  }
  try { await document.fonts.ready; } catch (e) {}
  return last;
})()"""
JS_CLICK_SCREEN = """(label => { const o = [...document.querySelectorAll('.st-key-step label[data-testid="stRadioOption"]')].find(l => l.innerText.includes(label));
  if (!o) return false; o.click(); return true; })(%s)"""
JS_OPEN_POPOVER = """(ic => { const b = [...document.querySelectorAll('[data-testid="stPopoverButton"]')].find(x => x.innerText.includes(ic));
  if (!b) return false; b.click(); return true; })(%s)"""
JS_TOGGLE_RECT = """(() => { const l = document.querySelector('.st-key-dark_toggle label'); if (!l) return null; const b = l.getBoundingClientRect(); return [b.x + 20, b.y + b.height / 2]; })()"""
JS_IS_DARK = """(() => { const c = getComputedStyle(document.body).backgroundColor.match(/\\d+/g); const bg = getComputedStyle(document.querySelector('.stApp')).backgroundColor.match(/\\d+/g) || c;
  return (+bg[0] + +bg[1] + +bg[2]) / 3 < 128; })()"""
JS_FONTS = """(() => ({ready: document.fonts.status, faces: [...document.fonts].filter(f => f.family.replace(/"/g, '') === 'Inter').map(f => f.status),
  used: getComputedStyle(document.querySelector('.stApp')).fontFamily.slice(0, 40), ok: document.fonts.check('600 14px Inter')}))()"""


class Runner:
    def __init__(self, out_dir: str, work: str, log=print):
        self.out, self.work, self.log = out_dir, work, log
        self.app: Optional[subprocess.Popen] = None
        self.chrome: Optional[subprocess.Popen] = None
        self.cdp: Optional[CDP] = None
        self.results: List[Dict] = []

    # -- app
    def start_app(self, db: str, data: str) -> None:
        env = dict(os.environ, PIPELINE_DB=db, PIPELINE_DATA=data, AUDIO_PROVIDER="mock", LLM_PROVIDER="mock", SUBJECT_PROVIDER="mock",
                   MOCK_REAL_MEDIA="1", FEATURE_UI_V2="1", DASHBOARD_AUTH="off", DASHBOARD_SYNC_BACKGROUND="0", FEATURE_SETTINGS_FILE=os.path.join(self.work, "feature_settings.json"))
        for k in ("ANTHROPIC_API_KEY", "CLIPAI_API_KEY"):
            env.pop(k, None)
        log = open(os.path.join(self.work, "streamlit.log"), "w", encoding="utf-8")
        self.app = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.port", str(PORT), "--server.headless", "true",
                                     "--browser.gatherUsageStats", "false"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(120):
            try:
                if urllib.request.urlopen(f"http://127.0.0.1:{PORT}/_stcore/health", timeout=2).read().strip() == b"ok":
                    return
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        raise RuntimeError("Streamlit không lên trong 60 s — xem streamlit.log")

    def stop_app(self) -> None:
        if self.app:
            self.app.terminate()
            try:
                self.app.wait(15)
            except subprocess.TimeoutExpired:
                self.app.kill()
            self.app = None

    # -- browser
    def start_browser(self) -> None:
        exe = find_browser()
        if not exe:
            raise RuntimeError("Không tìm thấy Chrome/Edge (đặt CHROME_PATH)")
        prof = tempfile.mkdtemp(prefix="uisnap_")
        self.chrome = subprocess.Popen([exe, "--headless=new", f"--remote-debugging-port={CDP_PORT}", f"--user-data-dir={prof}", "--hide-scrollbars",
                                        "--no-first-run", "--disable-gpu", "--mute-audio", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json", timeout=2))
                page = next(t for t in tabs if t.get("type") == "page")
                self.cdp = CDP(page["webSocketDebuggerUrl"])
                return
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        raise RuntimeError("Chrome không mở được cổng điều khiển")

    def stop_browser(self) -> None:
        if self.cdp:
            try:
                self.cdp.close()
            except Exception:  # noqa: BLE001
                pass
        if self.chrome:
            self.chrome.terminate()
            self.chrome = None

    # -- chụp
    def set_view(self, width: int, zoom: int, height: int = 900) -> None:
        v = viewport(width, zoom, height)
        self.cdp.call("Emulation.setDeviceMetricsOverride", width=v["width"], height=v["height"], deviceScaleFactor=v["deviceScaleFactor"], mobile=False)

    def load(self) -> None:
        self.cdp.call("Page.enable")
        self.cdp.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/")
        for _ in range(120):
            time.sleep(0.5)
            if self.cdp.js("!!document.querySelector('.st-key-step')"):
                break
        else:
            raise RuntimeError("Trang không dựng được thanh bước (xem streamlit.log)")
        self.cdp.js(JS_SETTLE)

    def ensure_theme(self, theme: str) -> None:
        if bool(self.cdp.js(JS_IS_DARK)) == (theme == "dark"):
            return
        self.cdp.js(JS_OPEN_POPOVER % json.dumps("⚙"))
        time.sleep(0.8)
        # công tắc nằm ở tab "Hệ thống" của popover
        self.cdp.js("""(() => { const t = [...document.querySelectorAll('[role="tab"]')].find(x => x.innerText.includes('Hệ thống')); if (t) t.click(); })()""")
        time.sleep(0.6)
        rect = self.cdp.js(JS_TOGGLE_RECT)
        if not rect:
            raise RuntimeError("Không thấy công tắc 🌙 Nền tối")
        for t in ("mousePressed", "mouseReleased"):       # chuột thật: label.click() bằng JS không đổi được công tắc của Streamlit
            self.cdp.call("Input.dispatchMouseEvent", type=t, x=rect[0], y=rect[1], button="left", clickCount=1)
        time.sleep(2.0)
        self.cdp.js(JS_SETTLE)
        self.cdp.call("Input.dispatchKeyEvent", type="keyDown", key="Escape", code="Escape", windowsVirtualKeyCode=27)
        self.cdp.call("Input.dispatchKeyEvent", type="keyUp", key="Escape", code="Escape", windowsVirtualKeyCode=27)
        time.sleep(0.4)
        if bool(self.cdp.js(JS_IS_DARK)) != (theme == "dark"):
            raise RuntimeError(f"Đổi nền sang {theme} không thành công")

    def go_screen(self, name: str) -> None:
        if not self.cdp.js(JS_CLICK_SCREEN % json.dumps(SCREENS[name])):
            raise RuntimeError(f"Không thấy nút màn {name} trên thanh bước")
        time.sleep(0.5)
        self.cdp.js(JS_SETTLE)

    def shot(self, s: Shot, overlay: bool) -> None:
        self.set_view(s.width, s.zoom, 900)
        time.sleep(0.4)
        h = int(self.cdp.js(JS_SETTLE) or 900)
        cut = False
        if not overlay:
            want = min(h + 24, MAX_HEIGHT)
            cut = h + 24 > MAX_HEIGHT
            self.set_view(s.width, s.zoom, max(want, 700))
            time.sleep(0.6)
            self.cdp.js(JS_SETTLE)
        r = self.cdp.call("Page.captureScreenshot", format="webp", quality=78, fromSurface=True)
        raw = base64.b64decode(r["data"])
        os.makedirs(self.out, exist_ok=True)
        name = shot_name(s)
        with open(os.path.join(self.out, name), "wb") as f:
            f.write(raw)
        self.results.append({"state": s.state, "screen": s.screen, "theme": s.theme, "width": s.width, "zoom": s.zoom,
                             "file": name, "bytes": len(raw), "height": min(h + 24, MAX_HEIGHT) if not overlay else 900, "cut": cut})
        self.log(f"  {name}  {len(raw) // 1024} KB")

    def capture_state(self, shots: List[Shot]) -> None:
        """Chụp các ảnh của MỘT trạng thái dự án chính (app đang chạy với dữ liệu của trạng thái đó), nhóm theo nền để chỉ bấm công tắc 2 lần."""
        self.set_view(1440, 100)
        self.load()
        for theme in dict.fromkeys(s.theme for s in shots):
            self.ensure_theme(theme)
            for s in [x for x in shots if x.theme == theme]:
                if s.screen in OVERLAYS:
                    self.set_view(s.width, s.zoom, 900)
                    self.go_screen("home")
                    if not self.cdp.js(JS_OPEN_POPOVER % json.dumps(OVERLAYS[s.screen])):
                        self.log(f"  (bỏ qua {s.screen}: không thấy nút {OVERLAYS[s.screen]})")
                        continue
                    time.sleep(1.0)
                    self.shot(s, overlay=True)
                    self.cdp.call("Input.dispatchKeyEvent", type="keyDown", key="Escape", code="Escape", windowsVirtualKeyCode=27)
                    self.cdp.call("Input.dispatchKeyEvent", type="keyUp", key="Escape", code="Escape", windowsVirtualKeyCode=27)
                    time.sleep(0.4)
                else:
                    self.go_screen(s.screen)
                    self.shot(s, overlay=False)

    def fonts_report(self) -> Dict:
        return self.cdp.js(JS_FONTS)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Chụp giao diện v2 trên dữ liệu mẫu (xem docstring đầu file)")
    ap.add_argument("--subset", action="store_true", help="chạy nhanh: 1440 px, phóng 100 %%, vài màn chính")
    ap.add_argument("--widths"), ap.add_argument("--themes"), ap.add_argument("--zooms"), ap.add_argument("--only"), ap.add_argument("--states")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--out", help="thư mục ảnh (mặc định docs/ui_snapshots/<ngày>)")
    ap.add_argument("--work", default=os.path.join(ROOT, "data", "ui_snapshot"), help="thư mục dữ liệu mẫu (không commit)")
    ap.add_argument("--list", action="store_true", help="chỉ in danh sách ảnh sẽ chụp")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    shots = build_matrix(a.subset, a.widths, a.themes, a.zooms, a.only, a.states)
    if a.list:
        for s in shots:
            print(shot_name(s))
        print(len(shots), "ảnh")
        return 0
    out = a.out or os.path.join(ROOT, "docs", "ui_snapshots", a.date)
    os.makedirs(a.work, exist_ok=True)
    r = Runner(out, a.work)
    try:
        r.start_browser()
        for state in dict.fromkeys(s.state for s in shots):
            print(f"== dữ liệu mẫu, dự án chính = {state}")
            d = build_sample_data(os.path.join(a.work, state), primary=state)
            r.start_app(d["db"], d["data"])
            try:
                r.capture_state([s for s in shots if s.state == state])
                if state == shots[0].state:
                    print("font:", r.fonts_report())
            finally:
                r.stop_app()
    finally:
        r.stop_browser()
        r.stop_app()
    total = sum(x["bytes"] for x in r.results)
    notes = []
    if any(x["cut"] for x in r.results):
        notes.append(f"Trang dài hơn {MAX_HEIGHT} px bị cắt ở {MAX_HEIGHT} px (đánh dấu ⚠ cắt).")
    with open(os.path.join(out, "index.md"), "w", encoding="utf-8") as f:
        f.write(index_markdown(a.date, r.results, total, notes))
    print(f"Xong: {len(r.results)} ảnh, {total / 1048576:.1f} MB -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
