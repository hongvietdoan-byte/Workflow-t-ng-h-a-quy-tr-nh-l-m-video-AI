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
from typing import Dict, List, Optional

KINDS = {"character": "Nhân vật", "weapon": "Vũ khí / trang bị", "pet": "Thú cưng", "prop": "Đạo cụ",
         "location": "Địa điểm / bản đồ", "style": "Phong cách"}
_KIND_WORDS = {"character": ("character", "characters", "char", "chars", "nhan vat", "nhanvat", "nv"),
               "weapon": ("weapon", "weapons", "vu khi", "vukhi", "trang bi", "gun", "guns"),
               "pet": ("pet", "pets", "thu cung", "thucung"),
               "prop": ("prop", "props", "item", "items", "do vat", "dao cu", "daocu"),
               "location": ("location", "locations", "map", "maps", "place", "places", "ban do", "bando", "dia diem", "bo canh"),
               "style": ("style", "styles", "phong cach")}
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
                 "top_down": "toàn cảnh từ trên (chỉ thông tin)", "detail": "chi tiết / mốc"},
}
ROLES["pet"] = ROLES["character"]
LOOKS = {"ingame": "in-game FF", "anime": "anime"}
STATUSES = {"approved": "đã duyệt", "pending": "chờ duyệt"}
_NOISE = {"front", "back", "side", "full", "avatar", "face", "portrait", "main", "ref", "reference", "hd", "final", "copy",
          "truoc", "sau", "ngang", "mat", "new", "old", "moi", "cu"}


class AssetError(Exception):
    """A message that can be shown to the person."""


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def root() -> str:
    return os.environ.get("ASSET_DIR") or os.path.join("data", "assets")


def resolve(path: Optional[str]) -> Optional[str]:
    """A stored picture path made usable from any working folder (A1): stored paths are relative to the repository ("data/assets/…"),
    so a Dashboard or tool started elsewhere used to find no picture at all — and the Director then described characters blind."""
    if not path or os.path.isabs(path) or os.path.exists(path):
        return path
    return os.path.join(REPO, path)


def missing_files(conn) -> List[Dict]:
    """Library pictures whose file cannot be found (checked when the Dashboard opens: rule 1 of docs/CHUAN_XAY_DUNG.md)."""
    return [{"id": r["id"], "asset": r["name"], "path": r["path"]} for r in conn.execute(
        "SELECT i.id, i.path, a.name FROM asset_images i JOIN assets a ON a.id=i.asset_id") if not os.path.exists(resolve(r["path"]))]


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
def create(conn, game: str, kind: str, name: str, description: str = "", aliases: str = "", project_id: Optional[int] = None,
           created_by: Optional[str] = None) -> int:
    name = " ".join((name or "").split())
    if not name:
        raise AssetError("Tên tài nguyên không được để trống")
    if kind not in KINDS:
        raise AssetError("Loại tài nguyên không hợp lệ")
    dup = conn.execute("SELECT id FROM assets WHERE game=? AND kind=? AND lower(name)=lower(?) AND COALESCE(project_id,0)=COALESCE(?,0)",
                       (game, kind, name, project_id)).fetchone()
    if dup:
        raise AssetError(f"Đã có {KINDS[kind].lower()} tên “{name}”")
    cur = conn.execute("INSERT INTO assets (game, kind, name, aliases, description, project_id, created_by, created_at)"
                       " VALUES (?,?,?,?,?,?,?, datetime('now'))",
                       (game, kind, name, aliases.strip(), description.strip(), project_id, created_by))
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
    have = conn.execute("SELECT COUNT(*) FROM asset_images WHERE asset_id=?", (asset_id,)).fetchone()[0]
    if have >= limit:
        raise AssetError(f"Mỗi tài nguyên tối đa {limit} ảnh")
    folder = os.path.join(root(), str(asset_id))
    os.makedirs(folder, exist_ok=True)
    n = have + 1
    while os.path.exists(os.path.join(folder, f"{n}{ext}")):
        n += 1
    path = os.path.join(folder, f"{n}{ext}")
    with open(path, "wb") as f:
        f.write(data)
    kind = (conn.execute("SELECT kind FROM assets WHERE id=?", (asset_id,)).fetchone() or {"kind": None})["kind"]
    role = role if role in ROLES.get(kind, {}) else guess_role(path, kind, conn)
    conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, src_path, sha256, src_size, src_mtime, status, role, look, variant)"
                 " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (asset_id, path, os.path.splitext(os.path.basename(filename))[0], n, src_path, fingerprint, src_size, src_mtime,
                  status if status in STATUSES else "pending", role, look if look in LOOKS else None, variant))
    conn.commit()
    return path


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
    shutil.rmtree(os.path.join(root(), str(asset_id)), ignore_errors=True)


