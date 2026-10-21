"""V3.1 M2.5 (C-M25, cloud-C 21/10) — write guard cấp trường `scenes.data`, chế độ SHADOW. Đặc tả: docs/V3_1_M0_10_BAO_VE_DU_LIEU_2026-10-20.md
(mục 2.1–2.5 trạng thái AUTO / USER_LOCKED / REVIEW_REQUIRED, 3.3 lỗ hổng L1–L6, 4.1 ca G1–G10). Sổ quyết định v31-d04-field-level-write-guard.

Cờ `field_guard` (TẮT = không đọc thêm, không ghi gì — đường ghi y hệt hôm nay). Bật: chỉ GHI ⚙ Chẩn đoán "lẽ ra đã…" — KHÔNG chặn, KHÔNG
đổi giá trị nào (shadow). Chế độ enforce (giữ trường khóa, ghi proposal, CAS theo `_rev`) = C3-6, chưa làm: write_scene(mode="enforce") ném
NotImplementedError.

  field_conflict  AI / tự động / công cụ ghi giá trị KHÁC vào trường USER_LOCKED (lẽ ra: giữ + đề xuất)          G1, G10
  field_review    AI ghi trường thuộc REVIEW_FIELDS đang có giá trị khác, hoặc trường đang REVIEW_REQUIRED       G4
  stale_write     ghi với revision cũ (`expected_rev` ≠ `_rev`), hoặc hàng đã đổi ở trường khác từ lúc nơi gọi đọc  G5, L6
Người (`actor kind human`) không bao giờ bị báo (G3). Trường dẫn xuất (DERIVED, mục 2.3) ghi tự do (G7). Trạng thái đọc tương thích: `_field_state`
(v2) trước, rồi `_user_locked` (v1) — khóa ở khóa gốc (`byd` khóa cả cây `byd.vat`).

Đã nối (shadow) các đường ghi: L1 llm_io.store_motion_prompts (khi nơi gọi AI truyền actor), L2 audio_first.fit_shots, L3 seedance_refs.set_route,
L4 prompt_rewrite._set_prompt, L5 tools/byd_fill, L6 prompt_formula._write + previz.compose_scene."""
import json
from typing import Any, Dict, List, Optional, Tuple

FLAG = "field_guard"
AUTO, USER_LOCKED, REVIEW_REQUIRED = "AUTO", "USER_LOCKED", "REVIEW_REQUIRED"
ACTOR_KINDS = ("human", "ai", "auto", "tool")
DELETE = object()                     # changes[field] = DELETE: xóa trường
# mục 2.2 — một nguồn; "Còn mở" ở mục 6 (người duyệt chốt danh sách khi bật enforce)
REVIEW_FIELDS = ("characters", "location_asset", "byd", "end_state", "dialogue", "duration_s", "image_prompt", "stage_camera", "plate_view")
# mục 2.3 — dẫn xuất / sổ sách của hệ thống: luôn AUTO (vẫn kiểm stale)
DERIVED = ("formula_check", "motion_en", "motion_en_src", "motion_en_src_fields", "motion_en_ambiguous", "ref_mark_sent", "layout",
           "layout_people", "difficulty_by", "difficulty_director", "stage_segment", "plate_setup", "plate_setup_scene", "spatial_state",
           "duration_from_voice")
META = ("_user_locked", "_field_state", "_field_prov", "_rev")


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def actor(kind: str, who: str, **extra) -> Dict[str, Any]:
    """Actor của lần ghi: kind human / ai / auto / tool, who = email / khâu / tên công cụ (+ job_id, run_id…)."""
    if kind not in ACTOR_KINDS:
        raise ValueError(f"actor kind '{kind}' không thuộc {ACTOR_KINDS}")
    return {"kind": kind, "who": who, **extra}


def _root(field: str) -> str:
    return str(field).split(".", 1)[0]


def state(data: Optional[Dict], field: str) -> str:
    """Trạng thái một trường (mục 2.5): `_field_state` (khóa đầy đủ hoặc khóa gốc) → `_user_locked` (khóa gốc) → AUTO."""
    data = data if isinstance(data, dict) else {}
    fs = data.get("_field_state") if isinstance(data.get("_field_state"), dict) else {}
    for key in (field, _root(field)):
        if fs.get(key) in (USER_LOCKED, REVIEW_REQUIRED):
            return fs[key]
    locked = set(data.get("_user_locked") or [])
    return USER_LOCKED if field in locked or _root(field) in locked else AUTO


def rev(data: Optional[Dict]) -> int:
    try:
        return int((data or {}).get("_rev") or 0)
    except (TypeError, ValueError):
        return 0


def _get(data: Dict, field: str):
    cur: Any = data
    for part in str(field).split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _empty(v) -> bool:
    return v in (None, "", [], {})


