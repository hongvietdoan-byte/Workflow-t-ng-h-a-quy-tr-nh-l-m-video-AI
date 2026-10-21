"""Ba sơ đồ dây chuyền SỐNG (C-DEVSYS-MAPS, người dùng 21/10: "vẽ thêm 3 sơ đồ này vào AI dev sys để theo dõi cụ thể chi tiết sự thay đổi").

Dữ liệu: devsys/pipeline_maps.json (mốc 17/10 = docs/so_do/gen_dashboard.py, gen_hien_trang_khau.py, SO_DO_TRUONG_CAU_TRUC_2026-10.svg).
Màu TÍNH mỗi lần dựng, không tô tay:
  - ô Dashboard / nút trường: thiếu bằng chứng (tệp + chữ phải có) → ĐỎ; việc kế hoạch đang làm (🔄) → TÍM; cờ hiệu lực TẮT / chỉ người /
    việc chưa ✅ → VÀNG; còn lại XANH;
  - hàng khâu: từ devsys/stages.json theo cờ thật (stages.effective) như sơ đồ 17/10 (tốn tiền thiếu kiểm trước / đọc chữ tự do → ĐỎ,
    chỉ người / cờ tắt → VÀNG) + TÍM khi việc kế hoạch gắn khâu (devsys/plan_map.json) đang làm + số lỗi mở (devsys/errors.json).
Thay đổi: mỗi lần dựng ghi ảnh chụp màu + đầu vào của mọi ô vào devsys/data/pipeline_maps_history.jsonl (khi có đổi) → tab Thay đổi so
lần trước / so mốc 17/10, lý do = đầu vào đổi (việc ✅, cờ bật, bằng chứng có / mất, lỗi mở).
Theo DỰ ÁN: sự kiện ui_step / cli_step (core/ui_step, cờ ui_step_log) đọc từ CSDL bằng mode=ro → ô nút tô theo lần bấm thật; lệnh CLI làm
thay Dashboard → nút ảo nét đứt "THIẾU NÚT: <việc>". Không đọc data/ sản xuất ngoài trạng thái cờ + CSDL (chỉ đọc); không ghi CSDL.
Xuất SVG: `py -m devsys.pipeline_maps <thư mục>`.
"""
import datetime
import glob as _glob
import json
import os
import sqlite3
from typing import Callable, Dict, List, Optional
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_FILE = os.path.join(ROOT, "devsys", "pipeline_maps.json")
HISTORY_FILE = os.path.join(ROOT, "devsys", "data", "pipeline_maps_history.jsonl")

COLORS = {"xanh": "#4dff6a", "vang": "#ffb020", "do": "#ff5a5a", "tim": "#b388ff", "xam": "#5b6b7a"}
COLOR_NAME = {"xanh": "có, đang chạy", "vang": "có code nhưng cờ tắt / chỉ người / theo nút / việc chưa xong", "do": "thiếu (nút / hàm / kiểm)",
              "tim": "việc kế hoạch đang sửa ô này", "xam": "dự án này chưa ai bấm"}
MOC = {"G": "xanh", "A": "vang", "R": "do", "C": "xanh"}
BG, PANEL, TEXT, MUTED = "#12161d", "#111a24", "#e6edf3", "#9aa4ae"
DONE = ("✅", "✖")


def load(path: str = MAP_FILE) -> Dict:
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    for key in ("dashboard", "khau", "truong"):
        if key not in doc:
            raise ValueError(f"pipeline_maps.json thiếu mục '{key}'")
    return doc


# ---- đầu vào ---------------------------------------------------------------------------------------------------------------------
def _evidence_ok(root: str, ev: Dict, cache: Dict) -> bool:
    key = (ev.get("glob"), ev.get("text"))
    if key not in cache:
        found = False
        for path in sorted(_glob.glob(os.path.join(root, ev["glob"]), recursive=True)):
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    if ev.get("text", "") in f.read():
                        found = True
                        break
            except OSError:
                continue
        cache[key] = found
    return cache[key]


