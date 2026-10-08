"""Resource library (Kho tài nguyên): characters, weapons, pets, props, places and styles with reference pictures.

Two scopes
  * shared library  - per game (FF, AOV...), managed by the owner / people with the "assets" right, usable by every project;
  * project assets  - uploaded by anyone for one project only (an original character, a one-off prop...).

How it is used with a script
  * `find_in_text` finds the assets whose name (or other names) appear in the script, so the person can tick them at once;
  * the ticked assets of a project are written into the Director prompt (`context_text`): the Character Bible then uses the
    real names and designs instead of inventing them;
  * their pictures are the references for image / video generation (`reference_paths`).
"""
import hashlib
import json
import os
import re
import shutil
import unicodedata
from typing import Dict, List, Optional, Tuple

KINDS = {"character": "Nhân vật", "weapon": "Vũ khí / trang bị", "pet": "Thú cưng", "prop": "Đạo cụ",
         "location": "Địa điểm / bản đồ", "style": "Phong cách", "outfit": "Trang phục"}
# S14.28: "outfit" = a costume / skin picture worn BY a character (set per project with set_outfit). It is never a character's face,
# a place or an object of a scene: match_character / scene_references / auto_attach's `main` filter on their own kinds and skip it.
_KIND_WORDS = {"character": ("character", "characters", "char", "chars", "nhan vat", "nhanvat", "nv"),
               "weapon": ("weapon", "weapons", "vu khi", "vukhi", "trang bi", "gun", "guns"),
               "pet": ("pet", "pets", "thu cung", "thucung"),
               "prop": ("prop", "props", "item", "items", "do vat", "dao cu", "daocu"),
               "location": ("location", "locations", "map", "maps", "place", "places", "ban do", "bando", "dia diem", "bo canh"),
               "style": ("style", "styles", "phong cach"),
               "outfit": ("outfit", "outfits", "trang phuc", "trangphuc", "costume", "costumes", "skin", "skins")}
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
MAX_IMAGE_BYTES = 10 * 1024 * 1024        # the image generator refuses larger reference pictures
MAX_IMAGES_PER_ASSET = 6
PLATES_PER_LOCATION = 12                  # rendered 3D backgrounds (several camera angles) of one place
# G1: the job of each library picture. Characters: which framing (a close-up shot needs a face, a back shot a back view). Places: which
# camera — only an eye-level empty background may be sent to the image model as pixels; a top-down map is information, never a background.
ROLES = {
    "character": {"front_standard": "chính diện nền xám (bộ chuẩn 1)", "design_sheet": "bảng nhiều góc (bộ chuẩn 2 — chỉ gửi model nhận bảng)",
                  "related": "ảnh liên quan: skill, vũ khí… (bộ chuẩn 3)",
                  "full_body": "toàn thân", "half_body": "nửa người", "close_up": "cận mặt", "back": "sau lưng", "side": "nghiêng",
                  "skill_pose": "tư thế kỹ năng"},
    "location": {"eye_level": "nền ngang tầm mắt", "low_angle": "nền góc thấp", "high_angle": "nền góc cao",
                 "top_down": "toàn cảnh từ trên (chỉ thông tin)", "detail": "chi tiết / mốc",
                 "interior": "trong nhà (không làm ảnh mốc / nền ngoài trời)"},
}
ROLES["pet"] = ROLES["character"]
LOOKS = {"ingame": "in-game FF", "anime": "anime"}
STATUSES = {"approved": "đã duyệt", "pending": "chờ duyệt", "redundant": "ảnh thừa (trùng / icon — không dùng)",
            "claude_ok": "Claude duyệt sơ bộ (dùng được, chờ người dùng xác nhận)"}   # S14.42: pending -> claude_ok -> approved
USABLE = (None, "approved", "claude_ok")        # statuses the pipeline may use; 'claude_ok' is shown with the "Claude duyệt" mark
USABLE_SQL = "('approved','claude_ok')"
_NOISE = {"front", "back", "side", "full", "avatar", "face", "portrait", "main", "ref", "reference", "hd", "final", "copy",
          "truoc", "sau", "ngang", "mat", "new", "old", "moi", "cu"}


class AssetError(Exception):
    """A message that can be shown to the person."""


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _db_path() -> Optional[str]:
    """The database file in use when it is named (PIPELINE_DB, as the Dashboard and the tools read it); None = not named / in memory."""
    db = os.environ.get("PIPELINE_DB")
    return os.path.abspath(db) if db and db != ":memory:" else None


def _db_home() -> Optional[str]:
    """The install folder of the named database (<home>/data/manifest.sqlite -> <home>), or None when it is not under a 'data' folder."""
    db = _db_path()
    if db and os.path.basename(os.path.dirname(db)).lower() == "data":
        return os.path.dirname(os.path.dirname(db))
    return None


def root() -> str:
    """The library picture folder, ALWAYS absolute (S14.43B): ASSET_DIR when set, else 'assets' next to the database in use
    (PIPELINE_DB), else <repository>/data/assets. It used to be "data/assets" relative to the working folder: S14.33 ran a script in a
    worktree with the main database — the rows went to the main database, the 33 picture files into the worktree, which was then
    cleaned away. A picture folder apart from the database is reported by root_warning()."""
    if os.environ.get("ASSET_DIR"):
        return os.path.abspath(os.environ["ASSET_DIR"])
    db = _db_path()
    if db:
        return os.path.join(os.path.dirname(db), "assets")
    return os.path.join(REPO, "data", "assets")


_WARNED = set()


def root_warning() -> Optional[str]:
    """A sentence when the pictures would not be stored next to the database in use (rule 1 of docs/CHUAN_XAY_DUNG.md: say it, never
    split silently), else None. Also written once per process to the log."""
    folder, db = root(), _db_path()
    msg = None
    if db and os.environ.get("ASSET_DIR"):
        expected = os.path.join(os.path.dirname(db), "assets")
        if os.path.normcase(folder) != os.path.normcase(expected):
            msg = (f"Thư mục ảnh Kho (ASSET_DIR = {folder}) KHÁC gốc với CSDL đang dùng ({db}, ảnh phải ở {expected}): hàng CSDL và file "
                   "ảnh sẽ nằm hai nơi — kiểm lại ASSET_DIR / PIPELINE_DB.")
    elif not db and not os.environ.get("ASSET_DIR"):
        cwd_db = os.path.abspath(os.path.join("data", "manifest.sqlite"))
        if os.path.normcase(os.path.dirname(cwd_db)) != os.path.normcase(os.path.join(REPO, "data")):
            msg = (f"Chưa đặt PIPELINE_DB: CSDL mặc định theo thư mục đang chạy ({cwd_db}) KHÁC gốc với thư mục ảnh Kho ({folder}) — "
                   "đặt PIPELINE_DB (đường tuyệt đối) hoặc chạy từ gốc repo.")
    if msg and msg not in _WARNED:
        _WARNED.add(msg)
        import logging
        logging.getLogger(__name__).warning(msg)
    return msg


def _homes() -> List[str]:
    """Folders that a stored relative path ("data/assets/…") may be relative to, most trusted first."""
    out = []
    for h in (_db_home(), REPO):
        if h and os.path.normcase(os.path.abspath(h)) not in {os.path.normcase(x) for x in out}:
            out.append(os.path.abspath(h))
    return out


def stored_path(path: str) -> str:
    """The form written in the database for a library file: relative "data/assets/…" (unchanged format) when the file sits under the
    data/assets of the database's install folder or of the repository; otherwise the absolute path (a test / a custom ASSET_DIR)."""
    full = os.path.abspath(path)
    for home in _homes():
        base = os.path.join(home, "data", "assets")
        if os.path.normcase(full).startswith(os.path.normcase(base) + os.sep):
            return os.path.relpath(full, home)
    return full


def resolve(path: Optional[str]) -> Optional[str]:
    """A stored picture path made usable from any working folder (A1): stored paths are relative to the install folder ("data/assets/…"),
    so a Dashboard or tool started elsewhere used to find no picture at all — and the Director then described characters blind.
    S14.43B: when the database in use is named (PIPELINE_DB under a 'data' folder) ONLY its install folder — never a same-named file
    of the working folder or of the repository (rà 06/10: kho_merge on a copy of the database moved the main machine's pictures).
    Otherwise the working folder, then the repository (as before)."""
    if not path or os.path.isabs(path):
        return path
    if _db_home():
        return os.path.join(_db_home(), path)
    homes = _homes()
    for cand in [os.path.join(homes[0], path), path] + [os.path.join(h, path) for h in homes[1:]]:
        if os.path.exists(cand):
            return cand
    return os.path.join(homes[0], path)


def missing_files(conn) -> List[Dict]:
    """Library pictures whose file cannot be found (checked when the Dashboard opens: rule 1 of docs/CHUAN_XAY_DUNG.md)."""
    return [{"id": r["id"], "asset": r["name"], "path": r["path"]} for r in conn.execute(
        "SELECT i.id, i.path, a.name FROM asset_images i JOIN assets a ON a.id=i.asset_id WHERE i.status IS NOT 'removed'")
        if not os.path.exists(resolve(r["path"]))]


def missing_files_detail(conn) -> List[Dict]:
    """B5 01/10: like missing_files, with the source file the picture was imported from and whether it can be copied back."""
    out = []
    for r in conn.execute("SELECT i.id, i.path, i.src_path, a.name FROM asset_images i JOIN assets a ON a.id=i.asset_id"
                          " WHERE i.status IS NOT 'removed'").fetchall():
        if not os.path.exists(resolve(r["path"])):
            src = r["src_path"]
            out.append({"id": r["id"], "asset": r["name"], "path": r["path"], "src_path": src,
                        "can_reload": bool(src and os.path.isfile(src))})
    return out


def reload_image(conn, image_id: int) -> bool:
    """B5: copy the picture back from the file it was imported from (the source still exists). False = nothing to copy from."""
    row = conn.execute("SELECT path, src_path FROM asset_images WHERE id=?", (image_id,)).fetchone()
    if not row or not row["src_path"] or not os.path.isfile(row["src_path"]):
        return False
    target = resolve(row["path"])
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    with open(row["src_path"], "rb") as f:
        data = f.read()
    if len(data) > MAX_IMAGE_BYTES:
        data, _ = _shrink(data, row["src_path"])
    with open(target, "wb") as f:
        f.write(data)
    return True


