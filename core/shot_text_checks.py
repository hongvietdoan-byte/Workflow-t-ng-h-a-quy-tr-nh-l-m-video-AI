"""Bộ kiểm chữ prompt ảnh ↔ trường của shot (17/10, #31 — 0 USD, không gọi model, không sửa dữ liệu; luật 1: nói ra, không im lặng).

G7 — prompt ảnh tả một nhân vật / trang phục KHÔNG có trong `characters` của shot: #31 shot 31/35 viết "black Cloaked Terror trenchcoat
     with a white mask" (trang phục Tai Họa của cảnh 7) trong khi shot có Yêu nữ tà linh dạng 2, Xúc tu đỏ, Sứ giả → ảnh ref gửi theo
     danh sách nhân vật, chữ theo người khác: chữ và ảnh lệch nhau. Kiểm bằng tên + tên khác (alias, tiếng Anh) của Kho nhân vật /
     trang phục gắn dự án và tên trong bảng nhân vật dự án.
G8 — chữ giờ / thời tiết trong prompt ảnh trái trường `time` / `weather` của shot: #31 shot 27–30 time=dawn, weather=clear mà prompt
     "cold violet-red night sky", "fog" → nền 3D render theo trường (bình minh, trời quang), ảnh theo chữ (đêm, sương).
     Chỉ báo VÀNG (không tự sửa — người / Đạo diễn chọn bên đúng).

Kết quả dạng phần công thức ({level, part, msg}) — prompt_formula gộp vào formula_check (Bước 1); `notes()` = câu tiếng Việt cho diag
lúc dựng gói ảnh."""
import re
from typing import Dict, List

from . import assets

PART_CAST = "nhan_vat"
PART_LIGHT = "anh_sang"
MIN_NAME = 4                       # tên / alias bỏ dấu ngắn hơn → không dùng để khớp (tránh khớp nhầm từ ngắn)


def _issue(part: str, msg: str) -> Dict:
    return {"level": "warn", "part": part, "msg": msg}


# ---- G7: người / trang phục ngoài danh sách nhân vật của shot ---------------------------------------------------------------
def _spans(name: str, words: List[str]):
    if len(assets.fold(name)) < MIN_NAME:
        return []
    return assets.name_spans(name, words)


def cast_leaks(conn, project_id: int, data: Dict, text: str = None) -> List[Dict]:
    """[{who, said}] — nhân vật / trang phục của dự án (Kho kind character / outfit gắn dự án + bảng characters) mà chữ prompt ảnh
    nhắc tên / alias trong khi shot không có họ trong `characters`. Chỗ chữ trùng tên một người CÓ trong shot không tính."""
    data = data or {}
    text = str(data.get("image_prompt") or "") if text is None else str(text or "")
    if not text.strip() or conn is None or project_id is None:
        return []
    cast = [str(n) for n in data.get("characters") or [] if str(n or "").strip()]
    cast_f = {assets.fold(n) for n in cast}
    words = assets._said_words(text)
    try:
        pool = [a for a in assets.project_assets(conn, project_id) if a.get("kind") in ("character", "outfit")]
    except Exception:  # noqa: BLE001 - a database without the Kho: only the character table
        pool = []
    try:
        table = [r["name"] for r in conn.execute("SELECT name FROM characters WHERE project_id=?", (project_id,))]
    except Exception:  # noqa: BLE001
        table = []
    try:
        linked = assets.link_characters(conn, project_id, cast, data) if cast else {}
    except Exception:  # noqa: BLE001 - linking failed: by name only
        linked = {}
    own_ids = {a["id"] for a in linked.values() if a}
    groups = []                                     # (label, [names]) per person / outfit
    for a in pool:
        names = assets.names_of(a)
        mine = a["id"] in own_ids or any(assets.fold(n) in cast_f for n in names)
        groups.append((a["name"], names, mine))
    for n in table:
        if assets.fold(n) not in {assets.fold(x) for _, ns, _ in groups for x in ns}:
            groups.append((n, [n], assets.fold(n) in cast_f))
    taken = set()                                   # word positions said by a person IN the shot
    for _, names, mine in groups:
        if mine:
            for n in names:
                for a, b in _spans(n, words):
                    taken.update(range(a, b))
    out = []
    for label, names, mine in groups:
        if mine:
            continue
        said = [n.strip() for n in names for a, b in _spans(n, words) if not taken & set(range(a, b))]
        if said:
            out.append({"who": label, "said": list(dict.fromkeys(said))})
    return out