def plan_statuses() -> Dict[str, str]:
    """{mã việc: trạng thái} của kế hoạch chính (mục 'chinh' devsys/plans.json); đọc lỗi → {}."""
    try:
        from . import plan_progress
        plan = plan_progress.load(plan_progress.main_plan_file()) or {"waves": []}
        return {t["id"]: t["status"] for w in plan["waves"] for t in w["tasks"]}
    except (OSError, ValueError):
        return {}


def _flag_state() -> Callable[[str], str]:
    from core import features

    def state(name: str) -> str:
        return features.state(name) if name in features.FEATURES else "unknown"
    return state


def _cell_color(cell: Dict, root: str, state, plan: Dict[str, str], cache: Dict, unknown_flags: set) -> Dict:
    """Màu + lý do + đầu vào của một ô (Dashboard / nút trường)."""
    ev = cell.get("evidence") or []
    oks = [_evidence_ok(root, e, cache) for e in ev]
    have = any(oks) if cell.get("evidence_any") else all(oks)
    flags = {}
    for f in cell.get("flags") or []:
        s = state(f)
        if s == "unknown":
            unknown_flags.add(f)
        flags[f] = s
    tasks = {t: plan.get(t, "?") for t in cell.get("plan") or [] if t in plan}
    why = []
    if ev and not have:
        color = "do"
        why += [f"thiếu bằng chứng: '{e['text']}' trong {e['glob']}" for e, ok in zip(ev, oks) if not ok]
    elif any(s == "🔄" for s in tasks.values()):
        color = "tim"
        why += [f"việc {t} đang làm" for t, s in tasks.items() if s == "🔄"]
    elif any(s != "on" for s in flags.values()):
        color = "vang"
        why += [f"cờ {f} {'không có trong code' if s == 'unknown' else s.upper()}" for f, s in flags.items() if s != "on"]
    elif cell.get("loose"):
        color = "vang"
        why.append("lỏng: chỉ người / chỉ theo nút / bỏ qua được (mốc 17/10)")
    elif any(s not in DONE for s in tasks.values()):
        color = "vang"
        why += [f"việc {t} {s} chưa xong" for t, s in tasks.items() if s not in DONE]
    else:
        color = "xanh"
        why.append("có bằng chứng" + (", cờ bật" if flags else "") + (", việc kế hoạch xong" if tasks else ""))
    inputs = {"evidence": have, "flags": flags, "plan": tasks}
    return {"id": cell["id"], "color": color, "why": why, "moc": MOC.get(cell.get("moc"), "xam"), "inputs": inputs}


def _check(states: List[str]) -> str:
    if any(s == "chay" for s in states):
        return "xanh"
    if any(s in ("tat", "hoc_viec") for s in states):
        return "vang"
    return "do"


def _khau_rows(doc: Dict, stage_rows: List[Dict], plan: Dict[str, str], plan_khau: Dict[str, List[str]],
               open_errors: Optional[Dict[str, int]]) -> List[Dict]:
    from . import stages as _stages
    out = []
    for row in doc["khau"]["rows"]:
        subs = [r for r in stage_rows if _stages.base_id(r["id"]) == row["id"]]
        tasks = {t: plan.get(t, "?") for t in plan_khau.get(row["id"], [])}
        errs = (open_errors or {}).get(row["id"], 0) + sum((open_errors or {}).get(r["id"], 0) for r in subs if r["id"] != row["id"])
        if subs:
            truoc = _check([r["kiem_truoc"] for r in subs])
            sau = _check([r["kiem_sau"] for r in subs])
            doc_tu = "do" if any(r["doc_tu"] == "chu_tu_do" for r in subs) else "xanh"
            money = any(r.get("ton_tien") for r in subs)
            color = "do" if (truoc == "do" and money) or doc_tu == "do" else ("vang" if "vang" in (truoc, doc_tu) else "xanh")
            why = [f"{r['id']}: trước {r['kiem_truoc']} · sau {r['kiem_sau']} · đọc từ {r['doc_tu']}"
                   + (f" ({r['ghi_co']})" if r.get("ghi_co") else "") for r in subs]
        else:
            truoc = sau = doc_tu = "xam"
            color, why = "xam", ["khâu không có trong devsys/stages.json"]
        if any(s == "🔄" for s in tasks.values()):
            color = "tim"
            why.append("đang sửa: " + ", ".join(t for t, s in tasks.items() if s == "🔄"))
        out.append({"id": row["id"], "label": row["label"], "money": row.get("money", ""), "color": color, "why": why,
                    "moc": MOC.get(row.get("moc"), "xam"), "moc_cells": row.get("moc_cells") or {}, "cells": {"truoc": truoc, "sau": sau, "doc": doc_tu},
                    "tasks": tasks, "open_errors": errs,
                    "inputs": {"truoc": truoc, "sau": sau, "doc": doc_tu, "plan": tasks, "open_errors": errs}})
    return out