def unlink_missing(conn, only_unreloadable: bool = True) -> int:
    """B5: drop the library entries whose picture file is gone (no file to delete — only the broken link). Returns how many.
    S14.4 (04/10): by default only the rows that can NOT be copied back from their source (`can_reload` False) — a reloadable one is
    one click from being whole again. The dropped rows are first written to <Kho>/_backup/unlink_missing_<date time>.json."""
    ids = [r["id"] for r in missing_files_detail(conn) if not (only_unreloadable and r["can_reload"])]
    if not ids:
        return 0
    rows = [dict(r) for r in conn.execute(f"SELECT i.*, a.name AS asset_name, a.game AS asset_game FROM asset_images i"
                                          f" JOIN assets a ON a.id=i.asset_id WHERE i.id IN ({','.join('?' * len(ids))})", ids)]
    import datetime
    folder = os.path.join(root(), "_backup")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"unlink_missing_{stamp}.json")
    n = 1
    while os.path.exists(path):                     # two clicks in the same second: never overwrite an earlier backup
        n += 1
        path = os.path.join(folder, f"unlink_missing_{stamp}_{n}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"when": stamp, "only_unreloadable": only_unreloadable, "rows": rows}, f, ensure_ascii=False, indent=1)
    conn.execute(f"DELETE FROM asset_images WHERE id IN ({','.join('?' * len(ids))})", ids)
    conn.commit()
    return len(ids)


def fold(text: str) -> str:
    """Lower case, no accents, single spaces: 'Ông lão ORIN' -> 'ong lao orin' (for matching names in a script)."""
    text = unicodedata.normalize("NFD", (text or "").replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", text.lower())).strip()


def kind_from_word(word: str) -> Optional[str]:
    w = fold(word)
    for kind, words in _KIND_WORDS.items():
        if w in words or w == kind:
            return kind
    return None


# ---- library ------------------------------------------------------------------------------------------------
def name_key(text: str) -> str:
    """S14.43B: the key two names of one thing share — fold() without spaces: 'Mr.Waggor' == 'Mr. Waggor' == 'mr waggor' == 'MR-WAGGOR'."""
    return fold(text).replace(" ", "")


def _all_names(name: str, aliases: Optional[str]) -> List[str]:
    return [n.strip() for n in [name] + re.split(r"[,;|\n]+", aliases or "") if n and n.strip()]


def find_same(conn, game: str, kind: str, name: str, aliases: str = "", project_id: Optional[int] = None,
              exclude_id: Optional[int] = None) -> Optional[Dict]:
    """The entry of the same game, kind and scope (shared Kho, or the same project) whose name or other names share a name_key() with `name`
    / `aliases` — {"id", "name", "matched": [(new word, existing word)]} — or None. S14.37 created 'CHIM CÁNH CỤT' with alias
    'Mr. Waggor' next to the existing 'Mr.Waggor' because nothing looked."""
    mine = {}
    for n in _all_names(name, aliases):
        if name_key(n):
            mine.setdefault(name_key(n), n)
    if not mine:
        return None
    rows = conn.execute("SELECT id, name, aliases FROM assets WHERE game=? AND kind=? AND project_id IS ? ORDER BY id",
                        (game, kind, project_id)).fetchall()      # same scope only: a project's own entry may shadow a shared one
    for r in rows:
        if exclude_id is not None and r["id"] == exclude_id:
            continue
        matched = [(mine[name_key(n)], n) for n in _all_names(r["name"], r["aliases"]) if name_key(n) in mine]
        if matched:
            return {"id": r["id"], "name": r["name"], "matched": matched}
    return None


def find_duplicates(conn, game: Optional[str] = None) -> List[Dict]:
    """S14.43B: pairs of entries of the same game + kind (shared, or one shared and one of a project, or of the same project) sharing
    a name_key() through their name or other names. Only a list for a person / tools/kho_merge.py — nothing is merged here.
    [{"a": {id, name, kind, game, project_id, aliases}, "b": {...}, "keys": [shared keys]}] ordered by ids."""
    sql = "SELECT id, game, kind, name, aliases, project_id FROM assets" + (" WHERE game=?" if game else "") + " ORDER BY id"
    rows = [dict(r) for r in conn.execute(sql, (game,) if game else ())]
    keys = {r["id"]: {name_key(n) for n in _all_names(r["name"], r["aliases"]) if name_key(n)} for r in rows}
    out = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if (a["game"], a["kind"]) != (b["game"], b["kind"]):
                continue
            if a["project_id"] is not None and b["project_id"] is not None and a["project_id"] != b["project_id"]:
                continue
            shared = sorted(keys[a["id"]] & keys[b["id"]])
            if shared:
                out.append({"a": a, "b": b, "keys": shared})
    return out


def create(conn, game: str, kind: str, name: str, description: str = "", aliases: str = "", project_id: Optional[int] = None,
           created_by: Optional[str] = None, allow_duplicate: bool = False, duplicate_reason: str = "") -> int:
    """A new library entry. Refused (AssetError naming the existing entry) when one of the same game and kind already carries the
    name or one of the other names, spelled any way (name_key) — S14.43B. `allow_duplicate=True` with a `duplicate_reason` creates it
    anyway (written to audit_log); the very same name in the same scope is always refused."""
    name = " ".join((name or "").split())
    if not name:
        raise AssetError("Tên tài nguyên không được để trống")
    if kind not in KINDS:
        raise AssetError("Loại tài nguyên không hợp lệ")
    dup = conn.execute("SELECT id FROM assets WHERE game=? AND kind=? AND lower(name)=lower(?) AND COALESCE(project_id,0)=COALESCE(?,0)",
                       (game, kind, name, project_id)).fetchone()
    if dup:
        raise AssetError(f"Đã có {KINDS[kind].lower()} tên “{name}” (#{dup['id']})")
    same = find_same(conn, game, kind, name, aliases or "", project_id)
    if same and not allow_duplicate:
        words = "; ".join(f"“{a}” = “{b}”" for a, b in same["matched"][:4])
        raise AssetError(f"Kho đã có {KINDS[kind].lower()} #{same['id']} “{same['name']}” trùng tên ({words}) — chưa tạo mục mới. "
                         "Dùng mục có sẵn (thêm tên gọi khác / ảnh vào đó); nếu thật sự là thứ khác thì tạo lại với "
                         "allow_duplicate=True kèm lý do.")
    if same and not (duplicate_reason or "").strip():
        raise AssetError(f"Tạo trùng với #{same['id']} “{same['name']}” cần ghi lý do (duplicate_reason) — chưa tạo mục mới.")
    cur = conn.execute("INSERT INTO assets (game, kind, name, aliases, description, project_id, created_by, created_at)"
                       " VALUES (?,?,?,?,?,?,?, datetime('now'))",
                       (game, kind, name, (aliases or "").strip(), (description or "").strip(), project_id, created_by))
    if same:
        conn.execute("INSERT INTO audit_log (at, email, action, detail) VALUES (datetime('now'), ?, 'kho_create_duplicate', ?)",
                     (created_by, f"#{cur.lastrowid} “{name}” trùng #{same['id']} “{same['name']}”: {duplicate_reason.strip()}"[:300]))
    conn.commit()
    return cur.lastrowid


def update(conn, asset_id: int, name: str, aliases: str, description: str) -> None:
    name = " ".join((name or "").split())
    if not name:
        raise AssetError("Tên tài nguyên không được để trống")
    conn.execute("UPDATE assets SET name=?, aliases=?, description=? WHERE id=?", (name, aliases.strip(), description.strip(), asset_id))
    conn.commit()


MAX_SIDE = 2560            # longest side kept when a big picture is shrunk to fit the 10 MB limit


def _shrink(data: bytes, filename: str) -> tuple:
    """(bytes, extension) of a copy of a too-big picture that fits the size limit, or raise AssetError. Only the stored copy is
    smaller: the original file stays where it is."""
    try:
        import io
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:  # noqa: BLE001 - not a readable picture
        raise AssetError(f"“{filename}” lớn hơn 10 MB và không đọc được để thu nhỏ") from None
    if img.mode not in ("RGB", "L"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        img = background
    side = MAX_SIDE
    for _ in range(6):
        work = img.copy()
        work.thumbnail((side, side))
        for quality in (90, 82, 74):
            buf = io.BytesIO()
            work.save(buf, "JPEG", quality=quality, optimize=True)
            if buf.tell() <= MAX_IMAGE_BYTES:
                return buf.getvalue(), ".jpg"
        side = int(side * 0.75)
    raise AssetError(f"“{filename}” quá lớn, không thu nhỏ được xuống 10 MB")


def add_image(conn, asset_id: int, filename: str, data: bytes, src_path: Optional[str] = None, sha256: Optional[str] = None,
              src_size: Optional[int] = None, src_mtime: Optional[int] = None, status: str = "approved", role: Optional[str] = None,
              look: Optional[str] = None, variant: Optional[str] = None, limit: int = MAX_IMAGES_PER_ASSET) -> str:
    """Store one picture. `status` 'pending' = imported without a person looking (folder sync, 3D render): the pipeline does not use it
    until approved (G2). `role` unset = guessed from the picture's shape (the person corrects it when approving)."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in IMAGE_EXT:
        raise AssetError(f"“{filename}”: chỉ nhận ảnh JPG / PNG / WebP")
    if not data:
        raise AssetError(f"“{filename}” rỗng")
    fingerprint = sha256 or hashlib.sha256(data).hexdigest()          # of the original file, so a re-sync recognises it
    if len(data) > MAX_IMAGE_BYTES:
        data, ext = _shrink(data, filename)
    have = _count(conn, asset_id)
    if have >= limit:
        raise AssetError(f"Mỗi tài nguyên tối đa {limit} ảnh")
    root_warning()                                                    # S14.43B: every Kho writer (Dashboard, tools) logs a split once
    folder = os.path.join(root(), str(asset_id))
    os.makedirs(folder, exist_ok=True)
    taken = _held_paths(conn, asset_id)
    n = have + 1
    while os.path.exists(os.path.join(folder, f"{n}{ext}")) or _path_key(os.path.join(folder, f"{n}{ext}")) in taken:
        n += 1
    full = os.path.join(folder, f"{n}{ext}")
    with open(full, "wb") as f:
        f.write(data)
    path = stored_path(full)                                          # S14.43B: "data/assets/…" as before, whatever the working folder
    kind = (conn.execute("SELECT kind FROM assets WHERE id=?", (asset_id,)).fetchone() or {"kind": None})["kind"]
    role = role if role in ROLES.get(kind, {}) else guess_role(full, kind, conn)
    conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, src_path, sha256, src_size, src_mtime, status, role, look, variant)"
                 " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (asset_id, path, os.path.splitext(os.path.basename(filename))[0], n, src_path, fingerprint, src_size, src_mtime,
                  status if status in STATUSES else "pending", role, look if look in LOOKS else None, variant))
    conn.commit()
    return path


def _count(conn, asset_id: int) -> int:
    """Pictures that take one of the 6 places of an asset: every status except the library trash ('removed')."""
    return conn.execute("SELECT COUNT(*) FROM asset_images WHERE asset_id=? AND status IS NOT 'removed'", (asset_id,)).fetchone()[0]


def _path_key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def _held_paths(conn, asset_id: int) -> set:
    """S14.4: file names the asset's rows already point at (every status — a lost file's row, a trashed picture): a new picture must
    not take one, or two rows share a file and deleting one deletes the other's picture."""
    out = set()
    for r in conn.execute("SELECT path FROM asset_images WHERE asset_id=?", (asset_id,)):
        if r["path"]:
            out.add(_path_key(r["path"]))
            out.add(_path_key(resolve(r["path"])))
    return out


def guess_role(path: str, kind: Optional[str], conn=None) -> Optional[str]:
    """A free first guess of a picture's role (no model call): the design board test, the picture's proportions, and for a place the
    camera class of its set analysis when it was read before. None = unknown (the person sets it)."""
    if kind in ("character", "pet"):
        shape = _shape(path)
        if not shape:
            return None
        if _is_composite_sheet(shape):
            return "design_sheet"
        w, h = shape
        return "full_body" if h >= w * 1.6 else "half_body" if h >= w * 1.05 else None
    if kind == "location" and conn is not None:
        try:
            with open(path, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return None
        row = conn.execute("SELECT data FROM set_analyses WHERE sha256=?", (sha,)).fetchone()
        camera = (json.loads(row["data"]).get("camera") if row else None)
        return {"eye": "eye_level", "low": "low_angle", "high": "high_angle", "top": "top_down"}.get(camera)
    return None


def set_image_meta(conn, image_id: int, role: Optional[str] = None, look: Optional[str] = None, variant: Optional[str] = None,
                   status: Optional[str] = None) -> None:
    """Correct what a picture shows / approve it. Empty string clears a field; None leaves it."""
    fields = {k: (v or None) for k, v in (("role", role), ("look", look), ("variant", variant)) if v is not None}
    if status is not None:
        fields["status"] = status if status in STATUSES else "pending"
    if fields:
        conn.execute("UPDATE asset_images SET " + ", ".join(f"{k}=?" for k in fields) + " WHERE id=?", (*fields.values(), image_id))
        conn.commit()


def approve_images(conn, image_ids: List[int]) -> int:
    cur = conn.execute(f"UPDATE asset_images SET status='approved' WHERE id IN ({','.join('?' * len(image_ids))})", list(image_ids)) \
        if image_ids else None
    conn.commit()
    return cur.rowcount if cur else 0


def pending_images(conn, game: Optional[str] = None) -> List[Dict]:
    """Pictures waiting for a person (G2), with their asset: [{id, path, role, look, variant, asset_id, asset, kind}]."""
    sql = ("SELECT i.id, i.path, i.role, i.look, i.variant, a.id AS asset_id, a.name AS asset, a.kind FROM asset_images i"
           " JOIN assets a ON a.id=i.asset_id WHERE i.status='pending'" + (" AND a.game=?" if game else "") + " ORDER BY a.name, i.id")
    return [dict(r, path=resolve(r["path"])) for r in conn.execute(sql, (game,) if game else ())]


def health(conn, game: str) -> List[Dict]:
    """G6: what each library entry still lacks before a project can rely on it (only approved pictures count)."""
    out = []
    for a in list_assets(conn, game, None, None, shared_only=True):
        if a["kind"] not in ("character", "pet", "location"):
            continue
        roles = {i.get("role") for i in a["images"]}
        looks = {i.get("look") for i in a["images"]}
        if a["kind"] == "location":
            need = [] if roles & {"eye_level", "low_angle"} else ["nền ngang tầm mắt"]
        else:
            need = [ROLES["character"][r] for r in ("half_body", "close_up", "back") if r not in roles] if a["images"] else ["ảnh"]
            if "anime" not in looks:
                need.append("ảnh chuẩn anime")
        out.append({"id": a["id"], "name": a["name"], "kind": a["kind_label"], "approved": len(a["images"]),
                    "pending": len(a["pending"]), "unlabelled": sum(1 for i in a["images"] if not i.get("role")), "missing": need})
    return out


def remove_image(conn, image_id: int) -> None:
    row = conn.execute("SELECT path FROM asset_images WHERE id=?", (image_id,)).fetchone()
    if row:
        try:
            os.remove(resolve(row["path"]))
        except OSError:
            pass
        conn.execute("DELETE FROM asset_images WHERE id=?", (image_id,))
        conn.commit()


# ---- S14.4 (04/10): the library trash — a picture deleted on screen can be brought back for 30 days ---------------------------
# Only the screens use it (⚙ → Kho). remove_image above keeps deleting at once (folder sync with remove_missing, tools, tests).
# The picture keeps its row and its file; status 'removed' is not in STATUSES, so every reader that takes None/approved/pending
# (_row, list_assets, pending_images, asset_vision.pending…) skips it, and it frees its place among the 6 of the asset.
TRASH_DAYS = 30


def trash_days() -> int:
    """How long a deleted library picture stays restorable: the project trash's setting (TRASH_DAYS, default 30)."""
    try:
        from . import trash
        return trash.retention_days()
    except Exception:  # noqa: BLE001 - the library works without the project trash module
        return TRASH_DAYS


def trash_image(conn, image_id: int) -> None:
    """Put a library picture in the trash: hidden everywhere, file kept, restorable with restore_image until purge_removed."""
    row = conn.execute("SELECT status FROM asset_images WHERE id=?", (image_id,)).fetchone()
    if row is None:
        raise AssetError("Không còn ảnh này trong Kho")
    if row["status"] == "removed":
        return
    conn.execute("UPDATE asset_images SET status='removed', removed_from=?, removed_at=datetime('now') WHERE id=?",
                 (row["status"], image_id))
    conn.commit()


def removed_images(conn, asset_id: int) -> List[Dict]:
    """The asset's pictures in the trash, newest first: [{id, path (usable), exists, removed_at, days_left, label}]."""
    days = trash_days()
    out = []
    for r in conn.execute("SELECT id, path, label, removed_at, CAST(julianday('now') - julianday(COALESCE(removed_at, 'now')) AS REAL) AS age"
                          " FROM asset_images WHERE asset_id=? AND status='removed' ORDER BY removed_at DESC, id DESC", (asset_id,)):
        path = resolve(r["path"])
        out.append({"id": r["id"], "path": path, "exists": bool(path and os.path.exists(path)), "removed_at": r["removed_at"],
                    "label": r["label"], "days_left": max(int(days - (r["age"] or 0) + 0.999), 0)})
    return out


def restore_image(conn, image_id: int) -> None:
    """Bring a trashed picture back with the status it had. Refused (AssetError, said on screen) when its file is gone or the asset
    already has its 6 pictures. The file never moved, so nothing on disk is overwritten (a newer upload took another file name)."""
    row = conn.execute("SELECT asset_id, path, status, removed_from FROM asset_images WHERE id=?", (image_id,)).fetchone()
    if row is None or row["status"] != "removed":
        raise AssetError("Ảnh này không nằm trong thùng rác của Kho")
    if not os.path.exists(resolve(row["path"])):
        raise AssetError("File ảnh đã mất khỏi ổ đĩa — không khôi phục được (tải ảnh lên lại)")
    have = _count(conn, row["asset_id"])
    if have >= MAX_IMAGES_PER_ASSET:
        raise AssetError(f"Mục này đã đủ {MAX_IMAGES_PER_ASSET} ảnh — xóa bớt một ảnh rồi khôi phục")
    back = row["removed_from"] if row["removed_from"] in STATUSES else "pending"     # unknown → a person looks again (G2)
    conn.execute("UPDATE asset_images SET status=?, removed_from=NULL, removed_at=NULL WHERE id=?", (back, image_id))
    conn.commit()


def purge_removed(conn, days: Optional[int] = None) -> int:
    """Empty the library trash: pictures deleted more than `days` (default trash_days()) ago lose their file and their row.
    Returns how many. Called by the Dashboard's housekeeping (dashboard/app.py, at most once an hour)."""
    days = trash_days() if days is None else days
    rows = conn.execute("SELECT id FROM asset_images WHERE status='removed' AND removed_at IS NOT NULL"
                        " AND julianday('now') - julianday(removed_at) >= ?", (days,)).fetchall()
    for r in rows:
        remove_image(conn, r["id"])
    return len(rows)


def thumbnail(path: str, side: int = 220) -> str:
    """Small cached copy of a picture for lists (decoding a 2560 px original for every rerun made the page slow)."""
    try:
        thumb_dir = os.path.join(root(), "_thumbs")
        out = os.path.join(thumb_dir, f"{fold(os.path.basename(os.path.dirname(path)))}_{side}_{os.path.basename(path)}.jpg")
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(path):
            return out
        os.makedirs(thumb_dir, exist_ok=True)
        from PIL import Image
        with Image.open(path) as im:
            im.thumbnail((side, side))
            if im.mode in ("RGBA", "LA", "P"):                # cut-out art: a light-grey background, not black
                rgba = im.convert("RGBA")
                flat = Image.new("RGB", rgba.size, (232, 232, 232))
                flat.paste(rgba, mask=rgba.getchannel("A"))
                flat.save(out, "JPEG", quality=85)
            else:
                im.convert("RGB").save(out, "JPEG", quality=85)
        return out
    except Exception:  # noqa: BLE001 - fall back to the original
        return path


def delete(conn, asset_id: int) -> None:
    conn.execute("DELETE FROM asset_images WHERE asset_id=?", (asset_id,))
    conn.execute("DELETE FROM project_assets WHERE asset_id=?", (asset_id,))
    conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    conn.commit()
    folder = asset_folder(asset_id)
    if folder:
        shutil.rmtree(folder, ignore_errors=True)


def asset_folder(asset_id) -> Optional[str]:
    """<library>/<id>, absolute, only for a whole positive id and only inside the library folder (S14.43B: delete used to remove
    "data/assets/<id>" under whatever folder the program was started from). None = refused."""
    try:
        n = int(asset_id)
    except (TypeError, ValueError):
        return None
    if n <= 0 or str(n) != str(asset_id).strip():
        return None
    base = os.path.realpath(root())
    folder = os.path.realpath(os.path.join(base, str(n)))
    return folder if os.path.normcase(os.path.dirname(folder)) == os.path.normcase(base) else None


def _same_profile(a: Dict, b: Dict) -> bool:
    return all(str(a.get(k) or "").strip() == str(b.get(k) or "").strip() for k in PROFILE_KEYS) and bool(a.get("approved")) == bool(b.get("approved"))


def merge(conn, from_id: int, into_id: int) -> int:
    """Fold asset `from_id` into `into_id` (same picture set, one name): EVERY picture row is moved (approved, waiting for review,
    redundant, in the trash, or with its file lost — S14.4: only approved readable ones used to move, the rest died with the deleted
    asset), its other names become aliases of the target, its standard profile is copied when the target has none, and it is
    deleted once it has no picture left. Refused before anything changes (AssetError, said on screen) when the target has no room
    for the pictures that take a place, or when both have a different standard profile that a person must choose between.
    Returns how many pictures moved."""
    if from_id == into_id:
        raise AssetError("Chọn một mục khác để gộp vào")
    src, dst = get(conn, from_id), get(conn, into_id)
    if src is None or dst is None:
        raise AssetError("Không có mục này")
    rows = [dict(r) for r in conn.execute("SELECT id, path, status FROM asset_images WHERE asset_id=? ORDER BY sort, id", (from_id,))]
    have = _count(conn, into_id)                                        # same count as add_image: the trash takes no place
    taking = sum(1 for r in rows if r["status"] != "removed")
    if have + taking > MAX_IMAGES_PER_ASSET:
        raise AssetError(f"“{dst['name']}” đã có {have}/{MAX_IMAGES_PER_ASSET} ảnh, còn {MAX_IMAGES_PER_ASSET - have} chỗ — "
                         f"“{src['name']}” có {taking} ảnh. Xóa bớt ảnh ở một trong hai mục rồi gộp lại (chưa đổi gì).")
    sp, dp = get_profile(conn, from_id), get_profile(conn, into_id)
    copy_profile = False
    if sp and not dp:
        copy_profile = True
    elif sp and dp and not _same_profile(sp, dp) and not (dp.get("approved") and not sp.get("approved")):
        raise AssetError(f"Hai mục đều có hồ sơ chuẩn khác nhau (“{src['name']}”: {'đã duyệt' if sp.get('approved') else 'nháp'}, "
                         f"“{dst['name']}”: {'đã duyệt' if dp.get('approved') else 'nháp'}) — mở 📋 Hồ sơ chuẩn, giữ một bản rồi gộp "
                         "lại (chưa đổi gì).")
    # else: the target's approved profile wins over the source's draft (a draft is never inherited)
    folder = os.path.join(root(), str(into_id))
    os.makedirs(folder, exist_ok=True)
    taken = _held_paths(conn, into_id)                                 # rows of the target whose file is lost / trashed keep their name
    moved = 0
    for img in rows:
        current = resolve(img["path"])
        ext = os.path.splitext(img["path"])[1]
        n = have + moved + 1
        while os.path.exists(os.path.join(folder, f"{n}{ext}")) or _path_key(os.path.join(folder, f"{n}{ext}")) in taken:
            n += 1
        target = os.path.join(folder, f"{n}{ext}")
        if current and os.path.exists(current):
            try:
                shutil.move(current, target)
            except OSError as e:                                        # e.g. a file held open by another program (Windows)
                raise AssetError(f"Không chuyển được ảnh “{os.path.basename(current)}” sang “{dst['name']}” ({e.strerror or e}) — "
                                 f"đã chuyển {moved} ảnh, “{src['name']}” còn {len(rows) - moved} ảnh và được giữ lại. Đóng chương "
                                 "trình đang mở ảnh rồi gộp lại.") from None
        taken.add(_path_key(target))
        # file lost: only the row moves (its path now points into the target folder, so ↻ Tải lại writes it there)
        conn.execute("UPDATE asset_images SET asset_id=?, path=?, sort=? WHERE id=?", (into_id, stored_path(target), n, img["id"]))
        conn.commit()                                                   # one row at a time: a failed move never leaves a file without its row
        moved += 1
    if copy_profile:
        conn.execute("UPDATE assets SET profile=(SELECT profile FROM assets WHERE id=?) WHERE id=?", (from_id, into_id))   # with its history
    names = [n for n in re.split(r"[,;|]", dst["aliases"]) if n.strip()]
    for n in [src["name"]] + [x for x in re.split(r"[,;|]", src["aliases"]) if x.strip()]:
        if fold(n) != fold(dst["name"]) and fold(n) not in {fold(x) for x in names}:
            names.append(n.strip())
    conn.execute("UPDATE assets SET aliases=? WHERE id=?", (", ".join(names), into_id))
    conn.execute("UPDATE project_assets SET asset_id=? WHERE asset_id=? AND NOT EXISTS (SELECT 1 FROM project_assets p2"
                 " WHERE p2.project_id=project_assets.project_id AND p2.asset_id=?)", (into_id, from_id, into_id))
    conn.commit()
    left = conn.execute("SELECT COUNT(*) FROM asset_images WHERE asset_id=?", (from_id,)).fetchone()[0]
    if left:                                                            # never delete a picture with its asset
        raise AssetError(f"Còn {left} ảnh chưa chuyển được khỏi “{src['name']}” — mục cũ được giữ lại")
    delete(conn, from_id)
    return moved


def _resolved(images: List[Dict]):
    """The pictures with their usable path and whether the file is there — one disk check each (resolve() + exists() made two)."""
    out, here = [], {}
    for i in images:
        path = i["path"]
        if not path:
            full, ok = path, False
        elif os.path.isabs(path) or os.path.exists(path):
            full, ok = path, os.path.exists(path) if os.path.isabs(path) else True
        else:
            full = os.path.join(REPO, path)
            ok = os.path.exists(full)
        out.append(dict(i, path=full))
        here[i["id"]] = ok
    return out, here


def _row(conn, r, images_by_asset: Optional[Dict] = None) -> Dict:
    if images_by_asset is not None:
        images = images_by_asset.get(r["id"], [])
    else:
        images = [dict(i) for i in conn.execute("SELECT id, path, label, role, look, variant, status FROM asset_images WHERE asset_id=?"
                                                " ORDER BY sort, id", (r["id"],))]
    images, here = _resolved(images)                                               # one disk check per picture (it was four)
    pending = [i for i in images if i.get("status") == "pending" and here[i["id"]]]
    images = [i for i in images if i.get("status") in USABLE]            # G2: only approved pictures (a person's, or S14.42 'claude_ok') are used
    return {"id": r["id"], "claude_only": sum(1 for i in images if i.get("status") == "claude_ok" and here[i["id"]]), "game": r["game"], "kind": r["kind"], "kind_label": KINDS.get(r["kind"], r["kind"]), "name": r["name"],
            "aliases": r["aliases"] or "", "description": r["description"] or "", "project_id": r["project_id"],
            "created_by": r["created_by"], "images": [i for i in images if here[i["id"]]], "pending": pending,
            "missing": [i["path"] for i in images if not here[i["id"]]]}   # approved pictures whose file is gone (said, luật 1)


def get(conn, asset_id: int) -> Optional[Dict]:
    r = conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
    return _row(conn, r) if r else None


def list_assets(conn, game: Optional[str] = None, kind: Optional[str] = None, project_id: Optional[int] = None,
                shared_only: bool = False) -> List[Dict]:
    """Shared library entries (of `game`), plus the project's own assets unless shared_only."""
    sql, args = "SELECT * FROM assets WHERE (project_id IS NULL", []
    if project_id is not None and not shared_only:
        sql += " OR project_id=?"
        args.append(project_id)
    sql += ")"
    if game:
        sql += " AND game=?"
        args.append(game)
    if kind:
        sql += " AND kind=?"
        args.append(kind)
    sql += " ORDER BY kind, lower(name)"
    rows = conn.execute(sql, args).fetchall()
    images: Dict[int, List[Dict]] = {}                # one query for every picture instead of one per entry (a library has hundreds)
    # only the pictures of the entries asked for (02/10: the whole table was read for every call — 10× the library, 10× the time)
    ids_sql = sql.replace("SELECT * FROM assets", "SELECT id FROM assets", 1).replace(" ORDER BY kind, lower(name)", "")
    for i in conn.execute("SELECT asset_id, id, path, label, role, look, variant, status FROM asset_images WHERE asset_id IN (" + ids_sql
                          + ") ORDER BY sort, id", args):
        images.setdefault(i["asset_id"], []).append({k: i[k] for k in ("id", "path", "label", "role", "look", "variant", "status")})
    return [_row(conn, r, images) for r in rows]


# ---- finding assets in a script ---------------------------------------------------------------------------------
def names_of(asset: Dict) -> List[str]:
    return [n for n in [asset["name"]] + re.split(r"[,;|]", asset["aliases"]) if fold(n)]


def _said_words(text: str) -> List[str]:
    """NFC lower-case words of a text (accents kept)."""
    return re.sub(r"[^\w]+", " ", unicodedata.normalize("NFC", text or "").lower()).split()


def name_spans(name: str, words: List[str]) -> List[Tuple[int, int]]:
    """[(start, end)] word spans where `name` is said in `words`: same letters WITH accents, or — the text typed without accents
    ("quang truong") — the folded letters where the text itself has no accent. 08/10 (#24): "ĐẠO CỤ" folded to "dao cu" matched the
    weapon "Đao"; a written accent that differs is another word."""
    want = _said_words(name)
    folded = [fold(w) for w in want]
    n, out = len(want), []
    if not n:
        return out
    for i in range(len(words) - n + 1):
        part = words[i:i + n]
        if part == want or all(w == fold(w) and fw == fold(w) for w, fw in zip(part, folded)):
            out.append((i, i + n))
    return out


def _qualifies_other_place(asset: Dict, words: List[str], other_places: List[str]) -> bool:
    """08/10 (#24): a place whose every mention sits right before / after ANOTHER place's name ("QUẢNG TRƯỜNG THÁP ĐỒNG HỒ") is the
    common noun of an area of that place, not the library place "Quảng Trường" (Đảo Thế Kỷ)."""
    if asset.get("kind") != "location":
        return False
    mine = [sp for nm in names_of(asset) for sp in name_spans(nm, words)]
    if not mine:
        return False
    others = [sp for nm in other_places for sp in name_spans(nm, words)]
    others = [o for o in others if o not in mine]
    if not others:
        return False
    return all(any(o[0] == e or o[1] == s0 for o in others) for s0, e in mine)


def find_in_text(conn, text: str, game: Optional[str], project_id: Optional[int] = None) -> List[Dict]:
    """Assets whose name or another name appears in the text (whole words, case ignored; accents must agree where the text has them —
    08/10). A place said only as the area word of another place ("Quảng Trường Tháp Đồng Hồ") is not suggested on its own."""
    words = _said_words(text)
    body = " " + fold(text) + " "
    found = []
    # names first (no pictures read, no disk checks); full entries only for the ones the text mentions
    sql, args = "SELECT id, kind, name, aliases FROM assets WHERE (project_id IS NULL", []
    if project_id is not None:
        sql += " OR project_id=?"
        args.append(project_id)
    sql += ")"
    if game:
        sql += " AND game=?"
        args.append(game)
    hit_ids, rows = {}, {}
    for r in conn.execute(sql + " ORDER BY kind, lower(name)", args).fetchall():
        names = [n for n in [r["name"]] + re.split(r"[,;|]", r["aliases"] or "") if fold(n)]
        if not any(" " + fold(n) + " " in body for n in names):   # cheap pre-filter
            continue
        hits = sum(len(name_spans(n, words)) for n in names if len(fold(n)) >= 2)
        if hits:
            hit_ids[r["id"]] = hits
            rows[r["id"]] = r
    place_names = [n for aid, r in rows.items() if r["kind"] == "location" for n in names_of(dict(r, aliases=r["aliases"] or ""))]
    if project_id is not None:
        place_names += [n for a in _project_assets(conn, project_id) if a["kind"] == "location" for n in names_of(a)]
    for aid, hits in hit_ids.items():
        r = rows[aid]
        if r["kind"] == "location":
            own = set(names_of(dict(r, aliases=r["aliases"] or "")))
            if _qualifies_other_place(dict(r, aliases=r["aliases"] or ""), words, [n for n in place_names if n not in own]):
                continue
        a = get(conn, aid)
        if a is not None:
            found.append(dict(a, mentions=hits))
    return sorted(found, key=lambda a: -a["mentions"])


def names_of_kinds(conn, game: Optional[str], kinds) -> List[Tuple[int, str]]:
    """[(id, name)] of the shared library entries of these kinds — names only (no pictures read), in the order of list_assets."""
    kinds = list(kinds)
    sql = "SELECT id, name FROM assets WHERE project_id IS NULL AND kind IN (" + ",".join("?" * len(kinds)) + ")"
    args = list(kinds)
    if game:
        sql += " AND game=?"
        args.append(game)
    return [(r["id"], r["name"]) for r in conn.execute(sql + " ORDER BY kind, lower(name)", args)]


def library_labels(conn, game: Optional[str], project_id: Optional[int] = None, exclude=()) -> List[Tuple[int, str]]:
    """[(id, "Loại: tên")] of the shared library (+ the project's own), in the order of list_assets — for a picker that needs only names."""
    sql, args = "SELECT id, kind, name FROM assets WHERE (project_id IS NULL", []
    if project_id is not None:
        sql += " OR project_id=?"
        args.append(project_id)
    sql += ")"
    if game:
        sql += " AND game=?"
        args.append(game)
    gone = set(exclude)
    return [(r["id"], f"{KINDS.get(r['kind'], r['kind'])}: {r['name']}")
            for r in conn.execute(sql + " ORDER BY kind, lower(name)", args) if r["id"] not in gone]


# ---- assets of a project --------------------------------------------------------------------------------------------
def attach(conn, project_id: int, asset_id: int) -> None:
    conn.execute("INSERT OR IGNORE INTO project_assets (project_id, asset_id) VALUES (?,?)", (project_id, asset_id))
    conn.commit()


def detach(conn, project_id: int, asset_id: int) -> None:
    """The person removes a resource from the project: it is also remembered as declined, so auto_attach never puts it back."""
    conn.execute("DELETE FROM project_assets WHERE project_id=? AND asset_id=?", (project_id, asset_id))
    conn.execute("INSERT OR IGNORE INTO project_assets_declined (project_id, asset_id) VALUES (?,?)", (project_id, asset_id))
    conn.commit()


def _spoken_form(text: str) -> str:
    """Lower case with the accents KEPT (NFC): "Nỏ" must not match "nó", nor "Đao" match "đạo" — auto_attach has no person to catch it."""
    import unicodedata
    return " " + re.sub(r"[^\w]+", " ", unicodedata.normalize("NFC", text or "").lower()) + " "


def _common_noun_only(asset: Dict, script: str) -> bool:
    """KLD-11 (#22, "Mũ"): every name of this resource the script says is ONE word, and the script writes it in lower case somewhere
    ("đội mũ đỏ") — a common noun (mũ, áo, súng, nhà…), not the resource's name. Characters / pets are names by nature and keep the old
    rule; a one-word name written only as a name ("UMP", "Mũ" at the start of a line) still attaches."""
    import unicodedata
    if asset["kind"] in ("character", "pet"):
        return False
    text = unicodedata.normalize("NFC", script or "")
    said = [n for n in names_of(asset) if _spoken_form(n) in _spoken_form(text)]
    if not said or any(len(fold(n).split()) != 1 for n in said):
        return False
    for n in said:
        low = unicodedata.normalize("NFC", n.strip()).lower()
        if not re.search(r"(?<!\w)" + re.escape(low) + r"(?!\w)", text):
            return False                                 # never written in lower case: used as a name
    return True


def auto_attach(conn, project_id: int) -> Dict[str, List[str]]:
    """Before the Director runs: attach the library resources the script names (as "➕ Dùng tất cả gợi ý" in Step 1), so the Director
    sees the places / characters of the library without a person clicking (người dùng chốt 2026-09-27). Stricter than the Step 1
    suggestions, because nobody confirms: the name must appear WITH its accents (whole words); skipped are resources the person removed
    from this project (declined), a resource whose name is already carried by an attached one (a "kenta" prop next to the attached
    character KENTA), and a name that fits several resources — left for a person to choose, and said.
    {"attached": [names], "ambiguous": [names]}"""
    row = conn.execute("SELECT game, script_text FROM projects WHERE id=?", (project_id,)).fetchone()
    if row is None or not (row["script_text"] or "").strip():
        return {"attached": [], "ambiguous": []}
    have = _project_assets(conn, project_id)
    have_ids = {a["id"] for a in have}
    have_names = {fold(n) for a in have for n in names_of(a)}
    declined = {r[0] for r in conn.execute("SELECT asset_id FROM project_assets_declined WHERE project_id=?", (project_id,))}
    body = _spoken_form(row["script_text"])
    hits: Dict[int, List[str]] = {}
    for a in list_assets(conn, row["game"], None, project_id):
        if a["id"] in have_ids or a["id"] in declined:
            continue
        said = [n for n in names_of(a) if len(fold(n)) >= 2 and _spoken_form(n) in body]
        if said and not any(fold(n) in have_names for n in names_of(a)):
            hits[a["id"]] = [fold(n) for n in said]
    by_id = {a["id"]: a for a in list_assets(conn, row["game"], None, project_id)}
    owners: Dict[str, set] = {}
    for aid, names in hits.items():
        for n in names:
            owners.setdefault(n, set()).add(aid)
    # a name shared with a prop / weapon goes to the one character / pet / place carrying it (KENTA the character, not a "kenta" prop)
    main = ("character", "pet", "location")
    for n, ids in owners.items():
        mains = [i for i in ids if by_id[i]["kind"] in main]
        if len(ids) > 1 and len(mains) == 1:
            owners[n] = set(mains)
            for i in ids - set(mains):
                hits[i] = [x for x in hits[i] if x != n]
    attached, ambiguous = [], []
    script = row["script_text"]
    words = _said_words(script)
    place_names = [n for a in have if a["kind"] == "location" for n in names_of(a)] + [
        n for i in hits if by_id[i]["kind"] == "location" for n in names_of(by_id[i])]
    for aid, names in hits.items():
        if not names:
            continue                                     # its only name belongs to a character / place — not this one
        own = set(names_of(by_id[aid]))
        if _qualifies_other_place(by_id[aid], words, [n for n in place_names if n not in own]):
            ambiguous.append(by_id[aid]["name"])         # 08/10 (#24): "QUẢNG TRƯỜNG THÁP ĐỒNG HỒ" — the area word of Tháp Đồng Hồ
            continue
        if _common_noun_only(by_id[aid], script):
            ambiguous.append(by_id[aid]["name"])         # KLD-11: "Mũ" matched "đội mũ" (#22) — a person chooses
            continue
        if any(len(owners[n]) == 1 for n in names):
            conn.execute("INSERT OR IGNORE INTO project_assets (project_id, asset_id) VALUES (?,?)", (project_id, aid))
            attached.append(by_id[aid]["name"])
        else:
            ambiguous.append(by_id[aid]["name"])
    conn.commit()
    return {"attached": sorted(attached), "ambiguous": sorted(set(ambiguous))}


def project_assets(conn, project_id: int) -> List[Dict]:
    # inside a dashboard rerun (core.memo.per_rerun) computed once per database state: Bước 1/2 asked 120+ times per click
    from .memo import cached
    return cached(conn, ("assets.project_assets", project_id), lambda: _project_assets(conn, project_id))


def _project_assets(conn, project_id: int) -> List[Dict]:
    rows = conn.execute("SELECT a.* FROM assets a JOIN project_assets pa ON pa.asset_id=a.id WHERE pa.project_id=?"
                        " ORDER BY a.kind, lower(a.name)", (project_id,)).fetchall()
    return [_row(conn, r) for r in rows]


def reference_paths(conn, project_id: int, kinds=("character",), limit: int = 4) -> List[str]:
    """Pictures to hand to an image / video generator as references (first picture of each chosen asset)."""
    out = []
    for a in project_assets(conn, project_id):
        if a["kind"] in kinds and a["images"]:
            out.append(a["images"][0]["path"])
    return out[:limit]


MAX_REFERENCES = 8                 # pictures sent with one image job (Seedream 5.0 Pro accepts up to 10)
MAX_REFS_PER_CHARACTER = 2         # one straight-on shot is not enough to lock a face/outfit; a second angle or close-up helps a lot


def match_character(chosen: List[Dict], name: str) -> Optional[Dict]:
    """The chosen character asset that is this Character Bible entry ("Kelly" -> KELLY): same name or alias, else the shortest asset whose
    first word is the name ("Kelly" -> "Kelly thức tỉnh"). None when nothing fits (the picture is then drawn from the text description)."""
    key = fold(name)
    if not key:
        return None
    pool = [a for a in chosen if a["kind"] in ("character", "pet") and a["images"]]
    for a in pool:
        if key in {fold(n) for n in names_of(a)}:
            return a
    close = [a for a in pool if fold(a["name"]).split(" ")[0] == key.split(" ")[0] and key.split(" ")[0]]
    # A15: a first-word guess only when it is the only candidate ("Kelly" -> "Kelly thức tỉnh"); two candidates = ask the person
    return close[0] if len(close) == 1 else None


def _reference_rows(conn, project_id: int) -> Dict[str, Dict]:
    return {r["name"]: dict(r) for r in conn.execute(
        "SELECT name, ref_asset_id, ref_image_id, ref_image_ids FROM characters WHERE project_id=?", (project_id,))}


_SHAPES: Dict[tuple, tuple] = {}         # (path, mtime_ns, size) -> (w, h): Bước 2 read ~1000 picture headers per click


def _shape(path: str):
    try:
        st = os.stat(path)
        key = (path, st.st_mtime_ns, st.st_size)             # a replaced file has a new time/size and is read again
        if key in _SHAPES:
            return _SHAPES[key]
        from PIL import Image
        with Image.open(path) as im:                         # only the header is read
            size = im.size
    except Exception:  # noqa: BLE001 - unreadable: not cached, asked again next time
        return None
    if len(_SHAPES) > 20000:
        _SHAPES.clear()
    _SHAPES[key] = size
    return size


def _is_composite_sheet(shape) -> bool:
    """A wide board with a character's turn-around, expressions and props all on one canvas: sending it as a reference makes an
    image model copy random pieces of it (and, with several people in a scene, mix faces/outfits between them)."""
    if not shape:
        return False
    w, h = shape
    return w > h and w >= 1200


def is_composite_sheet(path: str) -> bool:
    """Public wrapper of `_is_composite_sheet` for other modules (e.g. core/asset_vision.py) that want the same "is this a design
    board, not a single-figure shot" check without reaching into assets.py internals."""
    return _is_composite_sheet(_shape(path))


_CLOSE = ("ECU", "CU", "MCU")
_WIDE = ("WS", "EWS", "GAME_TPS")
_BACK_WORDS = ("back to camera", "from behind", "back view", "quay lưng", "sau lưng", "nhìn từ sau", "rear view")


def shot_size(scene: Optional[Dict]) -> Optional[str]:
    """ECU…EWS of a shot: the v3 `size` field, else read from the v2 `shot` words."""
    if not scene:
        return None
    if scene.get("size") in _CLOSE + ("MS",) + _WIDE:
        return scene["size"]
    words = f" {fold(str(scene.get('shot') or ''))} "
    for size, keys in (("ECU", ("extreme close", "ecu ")), ("MCU", ("medium close", " mcu ")), ("CU", ("close up", "close-up", " cu ", "can canh")),
                       ("EWS", ("extreme wide", " ews ")), ("WS", ("wide", "establishing", " ws ", " ls ", "long shot", "toan canh")),
                       ("MS", ("medium", " ms ", "trung canh"))):
        if any(k in words for k in keys):
            return size
    return None


SKIN_PREFIX = "skin:"      # a picture's variant "skin: …" = another outfit (01/10 Wolfrahh in white): only used when the project picks it


def is_skin(img: Dict) -> bool:
    return str(img.get("variant") or "").strip().lower().startswith(SKIN_PREFIX)


_SIDE_WORDS = ("profile", "side view", "from the side", "nghiêng", "góc nghiêng")


def shot_roles(scene: Optional[Dict], name: Optional[str] = None) -> List[Optional[str]]:
    """T3: which kind of character picture suits the shot, best first (None = a picture whose role nobody set).
    A close shot needs a face the model can copy; a wide shot the whole figure; a back-to-camera shot a back view. With `name`, the
    back / front is read for THAT person (runner.seen_from_behind — an over-the-shoulder shot shows one person's back, not everyone's);
    a profile shot puts the side pictures first (01/10: 3D renders of every side are in the library)."""
    size = shot_size(scene)
    order: List[Optional[str]] = (["close_up", "half_body", None, "full_body"] if size in _CLOSE else
                                  ["full_body", None, "half_body", "close_up"] if size in _WIDE else
                                  ["half_body", None, "full_body", "close_up"])
    text = fold(" ".join(str((scene or {}).get(k) or "") for k in ("blocking", "action", "shot", "image_prompt")))
    behind = None
    if name and scene:
        from .runner import seen_from_behind
        behind = seen_from_behind(scene, name)
    back_words = any(fold(w) in text for w in _BACK_WORDS)
    who = fold(name or "")
    # "Kelly quay lưng …" (the back words within 40 letters after the name) — seen_from_behind reads only the English patterns
    near = bool(who) and any(re.search(re.escape(who) + r".{0,40}" + re.escape(fold(w)), text) for w in _BACK_WORDS)
    # seen_from_behind says False also when the words do not name this person: a "from behind" shot that names nobody is everyone's back
    if behind is True or near or (back_words and (behind is None or who not in text)):
        order = ["back"] + order
    elif any(fold(w) in text for w in _SIDE_WORDS):
        order = ["side"] + order
    return order + [r for r in ("side", "skill_pose") if r not in order]


def best_references(asset: Dict, limit: int = 1, scene: Optional[Dict] = None, name: Optional[str] = None) -> List[Dict]:
    """The `limit` pictures that work best as a reference, for `asset["kind"]`:
    - character/pet: single-figure shots (portrait/full-body), a composite sheet only as a last resort — one straight-on shot rarely
      pins down a face well, so a second angle or a close-up is included when available.
    - location: the widest, biggest establishing shot (an environment, not a portrait).
    - everything else (weapon, prop): its first picture."""
    images = asset["images"]
    if not images:
        return []
    kind = asset.get("kind")
    if kind in ("character", "pet"):
        own = [i for i in images if not is_skin(i)] or images       # another outfit only through the project's outfit choice
        singles = [i for i in own if i.get("role") not in ("design_sheet", "related") and not _is_composite_sheet(_shape(i["path"]))]
        pool = singles or [i for i in own if i.get("role") != "related"] or own
        prefs = ["front_standard"] + shot_roles(scene, name)          # the person's grey-background front picture always leads
        want_look = (scene or {}).get("_look")                 # the project's look: its standard pictures first (T6)

        def score(img):
            role = img.get("role")
            rank = prefs.index(role) if role in prefs else len(prefs)
            look = 1 if want_look and img.get("look") == want_look else 0
            shape = _shape(img["path"])
            if not shape:
                return (look, -rank, 0, 0)
            w, h = shape
            return (look, -rank, 1 if h >= w * 1.05 else 0, w * h)   # the look, the shot's kind of picture, portrait, the biggest
        ranked = sorted(pool, key=score, reverse=True)
    elif kind == "location":
        def score(img):
            shape = _shape(img["path"])
            if not shape:
                return (0, 0)
            w, h = shape
            return (1 if w >= h else 0, w * h)                 # a wide establishing shot, not a portrait crop
        ranked = sorted(images, key=score, reverse=True)
    else:
        ranked = images
    return ranked[:max(limit, 1)]


def view_picture(asset: Dict, role: str) -> Optional[Dict]:
    """The approved picture of one side (role back / side / full_body) of the character's own outfit, the biggest — for QC to compare a
    frame with the same side of the standard (01/10: 3D renders + in-game screenshots of every side)."""
    pics = [i for i in asset.get("images") or [] if i.get("role") == role and not is_skin(i)]
    return max(pics, key=lambda i: (lambda s: s[0] * s[1] if s else 0)(_shape(i["path"])), default=None)


def best_reference(asset: Dict) -> Dict:
    return best_references(asset, 1)[0]


STANDARD_ROLES = ("front_standard", "design_sheet", "related")


def standard_set(asset: Dict, sheets: bool) -> List[tuple]:
    """The character's standard 3 pictures (user choice 2026-09-24): [(picture, ref role)] = the grey-background front picture
    ('character'), the multi-angle design sheet ('sheet' — only for a model that takes sheets without copying them), the related
    picture ('related', e.g. the skill). Empty when the asset has no approved front_standard picture (the automatic pick is used)."""
    by_role = {}
    for img in asset.get("images") or []:
        if img.get("status", "approved") in USABLE and img.get("role") in STANDARD_ROLES:
            by_role.setdefault(img["role"], img)
    if "front_standard" not in by_role:
        return []
    out = [(by_role["front_standard"], "character")]
    if sheets and "design_sheet" in by_role:
        out.append((by_role["design_sheet"], "sheet"))
    if sheets and "related" in by_role:                  # only with a model that understands what each picture is for
        out.append((by_role["related"], "related"))
    return out


def _chosen_images(asset: Dict, row: Dict, limit: int = MAX_REFS_PER_CHARACTER, scene: Optional[Dict] = None,
                   name: Optional[str] = None) -> List[Dict]:
    """The pictures to use for this asset: the person's explicit multi-picture choice, else their single-picture choice, else the
    automatic pick (up to `limit`)."""
    by_id = {img["id"]: img for img in asset["images"]}
    ids_field = str(row.get("ref_image_ids") or "").strip()
    if ids_field:
        wanted = [int(x) for x in ids_field.split(",") if x.strip().isdigit()]
        chosen = [by_id[i] for i in wanted if i in by_id]
        if chosen:
            return chosen
    if row.get("ref_image_id") in by_id:
        return [by_id[row["ref_image_id"]]]
    return best_references(asset, limit, scene, name)


def link_characters(conn, project_id: int, names: List[str], scene: Optional[Dict] = None) -> Dict[str, Optional[Dict]]:
    """Character Bible name -> the asset whose pictures are its reference, with the chosen pictures in `refs` (`ref` = refs[0], kept for
    single-picture callers) or None. The person's own choice wins (a chosen asset/pictures, or "no picture" = ref_asset_id 0);
    otherwise the chosen asset that matches the name, with an automatically picked set of pictures."""
    chosen = project_assets(conn, project_id)
    saved = _reference_rows(conn, project_id)
    out: Dict[str, Optional[Dict]] = {}
    for n in names:
        row = saved.get(n) or {}
        asset = None
        if row.get("ref_asset_id") == 0:
            asset = None                                            # explicitly no reference picture
        elif row.get("ref_asset_id"):
            asset = get(conn, row["ref_asset_id"])
            if asset is not None and not asset["images"]:
                asset = None
        else:
            asset = match_character(chosen, n)
        if asset is not None:
            imgs = _chosen_images(asset, row, scene=scene, name=n)
            asset = dict(asset, ref=imgs[0], refs=imgs)
        out[n] = asset
    return out


def set_character_link(conn, project_id: int, name: str, asset_id: Optional[int], image_id: Optional[int] = None,
                       image_ids: Optional[List[int]] = None) -> None:
    """asset_id None = automatic (by name), 0 = no reference picture, else that asset. image_ids (several pictures) wins over
    image_id (one picture); neither given = automatic picture choice for that asset."""
    ids_text = ",".join(str(i) for i in image_ids) if image_ids else None
    conn.execute("UPDATE characters SET ref_asset_id=?, ref_image_id=?, ref_image_ids=? WHERE project_id=? AND name=?",
                (asset_id, image_id, ids_text, project_id, name))
    conn.commit()


def set_outfit(conn, project_id: int, name: str, image_ids: Optional[List[int]]) -> None:
    """The outfit a Character Bible entry wears in this video, as picture(s) from the library (another skin, a costume photo...).
    Empty/None = the outfit of its own reference pictures. The face, hair and body still come from the reference pictures."""
    text = ",".join(str(int(i)) for i in image_ids) if image_ids else None
    conn.execute("UPDATE characters SET outfit_image_ids=? WHERE project_id=? AND name=?", (text, project_id, name))
    conn.commit()


def outfit_images(conn, project_id: int, name: str) -> List[Dict]:
    """[{id, path}] of the outfit pictures chosen for this character (files that exist), in the chosen order."""
    row = conn.execute("SELECT outfit_image_ids FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    ids = [int(x) for x in str((row["outfit_image_ids"] if row else "") or "").split(",") if x.strip().isdigit()]
    out = []
    for i in ids:
        r = conn.execute("SELECT id, path FROM asset_images WHERE id=? AND status IS NOT 'removed'", (i,)).fetchone()
        if r and os.path.exists(resolve(r["path"])):
            out.append({"id": r["id"], "path": resolve(r["path"])})
    return out


def outfit_label(conn, project_id: int, name: str) -> Optional[str]:
    """S14.28: the name of the outfit a character wears in this project ("Kelly đồ bơi", or "Kelly đồ bơi + Áo khoác" for two
    sets), None = the outfit of its own reference pictures (mặc định)."""
    pics = outfit_images(conn, project_id, name)
    if not pics:
        return None
    marks = ",".join("?" * len(pics))
    owners = {r["id"]: r["name"] for r in conn.execute(
        f"SELECT i.id, a.name FROM asset_images i JOIN assets a ON a.id=i.asset_id WHERE i.id IN ({marks})", [x["id"] for x in pics])}
    names: List[str] = []
    for x in pics:
        n = owners.get(x["id"])
        if n and n not in names:
            names.append(n)
    return " + ".join(names) or f"{len(pics)} ảnh"


_FLAT = re.compile(r"no stacked|flat|phẳng|không có (bậc|tầng)", re.I)


def flat_place(conn, project_id: int, scene: Dict) -> bool:
    """S5.4: the scene's place is described as flat ground (the library's layout sentence) — its frames are counted for stacked
    terraces by the free layer-0 check."""
    try:
        place = scene_location(conn, project_id, scene)
    except Exception:  # noqa: BLE001 - no library tables (old data): nothing to compare with
        return False
    return bool(place and _FLAT.search(place.get("description") or ""))


def missing_layout(conn, project_id: int, scene: Dict) -> Optional[str]:
    """S5.2 (kế hoạch sau #8, lỗi 1.4 — the tower drawn as stacked terraces): the scene names a place the library describes (layout in
    words), but the project does not resolve it (not attached, or no picture) — its picture prompt would go WITHOUT the layout sentence.
    A reason to hold the picture job (free), else None."""
    if scene_location(conn, project_id, scene) is not None:
        return None
    text = fold(str(scene.get("location") or ""))
    if not text:
        return None
    row = conn.execute("SELECT game FROM projects WHERE id=?", (project_id,)).fetchone()
    game = row["game"] if row is not None and "game" in row.keys() else None
    for a in conn.execute("SELECT id, name, description, game FROM assets WHERE kind='location' AND project_id IS NULL").fetchall():
        if game and a["game"] and a["game"] != game:
            continue
        if fold(a["name"]) and fold(a["name"]) in text and (a["description"] or "").strip():
            return (f"cảnh ghi nơi \"{scene.get('location')}\" — Kho có bối cảnh \"{a['name']}\" (có mô tả bố cục) nhưng dự án chưa gắn / "
                    "chưa có ảnh, prompt ảnh sẽ thiếu câu bố cục: gắn bối cảnh ở Bước 1 rồi gen lại")
    return None


def scene_location(conn, project_id: int, scene: Dict) -> Optional[Dict]:
    """The place a scene is set in: the resource the scene names by id (`location_asset`, chosen by the Director or by hand), else a
    chosen place whose name appears in the scene's `location` text. None when neither has a picture."""
    lid = scene.get("location_asset")
    if isinstance(lid, int) and not isinstance(lid, bool) and lid > 0:
        a = get(conn, lid)
        if a is not None and a["kind"] == "location" and a["images"]:
            return a
    place = fold(str(scene.get("location") or ""))
    if place:
        for a in project_assets(conn, project_id):
            if a["kind"] == "location" and a["images"] and fold(a["name"]) and fold(a["name"]) in place:
                return a
    return None


# ---- T1: the standard profile of a character, kept in the library (one source for every project) -------------------------------
PROFILE_KEYS = ("identity", "must_keep", "may_change", "forbidden", "height_m", "build")


def get_profile(conn, asset_id: int) -> Dict:
    row = conn.execute("SELECT profile FROM assets WHERE id=?", (asset_id,)).fetchone()
    try:
        return json.loads(row["profile"]) if row and row["profile"] else {}
    except ValueError:
        return {}


def set_profile(conn, asset_id: int, data: Dict, approved: bool, reason: Optional[str] = None) -> Dict:
    """Save the standard profile (identity words, Character Lock, real height, build). Only an approved profile is inherited.
    The change log (`history`) is kept; `reason` adds a dated entry (kế hoạch V4 4.4: every change of an approved profile says why).
    The short forms (`digest`, core/profile_digest.py) are made again from the new text the next time they are asked for."""
    old = get_profile(conn, asset_id)
    def text(v) -> str:                                  # a model may answer a list: one line of "a; b", not "['a', 'b']"
        return "; ".join(str(x).strip() for x in v if str(x).strip()) if isinstance(v, (list, tuple)) else str(v or "").strip()
    clean: Dict = {k: text(data.get(k)) for k in PROFILE_KEYS if k != "height_m"}
    history = list(old.get("history") or [])
    if reason:
        import datetime
        history.append({"date": datetime.date.today().isoformat(), "why": reason.strip()})
    if history:
        clean["history"] = history
    try:
        h = float(data.get("height_m") or 0)
    except (TypeError, ValueError):
        h = 0
    clean["height_m"] = round(h, 2) if 0.2 <= h <= 30 else None
    clean["approved"] = bool(approved)
    conn.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps(clean, ensure_ascii=False), asset_id))
    conn.commit()
    return clean


def standard_for(conn, project_id: int, name: str) -> Optional[Dict]:
    """The approved library profile of the resource a project character is linked to, or None. It wins over the project's own Lock
    (which the Director or a copied project may have written wrong — GĐ6 R1/A3)."""
    asset = link_characters(conn, project_id, [name]).get(name)
    if asset is None:
        return None
    prof = get_profile(conn, asset["id"])
    return dict(prof, asset=asset["name"]) if prof.get("approved") else None


# F1-B (09/10, #24 shot 5): a rule written for people ("Natural human eyes, no glowing eyes.") was sent for the well creature the
# Director wrote with "eyes: glowing red". Characters have no "kind" column — a creature is told by the words of its name / profile.
# Accents kept (NFC, no folding): "ma" must not match "màu"; English words whole (\b): "ghostwriter" is not a ghost.
_NON_HUMAN = re.compile(
    r"\b(?:creatures?|demons?|demonic|ghosts?|ghostly|monsters?|monstrous|wraiths?|phantoms?|spect(?:er|re)s?|ghouls?|zombies?|undead"
    r"|vampires?|apparitions?|yêu nữ|yêu quái|quỷ|ma nữ|ma quỷ|ma quái|bóng ma|con ma|hồn ma|thây ma|tà linh|ác linh|oan hồn|quái vật"
    r"|xác sống|faceless|sinh vật)\b", re.IGNORECASE)     # F1 sửa #1: the one list (prompt_formula uses it too)


def looks_non_human(text: str) -> bool:
    """The words describe a creature / ghost / monster rather than a person."""
    return bool(_NON_HUMAN.search(unicodedata.normalize("NFC", str(text or ""))))


def is_human(conn, project_id: int, name: str) -> bool:
    """A project character is a person unless its name, profile (description, lock rules) or its library resource (a pet, or a
    description of a creature) says otherwise. Unknown name: decided by the name alone."""
    texts = [str(name or "")]
    row = conn.execute("SELECT * FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    if row is not None:
        keys = row.keys()
        texts += [str(row[k] or "") for k in ("description", "lock_rules") if k in keys]
    try:
        asset = link_characters(conn, project_id, [name]).get(name)
    except Exception:  # noqa: BLE001 - no library tables (old test data): the profile words decide
        asset = None
    if asset is not None:
        if asset.get("kind") == "pet":
            return False
        texts += [str(asset.get("name") or ""), str(asset.get("aliases") or ""), str(asset.get("description") or "")]
    return not any(looks_non_human(t) for t in texts)


def cast_humans(conn, project_id: int, names) -> Dict[str, bool]:
    """{name: is a person} for the characters of a shot."""
    return {str(n): is_human(conn, project_id, str(n)) for n in dict.fromkeys(names or [])}


def location_plate(conn, place: Dict, scene: Optional[Dict]) -> Optional[Dict]:
    """B2/B3: the picture of a place that may be sent to the image model as pixels — an approved EMPTY background taken from the shot's
    own kind of camera (eye level / low / high), and only for a wide shot. A map screenshot from above, a picture whose camera nobody
    set, or any background for a close/medium shot is never sent: the model copies its camera and its tiny people (GĐ6, R7). The place
    then reaches the model as words (location_text)."""
    if shot_size(scene) not in _WIDE:
        return None
    angle = str((scene or {}).get("angle") or "eye")
    want = "high_angle" if angle in ("high", "overhead") else "low_angle" if angle == "low" else "eye_level"
    return next((i for i in place["images"] if i.get("role") == want), None)


def location_landmark(conn, place: Dict, scene: Optional[Dict]) -> Optional[Dict]:
    """A place's LANDMARK picture (role "detail", approved) for a close or medium shot, where no background plate may go: the model sees
    what the landmark really looks like and draws it in the background at the shot's own camera. The user (2026-09-25): the Free Fire
    Clock Tower came out as a generic European tower when the place reached the model only as words. The note tells the model to copy
    shape, materials and colours only — never the picture's camera, framing, time of day or light (R7)."""
    if shot_size(scene) in _WIDE or shot_size(scene) == "ECU":
        return None                                  # a wide shot gets the eye-level plate (location_plate) or words; an ECU has no background
    # 30/09 (thử #11): the 3D Kho of #263 had its indoor room as "detail" and it went out as the Clock Tower's landmark — the end frame
    # moved the shot indoors. Indoor pictures have their own role; without a detail picture the low-angle one (the landmark seen
    # from below) stands in.
    return (next((i for i in place["images"] if i.get("role") == "detail"), None)
            or next((i for i in place["images"] if i.get("role") == "low_angle"), None))


def location_text(conn, place: Dict, for_llm: bool = False) -> str:
    """B1: the place in words for the image prompt — its description and, from the set analyses already read or rendered, the real
    heights of its landmarks (so people get the right size next to a wall or a door without copying a picture's camera).
    for_llm=True (the QC agent's brief, read by Claude): the website part of the description goes wrapped by prompts.external_block
    (rà bảo mật 06/10); the image model gets plain words (a tag and a Vietnamese note would only pollute the picture prompt)."""
    marks, light = _landmark_heights(conn, place)
    head = (place.get("description") or "").split("[AI đọc ảnh]")[0]
    desc = re.sub(r"\s+", " ", head).strip()[:600]   # S5.2: 300 cut the tower's "No stacked terraces, no fortress." off its layout sentence
    web_part = ""
    own, web = split_web(head)
    if for_llm and web:
        from .prompts import external_block
        desc = re.sub(r"\s+", " ", own).strip()[:600]
        web_part = external_block("ff.garena.com — mô tả bối cảnh", re.sub(r"\s+", " ", web).strip()[:max(600 - len(desc), 120)])
    bits = [f"Setting: {place['name']}" + (f" — {desc}" if desc else "")]
    if marks:
        bits.append(_sizes_sentence(marks))
    if light and not light.startswith("3D render"):
        bits.append(f"Light: {light[:120]}")
    return ". ".join(bits) + "." + (f"\n{web_part}" if web_part else "")


def _landmark_heights(conn, place: Dict) -> Tuple[List[Tuple[str, float]], str]:
    """([(landmark, real height m)], light) read from the set analyses of the place's pictures."""
    marks, light = [], ""
    for img in place.get("images") or []:
        try:
            with open(img["path"], "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            continue
        row = conn.execute("SELECT data FROM set_analyses WHERE sha256=?", (sha,)).fetchone()
        data = json.loads(row["data"]) if row else {}
        light = light or str(data.get("light") or "")
        for lm in data.get("landmarks") or []:
            name, h = str(lm.get("name") or "").strip(), lm.get("height_m")
            if name and isinstance(h, (int, float)) and name not in [m[0] for m in marks]:
                marks.append((name, float(h)))
    return marks, light


def _sizes_sentence(marks) -> str:
    return ("Real sizes: " + ", ".join(f"{n} about {h:g} m tall" for n, h in marks[:6])
            + "; an adult is about 1.7 m, keep people in proportion to these")


RENDER_TAG = "{{place_render_image}}"   # replaced by " (Image N)" once the pictures really sent are known (runner._finish_args)


def render_place_text(conn, place: Dict, tag: str = RENDER_TAG) -> str:
    """F1-B (09/10, #24): the place sentence of a shot that HAS its 3D render attached. The place's general description ("… stone
    plaza; red-roof houses, grass, palms, sea around") pulled the picture away from the render, so the background is locked to the
    render the way #22's approved prompts did — what is right, never a list of what is forbidden (bài học L2). The real landmark heights
    stay (people's size); the library picture's light does not (the render and the scene light decide it)."""
    marks, _light = _landmark_heights(conn, place)
    bits = [f"Setting: {place['name']}",
            f"Background: exactly the 3D render picture of this place{tag} (same camera and spot) — it decides the architecture, the "
            "landmarks and where they sit in the frame; keep the scale of the objects as in that picture"]
    if marks:
        bits.append(_sizes_sentence(marks))
    return ". ".join(bits) + "."


def gap_severity(gap: str) -> str:
    """A library picture whose file is gone is a fault (warn); a character that simply has no picture was already warned about at the
    Bible gate (autopilot / the Gen ảnh button), so each job only notes it (info) instead of turning every stage yellow."""
    return "warn" if "mất file" in gap else "info"


def reference_gaps(conn, project_id: int, scene: Dict) -> List[str]:
    """Luật 1 at generation time: what the picture of this shot will be drawn WITHOUT — a character with no reference picture (drawn from
    words), library pictures whose file is gone. Vietnamese sentences for the job's diag; empty = nothing missing."""
    names = [str(n) for n in scene.get("characters") or []]
    if not names:
        return []
    from . import looks
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    scene = dict(scene, _look=looks.asset_look(proj)) if proj is not None else scene
    linked = link_characters(conn, project_id, names, scene)
    saved = _reference_rows(conn, project_id)
    out = []
    for name in dict.fromkeys(names):
        a = linked.get(name)
        if a is None and not outfit_images(conn, project_id, name):
            why = " (bạn chọn không dùng ảnh)" if (saved.get(name) or {}).get("ref_asset_id") == 0 else ""
            out.append(f"nhân vật {name} không có ảnh tham chiếu{why} — vẽ theo chữ, dễ lệch thiết kế")
        elif a is not None and a.get("missing"):
            out.append(f"ảnh tài nguyên của {name} mất file ({len(a['missing'])} ảnh: "
                       + ", ".join(os.path.basename(x) for x in a["missing"][:3]) + ") — bỏ qua, chỉ gửi ảnh còn lại")
    return out


def scene_references(conn, project_id: int, scene: Dict, limit: int = MAX_REFERENCES, reserve: int = 0,
                     sheets: bool = False) -> List[Dict]:
    """Reference pictures for one scene: the reference picture(s) of each character in the scene, then its place, then any other
    chosen resource the scene names. [{path, label, role}]
    The place always keeps its slot (a crowded scene used to fill every slot with faces and lose the background), and `reserve`
    slots are left free for the caller (e.g. the previous storyboard frame). Every person gets 1 picture first, then a 2nd angle
    goes to the people listed first while slots remain; when even 1 each does not fit, the people listed first win."""
    chosen = project_assets(conn, project_id)
    refs: List[Dict] = []
    names = [str(n) for n in scene.get("characters") or []]
    from . import looks
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    scene = dict(scene, _look=looks.asset_look(proj)) if proj is not None else scene
    linked = link_characters(conn, project_id, names, scene) if names else {}
    people, seen, caps = [], set(), []             # (label, [(path, role)...]) per person: face first, then outfit, then 2nd angle
    hand = _reference_rows(conn, project_id) if sheets else {}
    for name in names:
        a = linked.get(name)
        label = a["name"] if a else name
        outfit = outfit_images(conn, project_id, name)
        if label in seen or not (a or outfit):
            continue
        seen.add(label)
        chosen_by_hand = any(str((hand.get(name) or {}).get(k) or "") for k in ("ref_image_ids", "ref_image_id"))   # the person's pick wins
        standard = standard_set(a, sheets) if a and sheets and not chosen_by_hand else []
        if standard:                               # the standard 3 pictures: front (identity + true colors), sheet, related
            own = [(img["path"], role) for img, role in standard]
            side = shot_roles(scene, name)[0]
            seen_pic = view_picture(a, side) if side in ("back", "side") else None
            if seen_pic:                           # 01/10: the shot shows this person's back / side → that side right after the front
                own.insert(1, (seen_pic["path"], "character"))
            caps.append(len(STANDARD_ROLES) + (1 if seen_pic else 0))
        else:
            own = [(img["path"], "character") for img in (a["refs"] if a else [])]
            caps.append(MAX_REFS_PER_CHARACTER)
        people.append((label, own[:1] + [(img["path"], "outfit") for img in outfit[:1]] + own[1:]))
    place = scene_location(conn, project_id, scene)
    from .plate_choice import landmark_off_frame
    away = landmark_off_frame(scene)               # 08/10 (#24 shot 4): camera turned away from the landmark → no picture of it
    loc = location_plate(conn, place, scene) if place and not away else None
    mark = location_landmark(conn, place, scene) if place and loc is None and not away else None
    if mark is not None:
        loc = dict(mark, _landmark=True)
    room = max(limit - reserve - (1 if loc else 0), 0)
    counts = [0] * len(people)                     # 1 picture each first, then a 2nd (3rd) picture for the people listed first while room lasts
    for n in range(1, max(caps, default=0) + 1):
        for i, (_, items) in enumerate(people):
            if sum(counts) < room and len(items) >= n and n <= caps[i]:
                counts[i] = n
    for (label, items), k in zip(people, counts):  # grouped per person, so the note reads "Images 1/2 show KELLY"
        refs += [{"path": path, "label": label, "role": role} for path, role in items[:k]]
    if loc and len(refs) < limit - reserve:
        refs.append({"path": loc["path"], "label": place["name"], "role": "landmark" if loc.get("_landmark") else "location"})
    limit = limit - reserve
    # every other chosen resource (weapon, prop, pet, place) that the scene names is a reference too
    blob = " " + fold(" ".join(str(scene.get(k) or "") for k in ("text", "image_prompt", "location"))) + " "
    cast = {fold(n) for n in names}
    people_names = {fold(r["name"]) for r in conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,))} | {
        fold(n) for x in chosen if x["kind"] == "character" for n in names_of(x)}
    for a in chosen:
        if len(refs) >= limit:
            break
        if a["kind"] not in ("weapon", "prop", "pet", "location", "outfit") or not a["images"] or any(r["label"] == a["name"] for r in refs):
            continue
        if a["kind"] == "outfit" and (any(r["path"] == im["path"] for r in refs for im in a["images"])
                                      or fold(a["name"]) in people_names):
            continue          # already sent as the outfit a person in the shot wears / named like a person (S14.28: "Kelly" bơi)
        if place is not None and a["id"] == place["id"]:
            continue                                          # the scene's own place: already decided above (plate or words)
        if away and a["kind"] == "location":
            continue                                          # 08/10: another picture of a place would pull a landmark in too
        keys = [fold(n) for n in names_of(a) if len(fold(n)) >= 3 and fold(n) not in cast]
        if any(" " + k + " " in blob for k in keys):
            pic = location_plate(conn, a, scene) if a["kind"] == "location" else best_reference(a)
            if pic is not None:
                refs.append({"path": pic["path"], "label": a["name"],     # 07/10: an outfit named by a shot with nobody wearing it
                             "role": {"location": "location", "outfit": "outfit_object"}.get(a["kind"], "object")})   # (on the bed)
    return refs


def _outfit_strip() -> bool:
    """KLD-7 (08/10, feature outfit_strip_model, off until a cheap one-shot test): the OUTFIT note also drops the model wearing it."""
    from . import features
    return features.on("outfit_strip_model")


def reference_note(refs: List[Dict]) -> str:
    """Words that tell the image model what each attached picture is for. Several pictures of the same person (different angles /
    a close-up) are grouped: "Images 1-2 show KELLY..." instead of repeating a separate, disconnected line per picture."""
    groups: List[Dict] = []
    dressed = {r["label"] for r in refs if r["role"] == "outfit"}
    sheeted = {r["label"] for r in refs if r["role"] == "sheet"}
    for i, r in enumerate(refs, 1):
        if groups and groups[-1]["label"] == r["label"] and groups[-1]["role"] == r["role"]:
            groups[-1]["nums"].append(i)
        else:
            groups.append({"label": r["label"], "role": r["role"], "nums": [i]})
    bits, people = [], 0
    for g in groups:
        nums = g["nums"]
        tag = f"Image {nums[0]}" if len(nums) == 1 else f"Images {'/'.join(map(str, nums))}"
        if g["role"] == "layout":
            from .layout import layout_note
            r = refs[nums[0] - 1]
            figures = r.get("people") or []
            text = layout_note(figures, has_cutouts=bool(figures) and all(x.get("cutout") for x in figures)).strip()
            if r.get("redraw_note"):
                text += f" The background of the layout has the wrong camera angle and must be redrawn: {r['redraw_note']}."
            bits.append(f"{tag} is the LAYOUT. " + text.replace("The LAYOUT image is", "It is"))
        elif g["role"] == "location":
            bits.append(f"{tag} is the EMPTY background of {g['label']}: copy its architecture, materials and colours only — it does not "
                        "set the people, their size or their position (those come from the scene text)")
        elif g["role"] == "place_render":
            bits.append(f"{tag} is the EXACT background of this shot: a 3D render of the real {g['label']} from the game map, taken from this "
                        "shot's own camera (same position, height, lens and direction), with nobody in it. Keep its architecture and layout "
                        "exactly — the same buildings in the same places, the same number of floors, roofs, windows, stairs, walls, trees, "
                        "the same horizon line and perspective — and draw the people INTO it at the size and place the scene text gives; "
                        "improve only light, texture detail and atmosphere in the game's style; never move, add or remove a building")
        elif g["role"] == "skill_phase":
            from . import skill_dossier
            bits.append(skill_dossier.reference_note(tag, g["label"]))
        elif g["role"] == "landmark":
            bits.append(f"{tag} shows the real LANDMARK of {g['label']} (from the game): wherever it appears in the background, draw it with "
                        "exactly this shape, proportions, materials and colours — but NOT this picture's camera angle, framing, time of "
                        "day or lighting (those come from the scene text); it may be small, blurred or partly out of frame")
        elif g["role"] == "outfit":
            bits.append(f"{tag} {'shows' if len(nums) == 1 else 'show'} the OUTFIT {g['label']} wears in this video: dress {g['label']} "
                        "exactly in these clothes (garments, colours, accessories); take only the face, hair and body build from "
                        f"{g['label']}'s own reference image, never the clothes shown there"
                        + ("; ignore the hair, face and body of any person modelling these clothes; wear each accessory exactly as the "
                           "picture shows it" if _outfit_strip() else ""))
        elif g["role"] == "outfit_object":
            bits.append(f"{tag} is the outfit {g['label']} shown in this shot without anyone wearing it: draw exactly these garments — "
                        "every print and its drawing, colours, cap, mask and shoes — only laid out as the scene text says")
        elif g["role"] == "object":
            bits.append(f"{tag} is the object {g['label']}: draw it exactly like this whenever it appears")
        elif g["role"] == "sheet":
            bits.append(f"{tag} is the character design sheet of {g['label']} (front / three-quarter / side / back views and details): use it "
                        f"only to know how {g['label']} looks from every side — do NOT copy its layout, labels, color swatches or its several "
                        f"poses; where a color differs from {g['label']}'s front picture, the front picture is right")
        elif g["role"] == "related":
            bits.append(f"{tag} is related material of {g['label']} (e.g. their skill icon or skill in action): use it only for what the "
                        f"skill / effect / item looks like when the scene shows it — never draw it as an icon, a UI element or text, and "
                        f"never take {g['label']}'s appearance from it")
        elif g["role"] == "same_frame":            # 07/10: the shot right before, when this shot keeps its frame (cut on the spot)
            bits.append(f"{tag} is the shot RIGHT BEFORE this one: keep exactly its camera position, lens, framing and shot size, the "
                        "character's spot and pose direction, the background and the light — change only what this shot's text says "
                        "(e.g. the clothes)")
        elif g["role"] == "previous_scene":
            bits.append(f"{tag} is the PREVIOUS scene in this sequence (storyboard continuity): keep the same render style, "
                        "color palette, lighting mood and level of detail as this image, and keep any character/prop/location "
                        "already fixed by the other reference images exactly as those say; it is the same place, so keep its layout "
                        "and keep each person on the same side of the frame unless the blocking says they moved — but draw a NEW "
                        "moment in time (new pose, action, camera angle or framing), never a copy of this image")
        else:
            people += 1
            angles = " (different angles/details of the same person)" if len(nums) > 1 else ""
            verb = "show" if len(nums) > 1 else "is"
            keep = ("same face, hairstyle and hair color, body build; the clothes come from the OUTFIT image, not from this one"
                    if g["label"] in dressed else "same face, hairstyle and hair color, outfit and its colors, body build")
            front = (" — this front picture is the standard: its colors are the true colors" if g["label"] in sheeted else "")
            bits.append(f"{tag} {verb} {g['label']}{angles}: the person called {g['label']} in the scene must be exactly this person "
                        f"({keep}){front}")
    rule = ""
    if people:
        rule = (" Each person keeps ONLY the look of their own reference image(s): never swap or blend faces, hair or outfits between people, and ignore "
                "any clothing or hair words in the scene text that contradict the reference images. The people are different individuals."
                " The reference images set who each person is, not the pose, the camera or how big they are in the frame: take those from "
                "the scene text.")                                   # T5: a picture's job and what it does not control
        if people > 1:
            rule += (" Before drawing, pick ONE unmistakable visual anchor per named person from their reference image (hair color/style, "
                     "headwear, or a distinct clothing color) and keep checking each person against their own anchor as you draw the rest of "
                     "the scene. If two people would otherwise look similar in age, build or pose, exaggerate their point of difference "
                     "(e.g. hair color vs. no color) rather than letting them drift toward the same look.")
    return "Reference images are attached, grouped per named subject. " + "; ".join(bits) + "." + rule + " "


def _news_for(conn, items: List[Dict], limit: int = 3, around: int = 170) -> str:
    """Short passages of the official news that mention the chosen characters / pets / places (newest first), so the video follows what
    the game itself says about them. Empty when no news was read or nothing matches. OFF unless FF_NEWS_IN_CONTEXT=1: the news read so far
    is version notes (prices, balance changes), which is more noise than background for a script."""
    if os.environ.get("FF_NEWS_IN_CONTEXT", "0") != "1":
        return ""
    try:
        if not conn.execute("SELECT 1 FROM ff_articles LIMIT 1").fetchone():
            return ""
    except Exception:  # noqa: BLE001 - an old database without the table
        return ""
    lines, used = [], set()
    for a in items:
        if a["kind"] not in ("character", "pet", "location") or len(a["name"]) < 4:
            continue
        row = conn.execute("SELECT id, title, text FROM ff_articles WHERE text LIKE ? ORDER BY published DESC LIMIT 1", (f"%{a['name']}%",)).fetchone()
        if row is None or row["id"] in used:
            continue
        at = row["text"].lower().find(a["name"].lower())
        snippet = " ".join(row["text"][max(at - around, 0): at + len(a["name"]) + around].split())
        lines.append(f"- {a['name']} — theo “{row['title']}”: …{snippet}…")
        used.add(row["id"])
        if len(lines) >= limit:
            break
    if not lines:
        return ""
    from .prompts import external_block                                 # S14.5 C2b: website text is reference, not instruction
    return ("\n\n## Tin tức chính thức liên quan (tham khảo bối cảnh, không bắt buộc)\n"
            + external_block("ff.garena.com — tin tức", "\n".join(lines)) + "\n")


CONTEXT_DESC_CHARS = 320

# Automatic text blocks kept inside a library description, each owned by one tool. The person's own text comes first and is never touched.
BLOCK_MARKS = ("[ff.garena.com]", "[AI đọc ảnh]", "[Phân tích video kỹ năng]")


def replace_block(description: str, mark: str, text: str) -> str:
    """Put `text` in the block `mark` of a description and leave the person's text and every OTHER tool's block as they are
    (02/10: each tool used to cut the description at its own mark, so writing the ff.garena.com block erased the AI-read and video blocks
    after it). Blocks are written back in the fixed order of BLOCK_MARKS."""
    pattern = "(" + "|".join(re.escape(m) for m in BLOCK_MARKS) + ")"
    parts = re.split(pattern, description or "")
    base, blocks = parts[0].rstrip(), {}
    for m, body in zip(parts[1::2], parts[2::2]):
        blocks[m] = body.strip()
    blocks[mark] = text.strip()
    out = [base] if base else []
    out += [f"{m} {blocks[m]}" for m in BLOCK_MARKS if blocks.get(m)]
    return "\n\n".join(out)


WEB_MARK = BLOCK_MARKS[0]           # the block written by core/ff_site.py from the website


def split_web(description: str):
    """(the description without the website block, the website block's text) — S14.5 C2b: the person's words and our own tools'
    blocks stay as they are; only the website text is sent wrapped as outside material."""
    parts = re.split("(" + "|".join(re.escape(m) for m in BLOCK_MARKS) + ")", description or "")
    own, web = ([parts[0].rstrip()] if parts[0].strip() else []), ""
    for m, body in zip(parts[1::2], parts[2::2]):
        if m == WEB_MARK:
            web = body.strip()
        elif body.strip():
            own.append(f"{m} {body.strip()}")
    return "\n\n".join(own), web


def _brief(text: str, limit: int = CONTEXT_DESC_CHARS) -> str:
    """A library description for the Director prompt: sentences in order, a repeated sentence once, cut at a sentence end near `limit`
    (H3: the ff.garena.com backstories repeated a whole paragraph — 8,5k characters for 4 assets of "ANH CHỌN AI?"; the looks come
    from the pictures and the approved profile, the skills from their own block)."""
    seen, out, size = set(), [], 0
    for s in re.split(r"(?<=[.!?…])\s+", re.sub(r"\s+", " ", text or "").strip()):
        key = s.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if size and size + len(s) > limit:
            out.append("…")
            break
        out.append(s)
        size += len(s) + 1
    return " ".join(out)


def context_text(conn, project_id: int) -> str:
    """Block for the Director prompt; empty when the project has no chosen assets."""
    items = project_assets(conn, project_id)
    if not items:
        return ""
    from .prompts import external_block
    lines, web_lines = [], []
    for a in items:
        also = f" (tên khác: {a['aliases']})" if a["aliases"].strip() else ""
        pics = f" — có {len(a['images'])} ảnh tham khảo" if a["images"] else ""
        own, web = split_web(a["description"])
        own_brief = _brief(own) if own else ""
        desc = f": {own_brief}" if own_brief else ""
        if web:                                          # same total budget as before: the website part gets what the own text left
            web_lines.append(f"- {a['name']}: {_brief(web, max(CONTEXT_DESC_CHARS - len(own_brief), 120))}")
        ident = f" (id {a['id']})" if a["kind"] == "location" and a["images"] else ""
        worn = " — trang phục để nhân vật mặc, không phải nhân vật (không thêm vào Character Bible)" if a["kind"] == "outfit" else ""
        lines.append(f"- [{a['kind_label']}] **{a['name']}**{ident}{also}{desc}{pics}{worn}")
    news = _news_for(conn, items)
    site = ("\n\n## Mô tả từ website chính thức (ff.garena.com) của các mục trên\n"
            + external_block("ff.garena.com — mô tả mục Kho", "\n".join(web_lines))) if web_lines else ""
    return ("# Tài nguyên có sẵn cho dự án này (BẮT BUỘC dùng)\n" + "\n".join(lines) + site + news +
            "\nDùng đúng tên và thiết kế ở trên cho Character Bible và các cảnh; không tự bịa lại ngoại hình của những mục này. "
            "Chỉ thêm nhân vật/đạo cụ mới khi kịch bản cần mà danh sách không có. "
            "Cảnh diễn ra ở một địa điểm có `id` ở trên thì ghi đúng số đó vào `location_asset` của cảnh (ảnh địa điểm sẽ được "
            "gửi kèm khi gen ảnh); không có địa điểm nào khớp thì để `location_asset` là null.")


# ---- keeping the library in step with a folder ---------------------------------------------------------------------
DEFAULT_IGNORE = "khung, thumb, thumbnail, backup"


def _stem_name(filename: str) -> str:
    stem = os.path.splitext(filename)[0]
    words = [w for w in re.split(r"[\s_\-\.]+", stem) if w]
    while words and (words[-1].isdigit() or fold(words[-1]) in _NOISE):
        words.pop()
    return " ".join(words) or stem


def _spread(items: List[str], n: int) -> List[str]:
    """n items evenly spaced over the sorted list (first and last included)."""
    items = sorted(items)
    if len(items) <= n:
        return items
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)]


