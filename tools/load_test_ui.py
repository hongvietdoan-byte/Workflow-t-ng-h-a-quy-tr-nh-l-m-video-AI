"""M8.3 — đo tải GIAO DIỆN: N phiên trình duyệt cùng lúc trên Dashboard thật, nhà cung cấp GIẢ (0 USD).

    py tools/load_test_ui.py                              # N = 1, 2, 5, 10; CSDL giả 3 dự án × 30 shot
    py tools/load_test_ui.py --levels 1,5,10 --projects 4 --shots 40 --latency 0.3
    py tools/load_test_ui.py --db data/manifest.sqlite --data data/projects   # bản SAO dữ liệu thật (mở mode=ro → backup vào thư mục tạm)
    py tools/load_test_ui.py --out data/load_test_ui/may_chinh                  # nơi ghi bảng .md + .json (mặc định: thư mục tạm, in ra)

Mỗi mức N: chép CSDL mẫu sang thư mục tạm riêng → khởi `streamlit run dashboard/app.py` cổng riêng với IMAGE/VIDEO/AUDIO/LLM/SUBJECT
_PROVIDER=mock (xóa mọi khóa API khỏi môi trường; độ trễ giả `--latency` trên submit/status của bộ giả) → N phiên Chromium song song:
Trang chủ → mở dự án (phiên i mở dự án i mod số dự án) → Storyboard → duyệt 1 ảnh → Video → bấm Gen video (giả). Mỗi bước đo thời gian tới
khi màn ổn định (không còn biểu tượng chạy / script-state 'running' trong 0.3 s liền).
Phía server: CPU / RAM / số luồng tiến trình Streamlit (psutil, mỗi 0.5 s); chờ khóa SQLite + luồng theo tên qua đầu dò `sitecustomize`
(PYTHONPATH riêng của tiến trình đo — KHÔNG sửa dashboard/ hay core/): bọc sqlite3.connect → đo thời gian từng lệnh GHI / commit.

Không đo được ở đây (ghi trong bảng): khóa Blender, hàng đợi Claude CLI (bộ giả không xếp hàng), giới hạn của Deepix / Clip AI.
Cần: `pip install playwright psutil` (KHÔNG `playwright install` — dùng Chromium có sẵn: PLAYWRIGHT_BROWSERS_PATH / --chrome).
Phần không cần trình duyệt (dựng dữ liệu, chép CSDL, đầu dò, tổng hợp số đo, bảng) là hàm thuần — tests/test_load_test_ui.py.
"""
import argparse
import asyncio
import glob
import json
import os
import pathlib
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from typing import Dict, List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))

LEVELS = (1, 2, 5, 10)
PORT = 8541
SLOW_S = 2.0                                     # màn chính chậm hơn mức này = "chậm" (kế hoạch M8.3)
MAIN_STEPS = ("home", "open", "storyboard", "video")
STEPS = ("home", "open", "storyboard", "approve", "video", "gen")
STEP_LABEL = {"home": "Trang chủ", "open": "Mở dự án", "storyboard": "Storyboard (Bước 2)", "approve": "Duyệt 1 ảnh",
              "video": "Video (Bước 4)", "gen": "Bấm Gen video (giả)"}
LOCK_WAIT_S = 0.05                               # lệnh ghi / commit lâu hơn mức này coi là đã CHỜ khóa
SECRET_ENV = ("ANTHROPIC_API_KEY", "CLIPAI_API_KEY", "CLIPAI_TOKEN", "DEEPIX_TOKEN", "DEEPIX_API_KEY", "ELEVENLABS_API_KEY", "OPENAI_API_KEY")


# ---------------------------------------------------------------- dữ liệu
def build_data(out_dir: str, projects: int = 3, shots: int = 30) -> Dict:
    """CSDL giả bằng API Pipeline thật (như ảnh chụp G2): `projects` dự án × `shots` shot, đủ trạng thái ảnh / prompt / clip, ảnh giả nhỏ."""
    import ui_snapshot
    return ui_snapshot.build_sample_data(out_dir, n_projects=projects, scenes_primary=shots, rich_others=shots)