# ---- G8: giờ / thời tiết trong chữ ↔ trường time / weather ------------------------------------------------------------------
_TIME_RX = {
    "night": r"night(?:[- ]?time)?|midnight|moonlit|moonlight|starry sky|đêm|ban đêm",
    "dusk": r"dusk|sunset|twilight|golden hour|hoàng hôn|chạng vạng",
    "dawn": r"dawn|sunrise|daybreak|first light|bình minh|rạng sáng",
    "day": r"daylight|daytime|midday|noon|sunny|broad day|bright day|ban ngày|giữa trưa|nắng gắt",
}
_WEATHER_RX = {
    "fog": r"fog|foggy|mist|misty|haze|hazy|sương mù",
    "rain": r"rain(?![- ]?(?:coat|boots?|slicker))|raining|rainy|drizzle|downpour|mưa",
    "snow": r"snow|snowy|snowfall|blizzard|tuyết",
}
_WEATHER_FAMILY = {"fog": "fog", "rain": "rain", "storm": "rain", "snow": "snow", "snowfall": "snow", "ice": "snow"}


def _found(rx: str, text: str) -> List[str]:
    out = []
    for m in re.finditer(r"(?<!\w)(?:" + rx + r")(?!\w)", text, re.I):
        before = text[max(0, m.start() - 24):m.start()].lower()
        if re.search(r"(?:\bno|\bnot|\bnever|\bwithout|không có|không)\s+(?:\w+\s+){0,1}$", before):
            continue                                # "no fog", "never pitch black night" style negations
        out.append(m.group(0).lower())
    return list(dict.fromkeys(out))


def time_weather_conflicts(data: Dict, text: str = None) -> List[str]:
    """Câu tiếng Việt — chữ giờ / thời tiết của prompt ảnh trái trường time / weather (chỉ khi trường có giá trị đã biết). Giờ: chữ
    của giờ KHÁC có mà chữ của giờ shot không có. Thời tiết: chữ sương / mưa / tuyết khác loại trường (trời quang = không có loại nào)."""
    data = data or {}
    text = str(data.get("image_prompt") or "") if text is None else str(text or "")
    if not text.strip():
        return []
    out = []
    time = str(data.get("time") or "").strip().lower()
    if time in _TIME_RX:
        own = _found(_TIME_RX[time], text)
        other = {t: _found(rx, text) for t, rx in _TIME_RX.items() if t != time}
        other = {t: w for t, w in other.items() if w}
        if other and not own:
            said = "; ".join(f"{t}: {', '.join(w)}" for t, w in other.items())
            out.append(f"giờ của shot là '{time}' nhưng chữ prompt ảnh tả giờ khác ({said}) — nền 3D render theo trường time, ảnh theo chữ: "
                       "sửa chữ hoặc sửa trường time cho khớp")
    weather = str(data.get("weather") or "").strip().lower()
    if weather in ("clear", "cloudy") or weather in _WEATHER_FAMILY:
        mine = _WEATHER_FAMILY.get(weather)
        for fam, rx in _WEATHER_RX.items():
            if fam == mine:
                continue
            words = _found(rx, text)
            if words:
                out.append(f"thời tiết của shot là '{weather}' nhưng chữ prompt ảnh tả {fam} ({', '.join(words)}) — nền 3D render theo "
                           "trường weather: sửa chữ hoặc sửa trường weather cho khớp")
    return out


# ---- gộp ----------------------------------------------------------------------------------------------------------------
def issues(conn, project_id: int, data: Dict) -> List[Dict]:
    """Phần công thức cho formula_check (Bước 1). Không bao giờ ném (lỗi kiểm thành một cảnh báo)."""
    out = []
    try:
        for x in cast_leaks(conn, project_id, data):
            cast = ", ".join(str(n) for n in (data or {}).get("characters") or []) or "không ai"
            out.append(_issue(PART_CAST, f"chữ prompt ảnh tả {x['who']} ({', '.join(x['said'])}) nhưng nhân vật/trang phục này KHÔNG có "
                                         f"trong danh sách nhân vật của shot ({cast}) — ảnh ref gửi theo danh sách, chữ theo người khác: "
                                         "bỏ chữ đó hoặc thêm nhân vật vào shot"))
    except Exception as e:  # noqa: BLE001 - a check, never a reason to lose the plan
        out.append(_issue(PART_CAST, f"không kiểm được nhân vật ngoài danh sách: {type(e).__name__}: {e}"))
    try:
        out += [_issue(PART_LIGHT, m) for m in time_weather_conflicts(data)]
    except Exception as e:  # noqa: BLE001
        out.append(_issue(PART_LIGHT, f"không kiểm được giờ/thời tiết: {type(e).__name__}: {e}"))
    return out


def notes(conn, project_id: int, data: Dict) -> List[str]:
    """Câu diag VÀNG lúc dựng gói ảnh (runner) — cùng nội dung issues()."""
    return [i["msg"] for i in issues(conn, project_id, data)]