def _alias_after_dash(name: str) -> str:
    """'Khu vực - Dock' -> 'Dock' (what a script is likely to call it)."""
    parts = re.split(r"\s+-\s+", name or "")
    return parts[-1].strip() if len(parts) > 1 else ""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ignored(path_parts: List[str], words: List[str]) -> bool:
    """A folder or file name that contains one of the words (whole word, accents ignored) is left out."""
    for part in path_parts:
        padded = " " + fold(re.sub(r"[_\-\.]+", " ", os.path.splitext(part)[0])) + " "
        if any(" " + w + " " in padded for w in words):
            return True
    return False


def _words(text: str) -> List[str]:
    return [fold(w) for w in re.split(r"[,;\n]+", text or "") if fold(w)]


def sync_folder(conn, folder: str, game: str, kind: str = "character", created_by: Optional[str] = None,
                ignore: str = DEFAULT_IGNORE, remove_missing: bool = False) -> Dict:
    """Make the shared library of `game` match a folder of pictures, re-runnable at any time.

    Layouts understood (they can be mixed):
      folder/Lyra_front.png, Lyra_back.png      -> asset "Lyra" (trailing numbers and words like front/back/khung are dropped)
      folder/Lyra/1.png, 2.png                   -> asset "Lyra" (the folder name)
      folder/Nhân vật/..., Vũ khí/..., Bản đồ/...  -> the folder name chooses the kind
    Every picture remembers the file it came from and its fingerprint, so a second run only does the difference:
      new file -> added;  same file changed -> replaced;  same picture under another name/place -> just re-linked;
      unchanged -> skipped;  file gone from the folder -> reported (deleted only when remove_missing).
    Names, descriptions and other edits made in the dashboard are never overwritten."""
    if not os.path.isdir(folder):
        raise AssetError("Không tìm thấy thư mục này trên máy chạy Dashboard")
    words = _words(ignore)
    rep = {"created": [], "added": 0, "updated": 0, "unchanged": 0, "moved": 0, "skipped": [], "ignored": 0, "missing": [], "removed": 0}
    seen: set = set()

    def asset_for(name: str, k: str, description: str = "", aliases: str = "") -> int:
        row = conn.execute("SELECT id FROM assets WHERE game=? AND kind=? AND lower(name)=lower(?) AND project_id IS NULL",
                           (game, k, name)).fetchone()
        row = row or find_same(conn, game, k, name)                    # S14.43B: 'Mr Waggor.png' joins 'Mr.Waggor', never a twin
        if row:
            return row["id"]
        try:
            aid = create(conn, game, k, name, description, aliases, created_by=created_by)
        except AssetError as e:                                         # one refused name never stops the whole source
            rep["skipped"].append((name, str(e)))
            return None
        rep["created"].append(name)
        return aid

    def take_untracked(name: str, k: str, files: List[str], description: str, aliases: str) -> None:
        """Pictures that are also shown elsewhere (the overview of a map re-uses the first picture of each area): kept without
        remembering their file, so the area keeps its own record of the same file; a re-run recognises them by fingerprint."""
        aid = None
        for path in files:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError as e:
                rep["skipped"].append((path, str(e.strerror or e)))
                continue
            aid = aid or asset_for(name, k, description, aliases)
            if not aid:
                continue
            sha = _sha(data)
            if conn.execute("SELECT 1 FROM asset_images WHERE asset_id=? AND sha256=?", (aid, sha)).fetchone():
                continue
            try:
                add_image(conn, aid, os.path.basename(path), data, sha256=sha, status="pending")    # G2: a person looks first
                rep["added"] += 1
            except AssetError as e:
                rep["skipped"].append((path, str(e)))

    def take(name: str, k: str, files: List[str], description: str = "", aliases: str = "") -> None:
        aid = None
        for path in files:
            key = os.path.abspath(path)
            try:
                st = os.stat(path)
            except OSError as e:
                rep["skipped"].append((path, str(e.strerror or e)))
                continue
            seen.add(key)
            known = conn.execute("SELECT i.id, i.sha256, i.path, i.asset_id, i.src_size, i.src_mtime FROM asset_images i"
                                 " JOIN assets a ON a.id=i.asset_id WHERE i.src_path=? AND a.game=?", (key, game)).fetchone()
            if known and known["src_size"] == st.st_size and known["src_mtime"] == int(st.st_mtime):
                rep["unchanged"] += 1                                          # same size and date: no need to read the file at all
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError as e:
                rep["skipped"].append((path, str(e.strerror or e)))
                continue
            sha = _sha(data)
            if known and known["sha256"] == sha:
                conn.execute("UPDATE asset_images SET src_size=?, src_mtime=? WHERE id=?", (st.st_size, int(st.st_mtime), known["id"]))
                conn.commit()
                rep["unchanged"] += 1
                continue
            if known:                                                       # the same file, edited: replace the stored picture
                try:
                    stored = data if len(data) <= MAX_IMAGE_BYTES else _shrink(data, os.path.basename(path))[0]
                except AssetError as e:
                    rep["skipped"].append((path, str(e)))
                    continue
                with open(known["path"], "wb") as f:
                    f.write(stored)
                conn.execute("UPDATE asset_images SET sha256=?, src_size=?, src_mtime=? WHERE id=?",
                             (sha, st.st_size, int(st.st_mtime), known["id"]))
                conn.commit()
                rep["updated"] += 1
                continue
            aid = aid or asset_for(name, k, description, aliases)
            if not aid:
                continue
            twin = conn.execute("SELECT id FROM asset_images WHERE asset_id=? AND sha256=?", (aid, sha)).fetchone()
            if twin:                                                        # same picture, new name or place
                conn.execute("UPDATE asset_images SET src_path=? WHERE id=?", (key, twin["id"]))
                conn.commit()
                rep["moved"] += 1
                continue
            try:
                add_image(conn, aid, os.path.basename(path), data, src_path=key, sha256=sha, src_size=st.st_size, src_mtime=int(st.st_mtime),
                          status="pending")                                  # G2: a person looks first
                rep["added"] += 1
            except AssetError as e:
                rep["skipped"].append((path, str(e)))

    def walk(directory: str, k: str, top: bool, parts: List[str]) -> None:
        entries = sorted(os.listdir(directory))
        files = [e for e in entries if os.path.isfile(os.path.join(directory, e)) and e.lower().endswith(IMAGE_EXT)]
        groups: Dict[str, List[str]] = {}
        # "Lyra/1.png, 2.png": the folder is the name. "Map/burger 2.png, khu nha kinh 4.png": every picture names its own thing.
        folder_is_the_name = kind_from_word(os.path.basename(directory)) is None and all(
            re.fullmatch(r"(img[_ -]?)?\d+|\d+[_ -]?\d*|[a-z]{0,3}\d{1,4}", fold(os.path.splitext(e)[0]).replace(" ", "")) for e in files)
        for e in files:
            if _ignored(parts + [e], words):
                rep["ignored"] += 1
                continue
            key = os.path.basename(directory) if (not top and folder_is_the_name) else _stem_name(e)
            groups.setdefault(key, []).append(os.path.join(directory, e))
        parent = os.path.basename(directory) if not top else ""
        for name, paths in groups.items():
            if len(paths) > MAX_IMAGES_PER_ASSET:      # a folder with 66 shots: take an even spread, not the first six (often near-identical)
                paths = _spread(paths, MAX_IMAGES_PER_ASSET)
            # a picture folder that lives inside another folder is an "area" of it: remember where it belongs
            from_folder = not top and folder_is_the_name and name == parent
            desc = f"Thuộc: {os.path.basename(os.path.dirname(directory))}" if from_folder and len(parts) >= 2 else ""
            take(name, k, paths, desc, _alias_after_dash(name) if from_folder else "")
        subdirs = [e for e in entries if os.path.isdir(os.path.join(directory, e)) and not _ignored(parts + [e], words)]
        if not top and not files and len(subdirs) >= 2:
            overview(directory, k, subdirs, parts)
        for e in subdirs:
            walk(os.path.join(directory, e), kind_from_word(e) or k, False, parts + [e])

    def overview(directory: str, k: str, subdirs: List[str], parts: List[str]) -> None:
        """A folder made only of sub-folders of pictures (a map made of areas) also gets one asset of its own, with the first
        picture of up to 6 areas and the list of areas in its description, so a script that names the whole map finds it."""
        firsts, names = [], []
        for e in subdirs:
            pics = sorted(x for x in os.listdir(os.path.join(directory, e)) if x.lower().endswith(IMAGE_EXT))
            if pics:
                names.append(e)
                if len(firsts) < MAX_IMAGES_PER_ASSET:
                    firsts.append(os.path.join(directory, e, pics[0]))
        if len(names) >= 2:
            label = re.sub(r"^\s*map\s+", "", os.path.basename(directory), flags=re.I).strip() or os.path.basename(directory)
            take_untracked(label, k, firsts, "Gồm các khu vực: " + ", ".join(_alias_after_dash(n) or n for n in names),
                           os.path.basename(directory))

    walk(folder, kind, True, [])
    base = os.path.abspath(folder)
    for r in conn.execute("SELECT i.id, i.src_path, i.path, a.name FROM asset_images i JOIN assets a ON a.id=i.asset_id"
                          " WHERE a.game=? AND a.project_id IS NULL AND i.src_path LIKE ?", (game, base + os.sep + "%")).fetchall():
        if r["src_path"] not in seen and not os.path.exists(r["src_path"]):
            rep["missing"].append(f"{r['name']}: {os.path.basename(r['src_path'])}")
            if remove_missing:
                remove_image(conn, r["id"])
                rep["removed"] += 1
    return rep