def neutralize(db: str) -> List[str]:
    """Làm TRƠ bản sao trước khi Dashboard đo mở nó (rà C-M83-TOOL C1/C2): không đường nào từ bản sao chạm tới dữ liệu / dịch vụ thật.
    - ảnh Kho đã xóa (status 'removed'): bỏ hàng — dọn rác hằng giờ (assets.purge_removed) xóa FILE theo đường dẫn lưu (có thể tuyệt đối
      → file thật);
    - nguồn Kho ảnh / âm thanh 'auto': tắt — đồng bộ đầu phiên quét thư mục thật (Drive);
    - nguồn Claude khai theo dự án / job (projects/jobs.llm_provider, M1.4b): bỏ → mọi lời gọi theo LLM_PROVIDER=mock (claude_cli tốn hạn
      mức gói thật dù 0 USD)."""
    done = []
    conn = sqlite3.connect(db)
    try:
        def cols(t):
            return {r[1] for r in conn.execute(f"PRAGMA table_info({t})")}

        def run(label, sql):
            done.append(f"{label}: {conn.execute(sql).rowcount}")
        if "status" in cols("asset_images"):
            run("asset_images removed", "DELETE FROM asset_images WHERE status='removed'")
        for t in ("asset_sources", "sound_sources"):
            if "auto" in cols(t):
                run(f"{t} auto→0", f"UPDATE {t} SET auto=0 WHERE auto<>0")
        if "llm_provider" in cols("projects"):
            run("projects.llm_provider→NULL", "UPDATE projects SET llm_provider=NULL WHERE llm_provider IS NOT NULL")
        if "llm_provider" in cols("jobs"):
            run("jobs.llm_provider→mock", "UPDATE jobs SET llm_provider='mock' WHERE llm_provider IS NOT NULL")
        conn.commit()
    finally:
        conn.close()
    return done


def copy_db(src: str, out_dir: str, data: Optional[str] = None) -> Dict:
    """Bản SAO của CSDL thật: mở mode=ro (không ghi, không khóa ghi) → backup sang out_dir/manifest.sqlite, rồi làm trơ (neutralize).
    `data` (thư mục dự án thật): chỉ chép thư mục `<id>/images` (thẻ ảnh) — Dashboard đo chỉ ghi vào bản sao."""
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "manifest.sqlite")
    ro = sqlite3.connect(pathlib.Path(src).resolve().as_uri() + "?mode=ro", uri=True)   # as_uri: đường Windows / ký tự ?#% an toàn
    try:
        to = sqlite3.connect(dst)
        ro.backup(to)
        to.close()
    finally:
        ro.close()
    notes = neutralize(dst)
    out_data = os.path.join(out_dir, "projects")
    os.makedirs(out_data, exist_ok=True)
    if data and os.path.isdir(data):
        for name in os.listdir(data):
            img = os.path.join(data, name, "images")
            if os.path.isdir(img):
                shutil.copytree(img, os.path.join(out_data, name, "images"), dirs_exist_ok=True)
    conn = sqlite3.connect(dst)
    try:
        made = [(r[0], r[1], "copy") for r in conn.execute("SELECT id, name FROM projects ORDER BY id")]
    finally:
        conn.close()
    return {"db": dst, "data": out_data, "projects": made, "neutralized": notes}


# ---------------------------------------------------------------- đầu dò trong tiến trình Streamlit
PROBE = r'''
# Đầu dò đo tải (tools/load_test_ui.py) — chỉ nạp khi LOAD_PROBE_OUT có; không đổi hành vi, chỉ đếm giờ.
import os, sys, json, time, threading, sqlite3
_OUT = os.environ.pop("LOAD_PROBE_OUT", None)   # bỏ khỏi môi trường: tiến trình python con (Blender, công cụ) không ghi đè probe.json
if _OUT:
    import functools
    _LOCK_WAIT = float(os.environ.get("LOAD_PROBE_LOCK_WAIT", "0.05"))
    _LAT = float(os.environ.get("LOAD_MOCK_LATENCY", "0") or 0)
    _S = {"writes": 0, "write_s": 0.0, "waits": 0, "wait_s": 0.0, "wait_max": 0.0, "locked_errors": 0, "reads": 0, "read_s": 0.0,
          "connects": 0}
    _M = threading.Lock()
    _W = ("INSERT", "UPDATE", "DELETE", "REPLACE", "BEGIN", "CREATE", "DROP", "ALTER")

    def _rec(sql, dt, err=None):
        w = sql is None or str(sql).lstrip()[:8].upper().startswith(_W)
        with _M:
            if err is not None and "locked" in str(err).lower():
                _S["locked_errors"] += 1
            if w:
                _S["writes"] += 1; _S["write_s"] += dt
                if dt >= _LOCK_WAIT:
                    _S["waits"] += 1; _S["wait_s"] += dt; _S["wait_max"] = max(_S["wait_max"], dt)
            else:
                _S["reads"] += 1; _S["read_s"] += dt

    class _Timed(sqlite3.Connection):
        def _t(self, fn, sql, *a):
            t = time.perf_counter()
            try:
                r = fn(sql, *a)
            except sqlite3.OperationalError as e:
                _rec(sql, time.perf_counter() - t, e)
                raise
            _rec(sql, time.perf_counter() - t)
            return r

        def execute(self, sql, *a):
            return self._t(super().execute, sql, *a)

        def executemany(self, sql, *a):
            return self._t(super().executemany, sql, *a)

        def commit(self):
            t = time.perf_counter()
            try:
                return super().commit()
            finally:
                _rec(None, time.perf_counter() - t)

    _connect = sqlite3.connect

    def connect(*a, **k):
        k.setdefault("factory", _Timed)
        with _M:
            _S["connects"] += 1
        return _connect(*a, **k)
    sqlite3.connect = connect

    def _slow_mocks():                     # độ trễ mạng giả trên submit/status của bộ giả (như tools/load_test.py)
        while "core.providers" not in sys.modules:
            time.sleep(0.2)
        mod = sys.modules["core.providers"]
        while not all(hasattr(mod, n) for n in ("MockImageProvider", "MockVideoProvider")):
            time.sleep(0.05)
        for cls in (mod.MockImageProvider, mod.MockVideoProvider):
            for name in ("submit", "status"):
                fn = getattr(cls, name, None)
                if fn is None or getattr(fn, "_slow", False):
                    continue
                @functools.wraps(fn)          # giữ chữ ký (core/sent_package._bind đọc inspect.signature)
                def slow(*a, _fn=fn, **k):
                    time.sleep(_LAT)
                    return _fn(*a, **k)
                slow._slow = True
                setattr(cls, name, slow)
    if _LAT > 0:
        threading.Thread(target=_slow_mocks, name="load-probe-mock", daemon=True).start()

    def _dump():
        while True:
            names = {}
            for t in threading.enumerate():
                key = t.name.rstrip("0123456789-_ ") or t.name
                names[key] = names.get(key, 0) + 1
            with _M:
                snap = dict(_S)
            snap.update(threads=threading.active_count(), thread_names=names, at=time.time())
            tmp = _OUT + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(snap, f)
                os.replace(tmp, _OUT)
            except OSError:
                pass
            time.sleep(0.5)
    threading.Thread(target=_dump, name="load-probe-dump", daemon=True).start()

# Nạp tiếp sitecustomize gốc của hệ thống / venv (đầu dò đứng đầu PYTHONPATH nên che nó)
def _chain():
    import importlib.machinery, importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    rest = [p for p in sys.path if os.path.abspath(p or ".") != here]
    spec = importlib.machinery.PathFinder.find_spec("sitecustomize", rest)
    if spec and spec.loader and os.path.abspath(spec.origin or "") != os.path.abspath(__file__):
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
try:
    _chain()
except Exception:
    pass
'''


