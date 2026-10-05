"""S14.42 — duyệt tài nguyên Kho theo 3 tầng (người dùng không tự duyệt hàng loạt được).

    pending --(Claude nhìn/nghe, tầng A)--> claude_ok --(người dùng xác nhận khi dùng thật, tầng C)--> approved (= user_ok)
        ^                                       |
        +------------- thu hồi (bất cứ lúc nào) +

* Ảnh: `asset_images.status` = 'pending' / 'claude_ok' / 'approved'. 'claude_ok' DÙNG ĐƯỢC ngay như 'approved' (assets.USABLE) nhưng
  luôn hiện dấu "Claude duyệt" (assets._row → `claude_only`, từng ảnh có `status`). 'pending' của mục khác vẫn KHÔNG dùng được.
* Âm thanh: bảng `sounds` không có cổng duyệt (mọi bài trong nguồn đều dùng được) → trạng thái nằm ở `kho_review_log` (dòng cuối):
  claude_ok / user_ok / reject / revoke. Bài bị `reject` KHÔNG được gợi ý nhạc nền tự động (sound_lib.suggest_music); file vẫn giữ.
* Mục bị loại: KHÔNG xóa, giữ pending, ghi `reject` vào nhật ký + danh sách docs/KHO_TAI_NGUYEN_LOI_2026-10-05.md để làm lại sau.
* Bản giao: còn mục chỉ-Claude-duyệt thì CẢNH BÁO (không chặn) kèm danh sách (delivery_warnings).
Không gọi API tốn tiền; mọi hàm chỉ đọc/ghi CSDL."""
from typing import Dict, List, Optional

from . import assets

TAG = "Claude S14.42 duyệt sơ bộ"


class ReviewError(ValueError):
    """Shown to the person as it is."""


def _log(conn, kind: str, item_id: int, action: str, note: str = "") -> None:
    conn.execute("INSERT INTO kho_review_log (item_kind, item_id, action, note) VALUES (?,?,?,?)", (kind, item_id, action, note))


