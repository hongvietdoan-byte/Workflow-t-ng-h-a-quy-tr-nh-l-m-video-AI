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
_NOISE = {"front", "back", "side", "full", "avatar", "face", "portrait", "main", "ref", "reference", "hd", "final", "copy",
          "truoc", "sau", "ngang", "mat", "new", "old", "moi", "cu"}


class AssetError(Exception):
    """A message that can be shown to the person."""


def root() -> str:
    return os.environ.get("ASSET_DIR") or os.path.join("data", "assets")


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
              src_size: Optional[int] = None, src_mtime: Optional[int] = None) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in IMAGE_EXT:
        raise AssetError(f"“{filename}”: chỉ nhận ảnh JPG / PNG / WebP")
    if not data:
        raise AssetError(f"“{filename}” rỗng")
    fingerprint = sha256 or hashlib.sha256(data).hexdigest()          # of the original file, so a re-sync recognises it
    if len(data) > MAX_IMAGE_BYTES:
        data, ext = _shrink(data, filename)
    have = conn.execute("SELECT COUNT(*) FROM asset_images WHERE asset_id=?", (asset_id,)).fetchone()[0]
    if have >= MAX_IMAGES_PER_ASSET:
        raise AssetError(f"Mỗi tài nguyên tối đa {MAX_IMAGES_PER_ASSET} ảnh")
    folder = os.path.join(root(), str(asset_id))
    os.makedirs(folder, exist_ok=True)
    n = have + 1
    while os.path.exists(os.path.join(folder, f"{n}{ext}")):
        n += 1
    path = os.path.join(folder, f"{n}{ext}")
    with open(path, "wb") as f:
        f.write(data)
    conn.execute("INSERT INTO asset_images (asset_id, path, label, sort, src_path, sha256, src_size, src_mtime) VALUES (?,?,?,?,?,?,?,?)",
                 (asset_id, path, os.path.splitext(os.path.basename(filename))[0], n, src_path, fingerprint, src_size, src_mtime))
    conn.commit()
    return path


def remove_image(conn, image_id: int) -> None:
    row = conn.execute("SELECT path FROM asset_images WHERE id=?", (image_id,)).fetchone()
    if row:
        try:
            os.remove(row["path"])
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
        images = [dict(i) for i in conn.execute("SELECT id, path, label FROM asset_images WHERE asset_id=? ORDER BY sort, id", (r["id"],))]
    return {"id": r["id"], "game": r["game"], "kind": r["kind"], "kind_label": KINDS.get(r["kind"], r["kind"]), "name": r["name"],
            "aliases": r["aliases"] or "", "description": r["description"] or "", "project_id": r["project_id"],
            "created_by": r["created_by"], "images": [i for i in images if os.path.exists(i["path"])]}


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
    for i in conn.execute("SELECT asset_id, id, path, label FROM asset_images ORDER BY sort, id"):
        images.setdefault(i["asset_id"], []).append({"id": i["id"], "path": i["path"], "label": i["label"]})
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
    conn.execute("DELETE FROM project_assets WHERE project_id=? AND asset_id=?", (project_id, asset_id))
    conn.commit()


def project_assets(conn, project_id: int) -> List[Dict]:
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


MAX_REFERENCES = 6                 # pictures sent with one image job (Seedream 5.0 Pro accepts up to 10)


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
    return min(close, key=lambda a: len(a["name"])) if close else None


def _reference_rows(conn, project_id: int) -> Dict[str, Dict]:
    return {r["name"]: dict(r) for r in conn.execute("SELECT name, ref_asset_id, ref_image_id FROM characters WHERE project_id=?", (project_id,))}


def _shape(path: str):
    try:
        from PIL import Image
        with Image.open(path) as im:                         # only the header is read
            return im.size
    except Exception:  # noqa: BLE001
        return None


def best_reference(asset: Dict) -> Dict:
    """The picture that works best as a character's reference: ONE figure (a portrait / full-body shot), the sharpest one. A wide
    character sheet (turn-around, expressions, props on one board) is the last choice: image models copy pieces of it and mix people up."""
    def score(img):
        shape = _shape(img["path"])
        if not shape:
            return (0, 0)
        w, h = shape
        return (1 if h >= w * 1.05 else 0, w * h)              # portrait first, then the biggest
    return max(asset["images"], key=score)


def _pick_image(asset: Dict, image_id: Optional[int]) -> Dict:
    for img in asset["images"]:
        if image_id and img["id"] == image_id:
            return img
    return best_reference(asset) if asset.get("kind") in ("character", "pet") else asset["images"][0]


def link_characters(conn, project_id: int, names: List[str]) -> Dict[str, Optional[Dict]]:
    """Character Bible name -> the asset whose picture is its reference, with the chosen picture in `ref` (or None).
    The person's own choice wins (a chosen asset, or "no picture" = ref_asset_id 0); otherwise the chosen asset that matches the name."""
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
            asset = dict(asset, ref=_pick_image(asset, row.get("ref_image_id")))
        out[n] = asset
    return out


