"""Ngân sách TRÍCH RIÊNG từng dự án (người dùng 08/10 chọn phương án 1 — TODO.md "VIỆC ĐỂ SAU DỰ ÁN KHỦNG LONG ĐỎ" điểm 1a).

Trước đây trần đợt thử (core.budget, vd. 74,5 USD) là MỘT hàng chung cả Dashboard: dự án chạy nhanh ăn trước phần của dự án khác.

  trích     lượt gen TRẢ TIỀN đầu tiên của một dự án (ảnh / video / âm thanh / Claude — mọi dòng đi qua cost.record_usage, nhà cung
            cấp không phải mock) tự trích từ trần đợt thử một phần = ước tính DƯ cả dự án (project_budget.estimate_view "total" = đã chi
            + phần còn lại có cộng tỷ lệ gen lại đo được, Claude ×1,3; cộng âm thanh ước tính của cost_summary). Số dư chung không đủ →
            trích phần còn lại + cảnh báo rõ (diag, money_policy.note). Chỉ trích khi đợt thử đang bật (có trần chung để trích).
  bổ sung   khi số trích còn TỰ ĐỘNG (người chưa sửa tay) và bảng shot đổi số shot (vd. lượt Claude đầu tiên là Director, lúc đó chưa có
            shot nào) → tính lại; chỉ TĂNG, không trích một dự án hai lần.
  giữ       phần đã trích của dự án A không tính là chỗ trống cho dự án khác (`free`); chỉ người sửa tay (`set_amount`) mới đổi được.
  trả lại   giao bản cuối (core.delivered.mark) hoặc cất dự án (core.archive) → phần chưa dùng trả về hàng chung (state 'released').
  lịch sử   mọi lần trích / bổ sung / sửa tay / trả lại ghi vào project_reserve_log (ai, lúc nào, bao nhiêu, trước → sau).
  cảnh báo  chính sách tiền 04/10 giữ nguyên: KHÔNG chặn. Dự án vượt phần trích → cảnh báo riêng dự án (`warning`); dự án không có phần
            trích mà lượt gửi lấn vào phần đã trích của dự án khác → cảnh báo; tổng vượt trần chung → cảnh báo chung cũ (core.budget).
  không     dự án đã giao (core.delivered) / đã cất (📦) không trích; dự án đã có dòng sổ chi trả tiền TRƯỚC mốc bật tính năng
            (app_settings 'project_reserve_since') không bị trích hồi tố (vd. #22 Khủng Long Đỏ).
"""
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import access

TABLE = ("CREATE TABLE IF NOT EXISTS project_reserves (project_id INTEGER PRIMARY KEY, usd REAL NOT NULL, estimate_usd REAL,"
         " source TEXT NOT NULL DEFAULT 'auto', state TEXT NOT NULL DEFAULT 'active', scenes INTEGER, created_at TEXT NOT NULL,"
         " updated_at TEXT, released_at TEXT, returned_usd REAL, note TEXT)")
LOG_TABLE = ("CREATE TABLE IF NOT EXISTS project_reserve_log (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, at TEXT NOT NULL,"
             " who TEXT, action TEXT NOT NULL, usd REAL, before_usd REAL, note TEXT)")
START_KEY = "project_reserve_since"
SYSTEM = "hệ thống"
ACTIONS = {"reserve": "Trích", "top_up": "Bổ sung", "manual": "Sửa tay", "release": "Trả lại"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure(conn) -> None:
    """Hai bảng + mốc bật tính năng (idempotent; core/db.py SCHEMA cũng tạo bảng)."""
    conn.execute(TABLE)
    conn.execute(LOG_TABLE)
    if conn.execute("SELECT 1 FROM app_settings WHERE key=?", (START_KEY,)).fetchone() is None:
        conn.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)", (START_KEY, _now()))
        conn.commit()


def since(conn) -> Optional[str]:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (START_KEY,)).fetchone()
    return row[0] if row else None


def get(conn, pid: int) -> Optional[Dict]:
    try:
        row = conn.execute("SELECT * FROM project_reserves WHERE project_id=?", (pid,)).fetchone()
    except sqlite3.OperationalError:             # an old database without the table: nothing reserved
        return None
    return dict(row) if row else None


def history(conn, pid: Optional[int] = None, limit: int = 50) -> List[Dict]:
    try:
        q = "SELECT * FROM project_reserve_log" + (" WHERE project_id=?" if pid is not None else "") + " ORDER BY id DESC LIMIT ?"
        return [dict(r) for r in conn.execute(q, ((pid,) if pid is not None else ()) + (int(limit),))]
    except sqlite3.OperationalError:
        return []