def assess(data: Optional[Dict], changes: Dict[str, Any], who: Dict, expected_rev: Optional[int] = None, current: Optional[Dict] = None,
           before: Optional[Dict] = None) -> List[Dict]:
    """Thuần (không I/O): các điều guard enforce LẼ RA đã làm với lần ghi này. `data` = dữ liệu nơi gọi đã đọc; `current` = hàng trong CSDL lúc
    ghi (khác `data` ở trường nơi gọi không ghi → stale_write); `before` = giá trị cũ của trường không nằm trong scenes.data (motion_prompt)."""
    data = data if isinstance(data, dict) else {}
    out: List[Dict] = []
    if expected_rev is not None and rev(data) != expected_rev:
        out.append({"code": "stale_write", "would": "stale", "fields": [], "why": f"revision {rev(data)} ≠ mong đợi {expected_rev}"})
    if current is not None:
        moved = sorted(k for k in set(current) | set(data)
                       if k not in changes and k not in META and current.get(k) != data.get(k))
        if moved:
            out.append({"code": "stale_write", "would": "stale", "fields": moved,
                        "why": "hàng đã đổi từ lúc đọc ở " + ", ".join(moved) + " — ghi cả bảng sẽ đè thay đổi xen giữa"})
    if (who or {}).get("kind") == "human":
        return out
    for field, new in changes.items():
        if _root(field) in DERIVED or _root(field) in META:
            continue
        new_v = None if new is DELETE else new
        old = (before or {}).get(field) if before is not None and field in before else _get(data, field)
        if new_v == old:
            continue
        st = state(data, field)
        if st == USER_LOCKED:
            out.append({"code": "field_conflict", "would": "keep", "field": field, "state": st, "old": old, "new": new_v})
        elif st == REVIEW_REQUIRED or (_root(field) in REVIEW_FIELDS and not _empty(old)):
            out.append({"code": "field_review", "would": "review", "field": field, "state": st, "old": old, "new": new_v})
    return out


def _load(conn, scene_id: int):
    row = conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return None, {}
    try:
        data = json.loads(row["data"] or "{}")
    except ValueError:
        data = {}
    return row["project_id"], data if isinstance(data, dict) else {}


def _short(v) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= 80 else s[:77] + "…"


def _message(ev: Dict, who: Dict) -> str:
    by = f"{(who or {}).get('kind', '?')}:{(who or {}).get('who', '?')}"
    if ev["code"] == "field_conflict":
        return (f"[shadow field_guard] {by} ghi `{ev['field']}` đang USER_LOCKED ({_short(ev['old'])} → {_short(ev['new'])}) — enforce sẽ GIỮ "
                "giá trị người + ghi đề xuất; hiện vẫn ghi như cũ")
    if ev["code"] == "field_review":
        return (f"[shadow field_guard] {by} đổi `{ev['field']}` ({_short(ev['old'])} → {_short(ev['new'])}) — enforce sẽ chuyển "
                "REVIEW_REQUIRED (người duyệt); hiện vẫn ghi như cũ")
    return f"[shadow field_guard] {by}: {ev['why']} — enforce sẽ báo StaleWrite; hiện vẫn ghi như cũ"


# rà M25-1: diag.record tự commit — gọi giữa giao dịch của nơi gọi là commit hộ NỬA LÔ (shadow đổi dữ liệu bền). Đang trong giao dịch →
# giữ dòng diag ở đây; ghi khi nơi gọi xong (flush sau commit / rollback của nó, hoặc lần observe / lock sau ngoài giao dịch).
_PENDING: Dict[int, Tuple[Any, List[tuple]]] = {}


def _say(conn, message: str, code: str, pid, scene_id) -> None:
    if conn.in_transaction:
        _PENDING.setdefault(id(conn), (conn, []))[1].append((message, code, pid, scene_id))
        return
    from . import diag
    diag.record(conn, "system", "warn", message, code, pid, scene_id)


def discard(conn) -> int:
    """Nơi gọi ROLLBACK: bỏ các dòng diag shadow đang giữ của lần ghi đã hủy (không báo "lẽ ra đã chặn" cho lần ghi không xảy ra) —
    gọi ngay sau conn.rollback(). Trả số dòng bỏ. Không bao giờ ném lỗi."""
    held = _PENDING.pop(id(conn), None)
    return len(held[1]) if held and held[0] is conn else 0