def write_probe(dir_: str) -> str:
    os.makedirs(dir_, exist_ok=True)
    path = os.path.join(dir_, "sitecustomize.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(PROBE)
    return path


def read_probe(path: str) -> Dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


SECRET_RE = re.compile(r"(_KEY|_TOKEN|_SECRET|PASSCODE|PASSWORD)$|^ANTHROPIC_|^CLAUDE_CODE_", re.I)


def app_env(db: str, data: str, work: str, latency: float, probe_dir: str) -> Dict[str, str]:
    """Môi trường của tiến trình Streamlit đo: mọi nhà cung cấp GIẢ, không khóa API (bỏ theo DANH SÁCH + theo MẪU tên *_KEY / *_TOKEN /
    *_SECRET / *PASSCODE / ANTHROPIC_* — rà V2: SYNC_API_KEY, MESHY_API_KEY, ANTHROPIC_AUTH_TOKEN…), cờ theo tệp tạm (không baseline
    sản xuất), Kho ảnh + mô hình âm thanh trong thư mục đo (không ghi data/ của repo). Đồng bộ đầu phiên chạy NỀN như sản xuất
    (DASHBOARD_SYNC_BACKGROUND mặc định) — không phồng bước "Mở dự án"."""
    home = os.path.dirname(db)
    env = {k: v for k, v in os.environ.items() if k not in SECRET_ENV and not SECRET_RE.search(k)}
    env.update(PIPELINE_DB=db, PIPELINE_DATA=data, IMAGE_PROVIDER="mock", VIDEO_PROVIDER="mock", AUDIO_PROVIDER="mock",
               LLM_PROVIDER="mock", SUBJECT_PROVIDER="mock", MOCK_REAL_MEDIA="1", FEATURE_UI_V2="1", DASHBOARD_AUTH="off",
               FEATURE_SETTINGS_FILE=os.path.join(work, "feature_settings.json"), FEATURE_BASELINE="0",
               ASSET_DIR=os.path.join(home, "assets"), SOUND_MODEL_DIR=os.path.join(home, "models"),
               PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
               LOAD_PROBE_OUT=os.path.join(work, "probe.json"), LOAD_PROBE_LOCK_WAIT=str(LOCK_WAIT_S), LOAD_MOCK_LATENCY=str(latency),
               PYTHONPATH=os.pathsep.join([probe_dir] + [x for x in [os.environ.get("PYTHONPATH")] if x]))
    env.pop("DASHBOARD_SYNC_BACKGROUND", None)
    return env


# ---------------------------------------------------------------- tổng hợp
def pct(values: List[float], q: float) -> Optional[float]:
    xs = sorted(v for v in values if v is not None)
    if not xs:
        return None
    if len(xs) == 1:
        return round(xs[0], 3)
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 3)


