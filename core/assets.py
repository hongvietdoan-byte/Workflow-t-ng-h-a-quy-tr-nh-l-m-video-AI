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
          "truoc", "sau", "ngang", "mat"}


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


def add_image(conn, asset_id: int, filename: str, data: bytes) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in IMAGE_EXT:
        raise AssetError(f"“{filename}”: chỉ nhận ảnh JPG / PNG / WebP")
    if len(data) > MAX_IMAGE_BYTES:
        raise AssetError(f"“{filename}” lớn hơn 10 MB: hãy giảm dung lượng (bộ tạo ảnh không nhận)")
    if not data:
        raise AssetError(f"“{filename}” rỗng")
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
    conn.execute("INSERT INTO asset_images (asset_id, path, label, sort) VALUES (?,?,?,?)",
                 (asset_id, path, os.path.splitext(os.path.basename(filename))[0], n))
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


def delete(conn, asset_id: int) -> None:
    conn.execute("DELETE FROM asset_images WHERE asset_id=?", (asset_id,))
    conn.execute("DELETE FROM project_assets WHERE asset_id=?", (asset_id,))
    conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    conn.commit()
    shutil.rmtree(os.path.join(root(), str(asset_id)), ignore_errors=True)


def _row(conn, r) -> Dict:
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
    return [_row(conn, r) for r in conn.execute(sql, args).fetchall()]


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
    return ("# Tài nguyên có sẵn cho dự án này (BẮT BUỘC dùng)\n" + "\n".join(lines) +
            "\nDùng đúng tên và thiết kế ở trên cho Character Bible và các cảnh; không tự bịa lại ngoại hình của những mục này. "
            "Chỉ thêm nhân vật/đạo cụ mới khi kịch bản cần mà danh sách không có.")


# ---- import from a folder ---------------------------------------------------------------------------------------------
def _stem_name(filename: str) -> str:
    stem = os.path.splitext(filename)[0]
    words = [w for w in re.split(r"[\s_\-\.]+", stem) if w]
    while words and (words[-1].isdigit() or fold(words[-1]) in _NOISE):
        words.pop()
    return " ".join(words) or stem


def import_folder(conn, folder: str, game: str, kind: str = "character", created_by: Optional[str] = None) -> Dict[str, int]:
    """Bring a folder of pictures into the shared library.

    Recognised layouts (they can be mixed):
      folder/Lyra_front.png, Lyra_back.png      -> asset "Lyra" with 2 pictures (numbers and words like front/back are dropped)
      folder/Lyra/1.png, 2.png                   -> asset "Lyra" (the folder name)
      folder/Nhân vật/..., Vũ khí/..., Bản đồ/...  -> the folder name chooses the kind (characters, weapons, pets, maps, props, styles)
    Existing assets with the same name/kind get the extra pictures; nothing is deleted."""
    if not os.path.isdir(folder):
        raise AssetError("Không tìm thấy thư mục này trên máy chạy Dashboard")
    made = added = skipped = 0

    def take(name: str, k: str, files: List[str]) -> None:
        nonlocal made, added, skipped
        if not files:
            return
        row = conn.execute("SELECT id FROM assets WHERE game=? AND kind=? AND lower(name)=lower(?) AND project_id IS NULL",
                           (game, k, name)).fetchone()
        aid = row["id"] if row else create(conn, game, k, name, created_by=created_by)
        made += 0 if row else 1
        for path in files:
            try:
                with open(path, "rb") as f:
                    add_image(conn, aid, os.path.basename(path), f.read())
                added += 1
            except (AssetError, OSError):
                skipped += 1

    def walk(directory: str, k: str, top: bool) -> None:
        entries = sorted(os.listdir(directory))
        files = [e for e in entries if os.path.isfile(os.path.join(directory, e)) and e.lower().endswith(IMAGE_EXT)]
        groups: Dict[str, List[str]] = {}
        for e in files:
            key = os.path.basename(directory) if (not top and kind_from_word(os.path.basename(directory)) is None) else _stem_name(e)
            groups.setdefault(key, []).append(os.path.join(directory, e))
        for name, paths in groups.items():
            take(name, k, paths)
        for e in entries:
            sub = os.path.join(directory, e)
            if os.path.isdir(sub):
                walk(sub, kind_from_word(e) or k, False)

    walk(folder, kind, True)
    return {"assets_created": made, "images_added": added, "images_skipped": skipped}
