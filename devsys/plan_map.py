"""Sơ đồ tiến độ kế hoạch chính (V3.1 M0.8, người dùng 20/10: "vẽ lại theo plan mới nhất, sửa đến đâu theo dõi đến đó").

Mọi màu tính lại MỖI lần mở trang từ nguồn — không ai tô tay:
  - danh sách việc + trạng thái: file kế hoạch chính (`plan_progress.PLAN_FILE`, mục "chinh" trong devsys/plans.json);
  - khâu L1–L16 + tình trạng kiểm trước tiền: devsys/stages.json (theo cờ thật, `stages.effective`);
  - việc ↔ khâu: devsys/plan_map.json (việc chưa gắn khâu → báo, không bỏ im lặng);
  - sổ lỗi devsys/errors.json (M0.4): khi có, đếm lỗi còn mở theo khâu.
Hai SVG: (1) lộ trình theo milestone, mỗi việc một ô màu theo trạng thái; (2) khâu × việc: mỗi khâu một hàng, chip việc tô theo trạng thái.
"""
import json
import os
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

from . import plan_progress, errors

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_FILE = os.path.join(ROOT, "devsys", "plan_map.json")
ERRORS_FILE = os.path.join(ROOT, "devsys", "errors.json")

BG, PANEL, TEXT, MUTED = "#0f1720", "#16212c", "#e8eef5", "#8a99a8"
STATUS_COLOR = {"✅": "#4dff6a", "🔄": "#ffb020", "⏸": "#b388ff", "⬜": "#5b6b7a", "✖": "#3a4450"}
STATUS_NAME = {"✅": "xong", "🔄": "đang làm", "⏸": "chờ người dùng", "⬜": "chưa làm", "✖": "bỏ"}
STAGE_COLOR = {"thieu": "#ff5a5a", "tu_do": "#ffb020", "ok": "#22e5ff"}
NEN = "NEN"


