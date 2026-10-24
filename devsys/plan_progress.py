"""Tiến độ của kế hoạch đang chạy (mục "chinh": true trong devsys/plans.json; 20/10 = V3.1, trước đó docs/KE_HOACH_SUA_SAU_DU_AN_8.md) — % do code tính từ danh sách việc, không ai tự khai.

Mỗi việc là một dòng trong file kế hoạch:
    - [ ] S1.2 · Hiệu ứng âm thanh neo theo shot · nặng:2 · ⬜
    - [x] S1.1 · Bỏ bảng tên nhân vật · nặng:1 · ✅ · 1a2b3c4 · ghi chú / bằng chứng
Trạng thái: ⬜ chưa làm · 🔄 đang làm · ⏸ chờ người dùng · ✅ xong · ✖ bỏ. Trọng số nặng:1/2/3.
% đợt = (Σ nặng ✅ + ½ Σ nặng 🔄) / Σ nặng (không tính ✖). Tên đợt lấy từ tiêu đề `### S1 — …` trong mục danh sách việc.
CX24-G1: trạng thái trên vẫn là CODE. Thêm ` · cổng: ✅ <bằng chứng>` hoặc ` · cổng: ⬜ <thiếu gì>`;
dòng cũ không có cổng = ⬜. % cổng chỉ cộng việc đã ✅code và có cổng đạt, không cộng nửa cho đang làm.
Dòng đầu file có thể ghi trần đợt: `Trần đợt: 50 USD · Claude 3 USD · từ 2026-09-28T08:00:00+00:00`.
`tools/plan_progress.py --write` ghi lại bảng tiến độ giữa hai dấu <!-- tien-do --> … <!-- /tien-do --> để file đọc được cả ngoài web.
"""
import os
import re
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PLAN_FILE = os.path.join(ROOT, "docs", "KE_HOACH_SUA_SAU_DU_AN_8.md")


def _local_plan(root: str, rec) -> Optional[str]:
    """Path of a viec_s record read from this checkout (no `nhanh`, inside the repo, file exists); None otherwise."""
    if not isinstance(rec, dict) or rec.get("kieu") != "viec_s" or rec.get("nhanh") or not isinstance(rec.get("file"), str):
        return None
    parts = rec["file"].replace("\\", "/").split("/")
    if os.path.isabs(rec["file"]) or ".." in parts:
        return None
    path = os.path.join(root, *parts)
    return path if os.path.isfile(path) else None


def _records(root: str) -> list:
    import json
    try:
        with open(os.path.join(root, "devsys", "plans.json"), encoding="utf-8") as f:
            records = json.load(f)
        return records if isinstance(records, list) else []
    except (OSError, ValueError):
        return []


def main_plan_file(root: str = ROOT) -> str:
    """20/10 (V3.1): the running plan = the ONE devsys/plans.json record marked "chinh": true (kind viec_s, local file that exists);
    none / several / missing file / unreadable → the S plan. Read at each call so the pages follow a change without a restart."""
    main = [r for r in _records(root) if isinstance(r, dict) and r.get("chinh") is True]
    path = _local_plan(root, main[0]) if len(main) == 1 else None
    return path or DEFAULT_PLAN_FILE


def plan_files(root: str = ROOT) -> List[str]:
    """Every local viec_s plan file (archived ones included) — for readers that must see all plans' lines ('Số đo:'), not only the main one."""
    out = [p for p in (_local_plan(root, r) for r in _records(root)) if p]
    if os.path.isfile(DEFAULT_PLAN_FILE) and DEFAULT_PLAN_FILE not in out and root == ROOT:
        out.append(DEFAULT_PLAN_FILE)
    return out


PLAN_FILE = main_plan_file()

STATUS = {"⬜": "chưa làm", "🔄": "đang làm", "⏸": "chờ người dùng", "✅": "xong", "✖": "bỏ"}
TASK_RE = re.compile(r"^\s*- \[( |x|X)\] (?P<id>[A-Z]+\d*(?:\.\d+)?) · (?P<title>.+?) · nặng:(?P<w>[123]) · (?P<st>⬜|🔄|⏸|✅|✖)"
                     r"(?: · (?P<rest>.*))?\s*$")
WAVE_RE = re.compile(r"^###\s+(?P<id>[A-Z]+\d*)\s+[—-]\s+(?P<name>.+?)\s*$")
CAP_RE = re.compile(r"Trần đợt:\s*(?P<usd>[\d.,]+)\s*USD\s*·\s*Claude\s*(?P<llm>[\d.,]+)\s*USD\s*·\s*từ\s*(?P<since>\S+)")
FOCUS_RE = re.compile(r"^\s*>?\s*Đợt ưu tiên:\s*\**(?P<id>[A-Z]+\d*)\**", re.M)     # "Đợt ưu tiên: S13" = the person says which wave is current
MARK_START, MARK_END = "<!-- tien-do -->", "<!-- /tien-do -->"
DASHBOARD_TASKS = {"M4.7", "M4.8", "M6.10", "M8.0", "M8.1", "M8.2", "M8.3", "M8.4"}
UI_EVIDENCE_RE = re.compile(r"\bui_step\b|\S+\.(?:png|jpe?g|webp)\b", re.I)