def _log(conn, pid: int, who: Optional[str], action: str, usd: float, before: Optional[float], note: str = "") -> None:
    conn.execute("INSERT INTO project_reserve_log (project_id, at, who, action, usd, before_usd, note) VALUES (?,?,?,?,?,?,?)",
                 (pid, _now(), who or SYSTEM, action, round(float(usd), 2), None if before is None else round(float(before), 2), note))


# ---- số tiền ------------------------------------------------------------------------------------------------------------------------------
def project_spent(conn, pid: int, pricing: Optional[Dict] = None) -> float:
    """Tiền dự án đã chi (mọi dòng sổ chi trả tiền của dự án, kể cả âm thanh; dòng thiếu giá ước tính DƯ như budget_rounds)."""
    from . import budget_rounds, cost
    pricing = pricing if pricing is not None else cost.load_pricing()
    total, cache = 0.0, {}
    for r in conn.execute("SELECT * FROM usage_events WHERE project_id=? AND provider NOT LIKE 'mock%'", (pid,)).fetchall():
        usd, _ = budget_rounds.price(pricing, r, cache)
        total += usd or 0.0
    return round(total, 4)


def _active(conn) -> List[Dict]:
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM project_reserves WHERE state='active'")]
    except sqlite3.OperationalError:
        return []


def outstanding(conn, exclude: Optional[int] = None, pricing: Optional[Dict] = None) -> Dict:
    """Phần đã trích CHƯA dùng của các dự án đang giữ phần trích: {"usd", "projects": {pid: usd}}."""
    out = {}
    for r in _active(conn):
        if exclude is not None and r["project_id"] == exclude:
            continue
        left = max(0.0, float(r["usd"]) - project_spent(conn, r["project_id"], pricing))
        if left > 0:
            out[r["project_id"]] = round(left, 4)
    return {"usd": round(sum(out.values()), 4), "projects": out}


def pool(conn, pricing: Optional[Dict] = None) -> Optional[Dict]:
    """Trần chung của đợt thử: {"usd" (mức dự tính), "spent" (đã chi cả đợt)} hoặc None khi đợt thử tắt."""
    from . import budget
    b = budget.get(conn)
    if not b.get("enabled"):
        return None
    s = budget.spent(conn, since=b["since"]) if pricing is None else budget.spent(conn, pricing, since=b["since"])  # default prices: cached
    return {"usd": float(b["usd"]), "spent": float(s["usd"])}


def free(conn, exclude: Optional[int] = None, pricing: Optional[Dict] = None) -> Optional[float]:
    """Chỗ trống của hàng chung = trần đợt thử − đã chi cả đợt − phần đã trích chưa dùng của các dự án (trừ `exclude`). None = đợt
    thử tắt. Có thể âm (đã vượt)."""
    pl = pool(conn)
    if pl is None:
        return None
    return round(pl["usd"] - pl["spent"] - outstanding(conn, exclude, pricing)["usd"], 4)


def overview(conn) -> Dict:
    """Cho Dashboard: {"pool", "free", "reserved" (đang giữ, chưa dùng), "projects": số dự án đang giữ phần trích}."""
    from . import cost
    pricing = cost.load_pricing()
    pl = pool(conn)
    out = outstanding(conn, pricing=pricing)
    return {"pool": pl, "free": None if pl is None else round(pl["usd"] - pl["spent"] - out["usd"], 2),
            "reserved": round(out["usd"], 2), "projects": len(_active(conn))}


# ---- ai được trích -----------------------------------------------------------------------------------------------------------------------
def skip_reason(conn, pid: int) -> Optional[str]:
    """Vì sao dự án KHÔNG được tự trích, hoặc None."""
    row = conn.execute("SELECT COALESCE(archived, 0) FROM projects WHERE id=?", (pid,)).fetchone()
    if row is None:
        return "không có dự án"
    if row[0]:
        return "dự án đã cất"
    from . import delivered
    if delivered.is_delivered(conn, pid):
        return "dự án đã giao bản cuối"
    mark = since(conn)
    if mark and conn.execute("SELECT 1 FROM usage_events WHERE project_id=? AND provider NOT LIKE 'mock%' AND at < ? LIMIT 1",
                             (pid, mark)).fetchone():
        return "dự án đã chi tiền trước khi có tính năng trích riêng (không trích hồi tố)"
    return None


def _scenes(conn, pid: int) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0])


def estimate(conn, pid: int) -> Dict:
    """Ước tính DƯ cả dự án: {"usd", "note"} — estimate_view total (+ âm thanh của cost_summary). Lỗi → usd 0 + câu lý do."""
    from . import project_budget
    from .pipeline import Pipeline
    try:
        view = project_budget.estimate_view(Pipeline(conn), pid)
        audio = float(((view.get("summary") or {}).get("audio")) or 0.0)
        return {"usd": round(float(view["total"]) + audio, 2), "note": ""}
    except Exception as e:  # noqa: BLE001 - the reservation is still made (0) and the reason kept; retried when the shot table changes
        return {"usd": 0.0, "note": f"chưa tính được ước tính ({type(e).__name__}: {str(e)[:120]})"}