def load_map(path: str = MAP_FILE) -> Dict[str, List[str]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    khau = data.get("khau")
    if not isinstance(khau, dict) or not all(isinstance(v, list) and v for v in khau.values()):
        raise ValueError("plan_map.json: 'khau' phải là {mã việc: [khâu, …]}")
    return khau


def open_errors_by_stage(path: str = ERRORS_FILE) -> Optional[Dict[str, int]]:
    """{khâu: số lỗi chưa VERIFIED/WONT_FIX}; None khi chưa có sổ lỗi (M0.4). Mục sai dạng → ValueError có lý do (trang báo, không sập)."""
    if not os.path.exists(path):
        return None
    data = errors.load(path)
    issues = errors.register_problems(data)
    if issues:
        raise ValueError('Sổ lỗi không hợp lệ: ' + '; '.join(issues))
    out: Dict[str, int] = {}
    for n, e in enumerate(data['items']):
        if not isinstance(e, dict):
            raise ValueError(f"errors.json: mục {n} không phải object")
        if e.get("status") in ("VERIFIED", "WONT_FIX"):
            continue
        raw = e.get("stage")
        for st in raw if isinstance(raw, list) else [raw or NEN]:
            if not isinstance(st, str):
                raise ValueError(f"errors.json: mục {e.get('id', n)!r} có khâu không phải chuỗi")
            out[st] = out.get(st, 0) + 1
    return out


def model(plan: Dict, stage_rows: List[Dict], khau: Dict[str, List[str]], errors: Optional[Dict[str, int]] = None) -> Dict:
    """Dữ liệu thuần cho hai sơ đồ (test được không cần SVG)."""
    s = plan_progress.summary(plan)
    pct = {r["id"]: r for r in s["waves"]}
    tasks = [t for w in plan["waves"] for t in w["tasks"]]
    unmapped = [t["id"] for t in tasks if t["id"] not in khau]
    stale = sorted(set(khau) - {t["id"] for t in tasks})
    known = {NEN} | {r["id"] for r in stage_rows}
    unknown_stage = sorted({f"{tid}→{st}" for tid, sts in khau.items() for st in sts if st not in known})
    rows = [{"id": NEN, "ten": "Nền chung: sổ lỗi, audit, golden, pilot", "kind": "ok"}]
    rows += [{"id": r["id"], "ten": r["ten"], "kind": "thieu" if r["thieu"] else "tu_do" if r["tu_do"] else "ok"} for r in stage_rows]
    for r in rows:
        mine = [t for t in tasks if r["id"] in khau.get(t["id"], [])]
        counted = [t for t in mine if t["status"] != "✖"]
        r["tasks"] = mine
        r["done"] = sum(t["status"] == "✅" for t in counted)
        r["n"] = len(counted)
        r["pct"] = plan_progress.percent(mine)
        r["open_errors"] = None if errors is None else errors.get(r["id"], 0)
    return {"total": s["total"], "current": s["current"], "next": s["next"],
            "waves": [{"id": w["id"], "name": w["name"], "tasks": w["tasks"], "pct": pct[w["id"]]["pct"],
                       "done": pct[w["id"]]["done"], "n": pct[w["id"]]["n"]} for w in plan["waves"]],
            "rows": rows, "unmapped": unmapped, "stale": stale, "unknown_stage": unknown_stage}


def _wrap(text: str, width: int) -> List[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def _pct(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:g} %".replace(".", ",")


def _legend(y: int, width: int) -> str:
    out, x = [], 40
    for st, name in STATUS_NAME.items():
        out.append(f'<rect x="{x}" y="{y}" width="18" height="14" rx="3" fill="{STATUS_COLOR[st]}"/>'
                   f'<text x="{x + 26}" y="{y + 12}" fill="{MUTED}" font-size="13">{escape(name)}</text>')
        x += 150
    return "".join(out)


def roadmap_svg(m: Dict, title: str) -> str:
    """Sơ đồ 1: cột milestone, mỗi việc một ô màu theo trạng thái, đầu cột có % và thanh tiến độ."""
    waves = m["waves"]
    col_w, gap, top = 300, 18, 150
    width = 40 * 2 + len(waves) * col_w + (len(waves) - 1) * gap
    box_h = 62
    height = top + max((len(w["tasks"]) for w in waves), default=0) * (box_h + 10) + 60
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" font-family="Segoe UI, Arial">',
           f'<rect width="{width}" height="{height}" fill="{BG}"/>',
           f'<text x="{width / 2}" y="40" fill="{TEXT}" font-size="26" font-weight="700" text-anchor="middle">{escape(title)}</text>',
           f'<text x="{width / 2}" y="66" fill="{MUTED}" font-size="14" text-anchor="middle">Tổng {_pct(m["total"])} · đợt hiện tại '
           f'{escape(m["current"] or "—")} · việc kế {escape(m["next"]["id"] if m["next"] else "—")} — màu tính lại từ file kế hoạch mỗi lần mở</text>',
           _legend(84, width)]
    for i, w in enumerate(waves):
        x = 40 + i * (col_w + gap)
        cur = w["id"] == m["current"]
        border = "#22e5ff" if cur else "#2c3a48"
        out.append(f'<rect x="{x}" y="112" width="{col_w}" height="30" rx="6" fill="{PANEL}" stroke="{border}" stroke-width="{3 if cur else 1}"/>')
        name = w["name"].split("(")[0].strip()
        out.append(f'<text x="{x + 10}" y="132" fill="{TEXT}" font-size="14" font-weight="700">{escape(w["id"] + " " + name[:28])}</text>')
        out.append(f'<text x="{x + col_w - 10}" y="132" fill="{TEXT}" font-size="14" text-anchor="end">{_pct(w["pct"])}</text>')
        frac = (w["pct"] or 0) / 100.0
        out.append(f'<rect x="{x}" y="144" width="{col_w}" height="4" fill="#2c3a48"/>'
                   f'<rect x="{x}" y="144" width="{col_w * frac:.1f}" height="4" fill="#4dff6a"/>')
        for j, t in enumerate(w["tasks"]):
            y = top + 10 + j * (box_h + 10)
            c = STATUS_COLOR[t["status"]]
            out.append(f'<rect x="{x}" y="{y}" width="{col_w}" height="{box_h}" rx="7" fill="{PANEL}" stroke="{c}" stroke-width="2"/>'
                       f'<rect x="{x}" y="{y}" width="6" height="{box_h}" rx="3" fill="{c}"/>')
            out.append(f'<text x="{x + 14}" y="{y + 19}" fill="{c}" font-size="13" font-weight="700">{escape(t["id"])} · '
                       f'{escape(STATUS_NAME[t["status"]])}{" · " + escape(t["commit"]) if t["commit"] else ""}</text>')
            for k, line in enumerate(_wrap(t["title"], 44)[:2]):
                out.append(f'<text x="{x + 14}" y="{y + 37 + k * 16}" fill="{TEXT}" font-size="12">{escape(line)}</text>')
    out.append("</svg>")
    return "".join(out)


def stages_svg(m: Dict, title: str) -> str:
    """Sơ đồ 2: mỗi khâu một hàng (viền theo tình trạng kiểm trước tiền), chip việc V3.1 tô theo trạng thái, cột % + lỗi mở."""
    rows = m["rows"]
    width, row_h, top = 1500, 54, 120
    height = top + len(rows) * (row_h + 8) + 40
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" font-family="Segoe UI, Arial">',
           f'<rect width="{width}" height="{height}" fill="{BG}"/>',
           f'<text x="{width / 2}" y="40" fill="{TEXT}" font-size="26" font-weight="700" text-anchor="middle">{escape(title)}</text>',
           f'<text x="{width / 2}" y="64" fill="{MUTED}" font-size="13" text-anchor="middle">Viền khâu: đỏ = còn lỗi mở hoặc tốn tiền thiếu kiểm trước · '
           f'vàng = kết luận đọc chữ tự do · xanh = có kiểm (devsys/stages.json theo cờ thật). Chip = việc V3.1 sửa khâu đó.</text>',
           _legend(80, width)]
    hx = [40, 470, 1290, 1400]
    for x, h in zip(hx, ["KHÂU", "VIỆC V3.1 (màu = trạng thái)", "TIẾN ĐỘ", "LỖI MỞ"]):
        out.append(f'<text x="{x}" y="{top - 4}" fill="{MUTED}" font-size="12" font-weight="700">{h}</text>')
    for i, r in enumerate(rows):
        y = top + 6 + i * (row_h + 8)
        c = STAGE_COLOR['thieu'] if r['open_errors'] else STAGE_COLOR[r["kind"]]
        out.append(f'<rect x="40" y="{y}" width="410" height="{row_h}" rx="7" fill="{PANEL}" stroke="{c}" stroke-width="2"/>'
                   f'<text x="54" y="{y + 22}" fill="{c}" font-size="14" font-weight="700">{escape(r["id"] if r["id"] != NEN else "Nền")}</text>')
        for k, line in enumerate(_wrap(r["ten"], 46)[:2]):
            out.append(f'<text x="110" y="{y + 22 + k * 17}" fill="{TEXT}" font-size="13">{escape(line)}</text>')
        cx = hx[1]
        for n, t in enumerate(r["tasks"]):
            tc = STATUS_COLOR[t["status"]]
            wpx = 8 * len(t["id"]) + 18
            if cx + wpx > hx[2] - 60:
                out.append(f'<text x="{cx}" y="{y + 32}" fill="{MUTED}" font-size="12">+{len(r["tasks"]) - n}</text>')
                break
            out.append(f'<rect x="{cx}" y="{y + 14}" width="{wpx}" height="26" rx="13" fill="{tc}" fill-opacity="0.18" stroke="{tc}"/>'
                       f'<text x="{cx + wpx / 2}" y="{y + 32}" fill="{tc}" font-size="12" font-weight="700" text-anchor="middle">'
                       f'{escape(t["id"])}</text>')
            cx += wpx + 8
        if not r["tasks"]:
            out.append(f'<text x="{cx}" y="{y + 32}" fill="{MUTED}" font-size="12">— không có việc V3.1</text>')
        frac = (r["pct"] or 0) / 100.0
        out.append(f'<rect x="{hx[2]}" y="{y + 22}" width="90" height="8" rx="4" fill="#2c3a48"/>'
                   f'<rect x="{hx[2]}" y="{y + 22}" width="{90 * frac:.1f}" height="8" rx="4" fill="#4dff6a"/>'
                   f'<text x="{hx[2]}" y="{y + 46}" fill="{MUTED}" font-size="11">{r["done"]}/{r["n"]} · {_pct(r["pct"])}</text>')
        err = "chưa có sổ" if r["open_errors"] is None else str(r["open_errors"])
        ec = MUTED if r["open_errors"] in (None, 0) else "#ff5a5a"
        out.append(f'<text x="{hx[3]}" y="{y + 32}" fill="{ec}" font-size="13">{escape(err)}</text>')
    out.append("</svg>")
    return "".join(out)