def _gate(parts: List[str], tid: str, title: str, code_status: str) -> Dict:
    """Đọc khai báo cổng, không tự nâng cổng từ code/test hay kiểm dữ liệu live."""
    fields = [p for p in parts if p.casefold().startswith("cổng:")]
    declared, evidence, warning = "⬜", "", ""
    if fields:
        m = re.fullmatch(r"cổng:\s*(✅|⬜)(?:\s+(.*))?", fields[0], re.I)
        if len(fields) != 1 or not m:
            warning = f"{tid}: khai báo cổng không hợp lệ hoặc bị trùng"
        else:
            declared, evidence = m.group(1), (m.group(2) or "").strip()
    accepted = declared == "✅"
    if accepted:
        low = evidence.casefold()
        real_evidence = bool(re.search(r"chạy thật|máy chính|ui_step|sổ chi|commit\s+[0-9a-f]{7,40}\b", low)
                             or UI_EVIDENCE_RE.search(evidence))
        if not real_evidence or re.search(r"chưa\s+(?:kiểm|chạy|đo|có)|chỉ\s+có\s+(?:unit|test)", low):
            warning = f"{tid}: cổng ✅ thiếu bằng chứng chạy thật (commit/ảnh/ui_step/sổ chi)"
        elif (tid in DASHBOARD_TASKS or re.search(r"dashboard|giao diện", title, re.I)) and not UI_EVIDENCE_RE.search(evidence):
            warning = f"{tid}: cổng Dashboard thiếu ảnh chụp hoặc nhật ký ui_step dùng thật"
        elif code_status != "✅":
            warning = f"{tid}: cổng ✅ trong khi code chưa ✅"
    return {"gate_status": "✅" if accepted and not warning else "⬜", "gate_declared": declared,
            "gate_evidence": evidence, "gate_warning": warning}


class PlanError(ValueError):
    """The plan file has a line that looks like a task but cannot be read (shown to the person, never skipped in silence)."""


def _num(text: str) -> float:
    return float(text.replace(",", "."))


def wave_of(task_id: str) -> str:
    return task_id.split(".")[0]


def parse(text: str) -> Dict:
    """{"waves": [{"id", "name", "tasks": [...]}], "cap": {...} | None, "bad": [lines that look like tasks but do not parse]}."""
    waves: List[Dict] = []
    by_id: Dict[str, Dict] = {}
    bad: List[str] = []
    seen = set()
    for n, line in enumerate(text.splitlines(), 1):
        w = WAVE_RE.match(line)
        if w and w.group("id") not in by_id:
            by_id[w.group("id")] = {"id": w.group("id"), "name": w.group("name"), "tasks": []}
            waves.append(by_id[w.group("id")])
            continue
        if not re.match(r"^\s*- \[( |x|X)\] [A-Z]+\d*(\.\d+)? · ", line):
            continue
        m = TASK_RE.match(line)
        if not m:
            bad.append(f"dòng {n}: {line.strip()[:120]}")
            continue
        tid = m.group("id")
        if tid in seen:
            bad.append(f"dòng {n}: mã việc {tid} bị trùng")
            continue
        seen.add(tid)
        rest = [p.strip() for p in (m.group("rest") or "").split(" · ") if p.strip()]
        commit = rest[0] if rest and re.fullmatch(r"[0-9a-f]{7,40}", rest[0]) else ""
        note = " · ".join(rest[1:] if commit else rest)
        task = {"id": tid, "title": m.group("title").strip(), "weight": int(m.group("w")), "status": m.group("st"),
                "commit": commit, "note": note, "line": n}
        task.update(_gate(rest, tid, task["title"], task["status"]))
        wid = wave_of(tid)
        if wid not in by_id:
            by_id[wid] = {"id": wid, "name": wid, "tasks": []}
            waves.append(by_id[wid])
        by_id[wid]["tasks"].append(task)
    cap = None
    c = CAP_RE.search(text)
    if c:
        cap = {"usd": _num(c.group("usd")), "llm_usd": _num(c.group("llm")), "since": c.group("since")}
    f = FOCUS_RE.search(text)
    return {"waves": waves, "cap": cap, "bad": bad, "focus": f.group("id") if f else None}


def percent(tasks: List[Dict]) -> Optional[float]:
    """Weighted % done (✅ full, 🔄 half, ✖ left out); None when nothing counts."""
    counted = [t for t in tasks if t["status"] != "✖"]
    total = sum(t["weight"] for t in counted)
    if not total:
        return None
    done = sum(t["weight"] for t in counted if t["status"] == "✅") + 0.5 * sum(t["weight"] for t in counted if t["status"] == "🔄")
    return round(100.0 * done / total, 1)


def gate_percent(tasks: List[Dict]) -> Optional[float]:
    counted = [t for t in tasks if t["status"] != "✖"]
    total = sum(t["weight"] for t in counted)
    done = sum(t["weight"] for t in counted if t["status"] == "✅" and t.get("gate_status") == "✅")
    return round(100.0 * done / total, 1) if total else None