def summarize(levels: List[Dict]) -> Dict:
    """levels: [{"n", "sessions": [{"steps": {step: giây|None}, "errors": {step: lời}}], "server": {"cpu_peak", "rss_peak_mb",
    "threads_base", "threads_peak"}, "probe": {...}}] → bảng p50/p95 theo bước × N, ngưỡng chậm, khâu nghẽn."""
    rows = []
    first_slow = None
    for lv in levels:
        n = lv["n"]
        per = {}
        for step in STEPS:
            vals = [s["steps"].get(step) for s in lv["sessions"]]
            errs = sum(1 for s in lv["sessions"] if step in s.get("errors", {}))
            nr = sum(1 for s in lv["sessions"] if step in s.get("no_rerun", []))
            per[step] = {"p50": pct(vals, 0.5), "p95": pct(vals, 0.95), "max": pct(vals, 1.0), "errors": errs, "no_rerun": nr}
        # rà V3: bước LỖI / quá hạn ở một phiên = chậm (không bị pct() bỏ qua mà ra "không mức nào chậm")
        slow = [s for s in MAIN_STEPS if (per[s]["p95"] or 0) > SLOW_S or per[s]["errors"]]
        if slow and first_slow is None:
            first_slow = {"n": n, "steps": slow}
        srv, pr = lv.get("server", {}), lv.get("probe", {})
        base = srv.get("threads_base") or 0
        rows.append({"n": n, "steps": per, "slow": slow, "cpu_peak": srv.get("cpu_peak"), "rss_peak_mb": srv.get("rss_peak_mb"),
                     "sys_cpu_peak": srv.get("sys_cpu_peak"),
                     "threads_base": base, "threads_peak": srv.get("threads_peak"),
                     "threads_per_session": round(((srv.get("threads_peak") or base) - base) / n, 2) if n else None,
                     "sqlite": {k: pr.get(k) for k in ("writes", "waits", "wait_s", "wait_max", "locked_errors", "connects")},
                     "thread_names": pr.get("thread_names", {})})
    top = rows[-1] if rows else None
    bottleneck = None
    if top:
        step = max(STEPS, key=lambda s: (top["steps"][s]["errors"], top["steps"][s]["p95"] or 0))
        bottleneck = {"n": top["n"], "step": step, "p95": top["steps"][step]["p95"], "errors": top["steps"][step]["errors"]}
        sq = top["sqlite"]
        total = sum(v or 0 for lv in levels[-1:] for s_ in lv["sessions"] for v in s_["steps"].values())
        # rà V5: CPU xét TRƯỚC — "chờ khóa" đo theo thời gian lệnh ghi, gồm cả chờ GIL khi CPU bão hòa
        if top.get("sys_cpu_peak") and top["sys_cpu_peak"] >= 95:
            bottleneck["note"] = "CẢ MÁY đo bão hòa CPU (trình duyệt đo + Streamlit chung máy) — số đo phồng; đo lại với ít phiên hơn / máy mạnh hơn"
        elif top.get("cpu_peak") and top["cpu_peak"] >= 90:
            bottleneck["note"] = "CPU tiến trình Streamlit ~bão hòa một lõi (Python GIL) — script rerun của các phiên xếp hàng"
        elif sq.get("wait_s") and total and sq["wait_s"] >= 0.25 * total:
            bottleneck["note"] = "chờ khóa SQLite (gồm chờ GIL) ≥ 1/4 tổng thời gian các bước"
    errors = sum(r["steps"][s]["errors"] for r in rows for s in STEPS)
    return {"slow_s": SLOW_S, "rows": rows, "first_slow": first_slow, "bottleneck": bottleneck, "errors": errors}


def _f(x, unit="") -> str:
    return "—" if x is None else f"{x}{unit}"