def build_model(doc: Optional[Dict] = None, root: str = ROOT, state=None, plan_status: Optional[Dict[str, str]] = None,
                stage_rows: Optional[List[Dict]] = None, plan_khau: Optional[Dict[str, List[str]]] = None,
                open_errors: Optional[Dict[str, int]] = None) -> Dict:
    """Mô hình màu của 3 sơ đồ (thuần khi mọi nguồn được truyền vào — test không cần máy thật)."""
    doc = doc or load()
    state = state or _flag_state()
    plan = plan_statuses() if plan_status is None else plan_status
    warnings: List[str] = []
    if stage_rows is None:
        from . import stages
        stage_rows = stages.summary_rows(stages.effective(stages.load_stages()))
    if plan_khau is None:
        from . import plan_map
        plan_khau = {}
        for task, ks in plan_map.load_map().items():
            for k in ks:
                plan_khau.setdefault(k, []).append(task)
    if open_errors is None:
        from . import plan_map
        try:
            open_errors = plan_map.open_errors_by_stage() or {}
        except ValueError as e:
            warnings.append(f"sổ lỗi: {e}")
            open_errors = {}
    cache: Dict = {}
    unknown_flags: set = set()
    cells = []
    for c in doc["dashboard"]["cells"]:
        r = _cell_color(c, root, state, plan, cache, unknown_flags)
        r.update(screen=c["screen"], label=c["label"], desc=c.get("desc") or [], khau=c.get("khau") or [], ui=c.get("ui") or [],
                 cli=c.get("cli") or [])
        cells.append(r)
    nodes = []
    for n in doc["truong"]["nodes"]:
        r = _cell_color(n, root, state, plan, cache, unknown_flags)
        r.update(col=n["col"], label=n["label"], desc=n.get("desc") or [], khau=n.get("khau") or [])
        nodes.append(r)
    unknown_plan = sorted({t for c in doc["dashboard"]["cells"] + doc["truong"]["nodes"] for t in c.get("plan") or [] if t not in plan})
    if unknown_plan and plan:
        warnings.append("mã việc không có trong kế hoạch chính: " + ", ".join(unknown_plan))
    if unknown_flags:
        warnings.append("cờ không có trong core/features.py (tính là TẮT): " + ", ".join(sorted(unknown_flags)))
    return {"dashboard": {"title": doc["dashboard"]["title"], "screens": doc["dashboard"]["screens"], "cells": cells,
                          "outside": doc["dashboard"].get("outside") or []},
            "khau": {"title": doc["khau"]["title"], "rows": _khau_rows(doc, stage_rows, plan, plan_khau, open_errors)},
            "truong": {"title": doc["truong"]["title"], "columns": doc["truong"]["columns"], "nodes": nodes,
                       "edges": doc["truong"].get("edges") or []},
            "unknown_flags": sorted(unknown_flags), "warnings": warnings, "moc_date": doc.get("moc_date", "")}


def all_items(m: Dict) -> List[Dict]:
    return m["dashboard"]["cells"] + m["khau"]["rows"] + m["truong"]["nodes"]


# ---- lịch sử thay đổi -------------------------------------------------------------------------------------------------------------
def snapshot(m: Dict) -> Dict[str, Dict]:
    return {i["id"]: {"color": i["color"], "inputs": i["inputs"], "khau": i.get("khau") or [i["id"]]} for i in all_items(m)}


def _read_history(path: str) -> List[Dict]:
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
    except OSError:
        pass
    return out


