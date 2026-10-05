"""Bảng kê tài nguyên trước Director (S14.23 — Bộ não prompt Đợt 4, docs/KE_HOACH_BO_NAO_PROMPT_TU_HOC_2026-10-04.md; cờ
`asset_checklist`, TẮT tới khi chạy thật).

Before: the person attached library entries first, the Director was told "BẮT BUỘC dùng" them (assets.context_text) and invented
whatever was missing — the person learnt what was missing only AFTER paying for the Director. Here ONE cheap Claude call (stage
`asset_checklist`, no picture, prompts/27) reads the script and lists every character / place / prop / weapon / pet / outfit it needs,
matched to the library by id. The code does not trust the ids: an id not in the library, or of another kind, is dropped and said; an
exact name / other-name match of the same kind is filled in by the code (said too). The table (✅ đã gắn / ✅ có trong Kho / ⚠️ thiếu) is
shown before the Director button, with a quick "Gắn" for library entries not attached yet.

Flag off: nothing is drawn, nothing is called, the Director prompt is untouched (this module never writes into it).
Money: llm_runner client (sổ chi) tagged `asset_checklist` → project budget line claude_director; the estimate is on the button
(cost.llm_button_tag). State per project in app_settings ('asset_checklist:<pid>').
"""
import hashlib
import json
from typing import Dict, List, Optional

FEATURE = "asset_checklist"
STAGE = "asset_checklist"
PROMPT = "27_asset_checklist.md"
KINDS = ("character", "location", "prop", "weapon", "pet", "outfit")
# prop / weapon: the line between them is fuzzy (a "gậy" is both) — an id of the other one is still the same thing
SAME_KIND = {"prop": {"prop", "weapon"}, "weapon": {"prop", "weapon"}}
STATUS_LABEL = {"attached": "✅ đã gắn vào dự án", "in_library": "✅ có trong Kho (chưa gắn)", "missing": "⚠️ thiếu"}


class ChecklistError(ValueError):
    """Shown to the person as it is (a ValueError, so the dashboard's `act` shows it)."""


def enabled() -> bool:
    from . import features
    return features.on(FEATURE)


def _key(pid: int) -> str:
    return f"asset_checklist:{pid}"


# ---- inputs -------------------------------------------------------------------------------------------------------------------------
def script_text(p, pid: int) -> str:
    """The script as the Director reads it: the scenes ("### Cảnh N — tiêu đề") when the script is split, else the pasted text."""
    from . import shots
    scenes = shots.story_scenes(p, pid)
    text = "\n\n".join(f"### Cảnh {s['idx']} — {s['heading']}\n{s['text']}" for s in scenes if (s["text"] or "").strip())
    if not text.strip():
        row = p.conn.execute("SELECT script_text FROM projects WHERE id=?", (pid,)).fetchone()
        text = (row["script_text"] if row else "") or ""
    return text.strip()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _game(conn, pid: int) -> str:
    row = conn.execute("SELECT game FROM projects WHERE id=?", (pid,)).fetchone()
    return (row["game"] if row else None) or "FF"


def library(conn, pid: int) -> List[Dict]:
    """Every library entry (shared + this project's) the script could need — names only, no picture read; `anh` = approved pictures."""
    rows = conn.execute(
        "SELECT a.id, a.kind, a.name, a.aliases, (SELECT COUNT(*) FROM asset_images i WHERE i.asset_id=a.id AND "
        "(i.status IS NULL OR i.status IN ('approved','claude_ok'))) AS n, "
        "(SELECT COUNT(*) FROM asset_images i WHERE i.asset_id=a.id AND i.status='claude_ok') AS nc FROM assets a WHERE (a.project_id IS NULL OR a.project_id=?) AND a.game=? "
        "AND a.kind IN (" + ",".join("?" * len(KINDS)) + ") ORDER BY a.kind, lower(a.name)", (pid, _game(conn, pid), *KINDS)).fetchall()
    return [{"id": r["id"], "kind": r["kind"], "name": r["name"], "aliases": r["aliases"] or "", "images": r["n"], "claude_only": r["nc"]} for r in rows]


def _attached(conn, pid: int) -> set:
    return {r[0] for r in conn.execute("SELECT asset_id FROM project_assets WHERE project_id=?", (pid,))}


