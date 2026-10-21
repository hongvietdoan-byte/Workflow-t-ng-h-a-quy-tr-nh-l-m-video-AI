"""Character <-> Seedance subject (Kho chủ thể) links stored on the Character Bible.

A character with an ACTIVE subject can be attached to Seedance video requests as a `reference_image`
(`asset://` uri), which lets the character keep its look and lowers the chance of a risk-control block.
Copyright: Free Fire (FF) has a signed agreement with Clip AI, so an active FF subject also counts as copyright
reviewed. AOV, DF and other games: real-person review only, blocks are still possible.
"""
from typing import Dict, List, Optional

from .pipeline import Pipeline

import json
import os
import re
import threading

GAMES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "games.json")
_DEFAULT_GAMES = [{"key": "FF", "label": "Free Fire (FF)", "covered": True},
                  {"key": "OTHER", "label": "Nội dung khác", "covered": False}]


def games() -> Dict[str, tuple]:
    """key -> (label, covered by a signed copyright agreement). Read from data/games.json so new games or kinds of
    content can be added without code."""
    try:
        with open(GAMES_PATH, encoding="utf-8") as f:
            entries = json.load(f)["games"]
    except (OSError, ValueError, KeyError):
        entries = _DEFAULT_GAMES
    return {e["key"]: (e["label"], bool(e.get("covered"))) for e in entries}