def merge(conn, from_id: int, into_id: int) -> int:
    """Fold asset `from_id` into `into_id` (same picture set, one name): its pictures are moved (up to the 6-picture limit), its
    other names become aliases of the target, and it is deleted. Returns how many pictures moved."""
    if from_id == into_id:
        raise AssetError("Chọn một mục khác để gộp vào")
    src, dst = get(conn, from_id), get(conn, into_id)
    if src is None or dst is None:
        raise AssetError("Không có mục này")
    have = len(dst["images"])
    moved = 0
    for img in src["images"]:
        if have >= MAX_IMAGES_PER_ASSET:
            break
        ext = os.path.splitext(img["path"])[1]
        folder = os.path.join(root(), str(into_id))
        os.makedirs(folder, exist_ok=True)
        n = have + 1
        while os.path.exists(os.path.join(folder, f"{n}{ext}")):
            n += 1
        target = os.path.join(folder, f"{n}{ext}")
        shutil.move(img["path"], target)
        conn.execute("UPDATE asset_images SET asset_id=?, path=?, sort=? WHERE id=?", (into_id, target, n, img["id"]))
        have += 1
        moved += 1
    names = [n for n in re.split(r"[,;|]", dst["aliases"]) if n.strip()]
    for n in [src["name"]] + [x for x in re.split(r"[,;|]", src["aliases"]) if x.strip()]:
        if fold(n) != fold(dst["name"]) and fold(n) not in {fold(x) for x in names}:
            names.append(n.strip())
    conn.execute("UPDATE assets SET aliases=? WHERE id=?", (", ".join(names), into_id))
    conn.execute("UPDATE project_assets SET asset_id=? WHERE asset_id=? AND NOT EXISTS (SELECT 1 FROM project_assets p2"
                 " WHERE p2.project_id=project_assets.project_id AND p2.asset_id=?)", (into_id, from_id, into_id))
    conn.commit()
    delete(conn, from_id)
    return moved


def _row(conn, r, images_by_asset: Optional[Dict] = None) -> Dict:
    if images_by_asset is not None:
        images = images_by_asset.get(r["id"], [])
    else:
        images = [dict(i) for i in conn.execute("SELECT id, path, label, role, look, variant, status FROM asset_images WHERE asset_id=?"
                                                " ORDER BY sort, id", (r["id"],))]
    images = [dict(i, path=resolve(i["path"])) for i in images]
    pending = [i for i in images if i.get("status") == "pending" and os.path.exists(i["path"])]
    images = [i for i in images if i.get("status") != "pending"]            # G2: only pictures a person approved are used
    return {"id": r["id"], "game": r["game"], "kind": r["kind"], "kind_label": KINDS.get(r["kind"], r["kind"]), "name": r["name"],
            "aliases": r["aliases"] or "", "description": r["description"] or "", "project_id": r["project_id"],
            "created_by": r["created_by"], "images": [i for i in images if os.path.exists(i["path"])], "pending": pending,
            "missing": [i["path"] for i in images if not os.path.exists(i["path"])]}   # approved pictures whose file is gone (said, luật 1)


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
    for i in conn.execute("SELECT asset_id, id, path, label, role, look, variant, status FROM asset_images ORDER BY sort, id"):
        images.setdefault(i["asset_id"], []).append({k: i[k] for k in ("id", "path", "label", "role", "look", "variant", "status")})
    return [_row(conn, r, images) for r in rows]