def build_prompt(p, pid: int, script: str, lib: List[Dict]) -> str:
    from .assets import KINDS as LABELS
    from .prompts import _read
    attached = _attached(p.conn, pid)
    game = _game(p.conn, pid)
    if lib:
        entries = "\n".join(json.dumps({"id": a["id"], "loai": a["kind"], "nhan": LABELS.get(a["kind"], a["kind"]), "ten": a["name"],
                                        "ten_khac": a["aliases"], "so_anh": a["images"], "da_gan": a["id"] in attached},
                                       ensure_ascii=False) for a in lib)
        kho = (f"# Kho tài nguyên (game {game}) — {len(lib)} mục\nMỗi dòng một mục (`da_gan` = đã gắn vào dự án này; loại `outfit` = "
               f"Trang phục, để nhân vật mặc, không phải nhân vật).\n```json\n{entries}\n```")
    else:
        kho = (f"# Kho tài nguyên (game {game})\nKho trống — chưa có mục nào; mọi thứ kịch bản cần đều là thiếu (`trong_kho` = null).")
    return "\n\n".join([_read("prompts", PROMPT).strip(), kho, f"# Kịch bản\n```text\n{script}\n```"])


# ---- the answer ---------------------------------------------------------------------------------------------------------------------
def _validate(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("can"), list):
        raise ValueError("cần trường `can` (danh sách)")
    for row in obj["can"]:
        if not isinstance(row, dict):
            raise ValueError("mỗi dòng của `can` là một object")
        if row.get("loai") not in KINDS:
            raise ValueError(f"`loai` phải là một trong {', '.join(KINDS)}")
        if not str(row.get("ten") or "").strip():
            raise ValueError("mỗi dòng cần `ten`")
        k = row.get("trong_kho")
        if isinstance(k, str) and k.strip().isdigit():          # "12" → 12: not worth a paid retry
            row["trong_kho"] = k = int(k.strip())
        if k is not None and not (isinstance(k, int) and not isinstance(k, bool)):
            raise ValueError("`trong_kho` là id (số) hoặc null")
    return obj


def _kind_ok(row_kind: str, lib_kind: str) -> bool:
    return lib_kind in SAME_KIND.get(row_kind, {row_kind})


def _name_match(row: Dict, lib: List[Dict]) -> Optional[Dict]:
    from .assets import fold
    want = fold(row["ten"])
    for a in lib:
        if not _kind_ok(row["loai"], a["kind"]):
            continue
        names = [a["name"]] + [x for x in str(a["aliases"]).replace(";", ",").replace("|", ",").split(",")]
        if any(fold(n) == want for n in names if fold(n)):
            return a
    return None


def reconcile(obj: Dict, lib: List[Dict]) -> Dict:
    """Model answer → rows the code checked: {kind, name, scenes, main, asset_id, for_character, why, note}."""
    from .assets import KINDS as LABELS
    by_id = {a["id"]: a for a in lib}
    rows, seen = [], set()
    for r in obj["can"]:
        name = " ".join(str(r["ten"]).split())
        if (r["loai"], name.lower()) in seen:
            continue
        seen.add((r["loai"], name.lower()))
        notes, aid = [], r.get("trong_kho")
        if aid is not None:
            a = by_id.get(aid)
            if a is None:
                notes.append(f"Claude ghi id {aid} nhưng Kho không có mục này — code bỏ")
                aid = None
            elif not _kind_ok(r["loai"], a["kind"]):
                notes.append(f"Claude ghép với mục Kho {aid} '{a['name']}' loại {LABELS.get(a['kind'], a['kind'])}, không cùng loại "
                             f"{LABELS.get(r['loai'], r['loai'])} — code bỏ")
                aid = None
        if aid is None:
            hit = _name_match({"loai": r["loai"], "ten": name}, lib)
            if hit is not None:
                aid = hit["id"]
                notes.append(f"code ghép theo tên trùng khớp với mục Kho '{hit['name']}' (id {aid})")
        scenes = sorted({int(x) for x in (r.get("canh") or []) if isinstance(x, (int, float)) or str(x).isdigit()})
        rows.append({"kind": r["loai"], "name": name, "scenes": scenes, "main": r.get("quan_trong") == "chinh",
                     "asset_id": aid, "for_character": str(r.get("cho_nhan_vat") or "").strip() or None,
                     "why": str(r.get("vi_sao") or "").strip(), "note": "; ".join(notes)})
    return {"rows": rows, "model_missing": [str(x) for x in obj.get("thieu") or []]}


def _status(row: Dict, attached: set, lib_ids: set) -> str:
    if row["asset_id"] is None or row["asset_id"] not in lib_ids:
        return "missing"
    return "attached" if row["asset_id"] in attached else "in_library"