def summary(rep: Dict) -> str:
    bits = [(rep["created"], "mục mới"), (rep["added"], "ảnh thêm"), (rep["updated"], "ảnh cập nhật"), (rep["moved"], "ảnh đổi tên/vị trí"),
            (rep["unchanged"], "không đổi"), (rep["ignored"], "bỏ qua theo từ khóa"), (rep["skipped"], "lỗi/không nhận"),
            (rep["missing"], "không còn trong thư mục"), (rep["removed"], "đã xóa")]
    return ", ".join(f"{len(v) if isinstance(v, list) else v} {label}" for v, label in bits if (len(v) if isinstance(v, list) else v))


def add_files(conn, game: str, kind: str, files: List[tuple], created_by: Optional[str] = None) -> Dict:
    """Several uploaded pictures at once: the file name is the asset name (Lyra_front.png + Lyra_back.png -> Lyra).
    Known assets get the extra pictures; identical pictures are not added twice."""
    rep = {"created": [], "added": 0, "unchanged": 0, "skipped": []}
    groups: Dict[str, List[tuple]] = {}
    for name, data in files:
        groups.setdefault(_stem_name(name), []).append((name, data))
    for asset_name, items in groups.items():
        row = conn.execute("SELECT id FROM assets WHERE game=? AND kind=? AND lower(name)=lower(?) AND project_id IS NULL",
                           (game, kind, asset_name)).fetchone()
        row = row or find_same(conn, game, kind, asset_name)            # S14.43B: another spelling joins the existing entry
        if row:
            aid = row["id"]
        else:
            try:
                aid = create(conn, game, kind, asset_name, created_by=created_by)
            except AssetError as e:                                     # one refused name never stops the rest of the batch
                rep["skipped"] += [(name, str(e)) for name, _ in items]
                continue
            rep["created"].append(asset_name)
        for name, data in items:
            sha = _sha(data)
            if conn.execute("SELECT 1 FROM asset_images WHERE asset_id=? AND sha256=? AND status IS NOT 'removed'", (aid, sha)).fetchone():
                rep["unchanged"] += 1
                continue
            try:
                add_image(conn, aid, name, data, sha256=sha)
                rep["added"] += 1
            except AssetError as e:
                rep["skipped"].append((name, str(e)))
    return rep