def _short_note(conn, pid: int, want: float, took: float, free_usd: float, what: str) -> str:
    from . import money_policy
    text = (f"⚠ dự án #{pid}: {what} cần ≈ ${want:.2f} (ước tính dư cả dự án) nhưng hàng chung đợt thử chỉ còn trống ≈ "
            f"${max(0.0, free_usd):.2f} — đã trích ${took:.2f}, THIẾU ${want - took:.2f}. Không chặn: lượt gửi vẫn đi, dự án sẽ bị "
            "cảnh báo khi vượt phần trích. Cách xử lý: nâng trần đợt thử (⚙ → 💵 Tiền) hoặc sửa tay phần trích (Bước 1 → 💵)")
    money_policy.note(conn, text, stage="system", project_id=pid, key="project_reserve")
    return text


# ---- trích / bổ sung ---------------------------------------------------------------------------------------------------------------------
def on_paid(conn, pid: Optional[int], provider: str) -> Optional[Dict]:
    """Gọi sau MỖI dòng sổ chi (cost.record_usage). Lần trả tiền đầu tiên → trích; sau đó chỉ bổ sung khi bảng shot đổi và số trích còn
    tự động. Trả bản ghi phần trích (hoặc None). Không bao giờ ném lỗi ra nơi ghi sổ chi (nơi gọi bọc try)."""
    if pid is None or str(provider or "").startswith("mock"):
        return None
    from . import budget, cost
    if not budget.get(conn).get("enabled"):
        return None                                   # no shared cap to take from
    ensure(conn)
    cur = get(conn, pid)
    if cur is not None:
        if cur["state"] == "active" and cur["source"] == "auto" and _scenes(conn, pid) != (cur["scenes"] if cur["scenes"] is not None else -1):
            return _top_up(conn, pid, cur)
        return cur
    if skip_reason(conn, pid):
        return None
    pricing = cost.load_pricing()
    est = estimate(conn, pid)
    room = (free(conn, exclude=pid, pricing=pricing) or 0.0) + project_spent(conn, pid, pricing)   # its own spend is in the pool's spent
    took = round(min(est["usd"], max(0.0, room)), 2)
    note = est["note"]
    if est["usd"] - took > 0.005:
        note = (note + "; " if note else "") + f"thiếu ${est['usd'] - took:.2f} so với ước tính (hàng chung không đủ)"
    now = _now()
    ins = conn.execute("INSERT OR IGNORE INTO project_reserves (project_id, usd, estimate_usd, source, state, scenes, created_at, updated_at,"
                       " note) VALUES (?,?,?,?,?,?,?,?,?)",
                       (pid, took, est["usd"], "auto", "active", _scenes(conn, pid), now, now, note))
    if ins.rowcount:                                  # another thread may have reserved first: one reservation only
        _log(conn, pid, SYSTEM, "reserve", took, None, f"ước tính dư ${est['usd']:.2f}" + (f" — {note}" if note else ""))
    conn.commit()
    if ins.rowcount and est["usd"] - took > 0.005:
        _short_note(conn, pid, est["usd"], took, room, "lần trích đầu")
    return get(conn, pid)


def _top_up(conn, pid: int, cur: Dict) -> Dict:
    from . import cost
    pricing = cost.load_pricing()
    est = estimate(conn, pid)
    scenes = _scenes(conn, pid)
    old = float(cur["usd"])
    want = est["usd"] - old
    add, room = 0.0, None
    if want > 0.005:
        room = free(conn, exclude=None, pricing=pricing) or 0.0
        add = round(min(want, max(0.0, room)), 2)
    conn.execute("UPDATE project_reserves SET usd=?, estimate_usd=?, scenes=?, updated_at=? WHERE project_id=? AND source='auto'",
                 (round(old + add, 2), est["usd"], scenes, _now(), pid))
    if add > 0:
        _log(conn, pid, SYSTEM, "top_up", old + add, old, f"bảng shot đổi — ước tính dư mới ${est['usd']:.2f}")
    conn.commit()
    if want - add > 0.005:
        _short_note(conn, pid, est["usd"], old + add, (room or 0.0) + old, "bổ sung")
    return get(conn, pid)