def summary(plan: Dict) -> Dict:
    """{"total": %, "waves": [{"id", "name", "pct", "n", "done", "doing", "waiting", "dropped"}], "current": wave id or None,
    "doing": [tasks], "waiting": [tasks], "next": first task not started in the first unfinished wave}."""
    rows, all_tasks = [], []
    for w in plan["waves"]:
        t = w["tasks"]
        all_tasks += t
        rows.append({"id": w["id"], "name": w["name"], "pct": percent(t), "pct_gate": gate_percent(t), "n": len(t),
                     "gate_done": sum(x["status"] == "✅" and x.get("gate_status") == "✅" for x in t),
                     "done": sum(x["status"] == "✅" for x in t), "doing": sum(x["status"] == "🔄" for x in t),
                     "waiting": sum(x["status"] == "⏸" for x in t), "dropped": sum(x["status"] == "✖" for x in t)})
    unfinished = [r for r in rows if r["pct"] is not None and r["pct"] < 100]
    current = next((r["id"] for r in unfinished if r["done"] or r["doing"] or r["waiting"]), unfinished[0]["id"] if unfinished else None)
    focus = plan.get("focus")                    # the person's own choice wins while that wave is still unfinished
    if focus and any(r["id"] == focus for r in unfinished):
        current = focus
    nxt = None
    if current:                  # the first task not started: in the current wave, else in the waves after it (current waits for the person)
        ids = [w["id"] for w in plan["waves"]]
        for w in plan["waves"][ids.index(current):]:
            nxt = next((t for t in w["tasks"] if t["status"] == "⬜"
                        and "CHỜ PHỤ THUỘC" not in (t["title"] + " " + t["note"]).upper()
                        and "⏸" not in t["note"]), None)
            if nxt:
                break
    return {"total": percent(all_tasks), "total_code": percent(all_tasks), "total_gate": gate_percent(all_tasks),
            "gate_warnings": [t["gate_warning"] for t in all_tasks if t.get("gate_warning")],
            "waves": rows, "current": current,
            "doing": [t for t in all_tasks if t["status"] == "🔄"], "waiting": [t for t in all_tasks if t["status"] == "⏸"], "next": nxt}


def spend(cap: Optional[Dict], db_path: str) -> Optional[Dict]:
    """Money of this round from the project ledger (read-only): {"usd", "llm_usd", "cap_usd", "cap_llm", "since"}; None without a cap
    line or a database. Same sum as the dashboard's cap check (core.budget.spent)."""
    if not cap or not os.path.exists(db_path):
        return None
    import sqlite3
    from core import budget
    conn = sqlite3.connect("file:" + db_path.replace("\\", "/") + "?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        s = budget.spent(conn, since=cap["since"])
    finally:
        conn.close()
    return {"usd": s["usd"], "llm_usd": s["llm_usd"], "cap_usd": cap["usd"], "cap_llm": cap["llm_usd"], "since": cap["since"]}


def load(path: str = PLAN_FILE) -> Optional[Dict]:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


def _pct(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:g} %".replace(".", ",")


def table(plan: Dict) -> str:
    s = summary(plan)
    lines = ["| Đợt | Việc | Xong | Đang làm | Chờ người dùng | Bỏ | % code | % cổng |", "|---|---|---|---|---|---|---|---|"]
    for r in s["waves"]:
        lines.append(f"| {r['id']} {r['name']} | {r['n']} | {r['done']} | {r['doing']} | {r['waiting']} | {r['dropped']} | {_pct(r['pct'])} | {_pct(r['pct_gate'])} |")
    n = sum(r["n"] for r in s["waves"])
    lines.append(f"| **Tổng** | **{n}** | **{sum(r['done'] for r in s['waves'])}** | **{sum(r['doing'] for r in s['waves'])}** | "
                 f"**{sum(r['waiting'] for r in s['waves'])}** | **{sum(r['dropped'] for r in s['waves'])}** | **{_pct(s['total'])}** | **{_pct(s['total_gate'])}** |")
    nxt = s["next"]
    lines.append("")
    lines.append(f"Đợt hiện tại: **{s['current'] or '—'}** · việc kế: " + (f"**{nxt['id']}** {nxt['title']}" if nxt else "—"))
    if s["gate_warnings"]:
        lines.extend(["", "Cảnh báo cổng:"] + [f"- {warning}" for warning in s["gate_warnings"]])
    return "\n".join(lines)


def write_table(path: str = PLAN_FILE) -> bool:
    """Rewrite the progress table between the markers. Returns True when the file changed."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    plan = parse(text)
    if plan["bad"]:
        raise PlanError("Dòng việc không đọc được:\n" + "\n".join(plan["bad"]))
    a, b = text.find(MARK_START), text.find(MARK_END)
    if a < 0 or b < a:
        raise PlanError(f"Thiếu dấu {MARK_START} … {MARK_END} trong {os.path.basename(path)}")
    new = text[:a + len(MARK_START)] + "\n" + table(plan) + "\n" + text[b:]
    if new == text:
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    return True
