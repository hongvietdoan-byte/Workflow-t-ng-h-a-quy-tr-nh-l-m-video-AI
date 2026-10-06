"""S14.48 (ý 2 từ tài liệu 'Prompt Spider', 06/10): màu chính nhân vật đo bằng CODE — 0 USD, tất định. Cờ `palette_check` (TẮT).

Character Lock đã cấm "đổi bảng màu trang phục" (knowledge/character_lock.md) nhưng chỉ Claude soi bằng mắt. Ở đây:
  extract(ảnh mốc)      màu chiếm nhiều nhất ở vùng THÂN (ngay dưới mặt) của ảnh tham chiếu đã duyệt → [{"hex", "share"}]
  character_palette()   bảng màu của nhân vật, lưu characters.palette (trích một lần theo sha ảnh mốc; người đặt tay thì thắng)
  check(ảnh tạo ra)     màu nào của bảng thiếu ở vùng thân → ghi chú
  attach()              gắn kết quả vào số đo code của Tổ QC (core/qc_team.review_frame) khi cờ bật
Không dùng mã hex trong prompt: model ảnh làm theo hex kém — hex chỉ để ĐO. Ngưỡng (MATCH_DE, KEEP_RATIO) CHƯA hiệu chỉnh trên ảnh thật
→ kết quả luôn 'uncertain' (ghi chú cho người, không tự từ chối / vẽ lại), cùng nguyên tắc với qc_measure. Chỉ đo khi khung có đúng
MỘT mặt và bảng shot có đúng MỘT nhân vật (nhiều người thì không biết thân nào của ai — báo not_measurable, không đoán).
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

MIN_SHARE = 0.12          # một màu vào bảng khi chiếm ≥ 12 % vùng thân của ảnh mốc
CHECK_SHARE = 0.15        # chỉ kiểm màu chiếm ≥ 15 % (màu phụ nhỏ dễ khuất)
MATCH_DE = 20.0           # điểm ảnh 'cùng màu' khi ΔE76 ≤ 20 (chưa hiệu chỉnh)
KEEP_RATIO = 0.35         # thiếu khi chỉ còn < 35 % tỉ lệ của ảnh mốc (chưa hiệu chỉnh)
_HEX = re.compile(r"^#?([0-9A-Fa-f]{6})$")


# ---- màu --------------------------------------------------------------------------------------------------------------------
def to_hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(int(round(v)) for v in rgb))


def from_hex(text: str):
    m = _HEX.match(str(text or "").strip())
    if not m:
        raise ValueError(f"mã màu '{text}' phải dạng #RRGGBB")
    v = m.group(1)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def _lab(rgb_array):
    """sRGB (…, 3) 0–255 → CIE Lab (D65)."""
    import numpy as np
    c = np.asarray(rgb_array, dtype=float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e(a, b) -> float:
    import numpy as np
    return float(np.linalg.norm(_lab(a) - _lab(b)))


# ---- vùng thân ----------------------------------------------------------------------------------------------------------------
def _faces(path: str):
    from . import qc_measure
    return qc_measure.faces(path)


def _torso(path: str):
    """(pixels (N, 3) of the body under the only face, "") or (None, why)."""
    boxes = _faces(path)
    if boxes is None:
        return None, "không có bộ dò mặt"
    if len(boxes) != 1:
        return None, f"{len(boxes)} mặt trong khung — chỉ đo khi có đúng một mặt"
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
    except Exception as e:  # noqa: BLE001 - a missing / broken file is said, not raised
        return None, f"không mở được ảnh ({type(e).__name__})"
    import numpy as np
    w, h = im.size
    l, t, r, b = boxes[0]
    fw, fh = r - l, b - t
    box = (max(0.0, l - 0.5 * fw) * w, min(1.0, b + 0.1 * fh) * h, min(1.0, r + 0.5 * fw) * w, min(1.0, b + 2.0 * fh) * h)
    if box[3] - box[1] < 4 or box[2] - box[0] < 4:
        return None, "mặt sát mép dưới — không thấy thân"
    return np.asarray(im.crop(tuple(int(v) for v in box)).resize((48, 48))).reshape(-1, 3), ""


def extract(path: str, k: int = 6) -> Dict:
    """{"colors": [{"hex", "share"}] (nhiều nhất trước), "note"}; colors rỗng khi không đo được (note nói vì sao)."""
    px, why = _torso(path)
    if px is None:
        return {"colors": [], "note": why}
    import numpy as np
    from PIL import Image
    q = Image.fromarray(px.reshape(48, 48, 3).astype("uint8")).quantize(colors=k)
    pal = q.getpalette()[: 3 * k]
    counts = np.bincount(np.asarray(q).ravel(), minlength=k)
    groups: List[Dict] = []
    for i in np.argsort(-counts):
        if not counts[i]:
            continue
        rgb = tuple(pal[3 * i: 3 * i + 3])
        share = counts[i] / counts.sum()
        near = next((g for g in groups if delta_e(g["rgb"], rgb) < 10), None)
        if near:
            near["share"] += share
        else:
            groups.append({"rgb": rgb, "share": share})
    colors = [{"hex": to_hex(g["rgb"]), "share": round(float(g["share"]), 3)} for g in sorted(groups, key=lambda g: -g["share"])
              if g["share"] >= MIN_SHARE]
    return {"colors": colors, "note": ""}


def check(path: str, pal: Dict) -> Dict:
    """{"status": 'uncertain' | 'not_measurable', "missing": [hex], "value": {hex: share now}, "note"} — never certain (uncalibrated)."""
    wanted = [c for c in (pal or {}).get("colors") or [] if c.get("share", 0) >= CHECK_SHARE]
    if not wanted:
        return {"status": "not_measurable", "missing": [], "note": "chưa có bảng màu nhân vật"}
    px, why = _torso(path)
    if px is None:
        return {"status": "not_measurable", "missing": [], "note": why}
    import numpy as np
    lab = _lab(px)
    now, missing = {}, []
    for c in wanted:
        share = float((np.linalg.norm(lab - _lab(from_hex(c["hex"])), axis=-1) <= MATCH_DE).mean())
        now[c["hex"]] = round(share, 3)
        if share < KEEP_RATIO * c["share"]:
            missing.append(c["hex"])
    note = ("khớp bảng màu nhân vật" if not missing else
            "lệch màu trang phục: thiếu " + ", ".join(f"{h} (mốc {next(c['share'] for c in wanted if c['hex'] == h):.0%}, nay {now[h]:.0%})"
                                                       for h in missing) + " — người xem lại (ngưỡng chưa hiệu chỉnh)")
    return {"status": "uncertain", "missing": missing, "value": now, "note": note}


# ---- lưu theo nhân vật ----------------------------------------------------------------------------------------------------------
def file_sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _reference_path(conn, pid: int, name: str) -> Optional[str]:
    from . import assets
    a = assets.link_characters(conn, pid, [name]).get(name)
    ref = (a or {}).get("ref") or {}
    return assets.resolve(ref.get("path")) if ref.get("path") else None


def _row(conn, pid: int, name: str):
    return conn.execute("SELECT id, name, palette FROM characters WHERE project_id=? AND UPPER(name)=UPPER(?)", (pid, name)).fetchone()


def _save(conn, row_id: int, data: Dict) -> None:
    conn.execute("UPDATE characters SET palette=? WHERE id=?", (json.dumps(data, ensure_ascii=False), row_id))
    conn.commit()


def set_palette(conn, pid: int, name: str, hexes: List[str]) -> Dict:
    """The person's own palette (wins over the automatic one until cleared). ValueError for a bad colour / unknown character."""
    colors = [{"hex": to_hex(from_hex(h)), "share": round(1.0 / len(hexes), 3)} for h in hexes] if hexes else []
    row = _row(conn, pid, name)
    if row is None:
        raise ValueError(f"không có nhân vật '{name}' trong dự án")
    data = {"by": "user", "colors": colors, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _save(conn, row["id"], data)
    return data


def character_palette(conn, pid: int, name: str) -> Dict:
    """Stored palette; the automatic one is (re)made from the approved reference picture when that picture changed."""
    row = _row(conn, pid, name)
    if row is None:
        return {"colors": [], "note": f"không có nhân vật '{name}'"}
    try:
        stored = json.loads(row["palette"] or "null") or {}
    except ValueError:
        stored = {}
    if stored.get("by") == "user":
        return stored
    ref = _reference_path(conn, pid, row["name"])               # the stored spelling (the shot may write "Kelly")
    if not ref:
        return {"colors": [], "note": "nhân vật chưa có ảnh tham chiếu"}
    sha = file_sha(ref)
    if stored.get("ref_sha") == sha:
        return stored
    data = {**extract(ref), "by": "auto", "ref_sha": sha, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _save(conn, row["id"], data)
    return data


def attach(code: Dict, conn, pid: int, path: str, data: Dict) -> None:
    """Tổ QC: code["_palette"] = check of this frame (flag `palette_check` on; one character on the shot, else not_measurable)."""
    from . import features
    if not features.on("palette_check"):
        return
    cast = [str(c) for c in (data or {}).get("characters") or []]
    if len(cast) != 1:
        code["_palette"] = {"status": "not_measurable", "missing": [], "note": f"bảng shot có {len(cast)} nhân vật — chỉ đo khung một người"}
        return
    pal = character_palette(conn, pid, cast[0])
    code["_palette"] = {**check(path, pal), "character": cast[0].upper()}