def record_history(m: Dict, path: str = HISTORY_FILE, now: Optional[str] = None) -> bool:
    """Ghi ảnh chụp khi màu / đầu vào khác lần ghi trước (lần đầu luôn ghi). True = đã ghi. Lỗi ghi → False (trang vẫn vẽ)."""
    snap = snapshot(m)
    hist = _read_history(path)
    if hist and hist[-1].get("cells") == snap:
        return False
    rec = {"at": now or datetime.datetime.now().isoformat(timespec="seconds"), "cells": snap}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def _reasons(old: Dict, new: Dict) -> List[str]:
    o, n = old.get("inputs") or {}, new.get("inputs") or {}
    out = []
    for t, s in (n.get("plan") or {}).items():
        if (o.get("plan") or {}).get(t) != s:
            out.append(f"việc {t} {(o.get('plan') or {}).get(t, '—')} → {s}")
    for f, s in (n.get("flags") or {}).items():
        if (o.get("flags") or {}).get(f) != s:
            out.append(f"cờ {f} {(o.get('flags') or {}).get(f, '—')} → {s}")
    if "evidence" in n and o.get("evidence") != n.get("evidence"):
        out.append("bằng chứng code " + ("đã có" if n["evidence"] else "MẤT"))
    for k in ("truoc", "sau", "doc"):
        if k in n and o.get(k) != n.get(k):
            out.append(f"kiểm {k}: {o.get(k)} → {n.get(k)}")
    if n.get("open_errors") != o.get("open_errors") and "open_errors" in n:
        out.append(f"lỗi mở {o.get('open_errors')} → {n.get('open_errors')}")
    return out or ["đầu vào không ghi được lý do (dữ liệu sơ đồ đổi)"]


def changes(path: str = HISTORY_FILE) -> List[Dict]:
    """Ô đổi màu giữa hai lần ghi liền nhau (cũ → mới): {at, id, old, new, why, khau}."""
    hist = _read_history(path)
    out = []
    for prev, cur in zip(hist, hist[1:]):
        for cid, c in cur.get("cells", {}).items():
            p = prev.get("cells", {}).get(cid)
            if p is not None and p.get("color") != c.get("color"):
                out.append({"at": cur.get("at"), "id": cid, "old": p.get("color"), "new": c.get("color"), "why": _reasons(p, c),
                            "khau": c.get("khau") or []})
    return out


def vs_moc(m: Dict) -> List[Dict]:
    """Ô khác màu mốc 17/10."""
    return [{"id": i["id"], "old": i["moc"], "new": i["color"], "why": i["why"], "khau": i.get("khau") or [i["id"]]}
            for i in all_items(m) if i["moc"] != i["color"]]


def git_reason(files: List[str], root: str = ROOT) -> str:
    """Commit cuối chạm các tệp bằng chứng (lý do 'commit nào'); không có git → ""."""
    import subprocess
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h %ad %s", "--date=short", "--", *files], cwd=root, capture_output=True,
                             text=True, timeout=10, encoding="utf-8")
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# ---- tô theo dự án ---------------------------------------------------------------------------------------------------------------
def db_path() -> str:
    return os.environ.get("PIPELINE_DB") or os.path.join(ROOT, "data", "manifest.sqlite")


def _ro(path: str):
    return sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True, timeout=5)


def project_events(path: str, project_id: int) -> List[Dict]:
    """Sự kiện ui_step / cli_step của dự án — CSDL mở mode=ro (không tạo tệp, không ghi). Không đọc được → []."""
    if not os.path.isfile(path):
        return []
    try:
        conn = _ro(path)
    except sqlite3.Error:
        return []
    try:
        from core import ui_step
        return ui_step.events(conn, project_id)
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def projects(path: str) -> List[Dict]:
    if not os.path.isfile(path):
        return []
    try:
        conn = _ro(path)
        try:
            return [{"id": r[0], "name": r[1]} for r in conn.execute("SELECT id, name FROM projects ORDER BY id DESC")]
        finally:
            conn.close()
    except sqlite3.Error:
        return []


_SEV = {"error": 3, "warn": 2, "info": 1}