# ---- run / read ---------------------------------------------------------------------------------------------------------------------
def estimate_usd(conn) -> Optional[float]:
    from . import cost
    return cost.llm_estimate(conn, STAGE, 2)     # rà: ask_json may call twice when the JSON is wrong — the label counts both (tính dư)


def run(p, pid: int, client) -> Dict:
    """One Claude call; the checked table is saved and returned (see get). Missing script / flag off → ChecklistError, no call."""
    from . import diag, llm_runner
    if not enabled():
        raise ChecklistError("Bảng kê tài nguyên đang tắt (cờ `asset_checklist` ở ⚙ Cài đặt → 🧪) — chưa gọi Claude.")
    from . import access
    access.need_edit(p, pid, "lập bảng kê tài nguyên")    # rà S14.23: a viewer must not spend on Claude nor write the project's table
    if client is None:
        raise ChecklistError("Chưa cấu hình Claude (ANTHROPIC_API_KEY hoặc LLM_PROVIDER) — chưa lập được bảng kê tài nguyên.")
    script = script_text(p, pid)
    if not script:
        raise ChecklistError("Chưa có kịch bản — dán hoặc tải kịch bản ở Bước 1 rồi mới lập bảng kê tài nguyên (chưa gọi Claude).")
    lib = library(p.conn, pid)
    prompt = build_prompt(p, pid, script, lib)

    def note(text):
        diag.record(p.conn, "director", "info", f"Bảng kê tài nguyên: {text}", code="asset_checklist_retry", project_id=pid)
    try:
        with llm_runner.tagged(STAGE, pid):
            obj, tin, tout = llm_runner.ask_json(client, prompt, _validate, note=note)
    except Exception as e:
        diag.record(p.conn, "director", "warn", f"Bảng kê tài nguyên lỗi ({type(e).__name__}: {str(e)[:200]}) — chưa có bảng, "
                    "Director vẫn chạy được như cũ", code="asset_checklist_failed", project_id=pid)
        raise
    out = reconcile(obj, lib)
    state = {"script_hash": _hash(script), "rows": out["rows"], "model_missing": out["model_missing"], "library_size": len(lib),
             "game": _game(p.conn, pid), "tokens": [tin, tout]}
    p.conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                   (_key(pid), json.dumps(state, ensure_ascii=False)))
    p.conn.commit()
    res = get(p, pid)
    diag.record(p.conn, "director", "info",
                f"Bảng kê tài nguyên: {len(res['rows'])} thứ cần, {len(res['missing'])} thiếu"
                + (f" ({', '.join(res['missing'][:6])})" if res["missing"] else "")
                + f"; đã gửi Kho {len(lib)} mục, kịch bản {len(script)} ký tự", code="asset_checklist", project_id=pid)
    return res


def get(p, pid: int) -> Optional[Dict]:
    """The saved table with statuses read NOW (an entry attached since shows ✅), or None (flag off / never run).
    {rows: [... status, status_label], missing: [names], warnings: [...], stale: script changed since}."""
    if not enabled():
        return None
    row = p.conn.execute("SELECT value FROM app_settings WHERE key=?", (_key(pid),)).fetchone()
    make = to_create_rows(p.conn, pid)         # S14.35: sets the idea needs made (Đạo diễn ảnh ref / Meshy 3D) — listed, never run here
    if not row:
        if not make:
            return None
        return {"rows": make, "missing": [], "to_create": [r["name"] for r in make], "warnings": [], "stale": False, "library_size": 0}
    try:
        state = json.loads(row[0])
    except ValueError:
        return {"rows": [], "missing": [], "stale": True, "warnings": ["Bảng kê đã lưu bị hỏng — bấm lập lại."]}
    attached = _attached(p.conn, pid)
    libs = {a["id"]: a for a in library(p.conn, pid)}      # rà: the same Kho as at run time (this game / this project)
    lib_ids = set(libs)
    rows = []
    for r in state.get("rows") or []:
        r = dict(r)
        if r.get("asset_id") is not None and r["asset_id"] not in lib_ids:
            r["note"] = "; ".join(x for x in [r.get("note"), f"mục Kho {r['asset_id']} đã bị xóa"] if x)
        r["status"] = _status(r, attached, lib_ids)
        r["status_label"] = STATUS_LABEL[r["status"]]
        r["claude_only"] = (libs.get(r.get("asset_id")) or {}).get("claude_only") or 0   # S14.42 tầng C: ảnh chỉ-Claude-duyệt của mục này
        rows.append(r)
    missing = [r["name"] for r in rows if r["status"] == "missing"]
    warnings = []
    if not state.get("library_size"):
        warnings.append(f"Kho trống (game {state.get('game') or '?'}) — mọi thứ kịch bản cần đều là thiếu.")
    if not rows:
        warnings.append("Claude không kê được thứ gì kịch bản cần — kiểm lại kịch bản (có tên nhân vật / nơi chưa?).")
    told = {x.strip().lower() for x in state.get("model_missing") or []}
    differ = sorted({m for m in missing if m.lower() not in told})
    if told and differ:
        warnings.append("Code kiểm lại thấy thiếu thêm: " + ", ".join(differ) + " (Claude không ghi vào `thieu`).")
    stale = state.get("script_hash") != _hash(script_text(p, pid))
    return {"rows": rows + make, "missing": missing, "to_create": [r["name"] for r in make], "warnings": warnings, "stale": stale,
            "library_size": state.get("library_size") or 0}