# ---- remembered folders ("sources") that can be re-synced with one click or automatically -----------------------------
def folder_signature(folder: str) -> str:
    """Cheap fingerprint (file count, total size, newest change) to tell whether a folder changed since the last sync."""
    count = size = newest = 0
    for dirpath, _, names in os.walk(folder):
        for n in names:
            if n.lower().endswith(IMAGE_EXT):
                try:
                    st = os.stat(os.path.join(dirpath, n))
                except OSError:
                    continue
                count += 1
                size += st.st_size
                newest = max(newest, int(st.st_mtime))
    return f"{count}:{size}:{newest}"


def add_source(conn, game: str, path: str, kind: str = "character", ignore: str = DEFAULT_IGNORE, auto: bool = True) -> int:
    path = os.path.abspath((path or "").strip().strip('"'))
    if not os.path.isdir(path):
        raise AssetError("Không tìm thấy thư mục này trên máy chạy Dashboard")
    if kind not in KINDS:
        raise AssetError("Loại mặc định không hợp lệ")
    if conn.execute("SELECT 1 FROM asset_sources WHERE game=? AND path=?", (game, path)).fetchone():
        raise AssetError("Thư mục này đã có trong danh sách nguồn")
    cur = conn.execute("INSERT INTO asset_sources (game, path, kind, ignore, auto) VALUES (?,?,?,?,?)",
                       (game, path, kind, ignore.strip(), 1 if auto else 0))
    conn.commit()
    return cur.lastrowid