# ---- người sửa tay / trả lại -----------------------------------------------------------------------------------------------------------
def set_amount(conn, pid: int, usd: float, who: Optional[str], why: str = "", p=None) -> Dict:
    """Người sửa tay số trích (từ đây không tự bổ sung nữa). Vượt chỗ trống của hàng chung → vẫn lưu, trả "warning" có số liệu."""
    if p is not None:
        access.need_edit(p, pid, "sửa ngân sách trích riêng")
    usd = round(float(usd), 2)
    if usd < 0:
        raise ValueError("số trích phải ≥ 0")
    ensure(conn)
    cur = get(conn, pid)
    before = None if cur is None else float(cur["usd"])
    now = _now()
    if cur is None:
        conn.execute("INSERT INTO project_reserves (project_id, usd, estimate_usd, source, state, scenes, created_at, updated_at, note)"
                     " VALUES (?,?,?,?,?,?,?,?,?)", (pid, usd, None, "manual", "active", None, now, now, "người tạo tay"))
    else:
        conn.execute("UPDATE project_reserves SET usd=?, source='manual', state='active', released_at=NULL, returned_usd=NULL,"
                     " updated_at=? WHERE project_id=?", (usd, now, pid))
    _log(conn, pid, who, "manual", usd, before, str(why or "").strip())
    conn.commit()
    out = get(conn, pid)
    room = free(conn)
    if room is not None and room < -0.005:
        out["warning"] = (f"⚠ tổng phần trích riêng + đã chi vượt trần chung đợt thử ${-room:.2f} — vẫn lưu (chỉ cảnh báo); nâng trần đợt "
                          "thử ở ⚙ → 💵 Tiền nếu cần")
    return out


def release(conn, pid: int, who: Optional[str], why: str) -> Optional[Dict]:
    """Giao bản cuối / cất dự án: phần chưa dùng trả về hàng chung (ghi lịch sử). Không có phần trích đang giữ → None."""
    cur = get(conn, pid)
    if cur is None or cur["state"] != "active":
        return None
    left = round(max(0.0, float(cur["usd"]) - project_spent(conn, pid)), 2)
    conn.execute("UPDATE project_reserves SET state='released', released_at=?, returned_usd=?, updated_at=? WHERE project_id=?",
                 (_now(), left, _now(), pid))
    _log(conn, pid, who, "release", left, float(cur["usd"]), why)
    conn.commit()
    return get(conn, pid)


def release_quietly(conn, pid: int, who: Optional[str], why: str) -> None:
    """Cho các nơi giao / cất: lỗi trả lại không được làm hỏng việc giao / cất — ghi chẩn đoán."""
    try:
        release(conn, pid, who, why)
    except Exception as e:  # noqa: BLE001 - said in diag, the delivery / archive itself went through
        try:
            from . import diag
            diag.record(conn, "system", "warning", f"không trả được phần trích riêng của dự án #{pid}: {type(e).__name__}: {e}",
                        code="project_reserve", project_id=pid)
        except Exception:  # noqa: BLE001
            pass


# ---- cảnh báo (không chặn) ------------------------------------------------------------------------------------------------------------
def warning(conn, pid: Optional[int], usd: Optional[float]) -> Optional[str]:
    """Cảnh báo có số liệu cho một lượt gửi `usd` của dự án `pid`, hoặc None. Chỉ đọc (gọi được trong giao dịch của hold_llm).
    • dự án có phần trích đang giữ: vượt phần trích → cảnh báo riêng dự án;
    • dự án không có phần trích: lượt gửi lấn vào phần đã trích của dự án khác → cảnh báo (tổng vượt trần chung: cảnh báo cũ của
      core.budget lo)."""
    if pid is None:
        return None
    from . import cost, money_policy
    pricing = cost.load_pricing()
    cur = get(conn, pid)
    if cur is not None and cur["state"] == "active":
        spent = project_spent(conn, pid, pricing)
        if money_policy.over(spent, float(cur["usd"]), usd or 0.0):
            return money_policy.warning_text(f"dự án #{pid} — phần ngân sách trích riêng", spent, float(cur["usd"]), usd,
                                             extra="sửa phần trích ở Bước 1 → 💵 nếu cần (không chặn)")
        return None
    others = outstanding(conn, exclude=pid, pricing=pricing)
    if others["usd"] <= 0:
        return None
    room = free(conn, exclude=pid, pricing=pricing)
    if room is None or (usd or 0.0) <= room + 1e-9:
        return None
    ids = ", ".join(f"#{k}" for k in sorted(others["projects"]))
    return (f"⚠ dự án #{pid} không có phần trích riêng: hàng chung đợt thử chỉ còn trống ≈ ${max(0.0, room):.2f} ngoài phần đã trích "
            f"${others['usd']:.2f} của dự án {ids}; lượt này ≈ ${float(usd or 0):.2f} {money_policy.ESTIMATED} lấn vào phần của dự án "
            "khác — VẪN GỬI (chỉ cảnh báo)")
