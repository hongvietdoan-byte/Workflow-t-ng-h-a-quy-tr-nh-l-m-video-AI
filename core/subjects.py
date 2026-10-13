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
    by = {r["asset_id"]: r for r in library_overview(conn, library)["assets"]}
    busy = [i for i in ids if by.get(i, {}).get("category") == "in_use"]
    if busy:
        raise ValueError("Không xóa asset đang được dự án đang làm dùng: " + ", ".join(f"{i} ({'; '.join(by[i]['users'])})" for i in busy))
    deleted, errors = [], []
    for aid in ids:
        try:
            library.delete(aid)
        except ProviderError as e:
            errors.append((aid, f"[{e.code}] {e}"))
            continue
        deleted.append(aid)
        # a refused picture keeps its 'failed' memory (same input → same answer, luật 6); any other picture is forgotten → uploaded again
        conn.execute("UPDATE seedance_subject_pictures SET asset_id=NULL, asset_uri=NULL, updated_at=CURRENT_TIMESTAMP "
                     "WHERE asset_id=? AND status='failed'", (aid,))
        conn.execute("DELETE FROM seedance_subject_pictures WHERE asset_id=? AND status!='failed'", (aid,))
        conn.execute("UPDATE characters SET subject_asset_id=NULL, subject_asset_uri=NULL, subject_status=NULL, subject_name=NULL "
                     "WHERE subject_asset_id=?", (aid,))
        conn.commit()
    return {"deleted": deleted, "errors": errors}