def list_sources(conn, game: Optional[str] = None) -> List[Dict]:
    sql = "SELECT * FROM asset_sources" + (" WHERE game=?" if game else "") + " ORDER BY id"
    return [dict(r) for r in conn.execute(sql, (game,) if game else ()).fetchall()]


def set_source(conn, source_id: int, kind: str, ignore: str, auto: bool) -> None:
    conn.execute("UPDATE asset_sources SET kind=?, ignore=?, auto=? WHERE id=?", (kind, ignore.strip(), 1 if auto else 0, source_id))
    conn.commit()


def remove_source(conn, source_id: int) -> None:
    conn.execute("DELETE FROM asset_sources WHERE id=?", (source_id,))
    conn.commit()


def run_source(conn, source_id: int, created_by: Optional[str] = None, remove_missing: bool = False) -> Dict:
    src = conn.execute("SELECT * FROM asset_sources WHERE id=?", (source_id,)).fetchone()
    if src is None:
        raise AssetError("Không có nguồn này")
    rep = sync_folder(conn, src["path"], src["game"], src["kind"], created_by, src["ignore"] or "", remove_missing)
    conn.execute("UPDATE asset_sources SET last_sync=datetime('now'), last_signature=?, last_summary=? WHERE id=?",
                 (folder_signature(src["path"]), summary(rep) or "không có gì thay đổi", source_id))
    conn.commit()
    return rep