def add_game(key: str, label: str, covered: bool = False) -> None:
    key, label = (key or "").strip().upper().replace(" ", "_"), (label or "").strip()
    if not key or not label:
        raise ValueError("key and label must not be empty")
    try:
        with open(GAMES_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {"games": list(_DEFAULT_GAMES)}
    if any(g["key"] == key for g in data["games"]):
        raise ValueError(f"'{key}' already exists")
    data["games"].insert(max(len(data["games"]) - 1, 0), {"key": key, "label": label, "covered": bool(covered)})
    with open(GAMES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
STATUS_LABEL = {None: "chưa có", "submitted": "đã gửi", "processing": "đang xử lý", "active": "active ✓",
                "failed": "lỗi"}
_IMAGE_CAP = {"seedance-2.5": 29, "default": 8}  # reference images left after the first-frame image


def is_covered(game: str) -> bool:
    return games().get(game, (None, False))[1]


def link(pipeline: Pipeline, project_id: int, character: str, asset: Dict) -> None:
    """Attach a library asset (dict from the library) to a character."""
    if not asset.get("asset_id"):
        raise ValueError("asset has no asset_id")
    n = pipeline.conn.execute(
        "UPDATE characters SET subject_asset_id=?, subject_asset_uri=?, subject_status=?, subject_name=?"
        " WHERE project_id=? AND name=?",
        (asset["asset_id"], asset.get("asset_uri"), asset.get("provider_status"), asset.get("name"),
         project_id, character)).rowcount
    if n == 0:
        raise KeyError(f"character '{character}' does not exist")
    pipeline.conn.commit()


def unlink(pipeline: Pipeline, project_id: int, character: str) -> None:
    """Forget the link (the asset itself stays in the library)."""
    pipeline.conn.execute("UPDATE characters SET subject_asset_id=NULL, subject_asset_uri=NULL, subject_status=NULL,"
                          " subject_name=NULL WHERE project_id=? AND name=?", (project_id, character))
    pipeline.conn.commit()


def refresh(pipeline: Pipeline, project_id: int, library) -> int:
    """Re-read the status of every linked subject that is not active yet. Returns how many became active."""
    became = 0
    rows = pipeline.conn.execute("SELECT name, subject_asset_id FROM characters WHERE project_id=?"
                                 " AND subject_asset_id IS NOT NULL AND COALESCE(subject_status,'')!='active'",
                                 (project_id,)).fetchall()
    for r in rows:
        asset = library.get(r["subject_asset_id"])
        if asset is not None:
            link(pipeline, project_id, r["name"], asset)
            became += asset.get("provider_status") == "active"
    return became


def reference_cap(model: Optional[str]) -> int:
    return _IMAGE_CAP["seedance-2.5"] if model and "2-5" in model or model == "seedance-2.5" else _IMAGE_CAP["default"]


def usable_for_scene(pipeline: Pipeline, scene_id: int, limit: int) -> List[Dict]:
    """Active subjects of the characters that appear in the scene, in the order the scene lists them."""
    import json
    scene = pipeline.conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    cast = (json.loads(scene["data"] or "{}").get("characters") or []) if scene else []
    out = []
    for name in cast:
        row = pipeline.conn.execute(
            "SELECT name, subject_asset_uri FROM characters WHERE project_id=? AND name=? AND subject_status='active'"
            " AND subject_asset_uri IS NOT NULL", (scene["project_id"], name)).fetchone()
        if row:
            out.append({"name": row["name"], "uri": row["subject_asset_uri"]})
    return out[:limit]


# ---- S4.7: every picture sent to Seedance goes through the library, remembered by its bytes ---------------------------------------
# Official ClipAI guide (docs/CAP_NHAT_CLIPAI_2026-09-28.md): each character picture sent to Seedance is uploaded to the Subject Library
# and chosen from there, one picture at a time; an ACTIVE asset has passed the real-person review (FF: the copyright review too). This
# replaces the red plus on the eye (P2m) that Seedance 2.0 Fast once drew into a clip. A picture is uploaded ONCE: its sha256 → asset,
# kept in `seedance_subject_pictures` (made on first use, no schema migration). A picture the library refused is never uploaded again
# (the same input would get the same answer — luật 6); the caller falls back and says so.

def _pictures_table(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS seedance_subject_pictures (sha TEXT PRIMARY KEY, name TEXT NOT NULL, asset_id TEXT, "
                 "asset_uri TEXT, status TEXT NOT NULL, message TEXT, path TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, "
                 "updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")


def picture_sha(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def picture_row(conn, sha: str) -> Optional[Dict]:
    _pictures_table(conn)
    cur = conn.execute("SELECT * FROM seedance_subject_pictures WHERE sha=?", (sha,))
    row = cur.fetchone()
    return None if row is None else dict(zip([d[0] for d in cur.description], tuple(row)))


def _save_picture(conn, sha: str, name: str, status: str, asset: Optional[Dict] = None, message: Optional[str] = None,
                  path: Optional[str] = None) -> None:
    _pictures_table(conn)
    asset = asset or {}
    conn.execute("INSERT INTO seedance_subject_pictures (sha, name, asset_id, asset_uri, status, message, path) VALUES (?,?,?,?,?,?,?) "
                 "ON CONFLICT(sha) DO UPDATE SET name=excluded.name, asset_id=excluded.asset_id, asset_uri=excluded.asset_uri, "
                 "status=excluded.status, message=excluded.message, path=excluded.path, updated_at=CURRENT_TIMESTAMP",
                 (sha, name, asset.get("asset_id"), asset.get("asset_uri"), status, message, path))
    conn.commit()


def picture_name(label: str, sha: str) -> str:
    """Library name of a picture: its label + the start of its sha, so the new asset is found by an exact, unique name."""
    clean = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (label or "pic").strip())[:80].strip("_") or "pic"
    return f"{clean}_{sha[:12]}"


def _active(conn, sha: str, name: str, asset: Dict, path: str, uploaded: bool) -> Dict:
    _save_picture(conn, sha, name, "active", asset, None, path)
    return {"asset_id": asset["asset_id"], "asset_uri": asset["asset_uri"], "name": name, "sha": sha, "uploaded": uploaded}


def _refused(conn, sha: str, name: str, asset: Dict, path: str):
    from .providers import ProviderError
    _save_picture(conn, sha, name, "failed", asset, asset.get("provider_status_msg"), path)
    return ProviderError(asset.get("provider_status_msg") or "the library rejected this file", code="asset_failed")


def ensure_picture(conn, library, path: str, label: str) -> Dict:
    """The ACTIVE library asset of this picture ({"asset_id", "asset_uri", "name", "sha", "uploaded"}), uploading it only when it was
    never uploaded. Raises ProviderError: code "asset_failed" (the library refused it, now or before — not uploaded again), "timeout"
    (still being reviewed; the next call looks it up by its unique name — no second upload)."""
    from .providers import ProviderError
    from .adapters.clipai_subjects import is_active
    sha = picture_sha(path)
    row = picture_row(conn, sha)
    if row and row["status"] == "failed":
        raise ProviderError(f"kho chủ thể đã từ chối ảnh này trước đây: {row.get('message') or '?'}", code="asset_failed")
    if row and row["status"] in ("active", "processing"):
        found = library.get(row["asset_id"]) if row.get("asset_id") else \
            next((a for a in library.list_assets() if a.get("name") == row["name"]), None)
        if found is not None and is_active(found):
            return _active(conn, sha, row["name"], found, path, False)
        if found is not None and found.get("provider_status") == "failed":
            raise _refused(conn, sha, row["name"], found, path)
        if found is not None:
            raise ProviderError("kho chủ thể vẫn đang duyệt ảnh này — thử lại sau ít phút", code="timeout", transient=True)
        # not in the library any more (deleted on the web): upload again below
    name = picture_name(label, sha)
    _save_picture(conn, sha, name, "processing", None, None, path)       # before the upload: a crash mid-way is never uploaded twice
    try:
        asset = library.upload(path, name)
    except ProviderError as e:
        from .adapters.clipai_subjects import full_error, is_library_full
        if e.code != "library_full" and is_library_full(str(e)):     # lỗi 11 #27: whatever library said it, the library is FULL
            e = full_error(str(e))
        if e.code == "library_full":              # the library is full, the picture is fine: never remembered as refused
            conn.execute("DELETE FROM seedance_subject_pictures WHERE sha=? AND status='processing'", (sha,))
            conn.commit()
            raise e from None
        if e.code == "asset_failed":
            _save_picture(conn, sha, name, "failed", None, str(e), path)
        elif e.code != "timeout":                 # nothing reached the library (bad input / network): a later call may upload
            conn.execute("DELETE FROM seedance_subject_pictures WHERE sha=? AND status='processing'", (sha,))
            conn.commit()
        raise
    return _active(conn, sha, name, asset, path, True)


def picture_refs(conn, library, pictures: List[tuple]) -> Dict:
    """pictures: [(label, local path)] in the order they will be named (@Image 1…). All or nothing: {"refs": [{"uri", "label", …}]}
    when EVERY picture has an active asset, else {"refs": None, "problems": [...]} — the caller then sends the marked pictures and says
    why (mixing would leave one face unmarked AND unreviewed)."""
    from .providers import ProviderError
    refs, problems, full = [], [], False
    for label, path in pictures:
        if full:                                  # lỗi 11 #27: no more uploads into a full library (all-or-nothing anyway)
            problems.append(f"{label}: chưa thử (Kho chủ thể đầy)")
            continue
        try:
            a = ensure_picture(conn, library, path, label)
            refs.append({"uri": a["asset_uri"], "label": label, "asset_id": a["asset_id"], "uploaded": a["uploaded"]})
        except ProviderError as e:
            if e.code == "library_full":
                full = True
                problems.insert(0, str(e))        # first, in plain words: what to do
                continue
            problems.append(f"{label}: [{e.code}] {e}")
        except OSError as e:
            problems.append(f"{label}: không đọc được ảnh ({e})")
    if not problems:
        return {"refs": refs, "problems": [], "library_full": False}
    return {"refs": None, "problems": problems, "library_full": full}


# ---- lỗi 11 (#27): the library holds at most 100 assets per user — see what each one is used for, suggest, delete on request ------------
CATEGORY_LABEL = {"rejected": "bị kho từ chối (không dùng được)", "orphan": "không còn ai dùng",
                  "done_project": "chỉ dự án đã cất / đã giao", "unknown": "có trong bộ nhớ ảnh, chưa rõ dự án",
                  "in_use": "đang dùng (dự án đang làm)"}
_SUGGEST_RANK = {"rejected": 0, "orphan": 1, "done_project": 2}
_PROJECT_IN_NAME = re.compile(r"^P(\d+)_")                                     # runner labels: P{project_id}_… (kept by picture_name)
_PROJECT_IN_PATH = re.compile(r"(?:^|[\\/])(?:projects|data)[\\/](\d+)[\\/]")   # PIPELINE_DATA = data/projects/<pid>/…


def _projects_of_picture(name: Optional[str], path: Optional[str]) -> List[Optional[int]]:
    """Projects a remembered picture belongs to: the one in its library name (first use) and the one in its last path. One row per
    sha, so a picture shared by two projects shows both when they differ; neither readable → [None] (category 'unknown')."""
    found = [int(m.group(1)) for m in (_PROJECT_IN_NAME.match(name or ""), _PROJECT_IN_PATH.search(path or "")) if m]
    return list(dict.fromkeys(found)) or [None]


def library_overview(conn, library, assets: Optional[List[Dict]] = None) -> Dict:
    """Every asset of the library with what uses it and a cleanup category. Nothing is deleted here.
    in_use = a character link or a remembered picture of a project still being made (not archived, not delivered) → never suggested;
    rejected / orphan / done_project → suggested in that order, the least recently used first. {"count", "limit", "assets", "suggested"}."""
    from .adapters.clipai_subjects import LIBRARY_LIMIT
    assets = library.list_assets() if assets is None else assets
    _pictures_table(conn)
    projects = {r["id"]: {"name": r["name"], "done": bool(r["archived"])}
                for r in conn.execute("SELECT id, name, COALESCE(archived,0) AS archived FROM projects")}
    try:
        for r in conn.execute("SELECT DISTINCT project_id FROM deliveries"):
            if r["project_id"] in projects:
                projects[r["project_id"]]["done"] = True
    except Exception:  # noqa: BLE001 - an old database without the deliveries table: no project counts as delivered
        pass
    uses: Dict[str, List[tuple]] = {}           # asset_id -> [(project id or None, text)]
    last: Dict[str, str] = {}
    for r in conn.execute("SELECT name, asset_id, path, updated_at FROM seedance_subject_pictures WHERE asset_id IS NOT NULL"):
        for pid in _projects_of_picture(r["name"], r["path"]):
            uses.setdefault(r["asset_id"], []).append((pid, f"ảnh {r['name']}"))
        if r["updated_at"] and r["updated_at"] > last.get(r["asset_id"], ""):
            last[r["asset_id"]] = r["updated_at"]
    for r in conn.execute("SELECT project_id, name, subject_asset_id FROM characters WHERE subject_asset_id IS NOT NULL"):
        uses.setdefault(r["subject_asset_id"], []).append((r["project_id"], f"nhân vật {r['name']}"))
    rows = []
    for a in assets:
        aid = a.get("asset_id")
        used = uses.get(aid, [])
        if a.get("provider_status") == "failed":
            category = "rejected"
        elif not used:
            category = "orphan"
        elif any(pid in projects and not projects[pid]["done"] for pid, _ in used):
            category = "in_use"
        elif any(pid not in projects for pid, _ in used):
            category = "unknown"
        else:
            category = "done_project"
        users = [(f"#{pid} {projects[pid]['name']}" + (" (đã xong)" if projects[pid]["done"] else "") if pid in projects
                  else "dự án ?") + f" · {what}" for pid, what in used]
        rows.append({"asset_id": aid, "name": a.get("name"), "status": a.get("provider_status"), "local_id": a.get("id"),
                     "created": a.get("created_at") or a.get("create_time"), "last_used": last.get(aid), "category": category,
                     "category_label": CATEGORY_LABEL[category], "users": users, "suggest": category in _SUGGEST_RANK})

    def age(r):
        lid = r["local_id"]
        return (_SUGGEST_RANK[r["category"]], r["last_used"] or str(r["created"] or ""), lid if isinstance(lid, int) else 0,
                str(r["asset_id"]))
    suggested = [r["asset_id"] for r in sorted((r for r in rows if r["suggest"]), key=age)]
    return {"count": len(assets), "limit": LIBRARY_LIMIT, "assets": rows, "suggested": suggested}


def delete_assets(conn, library, asset_ids: List[str], who=None) -> Dict:
    """Delete the chosen assets from the ClipAI library (CANNOT be undone) and forget them locally so the next run uploads again.
    who: the signed-in identity ({'role','perms'}); None = system / sign-in off. Needs the "Kho tài nguyên" right. An asset still used by a
    project being made is refused before anything is deleted (ValueError). {"deleted": [...], "errors": [(asset_id, message)]} — every
    error is said, never skipped."""
    from . import auth
    from .access import AccessDenied
    from .providers import ProviderError
    if who is not None and not auth.can(who, "assets"):
        raise AccessDenied("Xóa asset ở Kho chủ thể ClipAI cần quyền “Kho tài nguyên” — nhờ Owner cấp ở 👥 Nhóm.")
    ids = list(dict.fromkeys(a.strip() for a in asset_ids if a and a.strip()))
    listed = library.list_assets()                # 13/10: the ONE list read before the batch (overview + delete_many share it)
    by = {r["asset_id"]: r for r in library_overview(conn, library, listed)["assets"]}
    busy = [i for i in ids if by.get(i, {}).get("category") == "in_use"]
    if busy:
        raise ValueError("Không xóa asset đang được dự án đang làm dùng: " + ", ".join(f"{i} ({'; '.join(by[i]['users'])})" for i in busy))
    errors = []
    if hasattr(library, "delete_many"):           # ClipAI: one list after the whole batch, 1130 waited out (not one get+list per asset)
        res = library.delete_many(ids, known=listed)
        gone = {a.get("asset_id") for a in res["deleted"]}
        errors = [(aid, f"[{e.code}] {e}") for aid, e in res["errors"]]
    else:                                         # mock / test doubles
        gone = set()
        for aid in ids:
            try:
                library.delete(aid)
                gone.add(aid)
            except ProviderError as e:
                errors.append((aid, f"[{e.code}] {e}"))
    deleted = [aid for aid in ids if aid in gone]
    for aid in deleted:
        # a refused picture keeps its 'failed' memory (same input → same answer, luật 6); any other picture is forgotten → uploaded again
        conn.execute("UPDATE seedance_subject_pictures SET asset_id=NULL, asset_uri=NULL, updated_at=CURRENT_TIMESTAMP "
                     "WHERE asset_id=? AND status='failed'", (aid,))
        conn.execute("DELETE FROM seedance_subject_pictures WHERE asset_id=? AND status!='failed'", (aid,))
        conn.execute("UPDATE characters SET subject_asset_id=NULL, subject_asset_uri=NULL, subject_status=NULL, subject_name=NULL "
                     "WHERE subject_asset_id=?", (aid,))
        conn.commit()
    return {"deleted": deleted, "errors": errors}


# ---- 13/10 (người dùng chốt): giao bản cuối / cất dự án → tự dọn khỏi Kho các KHUNG ẢNH ĐÃ BỊ LOẠI của dự án đó (cờ subject_auto_cleanup) ----
# Only a picture whose file is a frame of an image_gen job of THIS project that was rejected (refs_clean/job_<id>_…), whose every remembered
# use is this project, and that no character links. Approved frames, place plates, character pictures and other projects' assets are never
# touched. list/delete are free calls. Runs in a background thread; a missing token / network error is a yellow note, retried next time.
_JOB_IN_FILE = re.compile(r"^job_(\d+)_")


class CapacityWait(ValueError):
    """Giữ job trong queued; tuyệt đối không biến lỗi Kho thành đổi model."""
    def __init__(self, result):
        self.result = result
        super().__init__(result['reason'])


def capacity(conn, library, pictures, limit=None) -> Dict:
    """GET chỉ đọc; kiểm cả gói trước upload. Không phải allocator/reservation.

    Không bootstrap bảng. Cache thiếu coi rỗng; snapshot không đủ → giữ VÀNG.
    """
    from .adapters.clipai_subjects import LIBRARY_LIMIT, is_active
    limit = LIBRARY_LIMIT if limit is None else limit
    if not pictures:
        return {'code': 'READY', 'needed': 0, 'severity': 'info'}
    unknown = {'code': 'QUEUE_UNKNOWN_CAPACITY', 'severity': 'warn',
               'reason': 'VÀNG: chưa xác minh được sức chứa Kho chủ thể — giữ job CHỜ; kiểm cấu hình Kho và thử lại.'}
    try:
        if library is None:
            return unknown
        assets = library.list_assets(strict=True)
        ids = [a.get('asset_id') for a in assets]
        if any(not aid for aid in ids) or len(set(ids)) != len(ids):
            return unknown
        active = {a['asset_id'] for a in assets if is_active(a)}
        hashes = {picture_sha(path) for _, path in pictures}
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='seedance_subject_pictures'").fetchone()
        rows = [dict(r) for r in conn.execute('SELECT * FROM seedance_subject_pictures')] if exists else []
        cached = {r['sha']: r for r in rows}
        by_name = {}
        for asset in assets:
            if asset.get('name'):
                by_name.setdefault(asset['name'], []).append(asset)
        reserved = 0
        resolved = {}
        for row in rows:
            aid = row['asset_id']
            if not aid and row['status'] == 'processing':
                matches = by_name.get(row.get('name'), [])
                if len(matches) == 1:
                    aid = matches[0]['asset_id']
            resolved[row['sha']] = aid
            if row['status'] not in ('active', 'failed') and aid not in ids:
                if row['sha'] in hashes:
                    return unknown
                reserved += 1  # upload khác chưa rõ kết quả: giữ một chỗ, không khóa cả Kho
        needed = sum(1 for sha in hashes if sha not in cached or not (
            (cached[sha]['status'] == 'active' and resolved[sha] in active)
            or (cached[sha]['status'] == 'processing' and resolved[sha] in ids)))
        free = max(0, limit - len(ids) - reserved)
        full = needed > free
        return {'code': 'QUEUE_CAPACITY' if full else 'READY', 'severity': 'warn' if full else 'info',
                'count': len(ids), 'limit': limit, 'needed': needed, 'free': free,
                'reason': (f'Kho chủ thể đầy: {len(ids)}/{limit}, cần {needed}, còn {free} — job CHỜ. '
                           'Lập dry-run dọn Kho, xem phụ thuộc và chờ duyệt từng lần; không tự xóa/đổi Kling.') if full else ''}
    except Exception:  # không đưa thông điệp transport/credential vào diag
        return unknown


def auto_clean_candidates(assets, dependencies, now=None) -> Dict:
    """Lập plan chỉ đọc từ snapshot và dependency đã được xác minh bởi caller.

    Legacy tên/path không chứng minh owner/lifecycle → giữ UNKNOWN. Không tự suy
    tuổi từ mtime/updated_at; đầu vào này không cấp quyền apply hay xóa.
    """
    import hashlib
    from datetime import datetime, timezone
    now = now or datetime.now(timezone.utc)
    evidence = {}
    for d in dependencies:
        aid = d.get('asset_id')
        evidence[aid] = None if aid in evidence else d  # trùng evidence không đoán bản nào đúng
    eligible, protected = [], []
    for asset in assets:
        aid = asset.get('asset_id')
        d = evidence.get(aid) or {}
        owners, jobs, chars = d.get('project_refs'), d.get('job_refs'), d.get('character_refs')
        reason = 'UNKNOWN: thiếu bằng chứng đầy đủ về phụ thuộc'
        safe = (bool(aid) and d.get('verified') is True and d.get('owners_complete') is True
                and isinstance(owners, list) and bool(owners) and isinstance(jobs, list) and isinstance(chars, list))
        if safe:
            safe = (not chars and asset.get('provider_status') in ('active', 'failed')
                    and not d.get('processing') and not d.get('unknown') and not d.get('pinned'))
            reason = 'đang dùng / nhân vật / trạng thái chưa chắc chắn'
        if safe:
            safe = all(j.get('state') in ('rejected', 'failed') and j.get('job_id') is not None for j in jobs)
            reason = 'job đang dùng hoặc chưa đối soát'
        if safe:
            safe = all(p.get('project_id') is not None and p.get('state') in ('archived', 'delivered')
                       and not p.get('restored') for p in owners)
            reason = 'dự án active / restore / shared chưa kết thúc'
        if safe:
            rejected = bool(jobs) and all(j.get('state') == 'rejected' and j.get('type') == 'image_gen' for j in jobs)
            old = True
            for project in owners:
                try:
                    terminal = datetime.fromisoformat(project['terminal_at'])
                    old = old and terminal.utcoffset() is not None and now.utcoffset() is not None and (now - terminal).total_seconds() > 72 * 3600
                except (KeyError, ValueError, TypeError):
                    old = False
            safe = rejected or old
            reason = 'khung đã bị loại, không còn job dùng' if rejected else ('mọi dự án kết thúc trên 72 giờ' if old else 'chưa đủ >72 giờ hoặc thiếu mốc UTC đáng tin')
        row = {'asset_id': aid, 'reason': reason, 'dependencies': d}
        (eligible if safe else protected).append(row)
    plan = {'dry_run': True, 'eligible': eligible, 'protected': protected, 'created_at': now.isoformat()}
    plan['plan_hash'] = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    return plan


def cleanup_dependencies(conn, assets) -> List[Dict]:
    """Đọc dependency legacy để người rà; không DDL, không suy ownership hoàn chỉnh.

    Tên/path chỉ là gợi ý. Schema hiện chưa có lifecycle UTC/refs toàn cục:
    không thể biến một cache row thành bằng chứng được phép xóa.
    """
    def rows(sql):
        try:
            cur = conn.execute(sql)
            names = [c[0] for c in cur.description]
            return [dict(zip(names, r)) for r in cur]
        except Exception:
            return []
    pictures = rows('SELECT asset_id, name, path, status FROM seedance_subject_pictures WHERE asset_id IS NOT NULL')
    characters = rows('SELECT id, project_id, subject_asset_id FROM characters WHERE subject_asset_id IS NOT NULL')
    projects = {p['id']: p for p in rows('SELECT id, archived FROM projects')}
    jobs = rows('SELECT id, project_id, type, state, source_job_id FROM jobs')
    result = []
    for a in assets:
        aid = a.get('asset_id')
        matching = [p for p in pictures if p['asset_id'] == aid]
        char_refs = [c for c in characters if c['subject_asset_id'] == aid]
        owners = set(c['project_id'] for c in char_refs)
        job_ids = set()
        for p in matching:
            owners.update(_projects_of_picture(p['name'], p['path']))
            match = _JOB_IN_FILE.match(os.path.basename((p['path'] or '').replace('\\', '/')))
            if match:
                job_ids.add(int(match.group(1)))
        job_refs = [dict(j, job_id=j['id']) for j in jobs if j['id'] in job_ids or j['source_job_id'] in job_ids]
        owners.update(j['project_id'] for j in job_refs)
        project_refs = [{'project_id': pid, 'state': ('archived' if projects[pid]['archived'] else 'active')
                         if pid in projects else 'unknown'} for pid in sorted(owners, key=lambda p: -1 if p is None else p)]
        result.append({'asset_id': aid, 'verified': False, 'owners_complete': False,
                       'project_refs': project_refs, 'job_refs': job_refs, 'character_refs': char_refs,
                       'processing': any(p['status'] == 'processing' for p in matching),
                       'evidence': 'legacy: thiếu quan hệ toàn cục và mốc lifecycle UTC; chỉ gợi ý để rà'})
    return result


def rejected_frame_assets(conn, project_id: int) -> List[Dict]:
    """[{"asset_id", "name", "job_id"}] of this project's rejected frames still in the library (read only)."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='seedance_subject_pictures'").fetchone():
        return []
    rows = conn.execute("SELECT asset_id, name, path FROM seedance_subject_pictures WHERE asset_id IS NOT NULL").fetchall()
    owners: Dict[str, set] = {}
    for r in rows:
        owners.setdefault(r["asset_id"], set()).update(_projects_of_picture(r["name"], r["path"]))
    linked = {r[0] for r in conn.execute("SELECT subject_asset_id FROM characters WHERE subject_asset_id IS NOT NULL")}
    by_asset: Dict[str, List] = {}
    for r in rows:
        by_asset.setdefault(r["asset_id"], []).append(r)
    out = []
    for aid, group in by_asset.items():
        if aid in linked or owners.get(aid) != {project_id}:
            continue
        jobs = []                                 # EVERY remembered picture of this asset must be a rejected frame — else it is kept
        for r in group:
            m = _JOB_IN_FILE.match(os.path.basename((r["path"] or "").replace("\\", "/")))
            jid = int(m.group(1)) if m else None
            if jid is None or not _rejected_unused_frame(conn, project_id, jid):
                jobs = []
                break
            jobs.append((jid, r["name"]))
        if jobs:
            out.append({"asset_id": aid, "name": jobs[0][1], "job_id": jobs[0][0]})
    return out


def _rejected_unused_frame(conn, project_id: int, job_id: int) -> bool:
    """A rejected image_gen job of this project that no kept video was made from (jobs.source_job_id). Unsure → False (kept)."""
    if conn.execute("SELECT 1 FROM jobs WHERE id=? AND project_id=? AND type='image_gen' AND state='rejected'",
                    (job_id, project_id)).fetchone() is None:
        return False
    try:
        used = conn.execute("SELECT 1 FROM jobs WHERE source_job_id=? AND state NOT IN ('rejected','failed')", (job_id,)).fetchone()
    except Exception:  # noqa: BLE001 - an old database without jobs.source_job_id: cannot tell → keep
        return False
    return used is None


def _cleanup_note(conn, project_id: int, severity: str, message: str) -> None:
    from . import diag
    diag.record(conn, "video", severity, message, code="subject_cleanup_plan", project_id=project_id)


def run_auto_cleanup(conn, project_id: int, why: str, library=None) -> Dict:
    """C3-3: lập đề nghị DRY-RUN, không mở provider và không có đường xóa."""
    found = rejected_frame_assets(conn, project_id)
    # C3-3: ngoại lệ bắt buộc dù cờ mới OFF. Không mở provider, không xóa.
    import hashlib
    plan = {'dry_run': True, 'project_id': project_id, 'why': why, 'candidates': found,
            'reason': 'chờ duyệt xóa từng plan; dependency legacy cần xác minh lại'}
    plan['plan_hash'] = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    if found:
        _cleanup_note(conn, project_id, 'warn', f'Kho chủ thể: {len(found)} khung đề nghị xem xét — chờ duyệt xóa (DRY-RUN); không xóa: '
                      + ', '.join(f['asset_id'] for f in found) + f'. Plan {plan["plan_hash"]}')
    return {'deleted': [], 'errors': [], 'plan': plan}


_RUNNING_LOCK = threading.Lock()
_RUNNING: set = set()                             # projects whose background cleanup is running (a 2nd delivery / put-away waits for next time)


def _spawn(fn) -> None:
    threading.Thread(target=fn, name="subject-auto-cleanup", daemon=True).start()


def schedule_auto_cleanup(conn, project_id: int, why: str) -> bool:
    """Called after a delivery is recorded / a project is put away. Flag off or nothing to clean → nothing (False). Else the cleanup runs
    in the background on its own connection (an in-memory database — tests — runs it here). Never raises, never blocks the caller."""
    try:
        from . import features
        if not features.on("subject_auto_cleanup") or not rejected_frame_assets(conn, project_id):
            return False
        from .place_refs import _db_path
        db = _db_path(conn)
        if not db:
            run_auto_cleanup(conn, project_id, why)
            return True

        with _RUNNING_LOCK:
            if project_id in _RUNNING:
                return False
            _RUNNING.add(project_id)

        def work():
            import sqlite3
            c = None
            try:
                c = sqlite3.connect(db, timeout=60)
                c.row_factory = sqlite3.Row
                run_auto_cleanup(c, project_id, why)
            except Exception as e:  # noqa: BLE001 - a background note must never crash; say it on stderr
                import sys
                print(f"[subject_cleanup] dự án #{project_id}: {type(e).__name__}: {e}", file=sys.stderr)
            finally:
                if c is not None:
                    c.close()
                _RUNNING.discard(project_id)
        try:
            _spawn(work)
        except Exception:
            _RUNNING.discard(project_id)
            raise
        return True
    except Exception as e:  # noqa: BLE001 - never breaks the delivery / put-away
        try:
            _cleanup_note(conn, project_id, "warn", f"Tự dọn Kho chủ thể ({why}) không khởi động được: {type(e).__name__}: {e}")
        except Exception:  # noqa: BLE001
            pass
        return False