# ---- finding assets in a script ---------------------------------------------------------------------------------
def names_of(asset: Dict) -> List[str]:
    return [n for n in [asset["name"]] + re.split(r"[,;|]", asset["aliases"]) if fold(n)]


def find_in_text(conn, text: str, game: Optional[str], project_id: Optional[int] = None) -> List[Dict]:
    """Assets whose name or another name appears in the text (whole words, accents and case ignored)."""
    body = " " + fold(text) + " "
    found = []
    for a in list_assets(conn, game, None, project_id):
        hits = sum(body.count(" " + fold(n) + " ") for n in names_of(a) if len(fold(n)) >= 2)
        if hits:
            found.append(dict(a, mentions=hits))
    return sorted(found, key=lambda a: -a["mentions"])


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
    for aid, names in hits.items():
        if not names:
            continue                                     # its only name belongs to a character / place — not this one
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


def shot_roles(scene: Optional[Dict]) -> List[Optional[str]]:
    """T3: which kind of character picture suits the shot, best first (None = a picture whose role nobody set).
    A close shot needs a face the model can copy; a wide shot the whole figure; a back-to-camera shot a back view."""
    size = shot_size(scene)
    order: List[Optional[str]] = (["close_up", "half_body", None, "full_body"] if size in _CLOSE else
                                  ["full_body", None, "half_body", "close_up"] if size in _WIDE else
                                  ["half_body", None, "full_body", "close_up"])
    text = fold(" ".join(str((scene or {}).get(k) or "") for k in ("blocking", "action", "shot", "image_prompt")))
    if any(fold(w) in text for w in _BACK_WORDS):
        order = ["back"] + order
    return order + ["side", "skill_pose"]


def best_references(asset: Dict, limit: int = 1, scene: Optional[Dict] = None) -> List[Dict]:
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
        singles = [i for i in images if i.get("role") not in ("design_sheet", "related") and not _is_composite_sheet(_shape(i["path"]))]
        pool = singles or [i for i in images if i.get("role") != "related"] or images
        prefs = ["front_standard"] + shot_roles(scene)          # the person's grey-background front picture always leads
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


def best_reference(asset: Dict) -> Dict:
    return best_references(asset, 1)[0]


STANDARD_ROLES = ("front_standard", "design_sheet", "related")


def standard_set(asset: Dict, sheets: bool) -> List[tuple]:
    """The character's standard 3 pictures (user choice 2026-09-24): [(picture, ref role)] = the grey-background front picture
    ('character'), the multi-angle design sheet ('sheet' — only for a model that takes sheets without copying them), the related
    picture ('related', e.g. the skill). Empty when the asset has no approved front_standard picture (the automatic pick is used)."""
    by_role = {}
    for img in asset.get("images") or []:
        if img.get("status", "approved") != "pending" and img.get("role") in STANDARD_ROLES:
            by_role.setdefault(img["role"], img)
    if "front_standard" not in by_role:
        return []
    out = [(by_role["front_standard"], "character")]
    if sheets and "design_sheet" in by_role:
        out.append((by_role["design_sheet"], "sheet"))
    if sheets and "related" in by_role:                  # only with a model that understands what each picture is for
        out.append((by_role["related"], "related"))
    return out


def _chosen_images(asset: Dict, row: Dict, limit: int = MAX_REFS_PER_CHARACTER, scene: Optional[Dict] = None) -> List[Dict]:
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
    return best_references(asset, limit, scene)


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
            imgs = _chosen_images(asset, row, scene=scene)
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
        r = conn.execute("SELECT id, path FROM asset_images WHERE id=?", (i,)).fetchone()
        if r and os.path.exists(resolve(r["path"])):
            out.append({"id": r["id"], "path": resolve(r["path"])})
    return out


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
    clean: Dict = {k: str(data.get(k) or "").strip() for k in PROFILE_KEYS if k != "height_m"}
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
    return next((i for i in place["images"] if i.get("role") == "detail"), None)