def overlay(m: Dict, events: List[Dict]) -> Dict:
    """Màu ô Dashboard theo sự kiện thật của MỘT dự án: lỗi → đỏ (kèm mã), cảnh báo / giữ → vàng (số lần + câu mới nhất), ổn → xanh,
    chưa ai bấm → xám. Lệnh CLI làm thay Dashboard → nút ảo 'THIẾU NÚT: <việc>' ở cột màn của công cụ (đếm số lần)."""
    ui = [e for e in events if e["kind"] == "ui_step"]
    cells = {}
    for c in m["dashboard"]["cells"]:
        mine = [e for e in ui if e["key"] in c["ui"]]
        if not mine:
            cells[c["id"]] = {"color": "xam", "count": 0, "last": ""}
            continue
        worst = max(_SEV.get(e["severity"], 1) for e in mine)
        top = [e for e in mine if _SEV.get(e["severity"], 1) == worst]
        last = max(top, key=lambda e: e.get("last_at") or "")
        cells[c["id"]] = {"color": {3: "do", 2: "vang", 1: "xanh"}[worst], "count": sum(e["count"] for e in top), "last": last["message"]}
    screen_of = {o["tool"]: o["screen"] for o in m["dashboard"]["outside"]}
    for c in m["dashboard"]["cells"]:
        for t in c.get("cli") or []:
            screen_of.setdefault(t, c["screen"])
    virt: Dict[str, Dict] = {}
    for e in events:
        if e["kind"] != "cli_step":
            continue
        v = virt.setdefault(e["key"], {"tool": e["key"], "screen": screen_of.get(e["key"], "storyboard"), "count": 0, "task": ""})
        v["count"] += e["count"]
        task = e["message"].split(": ", 1)[1] if ": " in e["message"] else e["message"]
        v["task"] = task
        v["label"] = f"THIẾU NÚT: {task}"
    alerts = [{"id": c["id"], "label": c["label"], **cells[c["id"]]} for c in m["dashboard"]["cells"] if cells[c["id"]]["color"] in ("do", "vang")]
    return {"cells": cells, "virtual": list(virt.values()), "alerts": alerts}


# ---- SVG ---------------------------------------------------------------------------------------------------------------------------
def _head(w: int, h: int, title: str, sub: str) -> List[str]:
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" font-family="Segoe UI, Arial, sans-serif">',
         f'<rect width="{w}" height="{h}" fill="{BG}"/>',
         f'<text x="{w // 2}" y="40" text-anchor="middle" font-size="25" font-weight="700" fill="{TEXT}">{escape(title)}</text>',
         f'<text x="{w // 2}" y="66" text-anchor="middle" font-size="14" fill="{MUTED}">{escape(sub)}</text>']
    x = 60
    for k, name in COLOR_NAME.items():
        o.append(f'<rect x="{x}" y="84" width="20" height="14" rx="3" fill="{COLORS[k]}"/>'
                 f'<text x="{x + 28}" y="96" font-size="13" fill="{MUTED}">{escape(name)}</text>')
        x += 60 + 7 * len(name)
    return o


def _box(o: List[str], x, y, w, h, color: str, title: str, lines: List[str], tip: str = "", dashed: bool = False, moc: str = ""):
    c = COLORS[color]
    dash = ' stroke-dasharray="8 5"' if dashed else ""
    o.append(f'<g><title>{escape(tip)}</title><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{c}" fill-opacity="0.10" '
             f'stroke="{c}" stroke-width="2"{dash}/><rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{c}"/>')
    o.append(f'<text x="{x + 16}" y="{y + 22}" font-size="14" font-weight="700" fill="#ffffff">{escape(title[:52])}</text>')
    for k, line in enumerate(lines[:2]):
        o.append(f'<text x="{x + 16}" y="{y + 42 + k * 17}" font-size="12" fill="#b8c2cc">{escape(str(line)[:62])}</text>')
    if moc and moc != color:
        o.append(f'<circle cx="{x + w - 14}" cy="{y + 14}" r="6" fill="{COLORS[moc]}"><title>mốc 17/10: {escape(moc)}</title></circle>')
    o.append("</g>")