def auto_sync(conn, created_by: Optional[str] = "auto-sync") -> List[Dict]:
    """Re-sync every source marked 'auto' whose folder looks different from the last time. Never raises: a folder that is
    unavailable (a drive that is not connected) is just reported."""
    done = []
    for src in list_sources(conn):
        if not src["auto"]:
            continue
        try:
            if folder_signature(src["path"]) == src["last_signature"]:
                continue
            done.append({"source": src["path"], "report": run_source(conn, src["id"], created_by)})
        except (AssetError, OSError) as e:
            conn.execute("UPDATE asset_sources SET last_summary=? WHERE id=?", (f"Lỗi: {e}", src["id"]))
            conn.commit()
    return done


def add_reference_images(conn, project_id: int, game: str, kind: str, name: str, files: List[tuple], shared: bool,
                         created_by: Optional[str] = None) -> Dict:
    """Đợt 3 (01/10): a person attaches pictures to a script from the script screen. `shared` = into the common Kho (pictures wait as
    'chờ duyệt' — the pipeline does not use them until someone approves, rule G2); otherwise only for this project (the person who
    uploaded them for this very project has approved them). Same name already there → the pictures join it. The asset is attached to
    the project either way. Returns {"asset_id", "added", "skipped": [(file, why)], "created": bool}."""
    name = " ".join((name or "").split())
    if not name:
        raise AssetError("Cho ảnh một cái tên")
    scope = None if shared else project_id
    row = conn.execute("SELECT id FROM assets WHERE game=? AND kind=? AND lower(name)=lower(?) AND COALESCE(project_id,0)=COALESCE(?,0)",
                       (game, kind, name, scope)).fetchone()
    row = row or find_same(conn, game, kind, name, project_id=scope)    # S14.43B: another spelling joins the existing entry
    created = row is None
    aid = row["id"] if row else create(conn, game, kind, name, project_id=scope, created_by=created_by)
    rep = {"asset_id": aid, "added": 0, "skipped": [], "created": created}
    for fname, data in files:
        sha = _sha(data)
        if conn.execute("SELECT 1 FROM asset_images WHERE asset_id=? AND sha256=? AND status IS NOT 'removed'", (aid, sha)).fetchone():
            rep["skipped"].append((fname, "ảnh này đã có"))
            continue
        try:
            add_image(conn, aid, fname, data, sha256=sha, status="pending" if shared else "approved")
            rep["added"] += 1
        except AssetError as e:
            rep["skipped"].append((fname, str(e)))
    attach(conn, project_id, aid)
    return rep