def build(plan_path: Optional[str] = None) -> Tuple[Dict, str, str]:
    """(model, svg lộ trình, svg khâu) cho kế hoạch chính; lỗi đọc nguồn → ValueError có lý do."""
    from . import stages
    plan_path = plan_path or plan_progress.main_plan_file()
    plan = plan_progress.load(plan_path)
    if plan is None:
        raise ValueError(f"không thấy file kế hoạch {plan_path}")
    if plan["bad"]:
        raise ValueError("dòng việc không đọc được: " + "; ".join(plan["bad"]))
    if not plan["waves"]:
        raise ValueError(f"kế hoạch {os.path.basename(plan_path)} chưa có đợt / việc nào")
    rows = stages.summary_rows(stages.effective(stages.load_stages()))
    m = model(plan, rows, load_map(), open_errors_by_stage())
    name = os.path.basename(plan_path)
    return m, roadmap_svg(m, f"Lộ trình build — {name}"), stages_svg(m, "Khâu dây chuyền × việc đang sửa")


if __name__ == "__main__":       # py -m devsys.plan_map <thư mục ra>: xuất 2 SVG (để gửi / xem ngoài web)
    import sys
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    m, a, b = build()
    for fname, svg in (("so_do_lo_trinh.svg", a), ("so_do_khau.svg", b)):
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(svg)
    print(f"Đã ghi 2 SVG vào {out_dir}; tổng {_pct(m['total'])}; việc chưa gắn khâu: {', '.join(m['unmapped']) or 'không'}")