def location_text(conn, place: Dict) -> str:
    """B1: the place in words for the image prompt — its description and, from the set analyses already read or rendered, the real
    heights of its landmarks (so people get the right size next to a wall or a door without copying a picture's camera)."""
    marks, light = [], ""
    for img in place["images"]:
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
    desc = re.sub(r"\s+", " ", (place.get("description") or "").split("[AI đọc ảnh]")[0]).strip()[:600]   # S5.2: 300 cut the
    # tower's "No stacked terraces, no fortress." off its layout sentence
    bits = [f"Setting: {place['name']}" + (f" — {desc}" if desc else "")]
    if marks:
        bits.append("Real sizes: " + ", ".join(f"{n} about {h:g} m tall" for n, h in marks[:6])
                    + "; an adult is about 1.7 m, keep people in proportion to these")
    if light and not light.startswith("3D render"):
        bits.append(f"Light: {light[:120]}")
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
            caps.append(len(STANDARD_ROLES))
        else:
            own = [(img["path"], "character") for img in (a["refs"] if a else [])]
            caps.append(MAX_REFS_PER_CHARACTER)
        people.append((label, own[:1] + [(img["path"], "outfit") for img in outfit[:1]] + own[1:]))
    place = scene_location(conn, project_id, scene)
    loc = location_plate(conn, place, scene) if place else None
    mark = location_landmark(conn, place, scene) if place and loc is None else None
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
    for a in chosen:
        if len(refs) >= limit:
            break
        if a["kind"] not in ("weapon", "prop", "pet", "location") or not a["images"] or any(r["label"] == a["name"] for r in refs):
            continue
        if place is not None and a["id"] == place["id"]:
            continue                                          # the scene's own place: already decided above (plate or words)
        keys = [fold(n) for n in names_of(a) if len(fold(n)) >= 3 and fold(n) not in cast]
        if any(" " + k + " " in blob for k in keys):
            pic = location_plate(conn, a, scene) if a["kind"] == "location" else best_reference(a)
            if pic is not None:
                refs.append({"path": pic["path"], "label": a["name"], "role": "location" if a["kind"] == "location" else "object"})
    return refs


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
        elif g["role"] == "landmark":
            bits.append(f"{tag} shows the real LANDMARK of {g['label']} (from the game): wherever it appears in the background, draw it with "
                        "exactly this shape, proportions, materials and colours — but NOT this picture's camera angle, framing, time of "
                        "day or lighting (those come from the scene text); it may be small, blurred or partly out of frame")
        elif g["role"] == "outfit":
            bits.append(f"{tag} {'shows' if len(nums) == 1 else 'show'} the OUTFIT {g['label']} wears in this video: dress {g['label']} "
                        "exactly in these clothes (garments, colours, accessories); take only the face, hair and body build from "
                        f"{g['label']}'s own reference image, never the clothes shown there")
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
    return ("\n\n## Tin tức chính thức liên quan (tham khảo bối cảnh, không bắt buộc)\n" + "\n".join(lines) + "\n") if lines else ""


CONTEXT_DESC_CHARS = 320


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
    lines = []
    for a in items:
        also = f" (tên khác: {a['aliases']})" if a["aliases"].strip() else ""
        pics = f" — có {len(a['images'])} ảnh tham khảo" if a["images"] else ""
        desc = f": {_brief(a['description'])}" if a["description"] else ""
        ident = f" (id {a['id']})" if a["kind"] == "location" and a["images"] else ""
        lines.append(f"- [{a['kind_label']}] **{a['name']}**{ident}{also}{desc}{pics}")
    news = _news_for(conn, items)
    return ("# Tài nguyên có sẵn cho dự án này (BẮT BUỘC dùng)\n" + "\n".join(lines) + news +
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
        if row:
            return row["id"]
        aid = create(conn, game, k, name, description, aliases, created_by=created_by)
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
        aid = row["id"] if row else create(conn, game, kind, asset_name, created_by=created_by)
        if not row:
            rep["created"].append(asset_name)
        for name, data in items:
            sha = _sha(data)
            if conn.execute("SELECT 1 FROM asset_images WHERE asset_id=? AND sha256=?", (aid, sha)).fetchone():
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