def flush(conn) -> int:
    """Ghi các dòng diag shadow đã giữ khi nơi gọi đang trong giao dịch — gọi SAU commit / rollback của nó. Còn trong giao dịch → để
    sau (không commit hộ). Trả số dòng đã ghi. Không bao giờ ném lỗi."""
    try:
        if id(conn) not in _PENDING or conn.in_transaction:
            return 0
    except Exception:  # noqa: BLE001 - kết nối đã đóng: bỏ dòng giữ (không ghi được, không ném)
        _PENDING.pop(id(conn), None)
        return 0
    held = _PENDING.pop(id(conn))
    if held[0] is not conn:                              # id tái dùng sau khi kết nối cũ mất: không phải của kết nối này
        return 0
    from . import diag
    for message, code, pid, scene_id in held[1]:
        try:
            diag.record(conn, "system", "warn", message, code, pid, scene_id)
        except Exception:  # noqa: BLE001 - diag tự giữ dòng không ghi được (_keep_lost)
            pass
    return len(held[1])


def observe(conn, scene_id: int, changes: Dict[str, Any], who: Dict, read_data: Optional[Dict] = None,
            expected_rev: Optional[int] = None, before: Optional[Dict] = None) -> Optional[List[Dict]]:
    """Shadow: cờ tắt → None (không đọc gì). Bật: so lần ghi sắp làm với trạng thái trường, ghi một dòng diag mỗi điều lẽ ra đã chặn; trả
    danh sách. `read_data` = bản nơi gọi đã đọc (có → so với hàng hiện tại để bắt stale). Không đổi dữ liệu, không bao giờ ném lỗi."""
    if not enabled():
        return None
    pid = None
    try:
        pid, current = _load(conn, scene_id)
        data = read_data if isinstance(read_data, dict) else current
        events = assess(data, changes, who, expected_rev, current if isinstance(read_data, dict) else None, before)
        flush(conn)
        for ev in events:
            _say(conn, _message(ev, who), ev["code"], pid, scene_id)
        return events
    except Exception as e:  # noqa: BLE001 - shadow never stops the real write
        try:
            _say(conn, f"field_guard (shadow) lỗi ({type(e).__name__}: {e}) — lần ghi vẫn đi như cũ", "field_guard", pid, scene_id)
        except Exception:  # noqa: BLE001
            pass
        return None


def lock(conn, scene_id: int, field: str, who: Dict) -> Optional[Dict]:
    """C-M25B: NGƯỜI sửa tay một trường không nằm trong cơ chế khóa cũ (motion prompt) → `_field_state[field] = USER_LOCKED` + provenance
    `_field_prov[field] = {by, at}` + `_rev` + 1. Cờ tắt / không phải người → None, không đọc, không ghi. Không bao giờ ném lỗi (lỗi → diag)."""
    if not enabled() or (who or {}).get("kind") != "human":
        return None
    pid = None
    try:
        import datetime
        pid, data = _load(conn, scene_id)
        fs = data.get("_field_state") if isinstance(data.get("_field_state"), dict) else {}
        prov = data.get("_field_prov") if isinstance(data.get("_field_prov"), dict) else {}
        fs[field] = USER_LOCKED
        prov[field] = {"by": f"human:{who.get('who', '?')}", "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        data["_field_state"], data["_field_prov"], data["_rev"] = fs, prov, rev(data) + 1
        mine = not conn.in_transaction                   # rà M25-1: giao dịch của nơi gọi → nó commit cùng lần sửa tay, không commit hộ
        conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), scene_id))
        if mine:
            conn.commit()
            flush(conn)
        return data
    except Exception as e:  # noqa: BLE001 - a lock that cannot be written is said, the person's edit stands
        try:
            _say(conn, f"field_guard: không ghi được khóa `{field}` ({type(e).__name__}: {e})", "field_guard", pid, scene_id)
        except Exception:  # noqa: BLE001
            pass
        return None


def write_scene(conn, scene_id: int, changes: Dict[str, Any], who: Dict, expected_rev: Optional[int] = None,
                mode: str = "shadow") -> Dict[str, Any]:
    """Hợp đồng M0.10 mục 2.4. shadow: chỉ observe — KHÔNG ghi (nơi gọi ghi như hôm nay); trả WriteResult {applied False, mode, kept_locked,
    proposals, conflicts, rev}. enforce = C3-6 (Cấp 3, chưa làm)."""
    if mode != "shadow":
        raise NotImplementedError("write_guard enforce = C3-6 (Cấp 3, sau shadow trên dự án thật) — chưa làm")
    events = observe(conn, scene_id, changes, who, expected_rev=expected_rev) or []
    keep = [e["field"] for e in events if e["code"] == "field_conflict"]
    review = [e["field"] for e in events if e["code"] == "field_review"]
    return {"applied": False, "mode": "shadow", "kept_locked": keep, "review": review,
            "proposals": {f: (None if changes[f] is DELETE else changes[f]) for f in keep + review}, "conflicts": events,
            "rev": rev(_load(conn, scene_id)[1]) if events or enabled() else None}