def add_outfit_images(conn, project_id: int, game: str, name: str, files: List[tuple], shared: bool, character: Optional[str] = None,
                      created_by: Optional[str] = None) -> Dict:
    """S14.28: pictures of an outfit ("Trang phục") from the script screen → into the Kho (kind "outfit", reusable in other projects
    when `shared`) and, when `character` is given, set as that character's outfit in this project (set_outfit, up to 2 pictures).
    The character must be in this project's Character Bible — checked BEFORE anything is saved (luật 1: không im lặng).
    Shared pictures wait for approval (G2), so the outfit is then NOT set and `note` says why. Returns add_reference_images' dict +
    {"outfit_set": bool, "note": str}."""
    who = " ".join((character or "").split())
    if who and conn.execute("SELECT 1 FROM characters WHERE project_id=? AND name=?", (project_id, who)).fetchone() is None:
        raise AssetError(f"Không có nhân vật “{who}” trong Character Bible của dự án — chạy Director hoặc thêm nhân vật trước")
    rep = add_reference_images(conn, project_id, game, "outfit", name, files, shared, created_by=created_by)
    rep.update(outfit_set=False, note="")
    if not who:
        rep["note"] = "đã lưu vào Kho — chưa gắn cho nhân vật nào (chọn ở 👗 Trang phục của nhân vật)"
        return rep
    shas = [_sha(data) for _, data in files]
    rows = conn.execute("SELECT id, sha256, status FROM asset_images WHERE asset_id=? AND status IS NOT 'removed'", (rep["asset_id"],)).fetchall()
    by_sha = {r["sha256"]: r for r in rows}
    ids = [by_sha[h]["id"] for h in dict.fromkeys(shas) if h in by_sha and by_sha[h]["status"] in USABLE][:2]
    if ids:
        set_outfit(conn, project_id, who, ids)
        rep.update(outfit_set=True, note=f"đã gắn {len(ids)} ảnh làm trang phục của {who} trong dự án này")
    elif shared:
        rep["note"] = (f"ảnh ở Kho chung đang chờ duyệt — duyệt xong (📁 Kho tài nguyên) rồi chọn ở 👗 Trang phục của {who}; "
                       "chưa gắn cho nhân vật")
    else:
        rep["note"] = f"không có ảnh nào dùng được — chưa gắn trang phục cho {who}"
    return rep