def markdown(summary: Dict, meta: Dict) -> str:
    out = [f"# Đo tải giao diện (M8.3) — {meta.get('when', '')}", "",
           f"- Máy: {meta.get('host', '')} · Python {meta.get('python', '')} · dữ liệu: {meta.get('data', '')}",
           f"- Nhà cung cấp GIẢ (0 USD), độ trễ giả {meta.get('latency')} s; ngưỡng chậm màn chính: p95 > {summary['slow_s']} s", ""]
    out += ["## Thời gian tới khi màn ổn định (giây, p50 / p95)", "",
            "| Bước | " + " | ".join(f"N={r['n']}" for r in summary["rows"]) + " |",
            "|---|" + "---|" * len(summary["rows"])]
    for step in STEPS:
        cells = []
        for r in summary["rows"]:
            c = r["steps"][step]
            cells.append(f"{_f(c['p50'])} / {_f(c['p95'])}" + (f" ⚠{c['errors']} lỗi" if c["errors"] else "")
                         + (f" ·{c['no_rerun']} không rerun" if c.get("no_rerun") else "")
                         + (" 🐢" if step in r["slow"] else ""))
        out.append(f"| {STEP_LABEL[step]} | " + " | ".join(cells) + " |")
    out += ["", "## Server (tiến trình Streamlit)", "",
            "| N | CPU đỉnh % | CPU cả máy đỉnh % | RAM đỉnh MB | Luồng gốc → đỉnh | Luồng thêm / phiên | Lệnh ghi SQLite | Chờ khóa (≥ "
            f"{LOCK_WAIT_S} s) | Chờ lâu nhất s | Lỗi locked |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary["rows"]:
        sq = r["sqlite"]
        out.append(f"| {r['n']} | {_f(r['cpu_peak'])} | {_f(r.get('sys_cpu_peak'))} | {_f(r['rss_peak_mb'])} | {_f(r['threads_base'])} → {_f(r['threads_peak'])} | "
                   f"{_f(r['threads_per_session'])} | {_f(sq.get('writes'))} | {_f(sq.get('waits'))} ({_f(sq.get('wait_s'))} s) | "
                   f"{_f(sq.get('wait_max'))} | {_f(sq.get('locked_errors'))} |")
    fs, bn = summary["first_slow"], summary["bottleneck"]
    out += ["", "## Kết luận", "",
            f"- Ngưỡng chậm xuất hiện ở: {'N=' + str(fs['n']) + ' (' + ', '.join(STEP_LABEL[s] for s in fs['steps']) + ')' if fs else 'không mức nào'}",
            f"- Khâu nghẽn (lỗi rồi p95 lớn nhất ở N={bn['n']}): {STEP_LABEL[bn['step']]} {bn['p95']} s"
            + (f" · {bn['errors']} phiên lỗi" if bn.get("errors") else "") + (f" — {bn['note']}" if bn.get("note") else "")
            if bn else "- Khâu nghẽn: —",
            f"- Tổng bước lỗi: {summary.get('errors', 0)}" + (" — xem ảnh loi_n*/ trong thư mục kết quả" if summary.get("errors") else ""),
            "- Không đo ở đây: khóa Blender, hàng đợi Claude CLI, giới hạn Deepix / Clip AI (bộ giả).",
            "- Khác máy chính: DASHBOARD_AUTH=off (bỏ ghi team.touch / quyền mỗi lần chạy lại), `streamlit run dashboard/app.py` (máy chính: "
            "dashboard.serve), trình duyệt đo chạy CÙNG máy với server — tranh chấp SQLite thấp hơn, CPU cao hơn thực tế.",
            "- Mỗi số đo gồm ~0.3 s cửa sổ \"yên\" của bộ đo; \"không rerun\" = bấm mà không có lượt chạy lại trong "
            f"{NO_RERUN_S:.0f} s (số đo gồm thời gian chờ đó). Luồng thêm / phiên tính cả luồng khởi một lần mỗi tiến trình (N=1 phồng)."]
    if summary["rows"]:
        names = summary["rows"][-1]["thread_names"]
        if names:
            top = sorted(names.items(), key=lambda kv: -kv[1])[:8]
            out.append(f"- Luồng theo tên ở N={summary['rows'][-1]['n']}: " + ", ".join(f"{k}×{v}" for k, v in top))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- chạy thật (trình duyệt)
BUSY_STATES = ("running", "rerunRequested", "stopRequested")   # rà C3: cả lúc đã bấm mà server chưa nhận rerun
JS_BUSY = ("() => !!document.querySelector('[data-testid=\"stStatusWidget\"]') || "
           f"{list(BUSY_STATES)!r}.includes(document.querySelector('.stApp')?.getAttribute('data-test-script-state'))")
# Đếm số lần trang CHUYỂN sang bận (MutationObserver từ lúc tải trang): một bước chỉ "ổn định" khi đã thấy lượt chạy lại MỚI của chính nó
# rồi yên — không trả sớm khi server tải nặng chưa kịp nhận cú bấm (thăm dò 0.1 s có thể lỡ một lượt ngắn; bộ đếm thì không)
JS_COUNT_RUNS = """(() => {
  window.__ltRuns = 0;
  const busy = v => %s.includes(v);
  const hook = () => {
    const el = document.querySelector('.stApp');
    if (!el) return setTimeout(hook, 30);
    let last = el.getAttribute('data-test-script-state');
    if (busy(last)) window.__ltRuns++;
    new MutationObserver(() => {
      const v = el.getAttribute('data-test-script-state');
      if (busy(v) && !busy(last)) window.__ltRuns++;
      last = v;
    }).observe(el, {attributes: true, attributeFilter: ['data-test-script-state']});
  };
  hook();
})()""" % json.dumps(list(BUSY_STATES))
NO_RERUN_S = 10.0                                # bấm xong mà trong ngần này giây không có lượt chạy lại nào → ghi "không rerun"


async def runs(pg) -> int:
    return int(await pg.evaluate("() => window.__ltRuns || 0") or 0)


async def settle(pg, before: int = 0, timeout: float = 120.0) -> bool:
    """Chờ tới khi màn ổn định SAU một lượt chạy lại mới (bộ đếm > `before`) và không bận 3 lần liền cách 0.1 s. Trả True; không thấy lượt
    chạy lại nào trong NO_RERUN_S (cú bấm không gây rerun) → False khi đã yên; quá hạn → TimeoutError."""
    t0, quiet = time.perf_counter(), 0
    while time.perf_counter() - t0 < timeout:
        quiet = 0 if await pg.evaluate(JS_BUSY) else quiet + 1
        if quiet >= 3:
            if await runs(pg) > before:
                return True
            if time.perf_counter() - t0 > NO_RERUN_S:
                return False
        await asyncio.sleep(0.1)
    raise TimeoutError("màn không ổn định")


async def _radio(pg, label: str) -> None:
    await pg.locator('.st-key-step label[data-testid="stRadioOption"]', has_text=label).first.click()


async def session(browser, url: str, i: int, n_projects: int, log, shots_dir: Optional[str] = None) -> Dict:
    ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
    await ctx.add_init_script(JS_COUNT_RUNS)
    pg = await ctx.new_page()
    steps, errors, no_rerun = {}, {}, []

    async def step(name, act):
        t0 = time.perf_counter()
        try:
            before = 0 if name == "home" else await runs(pg)
            await act()
            if not await settle(pg, before):
                no_rerun.append(name)           # số đo của bước này gồm NO_RERUN_S chờ — ghi rõ, không coi là màn nhanh
            steps[name] = round(time.perf_counter() - t0, 3)
        except Exception as e:  # noqa: BLE001 - một bước lỗi không dừng phiên: ghi lại, đo tiếp
            steps[name] = None
            errors[name] = f"{type(e).__name__}: {str(e)[:160]}"
            if shots_dir and len(errors) == 1:   # ảnh màn lúc lỗi ĐẦU của phiên — chẩn đoán (trang trắng / "Connecting" / lỗi Python)
                try:
                    os.makedirs(shots_dir, exist_ok=True)
                    await pg.screenshot(path=os.path.join(shots_dir, f"loi_s{i}_{name}.png"), timeout=10000)
                except Exception:  # noqa: BLE001
                    pass

    async def home():
        await pg.goto(url)
        await pg.wait_for_selector(".st-key-step", timeout=120000)
        await settle(pg, 0)                      # lượt vẽ đầu (mở mặc định dự án #1) xong rồi mới bấm Trang chủ
        before = await runs(pg)
        await _radio(pg, "Tất cả dự án")
        await settle(pg, before)

    async def open_():
        opens = pg.locator("button", has_text="Mở →")
        await opens.nth(i % max(1, min(n_projects, await opens.count()))).click()

    async def click_first(text: str, exact: bool, why: str, wait: float = 20.0):
        """Bấm nút đầu tiên khớp + bấm được; màn có thể còn đang vẽ phần sau (tải nặng) → thử lại tới `wait` giây (tính vào bước)."""
        t0 = time.perf_counter()
        while True:
            for b in await pg.locator("button", has_text=text).all():
                try:
                    if (not exact or (await b.inner_text()).strip() == text) and await b.is_enabled():
                        await b.click(timeout=5000)
                        return
                except Exception:  # noqa: BLE001 - nút bị vẽ lại giữa chừng: tìm lại
                    continue
            if time.perf_counter() - t0 > wait:
                raise LookupError(why)
            await asyncio.sleep(0.25)

    async def approve():
        await click_first("✔ Duyệt", True, "không có ảnh nào chờ duyệt")

    async def gen():
        await click_first("▶ Gen video", False, "nút Gen video không bấm được")

    await step("home", home)
    await step("open", open_)
    await step("storyboard", lambda: _radio(pg, "Storyboard"))
    await step("approve", approve)
    await step("video", lambda: _radio(pg, "Video"))
    await step("gen", gen)
    await ctx.close()
    if errors:
        log(f"    phiên {i}: lỗi {errors}")
    return {"i": i, "steps": steps, "errors": errors, "no_rerun": no_rerun}


async def run_sessions(n: int, url: str, n_projects: int, chrome: Optional[str], log, shots_dir: Optional[str] = None) -> List[Dict]:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        kw = {"executable_path": chrome} if chrome else {}
        browser = await pw.chromium.launch(**kw)
        try:
            return list(await asyncio.gather(*[session(browser, url, i, n_projects, log, shots_dir) for i in range(n)]))
        finally:
            await browser.close()


class Sampler(threading.Thread):
    """CPU% / RSS / số luồng của tiến trình Streamlit mỗi 0.5 s (psutil)."""

    def __init__(self, pid: int):
        super().__init__(daemon=True)
        import psutil
        self.proc = psutil.Process(pid)
        self.samples: List[Dict] = []
        self.stop = threading.Event()

    def run(self):
        import psutil
        self.proc.cpu_percent(None)
        psutil.cpu_percent(None)
        while not self.stop.is_set():
            try:
                with self.proc.oneshot():
                    self.samples.append({"cpu": self.proc.cpu_percent(None), "rss_mb": self.proc.memory_info().rss / 2**20,
                                         "threads": self.proc.num_threads(), "sys_cpu": psutil.cpu_percent(None)})
            except Exception:  # noqa: BLE001 - tiến trình đã dừng
                return
            self.stop.wait(0.5)

    def peaks(self, base_threads: int) -> Dict:
        s = self.samples
        return {"cpu_peak": round(max((x["cpu"] for x in s), default=0), 1), "rss_peak_mb": round(max((x["rss_mb"] for x in s), default=0), 1),
                "threads_base": base_threads, "threads_peak": max((x["threads"] for x in s), default=base_threads),
                "cpu_mean": round(statistics.mean(x["cpu"] for x in s), 1) if s else None,
                # CPU CẢ MÁY (mọi lõi, %): trình duyệt đo chạy CÙNG máy — gần 100 % thì số đo phồng do máy đo, không chỉ do Streamlit
                "sys_cpu_peak": round(max((x.get("sys_cpu", 0) for x in s), default=0), 1)}


def _ver(path: str) -> int:
    import re as _re
    m = _re.search(r"chromium[-_](\d+)", path.replace("\\", "/"))
    return int(m.group(1)) if m else -1


def find_chrome(arg: Optional[str]) -> Optional[str]:
    """Chromium của Playwright (PLAYWRIGHT_BROWSERS_PATH, /opt/pw-browsers, %LOCALAPPDATA%\\ms-playwright, ~/.cache/ms-playwright; bản số
    lớn nhất — so SỐ, không so chữ) → Chrome / Edge của máy (ui_snapshot.find_browser). None = để Playwright tự tìm (có thể cần
    `playwright install` — đề bài cấm: hãy truyền --chrome)."""
    if arg:
        return arg
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""), "/opt/pw-browsers",
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright") if os.environ.get("LOCALAPPDATA") else "",
             os.path.expanduser("~/.cache/ms-playwright")]
    hits = []
    for root in [r for r in roots if r and os.path.isdir(r)]:
        for pat in ("chromium-*/chrome-linux/chrome", "chromium-*/chrome-linux64/chrome", "chromium-*/chrome-win/chrome.exe",
                    "chromium-*/chrome-win64/chrome.exe", "chromium/chrome-linux/chrome"):
            hits += glob.glob(os.path.join(root, pat))
    if hits:
        return max(hits, key=_ver)
    try:
        import ui_snapshot
        return ui_snapshot.find_browser()
    except Exception:  # noqa: BLE001
        return None


