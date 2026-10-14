"""Kiểm dây nối bố cục giữa các shot CÙNG chỗ đứng (người dùng 14/10, chuẩn bị tập 2) — chỉ đọc CSDL, 0 USD, không gọi model/Blender.

Vì sao: thử D6 #28/#29 (Kelly chạy A chân cầu thang → B đỉnh bậc thang): shot 2–5 cùng đứng ở B nhưng shot neo cả cảnh (shot 1) ở A →
cả bốn shot bị coi là "máy riêng", KHÔNG ảnh nào nối chúng với nhau; tường keo / Kelly / tháp mỗi ảnh một chỗ. Công cụ này in, TRƯỚC
khi bấm Gen ảnh, từng shot: chỗ đứng, góc máy sơ đồ G0, nền, ảnh neo, máy chung, giữ bố cục — và báo shot nào cùng chỗ với shot khác
mà không có dây nối nào.

Dây nối giữa hai shot cùng cảnh + cùng chỗ (một là đủ):
  neo       shot này nhận ảnh của shot kia làm ảnh neo storyboard (core/scene_storyboard.uses_anchor), hoặc ngược lại
  máy chung hai shot dùng chung một máy 3D / một render (location_pack.plan → shared_with: cùng camera_setup + cùng cỡ)
  bố cục    `continuity_from` của shot này là shot kia, hoặc ngược lại (ảnh shot kia gửi kèm vai layout_from)

Mức: do = có shot cùng chỗ mà không dây nối nào (bố cục sẽ lệch); vang = có dây nhưng ảnh neo chưa duyệt / chế độ storyboard tắt;
xanh = có dây.
"""
import json
from typing import Dict, List, Optional, Tuple

from . import features, scene_storyboard

LEVEL_ICON = {"do": "🔴", "vang": "🟡", "xanh": "🟢", "": "·"}


def _rows(conn, pid: int) -> List[Dict]:
    out = []
    for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        out.append({"id": r["id"], "idx": r["idx"], "data": json.loads(r["data"] or "{}")})
    return out


def _view(data: Dict) -> str:
    v = data.get("plate_view")
    v = v.get("background") if isinstance(v, dict) else v
    return "" if v in (None, "") else str(v)


def _shared_cameras(conn, pid: int) -> Tuple[Dict[int, int], Optional[str]]:
    """{scene id: scene id của shot đầu dùng chung máy} theo location_pack.plan; (…, lý do) khi không tính được."""
    try:
        from . import location_pack
        items = location_pack.plan(conn, pid)
    except Exception as e:  # noqa: BLE001 - không có bảng Kho / mô hình 3D: báo, không đoán
        return {}, f"không tính được máy 3D chung ({type(e).__name__}: {e})"
    by_name = {f"shot_{it['scene_id']}": it["scene_id"] for it in items}
    out = {}
    for it in items:
        first = (it.get("camera_why") or {}).get("shared_with")
        if first in by_name and by_name[first] != it["scene_id"]:
            out[it["scene_id"]] = by_name[first]
    return out, None