def svg_dashboard(m: Dict, ov: Optional[Dict] = None) -> str:
    d = m["dashboard"]
    screens = d["screens"]
    cw, gap, x0, top, ch = 405, 15, 30, 150, 74
    per = {s["id"]: [c for c in d["cells"] if c["screen"] == s["id"]] for s in screens}
    virt = (ov or {}).get("virtual") or []
    nmax = max(len(per[s["id"]]) + sum(1 for v in virt if v["screen"] == s["id"]) for s in screens)
    w = x0 * 2 + len(screens) * cw + (len(screens) - 1) * gap
    lane = top + 90 + nmax * (ch + 10) + 20
    h = lane + 60 + 34 * ((len(d["outside"]) + 1) // 2) + 30
    sub = (f"Màu theo sự kiện thật của dự án — chấm nhỏ góc = màu mốc {m['moc_date']}" if ov else
           f"Màu tính từ code + cờ hiệu lực + kế hoạch — chấm nhỏ góc = màu mốc {m['moc_date']}")
    o = _head(w, h, d["title"], sub)
    for i, s in enumerate(screens):
        x = x0 + i * (cw + gap)
        o.append(f'<rect x="{x}" y="{top}" width="{cw}" height="64" rx="10" fill="{PANEL}" stroke="{s["color"]}" stroke-width="3"/>'
                 f'<text x="{x + cw / 2}" y="{top + 30}" text-anchor="middle" font-size="20" font-weight="700" fill="{s["color"]}">'
                 f'{escape(s["title"])}</text><text x="{x + cw / 2}" y="{top + 52}" text-anchor="middle" font-size="12" fill="{MUTED}">'
                 f'{escape(s["src"])}</text>')
        j = 0
        for c in per[s["id"]]:
            y = top + 84 + j * (ch + 10)
            if ov:
                p = ov["cells"][c["id"]]
                lines = [f"{p['count']} lần · {p['last']}" if p["count"] else "dự án này chưa ai bấm"] + c["desc"][:1]
                _box(o, x, y, cw, ch, p["color"], c["label"], lines, p["last"] or c["label"])
            else:
                _box(o, x, y, cw, ch, c["color"], c["label"], c["desc"], "; ".join(c["why"]), moc=c["moc"])
            j += 1
        for v in virt:
            if v["screen"] != s["id"]:
                continue
            y = top + 84 + j * (ch + 10)
            _box(o, x, y, cw, ch, "do", v["label"], [f"{v['count']} lần làm ngoài Dashboard bằng tools/{v['tool']}.py"],
                 f"{v['tool']}: {v['task']}", dashed=True)
            o.append(f'<line x1="{x + cw / 2}" y1="{y + ch}" x2="{x + cw / 2}" y2="{lane}" stroke="{COLORS["do"]}" stroke-width="2" '
                     f'stroke-dasharray="6 4"/>')
            j += 1
    o.append(f'<rect x="{x0}" y="{lane}" width="{w - 2 * x0}" height="{h - lane - 20}" rx="10" fill="{PANEL}" stroke="{COLORS["do"]}" '
             f'stroke-width="2.5" stroke-dasharray="10 6"/>'
             f'<text x="{x0 + 20}" y="{lane + 32}" font-size="17" font-weight="700" fill="#ff9a9a">⛔ NGOÀI DASHBOARD — Claude chạy tay</text>')
    for k, t in enumerate(d["outside"]):
        o.append(f'<text x="{x0 + 36 + (k % 2) * 830}" y="{lane + 64 + (k // 2) * 34}" font-size="14" fill="{TEXT}">• '
                 f'{escape(t["label"])}</text>')
    o.append("</svg>")
    return "".join(o)


def svg_khau(m: Dict) -> str:
    rows = m["khau"]["rows"]
    w, rh, top = 1720, 92, 160
    h = top + rh * len(rows) + 40
    o = _head(w, h, m["khau"]["title"], "Theo cờ thật (devsys/stages.json · stages.effective) + kế hoạch (devsys/plan_map.json) + "
              "sổ lỗi — chấm nhỏ góc = màu mốc 17/10")
    cols = ((96, 470, "KHÂU"), (590, 330, "KIỂM TRƯỚC KHI TRẢ TIỀN"), (940, 300, "KIỂM SAU"), (1255, 125, "KẾT LUẬN TỪ"),
            (1395, 300, "LỖI MỞ · VIỆC ĐANG SỬA"))
    for x, cw, t in cols:
        o.append(f'<text x="{x + cw / 2}" y="{top - 16}" text-anchor="middle" font-size="15" font-weight="700" fill="{TEXT}">{t}</text>')
    for i, r in enumerate(rows):
        y = top + i * rh
        hh = rh - 14
        c = COLORS[r["color"]]
        o.append(f'<g><title>{escape("; ".join(r["why"]))}</title><circle cx="56" cy="{y + hh / 2}" r="24" fill="{PANEL}" stroke="{c}" '
                 f'stroke-width="2.5"/><text x="56" y="{y + hh / 2 + 5}" text-anchor="middle" font-size="15" font-weight="700" '
                 f'fill="{c}">{escape(r["id"])}</text></g>')
        _box(o, 96, y, 470, hh, r["color"], r["label"][0] + (f"  {r['money']}" if r["money"] else ""), [r["label"][1]],
             "; ".join(r["why"]), moc=r["moc"])
        mc = r["moc_cells"]
        for (x, cw, _), key in zip(cols[1:4], ("truoc", "sau", "doc")):
            mt = (mc.get(key) or ["", ""])[1]
            _box(o, x, y, cw, hh, r["cells"][key], {"xanh": "có, đang chạy", "vang": "cờ tắt / chỉ người", "do": "KHÔNG CÓ / chữ tự do",
                                                    "xam": "—"}[r["cells"][key]], [f"mốc: {mt}"], mt,
                 moc=MOC.get((mc.get(key) or ["", ""])[0], ""))
        doing = [t for t, s in r["tasks"].items() if s == "🔄"]
        lines = [f"lỗi mở: {r['open_errors']}"] + ([f"đang sửa: {', '.join(doing)}"] if doing else [])
        _box(o, 1395, y, 300, hh, "do" if r["open_errors"] else ("tim" if doing else "xanh"), mc.get("loi") or "—", lines, mc.get("loi") or "")
    o.append("</svg>")
    return "".join(o)


def svg_truong(m: Dict) -> str:
    t = m["truong"]
    cols = t["columns"]
    cw, gap, x0, top, nh = 390, 40, 30, 150, 74
    per = {c["id"]: [n for n in t["nodes"] if n["col"] == c["id"]] for c in cols}
    w = x0 * 2 + len(cols) * cw + (len(cols) - 1) * gap
    h = top + 60 + max(len(v) for v in per.values()) * (nh + 12) + 40
    o = _head(w, h, t["title"], "Màu = code đọc TRƯỜNG có chưa (bằng chứng) + cờ + việc kế hoạch — chấm nhỏ góc = màu mốc 17/10")
    pos = {}
    for i, c in enumerate(cols):
        x = x0 + i * (cw + gap)
        o.append(f'<text x="{x + cw / 2}" y="{top + 10}" text-anchor="middle" font-size="15" font-weight="700" fill="{TEXT}">'
                 f'{escape(c["title"])}</text>')
        for j, n in enumerate(per[c["id"]]):
            y = top + 30 + j * (nh + 12)
            pos[n["id"]] = (x, y)
    for a, b in t["edges"]:
        if a in pos and b in pos:
            (xa, ya), (xb, yb) = pos[a], pos[b]
            x1, x2 = (xa + cw, xb) if xb > xa else (xa + cw / 2, xb + cw / 2)
            y1, y2 = (ya + nh / 2, yb + nh / 2) if xb > xa else (ya + nh, yb)
            o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#3a4450" stroke-width="1.5"/>')
    for n in t["nodes"]:
        x, y = pos[n["id"]]
        _box(o, x, y, cw, nh, n["color"], n["label"], n["desc"], "; ".join(n["why"]), moc=n["moc"])
    o.append("</svg>")
    return "".join(o)


def main(argv: Optional[List[str]] = None) -> int:
    import sys
    argv = sys.argv[1:] if argv is None else argv
    out = argv[0] if argv else "."
    os.makedirs(out, exist_ok=True)
    m = build_model()
    for name, svg in (("so_do_dashboard.svg", svg_dashboard(m)), ("so_do_hien_trang_khau.svg", svg_khau(m)),
                      ("so_do_truong_cau_truc.svg", svg_truong(m))):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(svg)
    print(f"Đã ghi 3 SVG vào {out}" + ("; " + " · ".join(m["warnings"]) if m["warnings"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