def history(conn, kind: str, item_id: int) -> List[Dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM kho_review_log WHERE item_kind=? AND item_id=? ORDER BY id", (kind, item_id))]


def _last(conn, kind: str, item_id: int) -> Optional[str]:
    r = conn.execute("SELECT action FROM kho_review_log WHERE item_kind=? AND item_id=? ORDER BY id DESC LIMIT 1", (kind, item_id)).fetchone()
    return r[0] if r else None


# ---- images -------------------------------------------------------------------------------------------------------------------------
def claude_approve(conn, image_ids: List[int], why: str, tag: str = TAG) -> int:
    """Tầng A: only a 'pending' picture becomes 'claude_ok' (a person's 'approved' is never lowered). Returns how many moved."""
    moved = 0
    for i in image_ids:
        cur = conn.execute("UPDATE asset_images SET status='claude_ok' WHERE id=? AND status='pending'", (i,))
        if cur.rowcount:
            moved += 1
            _log(conn, "image", i, "claude_ok", f"{tag}: {why}")
    conn.commit()
    return moved


def confirm(conn, kind: str, item_id: int) -> None:
    """Tầng C: the person confirms what Claude approved (image claude_ok → approved; sound → user_ok). A 'pending' one is refused."""
    if kind == "image":
        cur = conn.execute("UPDATE asset_images SET status='approved' WHERE id=? AND status='claude_ok'", (item_id,))
        if not cur.rowcount:
            raise ReviewError("Ảnh này chưa ở trạng thái “Claude duyệt” — duyệt nó ở hộp 📥 Ảnh chờ duyệt.")
    elif kind == "sound":
        if _last(conn, "sound", item_id) != "claude_ok":
            raise ReviewError("Âm thanh này chưa ở trạng thái “Claude duyệt”.")
    else:
        raise ReviewError(f"loại không rõ: {kind}")
    _log(conn, kind, item_id, "user_ok", "người dùng xác nhận")
    conn.commit()


def confirm_asset(conn, asset_id: int) -> int:
    """Confirm every 'claude_ok' picture of one library entry (the 'Xác nhận' button of the entry). Returns how many."""
    ids = [r[0] for r in conn.execute("SELECT id FROM asset_images WHERE asset_id=? AND status='claude_ok'", (asset_id,))]
    for i in ids:
        confirm(conn, "image", i)
    return len(ids)


def revoke(conn, kind: str, item_id: int) -> None:
    """Thu hồi: back to pending (image: only a 'claude_ok' one — a person's own approval is theirs to undo elsewhere)."""
    if kind == "image":
        cur = conn.execute("UPDATE asset_images SET status='pending' WHERE id=? AND status='claude_ok'", (item_id,))
        if not cur.rowcount:
            raise ReviewError("Chỉ thu hồi được ảnh đang ở trạng thái “Claude duyệt”.")
    elif kind != "sound":
        raise ReviewError(f"loại không rõ: {kind}")
    _log(conn, kind, item_id, "revoke", "thu hồi về chờ duyệt")
    conn.commit()


def reject(conn, kind: str, item_id: int, why: str) -> None:
    """Claude refuses a candidate: it is KEPT (no delete), unusable (image stays pending; sound is not suggested) and listed for a redo."""
    _log(conn, kind, item_id, "reject", why)
    conn.commit()


def rejected(conn, kind: str) -> List[Dict]:
    """Items whose last action is 'reject': [{item_kind, item_id, note, at}]."""
    out = []
    for r in conn.execute("SELECT item_id, MAX(id) m FROM kho_review_log WHERE item_kind=? GROUP BY item_id", (kind,)).fetchall():
        row = conn.execute("SELECT * FROM kho_review_log WHERE id=?", (r["m"],)).fetchone()
        if row["action"] == "reject":
            out.append(dict(row))
    return out


def pending_of(conn, created_by: str) -> List[Dict]:
    """Only the 'pending' pictures of entries made by `created_by` (e.g. 'S14.33'); other people's pending are never listed here."""
    return [dict(r) for r in conn.execute(
        "SELECT i.id, i.path, i.role, i.src_path, a.id AS asset_id, a.name AS asset, a.kind FROM asset_images i"
        " JOIN assets a ON a.id=i.asset_id WHERE i.status='pending' AND a.created_by=? ORDER BY a.id, i.id", (created_by,))]


def claude_only_images(conn, asset_ids: Optional[List[int]] = None) -> List[Dict]:
    """Pictures a person has not confirmed yet (status 'claude_ok'), with their entry: [{id, asset_id, asset, kind, path, role}]."""
    sql = ("SELECT i.id, i.path, i.role, a.id AS asset_id, a.name AS asset, a.kind FROM asset_images i JOIN assets a ON a.id=i.asset_id"
           " WHERE i.status='claude_ok'")
    args: list = []
    if asset_ids is not None:
        if not asset_ids:
            return []
        sql += " AND a.id IN (" + ",".join("?" * len(asset_ids)) + ")"
        args = list(asset_ids)
    return [dict(r, path=assets.resolve(r["path"])) for r in conn.execute(sql + " ORDER BY a.name, i.id", args)]


# ---- sounds -------------------------------------------------------------------------------------------------------------------------
def claude_approve_sound(conn, sound_id: int, why: str, tag: str = TAG) -> None:
    _log(conn, "sound", sound_id, "claude_ok", f"{tag}: {why}")
    conn.commit()


def sound_state(conn, sound_id: int) -> str:
    """pending (never reviewed / revoked) | claude_ok | user_ok | rejected."""
    return {"claude_ok": "claude_ok", "user_ok": "user_ok", "reject": "rejected"}.get(_last(conn, "sound", sound_id) or "", "pending")


def rejected_sound_ids(conn) -> set:
    return {r["item_id"] for r in rejected(conn, "sound")}


def claude_only_sounds(conn) -> List[Dict]:
    out = []
    for r in conn.execute("SELECT item_id, MAX(id) m FROM kho_review_log WHERE item_kind='sound' GROUP BY item_id").fetchall():
        if conn.execute("SELECT action FROM kho_review_log WHERE id=?", (r["m"],)).fetchone()[0] == "claude_ok":
            s = conn.execute("SELECT id, name, kind, path FROM sounds WHERE id=?", (r["item_id"],)).fetchone()
            if s:
                out.append(dict(s))
    return out


# ---- delivery -----------------------------------------------------------------------------------------------------------------------
def delivery_warnings(conn, project_id: int, used_audio_names=()) -> List[str]:
    """Tầng C: a WARNING (never a block) listing what the delivered video used that only Claude approved: pictures of the entries
    attached to the project, and library sounds whose name is in `used_audio_names` (file names of the music / effects in the mix)."""
    ids = [r[0] for r in conn.execute("SELECT asset_id FROM project_assets WHERE project_id=?", (project_id,))]
    by_asset: Dict[str, int] = {}
    for r in claude_only_images(conn, ids):
        by_asset[r["asset"]] = by_asset.get(r["asset"], 0) + 1
    names = [assets.fold(n) for n in used_audio_names if n]
    snd = [s["name"] for s in claude_only_sounds(conn) if any(assets.fold(s["name"]) and assets.fold(s["name"]) in n for n in names)]
    parts = [f"{a} ({n} ảnh)" for a, n in by_asset.items()] + [f"âm thanh {s}" for s in snd]
    if not parts:
        return []
    return ["Bản giao dùng " + str(len(parts)) + " mục chỉ có “Claude duyệt”, chưa được người dùng xác nhận: " + "; ".join(parts[:12])
            + " — xác nhận hoặc thu hồi ở 📁 Kho tài nguyên → 🔎 Claude duyệt sơ bộ."]