def audit(conn, pid: int, data_dir: str) -> Dict:
    """{"rows": [...một dòng mỗi shot có story_scene...], "notes": [...]}."""
    shots = _rows(conn, pid)
    notes: List[str] = []
    storyboard = scene_storyboard.enabled()
    if not storyboard:
        notes.append("Cờ storyboard_api TẮT: không shot nào nhận ảnh neo — chỉ còn máy chung / giữ bố cục nối các shot")
    if not features.on("anchor_by_spot"):
        notes.append("Cờ anchor_by_spot TẮT: shot đứng khác chỗ shot neo cả cảnh không nhận ảnh neo nào (kể cả khi chỗ đó có nhiều shot)")
    shared, why = _shared_cameras(conn, pid)
    if why:
        notes.append(why)
    by_idx = {s["idx"]: s for s in shots}
    edges: Dict[int, set] = {s["id"]: set() for s in shots}
    kinds: Dict[Tuple[int, int], List[str]] = {}

    def tie(a: int, b: int, kind: str) -> None:
        edges.setdefault(a, set()).add(b)
        edges.setdefault(b, set()).add(a)
        kinds.setdefault((min(a, b), max(a, b)), []).append(kind)

    groups: Dict[int, Optional[Dict]] = {}
    for s in shots:
        g = scene_storyboard.group_of(conn, pid, s["id"]) if storyboard else None
        groups[s["id"]] = g
        if g and scene_storyboard.uses_anchor(g, s["id"]):
            tie(s["id"], g["anchor"]["id"], "neo")
        if s["id"] in shared:
            tie(s["id"], shared[s["id"]], "máy chung")
        src = s["data"].get("continuity_from")
        if src is not None and by_idx.get(_int(src)) is not None:
            tie(s["id"], by_idx[_int(src)]["id"], "bố cục")
    rows = []
    for s in shots:
        d = s["data"]
        if not d.get("story_scene"):
            continue
        spot = d.get("plate_spot") if isinstance(d.get("plate_spot"), str) else None
        mates = [m for m in shots if spot and m["id"] != s["id"] and m["data"].get("story_scene") == d.get("story_scene")
                 and m["data"].get("plate_spot") == spot]
        linked = [m for m in mates if m["id"] in edges.get(s["id"], set())]
        g = groups[s["id"]]
        anchor = ""
        if g:
            anchor = ("chính là neo" if g["anchor"]["id"] == s["id"] else
                      f"shot {g['anchor']['idx']}" if scene_storyboard.uses_anchor(g, s["id"]) else
                      "không (máy riêng / quay khỏi mốc)")
        level, why_text = "", ""
        if mates and not linked:
            level = "do"
            why_text = (f"cùng chỗ {spot} với shot {', '.join(str(m['idx']) for m in mates)} nhưng KHÔNG dây nối nào — "
                        "bố cục tường/người/mốc có thể lệch; bật anchor_by_spot, hoặc cho cùng camera_setup, hoặc ghi continuity_from")
        elif mates:
            warn = scene_storyboard.anchor_warning(conn, data_dir, pid, s["id"]) if storyboard else None
            level = "vang" if warn else "xanh"
            why_text = warn or ("nối với shot " + ", ".join(
                f"{m['idx']} ({'/'.join(kinds.get((min(s['id'], m['id']), max(s['id'], m['id'])), []))})" for m in linked))
        rows.append({"idx": s["idx"], "story_scene": d.get("story_scene"), "size": d.get("size") or "", "spot": spot or "",
                     "setup": d.get("plate_setup") or d.get("camera_setup") or "", "view": _view(d),
                     "stage_camera": bool(d.get("stage_camera")), "continuity_from": d.get("continuity_from"),
                     "anchor": anchor, "mates": [m["idx"] for m in mates], "linked": [m["idx"] for m in linked],
                     "level": level, "why": why_text})
    return {"rows": rows, "notes": notes}


def _int(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def report(res: Dict, title: str = "") -> str:
    lines = [f"# Kiểm dây nối bố cục{(' — ' + title) if title else ''}", ""]
    for n in res["notes"]:
        lines.append(f"- ⚠ {n}")
    if res["notes"]:
        lines.append("")
    red = [r for r in res["rows"] if r["level"] == "do"]
    lines.append(f"**{len(red)} shot ĐỎ** (cùng chỗ mà không dây nối) / {len(res['rows'])} shot có cảnh.")
    lines += ["", "| Mức | Cảnh | Shot | Cỡ | Chỗ đứng | Góc máy | Nền | Máy 3D giải | Ảnh neo | Lý do |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        lines.append(f"| {LEVEL_ICON[r['level']]} | {r['story_scene']} | {r['idx']} | {r['size']} | {r['spot'] or '—'} | "
                     f"{r['setup'] or '—'} | {r['view'] or '—'} | {'có' if r['stage_camera'] else '—'} | {r['anchor'] or '—'} | "
                     f"{r['why'] or ''} |")
    return "\n".join(lines) + "\n"