def port_free(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sk:
        try:
            sk.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def listens(pid: int, port: int) -> bool:
    """Tiến trình `pid` (hoặc con của nó) đang nghe `port` — health 'ok' phải là của Streamlit ĐO, không phải Dashboard thật cùng cổng."""
    import psutil
    try:
        procs = [psutil.Process(pid)] + psutil.Process(pid).children(recursive=True)
    except psutil.Error:
        return False
    for pr in procs:
        try:
            conns = pr.net_connections(kind="tcp") if hasattr(pr, "net_connections") else pr.connections(kind="tcp")
        except psutil.Error:
            continue
        if any(c.laddr and c.laddr.port == port and c.status == psutil.CONN_LISTEN for c in conns):
            return True
    return False


PROD_PORTS = (8501, 8502)                        # cổng Dashboard thật trên máy chính — không bao giờ đo ở đây


def run_level(n: int, template: Dict, args, log) -> Dict:
    work = tempfile.mkdtemp(prefix=f"load_ui_n{n}_")
    home = os.path.join(work, "data")          # <work>/data/manifest.sqlite: assets.resolve() giải đường tương đối về <work>, không về repo
    os.makedirs(home)
    db = os.path.join(home, "manifest.sqlite")
    shutil.copy2(template["db"], db)
    data = os.path.join(home, "projects")
    shutil.copytree(template["data"], data)
    probe_dir = os.path.join(work, "probe")
    write_probe(probe_dir)
    env = app_env(db, data, work, args.latency, probe_dir)
    port = args.port
    if port in PROD_PORTS or not port_free(port):
        raise RuntimeError(f"Cổng {port} " + ("là cổng Dashboard thật" if port in PROD_PORTS else "đang bận") + " — chọn --port khác")
    with open(os.path.join(work, "streamlit.log"), "w", encoding="utf-8") as lg:
        app = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.port", str(port),
                                "--server.headless", "true", "--browser.gatherUsageStats", "false"], cwd=ROOT, env=env, stdout=lg,
                               stderr=subprocess.STDOUT)
    try:
        for _ in range(240):
            if app.poll() is not None:
                raise RuntimeError(f"Streamlit đo đã thoát (mã {app.returncode}) — xem {work}/streamlit.log")
            try:
                if urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2).read().strip() == b"ok":
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError(f"Streamlit không lên — xem {work}/streamlit.log")
        if not listens(app.pid, port):
            raise RuntimeError(f"Cổng {port} trả lời nhưng KHÔNG phải Streamlit đo (pid {app.pid}) — dừng, không bấm gì")
        time.sleep(1.0)
        import psutil
        base = psutil.Process(app.pid).num_threads()
        smp = Sampler(app.pid)
        smp.start()
        t0 = time.perf_counter()
        sessions = asyncio.run(run_sessions(n, f"http://127.0.0.1:{port}/", len(template["projects"]), args.chrome, log,
                                            os.path.join(args.out, f"loi_n{n}") if args.out else None))
        wall = round(time.perf_counter() - t0, 2)
        time.sleep(1.0)                           # đầu dò ghi 0.5 s / lần
        smp.stop.set()
        smp.join(3)
        probe = read_probe(env["LOAD_PROBE_OUT"])
        return {"n": n, "sessions": sessions, "server": smp.peaks(base), "probe": probe, "wall_s": wall, "work": work}
    finally:
        app.terminate()
        try:
            app.wait(15)
        except subprocess.TimeoutExpired:
            app.kill()
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default=",".join(map(str, LEVELS)), help="số phiên mỗi mức, phẩy (mặc định 1,2,5,10)")
    ap.add_argument("--projects", type=int, default=3)
    ap.add_argument("--shots", type=int, default=30, help="số shot mỗi dự án giả (20–40)")
    ap.add_argument("--db", help="CSDL thật để SAO (mode=ro) thay dữ liệu giả")
    ap.add_argument("--data", help="thư mục ảnh của --db (được chép, không ghi vào bản gốc)")
    ap.add_argument("--latency", type=float, default=0.2, help="độ trễ giả (giây) trên submit/status của bộ giả")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--chrome", help="đường dẫn Chromium (mặc định: PLAYWRIGHT_BROWSERS_PATH hoặc bản playwright tự tìm)")
    ap.add_argument("--out", help="thư mục ghi load_ui.md + load_ui.json (mặc định: thư mục tạm)")
    ap.add_argument("--keep", action="store_true", help="giữ thư mục làm việc từng mức (log streamlit, CSDL sau đo)")
    args = ap.parse_args(argv)
    try:
        import playwright  # noqa: F401
        import psutil  # noqa: F401
    except ImportError as e:
        print(f"Thiếu gói: {e.name} — chạy: pip install playwright psutil (KHÔNG chạy 'playwright install')", file=sys.stderr)
        return 2
    levels = [int(x) for x in args.levels.split(",") if x.strip()]
    args.chrome = find_chrome(args.chrome)
    tpl_dir = tempfile.mkdtemp(prefix="load_ui_tpl_")
    try:
        if args.db:
            template = copy_db(args.db, tpl_dir, args.data)
            label = f"bản sao {args.db} ({len(template['projects'])} dự án)"
        else:
            template = build_data(os.path.join(tpl_dir, "d"), args.projects, args.shots)
            label = f"giả {args.projects} dự án × {args.shots} shot"
        results = []
        for n in levels:
            print(f"N = {n} …", flush=True)
            lv = run_level(n, template, args, print)
            print(f"  xong trong {lv['wall_s']} s", flush=True)
            results.append(lv)
    finally:
        shutil.rmtree(tpl_dir, ignore_errors=True)
    summary = summarize(results)
    import platform
    meta = {"when": time.strftime("%Y-%m-%d %H:%M"), "host": f"{platform.system()} {platform.release()} · {os.cpu_count()} lõi",
            "python": platform.python_version(), "data": label, "latency": args.latency}
    out = args.out or tempfile.mkdtemp(prefix="load_ui_out_")
    os.makedirs(out, exist_ok=True)
    md = markdown(summary, meta)
    with open(os.path.join(out, "load_ui.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(out, "load_ui.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "summary": summary, "levels": [{k: v for k, v in r.items() if k != "work"} for r in results]}, f,
                  ensure_ascii=False, indent=1)
    print(md)
    print(f"Đã ghi {out}/load_ui.md + load_ui.json")
    return 1 if summary["errors"] else 0         # rà V3: có bước lỗi → mã ≠ 0 (lượt đo không sạch)


if __name__ == "__main__":
    sys.exit(main())
