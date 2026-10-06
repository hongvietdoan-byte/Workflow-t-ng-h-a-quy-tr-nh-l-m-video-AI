"""S14.51 (ý 2 từ tài liệu 'Prompt Spider', 06/10): màu chính nhân vật đo bằng CODE — 0 USD, tất định. Cờ `palette_check` (TẮT).

Character Lock đã cấm "đổi bảng màu trang phục" (knowledge/character_lock.md) nhưng chỉ Claude soi bằng mắt. Ở đây:
  extract(ảnh)          màu chiếm nhiều nhất ở vùng THÂN (ngay dưới mặt) → [{"hex", "share"}]
  character_palette()   bảng màu nhân vật từ ảnh tham chiếu đã duyệt, lưu characters.palette (theo sha ảnh; người đặt tay thắng)
  check(khung, bảng)    màu nào của bảng thiếu ở vùng thân khung → ghi chú
  scene_check(khung…)   so các khung CÙNG CẢNH với nhau (cùng ánh sáng) → khung nào lệch màu so với các khung còn lại
  attach()              gắn kết quả vào số đo code của Tổ QC (core/qc_team.review_frame) khi cờ bật

Người dùng hỏi 06/10 "màu có bị thời tiết, đèn ảnh hưởng, có dễ báo nhầm?" → CÓ, nên đo NỚI:
  1. cân trắng theo cả khung (gray-world) rồi so SẮC MÀU (góc hue, ±HUE_TOL), không so độ sáng — áo đỏ dưới đèn tối vẫn là đỏ;
     màu không sắc (đen / trắng / xám) chỉ so 'không sắc', mọi độ sáng;
  2. cảnh đêm / hoàng hôn / quá tối (qc_measure.sky + độ sáng khung) → not_measurable, không so;
  3. ưu tiên so TRONG CẢNH (scene_check): cùng ánh sáng nên ít bị đánh lừa; chỉ chỉ ra khung lệch khi ≥ 3 khung và các khung còn lại
     khớp nhau;
  4. ngưỡng rộng (KEEP_RATIO 25 %), bỏ khung cận mặt, bỏ so với ảnh mốc khi dự án gắn trang phục riêng (outfit) cho nhân vật.
Không dùng mã hex trong prompt (model ảnh làm theo hex kém) — hex chỉ để ĐO. Ngưỡng chưa hiệu chỉnh trên ảnh thật → kết quả luôn
'uncertain' (ghi chú cho người, không tự từ chối / vẽ lại), cùng nguyên tắc với qc_measure. Chỉ đo khung có đúng MỘT mặt và bảng shot có
đúng MỘT nhân vật (nhiều người thì không biết thân nào của ai — not_measurable, không đoán).
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

MIN_SHARE = 0.12          # một màu vào bảng khi chiếm ≥ 12 % vùng thân
CHECK_SHARE = 0.15        # chỉ kiểm màu chiếm ≥ 15 % (màu phụ nhỏ dễ khuất)
HUE_TOL = 30.0            # độ — cùng sắc màu khi góc hue lệch ≤ 30° (chưa hiệu chỉnh)
CHROMA_MIN = 12.0         # dưới mức này một màu là 'không sắc' (đen / trắng / xám)
KEEP_RATIO = 0.25         # thiếu khi chỉ còn < 25 % tỉ lệ của mốc (chưa hiệu chỉnh)
CLOSE_UP_FACE = 0.35      # mặt cao hơn 35 % khung = cận mặt, không thấy thân
DARK_FRAME = 60           # độ sáng trung bình khung (0–255) dưới mức này = quá tối
SCENE_MIN_FRAMES = 3      # cần ≥ 3 khung cùng nhân vật trong cảnh mới chỉ ra được khung lệch
_HEX = re.compile(r"^#?([0-9A-Fa-f]{6})$")


# ---- màu --------------------------------------------------------------------------------------------------------------------
def to_hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(int(round(min(255, max(0, v)))) for v in rgb))


def from_hex(text: str):
    m = _HEX.match(str(text or "").strip())
    if not m:
        raise ValueError(f"mã màu '{text}' phải dạng #RRGGBB")
    v = m.group(1)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def _lab(rgb_array):
    """sRGB (…, 3) 0–255 → CIE Lab (D65)."""
    import numpy as np
    c = np.clip(np.asarray(rgb_array, dtype=float), 0, 255) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def _lch(rgb_array):
    import numpy as np
    lab = _lab(rgb_array)
    return lab[..., 0], np.hypot(lab[..., 1], lab[..., 2]), np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360


def delta_e(a, b) -> float:
    import numpy as np
    return float(np.linalg.norm(_lab(a) - _lab(b)))


def _matches(px, rgb) -> float:
    """Share of `px` (already white-balanced) of the same COLOUR as `rgb`: same hue (± HUE_TOL) for a coloured one, any lightness;
    'no colour' for black / white / grey."""
    import numpy as np
    _, c, h = _lch(px)
    _, c0, h0 = _lch(np.asarray([rgb], dtype=float))
    c0, h0 = float(c0[0]), float(h0[0])
    if c0 < CHROMA_MIN:
        return float((c < CHROMA_MIN * 1.5).mean())
    dh = np.abs((h - h0 + 180) % 360 - 180)
    return float(((c >= CHROMA_MIN) & (dh <= HUE_TOL)).mean())


# ---- khung + vùng thân ---------------------------------------------------------------------------------------------------------
def _faces(path: str):
    from . import qc_measure
    return qc_measure.faces(path)


def _sky(path: str):
    from . import qc_measure
    return qc_measure.sky(path)


def _light_problem(img_array, path: str) -> Optional[str]:
    """Why the colours of this frame cannot be trusted (night, sunset, too dark), else None."""
    bright = float(img_array.mean())
    if bright < DARK_FRAME:
        return f"khung quá tối (độ sáng {bright:.0f}/255) — màu không đo được"
    sk = _sky(path) or {}
    if sk.get("reading") in ("dark", "warm"):
        return f"ánh sáng {'đêm' if sk['reading'] == 'dark' else 'ấm (hoàng hôn / đèn vàng)'} — màu trang phục đổi theo đèn, không so"
    return None


def _torso(path: str, check_light: bool = True):
    """(white-balanced pixels (N, 3) of the body under the only face, "") or (None, why)."""
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
    whole = np.asarray(im.resize((96, 96)), dtype=float).reshape(-1, 3)
    if check_light:
        why = _light_problem(whole, path)
        if why:
            return None, why
    l, t, r, b = boxes[0]
    fw, fh = r - l, b - t
    if fh > CLOSE_UP_FACE:
        return None, "khung cận mặt — không thấy thân"
    w, h = im.size
    box = (max(0.0, l - 0.5 * fw) * w, min(1.0, b + 0.1 * fh) * h, min(1.0, r + 0.5 * fw) * w, min(1.0, b + 2.0 * fh) * h)
    if box[3] - box[1] < 4 or box[2] - box[0] < 4:
        return None, "mặt sát mép dưới — không thấy thân"
    px = np.asarray(im.crop(tuple(int(v) for v in box)).resize((48, 48)), dtype=float).reshape(-1, 3)
    gains = np.clip(whole.mean() / np.maximum(whole.mean(axis=0), 1.0), 0.5, 2.0)    # gray-world: cân trắng theo CẢ khung
    return np.clip(px * gains, 0, 255), ""


def _palette_of(px, k: int = 6) -> List[Dict]:
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
    return [{"hex": to_hex(g["rgb"]), "share": round(float(g["share"]), 3)} for g in sorted(groups, key=lambda g: -g["share"])
            if g["share"] >= MIN_SHARE]


def extract(path: str, check_light: bool = False) -> Dict:
    """{"colors": [{"hex", "share"}] (nhiều nhất trước), "note"}; colors rỗng khi không đo được (note nói vì sao). Ảnh mốc không bị chặn
    vì ánh sáng (check_light=False): ảnh tham chiếu Kho thường sáng đều; khung cảnh thì có."""
    px, why = _torso(path, check_light=check_light)
    if px is None:
        return {"colors": [], "note": why}
    return {"colors": _palette_of(px), "note": ""}


def _compare(px, wanted: List[Dict]) -> Dict:
    now, missing = {}, []
    for c in wanted:
        share = _matches(px, from_hex(c["hex"]))
        now[c["hex"]] = round(share, 3)
        if share < KEEP_RATIO * c["share"]:
            missing.append(c["hex"])
    return {"now": now, "missing": missing}


def check(path: str, pal: Dict) -> Dict:
    """{"status": 'uncertain' | 'not_measurable', "missing": [hex], "value": {hex: share now}, "note"} — never certain (uncalibrated)."""
    wanted = [c for c in (pal or {}).get("colors") or [] if c.get("share", 0) >= CHECK_SHARE]
    if not wanted:
        return {"status": "not_measurable", "missing": [], "note": (pal or {}).get("note") or "chưa có bảng màu nhân vật"}
    px, why = _torso(path)
    if px is None:
        return {"status": "not_measurable", "missing": [], "note": why}
    got = _compare(px, wanted)
    share_of = {c["hex"]: c["share"] for c in wanted}
    note = ("khớp bảng màu nhân vật" if not got["missing"] else
            "có thể lệch màu trang phục so ảnh mốc: thiếu " + ", ".join(f"{h} (mốc {share_of[h]:.0%}, nay {got['now'][h]:.0%})"
                                                                      for h in got["missing"]) + " — người xem lại (ngưỡng chưa hiệu chỉnh)")
    return {"status": "uncertain", "missing": got["missing"], "value": got["now"], "note": note}


def scene_check(frames: List[Dict]) -> Dict[int, Dict]:
    """Khung CÙNG CẢNH, cùng một nhân vật: {job_id: {"status", "note", "outlier"}}. Khung lệch = khung mà màu chính của nó không có ở
    các khung khác, TRONG KHI các khung khác khớp nhau. frames: [{"job_id", "path", "data"}] (chỉ khung một người được đo)."""
    by_char: Dict[str, List[Dict]] = {}
    for f in frames:
        cast = [str(c).upper() for c in (f.get("data") or {}).get("characters") or []]
        if len(cast) == 1:
            by_char.setdefault(cast[0], []).append(f)
    out: Dict[int, Dict] = {}
    for name, group in by_char.items():
        measured = []
        for f in group:
            px, why = _torso(f["path"], check_light=False)          # same scene = same light: no light gate here
            if px is None:
                out[f["job_id"]] = {"status": "not_measurable", "outlier": False, "note": f"{name}: {why}"}
            else:
                pal = [c for c in _palette_of(px) if c["share"] >= CHECK_SHARE]
                measured.append({"f": f, "px": px, "pal": pal})
        if len(measured) < 2:
            continue

        def agree(a, b) -> bool:            # a's main colours are present in b
            return not _compare(b["px"], a["pal"])["missing"] if a["pal"] else True
        for i, m in enumerate(measured):
            others = [o for j, o in enumerate(measured) if j != i]
            mine_ok = sum(1 for o in others if agree(m, o) and agree(o, m))
            if len(measured) < SCENE_MIN_FRAMES:
                status_note = ("khớp màu với khung còn lại trong cảnh" if mine_ok else
                               "2 khung trong cảnh khác màu trang phục — người xem khung nào đúng")
                out[m["f"]["job_id"]] = {"status": "uncertain", "outlier": False, "note": f"{name}: {status_note}"}
                continue
            others_agree = all(agree(a, b) for a in others for b in others if a is not b)
            outlier = mine_ok == 0 and others_agree
            note = (f"{name}: màu trang phục khác {len(others)} khung còn lại trong cảnh (các khung kia khớp nhau) — người xem lại"
                    if outlier else f"{name}: khớp màu trong cảnh ({mine_ok}/{len(others)} khung)")
            out[m["f"]["job_id"]] = {"status": "uncertain", "outlier": outlier, "note": note}
    return out


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


def _has_outfit(conn, pid: int, name: str) -> bool:
    from . import assets
    try:
        return bool(assets.outfit_images(conn, pid, name))
    except Exception:  # noqa: BLE001 - an old database without the outfit column: no outfit
        return False


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
    """Stored palette; the automatic one is (re)made from the approved reference picture when that picture changed. A character
    wearing a project outfit (assets.set_outfit) has no reference palette: only the in-scene comparison applies."""
    row = _row(conn, pid, name)
    if row is None:
        return {"colors": [], "note": f"không có nhân vật '{name}'"}
    try:
        stored = json.loads(row["palette"] or "null") or {}
    except ValueError:
        stored = {}
    if stored.get("by") == "user":
        return stored
    if _has_outfit(conn, pid, row["name"]):
        return {"colors": [], "note": "nhân vật mặc trang phục riêng của dự án — không so với ảnh mốc, chỉ so trong cảnh"}
    ref = _reference_path(conn, pid, row["name"])               # the stored spelling (the shot may write "Kelly")
    if not ref:
        return {"colors": [], "note": "nhân vật chưa có ảnh tham chiếu"}
    try:
        sha = file_sha(ref)
    except OSError as e:
        return {"colors": [], "note": f"không đọc được ảnh tham chiếu ({type(e).__name__}) — kiểm lại file trong Kho"}
    if stored.get("ref_sha") == sha:
        return stored
    data = {**extract(ref), "by": "auto", "ref_sha": sha, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _save(conn, row["id"], data)
    return data


def on() -> bool:
    from . import features
    return features.on("palette_check")


def attach(code: Dict, conn, pid: int, path: str, data: Dict) -> None:
    """Tổ QC: code["_palette"] = check of this frame against the reference palette (flag on; one character on the shot)."""
    if not on():
        return
    cast = [str(c) for c in (data or {}).get("characters") or []]
    if len(cast) != 1:
        code["_palette"] = {"status": "not_measurable", "missing": [], "note": f"bảng shot có {len(cast)} nhân vật — chỉ đo khung một người"}
        return
    pal = character_palette(conn, pid, cast[0])
    code["_palette"] = {**check(path, pal), "character": cast[0].upper()}


def note(res: Dict) -> Optional[str]:
    """The palette line for the person (Tổ QC note), only when something may be wrong."""
    parts = []
    ref = res.get("palette") or {}
    if ref.get("missing"):
        parts.append(ref["note"])
    scene = res.get("palette_scene") or {}
    if scene.get("outlier") or "khác màu" in str(scene.get("note") or ""):
        parts.append(scene["note"])
    return "Màu (code, thử): " + "; ".join(parts) if parts else None