def to_create_rows(conn, pid: int) -> List[Dict]:
    """S14.35: a place outside the game that the Kho does not have — status `to_create`, with the person's choice and the price estimate."""
    from . import idea_buildable
    try:
        needs = idea_buildable.scene_needs(conn, pid)
    except Exception:  # noqa: BLE001 - the table must still draw without the idea's state
        return []
    rows = []
    for n in needs:
        price = f" · ước ≤ {n['est_usd']:.2f} USD" if n.get("est_usd") else ""
        rows.append({"kind": "location", "name": n["name"], "scenes": [], "main": True, "asset_id": None, "for_character": None,
                     "why": "nơi ngoài game, chưa có trong Kho", "note": n["note"], "status": "to_create", "choice": n["choice"],
                     "est_usd": n.get("est_usd"), "status_label": f"🛠 cần tạo bối cảnh — {n['label']}{price}"})
    try:                                       # S14.43 mục 4: an exposed phone screen = a simulated screen to draw (listed, never run here)
        screens = idea_buildable.screen_needs(conn, pid)
    except Exception as e:  # noqa: BLE001 - said in the table, never a silent skip
        screens = [{"scene": None, "name": "Màn hình điện thoại mô phỏng", "what": "", "est_usd": None,
                    "note": f"không kiểm được màn hình trong kịch bản: {e}"}]
    for n in screens:
        price = f" · ước ≤ {n['est_usd']:.2f} USD" if n.get("est_usd") else " · chưa ước được giá"
        rows.append({"kind": "prop", "name": n["name"], "scenes": [n["scene"]] if n.get("scene") else [], "main": True, "asset_id": None,
                     "for_character": None, "why": "lộ góc nhìn màn hình điện thoại: " + n["what"] if n.get("what") else "lộ màn hình",
                     "note": n["note"], "status": "to_create", "choice": "screen_mock", "est_usd": n.get("est_usd"),
                     "status_label": f"🛠 cần vẽ màn hình mô phỏng{price}"})
    return rows


def attach(p, pid: int, asset_id: int) -> None:
    """Quick "Gắn": the library entry joins the project (the Director then reads it in 'Tài nguyên có sẵn')."""
    from . import access, assets
    access.need_edit(p, pid, "gắn tài nguyên")
    if asset_id not in {a["id"] for a in library(p.conn, pid)}:     # rà: only an entry of THIS project's Kho (game, shared or own)
        raise ChecklistError(f"Mục Kho {asset_id} không còn hoặc không thuộc Kho của dự án này — lập lại bảng kê.")
    assets.attach(p.conn, pid, asset_id)


def mock_answer(prompt: str) -> Dict:
    """MockLlm (LLM_PROVIDER=mock): every library entry whose name is in the script, nothing invented."""
    import re
    from .assets import fold
    m = re.search(r"# Kho tài nguyên[^\n]*\n[^\n]*\n```json\n(.*?)\n```", prompt, re.S)
    script = prompt.rsplit("# Kịch bản", 1)[-1]
    body = " " + fold(script) + " "
    rows = []
    for line in (m.group(1).splitlines() if m else []):
        a = json.loads(line)
        if " " + fold(a["ten"]) + " " in body:
            rows.append({"loai": a["loai"], "ten": a["ten"], "canh": [1], "quan_trong": "chinh", "trong_kho": a["id"],
                         "vi_sao": "giả lập: tên có trong kịch bản"})
    return {"can": rows, "thieu": []}