def set_character_link(conn, project_id: int, name: str, asset_id: Optional[int], image_id: Optional[int] = None) -> None:
    """asset_id None = automatic (by name), 0 = no reference picture, else that asset (and image_id, or its first picture)."""
    conn.execute("UPDATE characters SET ref_asset_id=?, ref_image_id=? WHERE project_id=? AND name=?", (asset_id, image_id, project_id, name))
    conn.commit()


def scene_references(conn, project_id: int, scene: Dict, limit: int = MAX_REFERENCES) -> List[Dict]:
    """Reference pictures for one scene: the reference picture of each character in the scene, then of a chosen place that the scene's
    location names. [{path, label, role}]"""
    chosen = project_assets(conn, project_id)
    refs: List[Dict] = []
    names = [str(n) for n in scene.get("characters") or []]
    linked = link_characters(conn, project_id, names) if names else {}
    for name in names:
        a = linked.get(name)
        if a and len(refs) < limit and all(r["label"] != a["name"] for r in refs):
            refs.append({"path": a["ref"]["path"], "label": a["name"], "role": "character"})
    place = fold(str(scene.get("location") or ""))
    if place:
        for a in chosen:
            if a["kind"] == "location" and a["images"] and fold(a["name"]) and fold(a["name"]) in place and len(refs) < limit:
                refs.append({"path": a["images"][0]["path"], "label": a["name"], "role": "location"})
    # every other chosen resource (weapon, prop, pet, place) that the scene names is a reference too
    blob = " " + fold(" ".join(str(scene.get(k) or "") for k in ("text", "image_prompt", "location"))) + " "
    cast = {fold(n) for n in names}
    for a in chosen:
        if len(refs) >= limit:
            break
        if a["kind"] not in ("weapon", "prop", "pet", "location") or not a["images"] or any(r["label"] == a["name"] for r in refs):
            continue
        keys = [fold(n) for n in names_of(a) if len(fold(n)) >= 3 and fold(n) not in cast]
        if any(" " + k + " " in blob for k in keys):
            refs.append({"path": a["images"][0]["path"], "label": a["name"], "role": "location" if a["kind"] == "location" else "object"})
    return refs


def reference_note(refs: List[Dict]) -> str:
    """Words that tell the image model what each attached picture is for."""
    bits, people = [], 0
    for i, r in enumerate(refs, 1):
        if r["role"] == "location":
            bits.append(f"Image {i} is the location {r['label']}: keep the look of this environment")
        elif r["role"] == "object":
            bits.append(f"Image {i} is the object {r['label']}: draw it exactly like this whenever it appears")
        else:
            people += 1
            bits.append(f"Image {i} is {r['label']}: the person called {r['label']} in the scene must be exactly this person "
                        "(same face, hairstyle and hair color, outfit and its colors, body build)")
    rule = ""
    if people:
        rule = (" Each person keeps ONLY the look of their own reference image: never swap or blend faces, hair or outfits between people, and ignore any "
                "clothing or hair words in the scene text that contradict the reference images. The people are different individuals.")
    return "Reference images are attached, one per named subject. " + "; ".join(bits) + "." + rule + " "


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


def context_text(conn, project_id: int) -> str:
    """Block for the Director prompt; empty when the project has no chosen assets."""
    items = project_assets(conn, project_id)
    if not items:
        return ""
    lines = []
    for a in items:
        also = f" (tên khác: {a['aliases']})" if a["aliases"].strip() else ""
        pics = f" — có {len(a['images'])} ảnh tham khảo" if a["images"] else ""
        desc = f": {a['description']}" if a["description"] else ""
        lines.append(f"- [{a['kind_label']}] **{a['name']}**{also}{desc}{pics}")
    news = _news_for(conn, items)
    return ("# Tài nguyên có sẵn cho dự án này (BẮT BUỘC dùng)\n" + "\n".join(lines) + news +
            "\nDùng đúng tên và thiết kế ở trên cho Character Bible và các cảnh; không tự bịa lại ngoại hình của những mục này. "
            "Chỉ thêm nhân vật/đạo cụ mới khi kịch bản cần mà danh sách không có.")


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
                add_image(conn, aid, os.path.basename(path), data, sha256=sha)
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
                add_image(conn, aid, os.path.basename(path), data, src_path=key, sha256=sha, src_size=st.st_size, src_mtime=int(st.st_mtime))
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


def import_folder(conn, folder: str, game: str, kind: str = "character", created_by: Optional[str] = None) -> Dict[str, int]:
    """One-off import (same as a sync without remembering the folder). Kept for callers that want the short result."""
    rep = sync_folder(conn, folder, game, kind, created_by)
    return {"assets_created": len(rep["created"]), "images_added": rep["added"] + rep["updated"], "images_skipped": len(rep["skipped"])}


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
