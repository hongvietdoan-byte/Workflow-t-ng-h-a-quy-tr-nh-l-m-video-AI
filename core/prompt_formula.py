"""Công thức prompt (F1-A, 09/10/2026) — code kiểm PHẦN của prompt ảnh khung đầu / motion, không kiểm câu chữ, không gọi model.

Nguồn: docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md (người dùng đã duyệt) mục 1–4b; sổ công thức knowledge/formula/ (anh_khung_dau.md,
motion.md) giải thích từng phần: bắt buộc khi nào, lấy từ trường nào của scenes.data, ví dụ #22, lý do, code kiểm gì.

Vì sao: #22 đẹp nhờ câu viết tay (khóa nền, trang phục từng món, khóa tóc…) — không câu nào quay về hệ thống; #24 hỏng vì prompt là
nhiều câu nối dần theo từng lỗi, có câu tự mâu thuẫn (trung cận ↔ ngồi bệt; luật mắt người ↔ yêu nữ mắt đỏ), từ ghê không tiết chế,
bóng lao sát mặt không có đường đi. Code chỉ báo ĐÚNG những điều đó; phần sáng tạo của Đạo diễn để nguyên.

    shot_kind(data, chars=None) -> dialogue | action | dance_ref | object | establishing | creature | skill_fx | other
    lint_image(prompt, data, chars=None) / lint_motion(prompt, data, chars=None) -> [{"level": "red"|"warn", "part", "msg"}]
    cross_shot(shots) -> [issue + "shots"]          cùng món đồ của cùng nhân vật khác màu giữa các shot (warn)
    growth_check(old, new) -> [issue]                lớp dò "viết chồng thêm" (mục 4b)
    review_shot(data, image_prompt, motion_prompt, chars=None, previous=None) -> {"image", "motion", "growth", "red"}
    red_issues(conn, scene_id, kind=None) -> [câu]   phiên chính gọi từ ImageRunner/VideoRunner._blocked (nhánh này chưa chặn)

Giới hạn (nói rõ, không giả vờ hiểu câu): so bằng regex tiếng Anh có \\b và cụm tiếng Việt CÓ DẤU (không bỏ dấu: "máu" ≠ "màu");
"chi tiết ghê" chỉ cần MỘT câu tiết chế ở bất kỳ đâu trong prompt; màu trang phục chỉ bắt "màu + (≤ 3 từ) + tên món" và gán cho tên
nhân vật đứng gần nhất phía trước. Cờ `prompt_formula` tắt → không kiểm, không ghi.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

I = re.I

# ---- tên phần (khớp knowledge/formula/*.md) -----------------------------------------------------------------------------------
PART_LABELS = {
    "phong_cach": "Phong cách", "khung_hinh": "Khung hình", "khoa_nen": "Khóa nền", "noi_tiep": "Nối tiếp", "nhan_vat": "Nhân vật",
    "khoanh_khac": "Khoảnh khắc", "luat_ff": "Luật FF", "anh_sang": "Ánh sáng", "chot_chat_luong": "Chốt chất lượng",
    "diem_bat_dau": "Điểm bắt đầu", "hanh_dong": "Hành động", "vat_ly": "Vật lý", "may_quay": "Máy quay", "trang_thai_cuoi": "Trạng thái cuối",
    "nguon_dong_tac": "Nguồn động tác", "thoai": "Thoại", "duong_di_vat_gan_nguoi": "Đường đi vật gần người",
    "loai_nhan_vat": "Loại nhân vật", "mau_thuan": "Câu mâu thuẫn", "cau_chu": "Ngắt câu", "viet_chong": "Viết chồng thêm",
    "ta_cai_dung": "Tả cái đúng",
}
CLOSE_SIZES = ("ECU", "CU", "MCU")
WIDE_SIZES = ("WS", "EWS", "MLS")

# ---- (a) phần bắt buộc -------------------------------------------------------------------------------------------------------
_STYLE = re.compile(r"free fire|in-game 3d|\b3d render\b|\bgame render\b|stylized proportions", I)
_FRAMING = re.compile(r"\b(?:extreme )?close[- ]up\b|\bmedium(?: long| close)?[- ]shot\b|\bmedium close[- ]up\b|\b(?:extreme )?wide shot\b|"
                      r"\blong shot\b|\bfull[- ]bod(?:y|ies)\b|over[- ]the[- ]shoulder|\bestablishing shot\b|\binsert shot\b|\bpov\b|"
                      r"\bfrom (?:the )?(?:mid-?chest|chest|waist|knees|shoulders) up\b|\btwo[- ]shot\b|\bcận cảnh\b|\btrung cảnh\b|"
                      r"\btoàn cảnh\b|\btrung cận\b", I)
_ING_STOP = {"lighting", "everything", "nothing", "something", "anything", "building", "buildings", "ceiling", "evening", "morning",
             "clothing", "painting", "string", "ring", "wing", "king", "thing", "things", "spring", "swing", "ceiling", "awning", "railing",
             "wedding", "pudding", "during", "framing", "setting", "blocking", "opening", "ending", "bring"}
_MOMENT = re.compile(r"\bmid[- ]\w+|\b\w{3,}ing\b|\bfrozen\b|\bpos(?:e|es|ed)\b|\bseated\b|\bcrouched\b|\bkneels?\b|\bstands?\b|\bsits?\b|"
                     r"\bleans?\b|\blooks?\b|\bholds?\b|\bđứng\b|\bngồi\b|\bnhìn\b|\bcúi\b|\bchạy\b|\bquỳ\b|\bnằm\b", I)
_LIGHT = re.compile(r"light|\blit\b|\bsun\w*|\bmoon\w*|\blamp|\bdaylight\b|\bnight\b|ánh sáng|\bđèn\b|\bnắng\b|\btrăng\b", I)
_START = re.compile(r"\b(?:clip|shot|video) (?:starts|begins|opens)\b|\bstarts? (?:exactly )?(?:on|from|with)\b|\bfirst (?:image|frame)\b|"
                    r"\bopening frame\b|\bbegins? (?:on|from|with)\b|bắt đầu|khung đầu", I)
_ACTION = re.compile(
    r"\b(?:then|turns?|walks?|steps?|moves?|spins?|lifts?|raises?|grips?|crawls?|leans?|looks?|runs?|jumps?|says?|reaches?|falls?|"
    r"flicks?|lands?|holds?|nods?|smiles?|points?|opens?|closes?|pulls?|pushes|drops?|picks?|throws?|dances?|kicks?|punches|shoots?|"
    r"waves?|sits?|stands?|kneels?|rises?|freezes?|stares?|glances?|shakes?|grabs?|hugs?|climbs?|slides?|rolls?|ducks?|dodges?|fires?|"
    r"aims?|leaps?|crouches|backs away|emerges?|appears?|vanishes|flies|streaks?|rushes|lunges?)\b|"
    r"\bquay\b|\bbước\b|\bchạy\b|\bnhảy\b|\bngã\b|\bcúi\b|\bgiơ\b|\bvung\b|\bbò\b", I)
_CAMERA = re.compile(r"\bcamera\b|\bstatic\b|\bpush(?:es)?[- ]in\b|\bpull(?:s)?[- ](?:out|back)\b|\bdolly\b|\bpan(?:s|ning)?\b|"
                     r"\btracking\b|\borbit\w*\b|\bcrane\b|\bzoom\w*\b|\bhandheld\b|\blocked[- ]off\b|máy quay|máy đứng|máy tĩnh", I)
_DIALOGUE = re.compile(r"\bsays?\b|\bspeaks?\b|\bsaying\b|\bline\b|\bmouth\b|\blips?\b|\btalks?\b|\bnói\b|thoại|khẩu hình", I)
_DANCE_SRC = re.compile(r"reference video|ref(?:erence)? clip|beat by beat|<<<video_\d+>>>|video mẫu|video tham chiếu|exactly the moves", I)
_END = re.compile(r"\bends?\b|\bending\b|\bholds?\b|\buntil\b|\bfinal\b|\bfinish\w*\b|\bsettles?\b|\bstops?\b|\bcomes to rest\b|"
                  r"\blast frame\b|\bkết\b|\bdừng\b|\bgiữ\b", I)

# ---- (b) khung ↔ tư thế -------------------------------------------------------------------------------------------------------
_CLOSE = re.compile(r"\bmedium close[- ]up\b|\b(?:extreme )?close[- ]up\b|\bno legs\b|\bmid[- ]chest up\b|\bfrom the (?:chest|waist|shoulders?) up\b|"
                    r"\bhead and shoulders\b|\bcận mặt\b|\btrung cận\b|không thấy chân", I)
_CLOSE_CS = re.compile(r"\b(?:MCU|ECU|CU)\b")
_LEGS = re.compile(r"\bsprawl\w*\b|\bseated on the (?:ground|floor)\b|\bsit(?:s|ting)? on the (?:ground|floor)\b|"
                   r"\blegs? (?:stretched|spread|outstretched|splayed|sprawled)\b|\bstretched[- ]out legs\b|\bkneeling,? full[- ]body\b|"
                   r"\bfull[- ]bod(?:y|ies)\b(?! (?:reference|sheet|picture|image|turnaround|character sheet)\b)|\bfeet (?:are )?visible\b|\b(?:whole|entire) body\b|\bhead to toe\b|ngồi bệt|thấy chân|"
                   r"duỗi chân|sõng soài|\bcả người\b", I)

# ---- (c) chi tiết ghê — luật tầng 1 cho mọi dự án Free Fire (người dùng chốt 09/10) ----------------------------------------
# F1 sửa (09/10): MỘT bộ từ máu/xác chung với câu tiết chế (looks._GORE qua looks.gore_search) — trước đây hai regex lệch nhau.
_RESTRAINT = re.compile(r"\bonly (?:hinted|suggested|implied)\b|\bhinted\b|\bin (?:deep |dark )?shadows?\b|\bout of focus\b|\bpart(?:ly|ially) hidden\b|"
                        r"\bbarely visible\b|\boff[- ]screen\b|\bimplied\b|(?<!not )\bblurred\b|\bsoft[- ]focus\b|chỉ gợi|trong tối|"
                        r"ngoài nét|che khuất|\bkhuất\b|\bmờ\b", I)

# ---- (d) vật / bóng / sinh vật lao sát nhân vật ----------------------------------------------------------------------------
_RUSH = re.compile(r"\b(?:streak\w*|dash(?:es|ed|ing)?|fl(?:y|ies|ying|ew)|rush\w*|lung(?:e|es|ed|ing)|whoosh\w*|swoop\w*|dart(?:s|ed|ing)?|"
                   r"zoom(?:s|ing)? past|shoot(?:s|ing)? (?:past|across)|hurtl\w*|leap(?:s|ing)? at)\b|\blao\b|\bvụt\b|\blướt\b", I)
_NEAR = re.compile(r"\b(?:right )?in front of (?:her|his|their|[a-z]+'s) (?:face|head|eyes|nose|body)\b|\bright in front of (?:her|him|them)\b|"
                   r"\b(?:right )?next to (?:her|him|them)\b|\bpast (?:her|his|their) (?:face|head|ears?|eyes)\b|\binches from\b|"
                   r"\bacross (?:her|his|their) (?:face|eyes)\b|\btoward (?:her|his|their) face\b|\bbrush\w* (?:past )?(?:her|him|them)\b|"
                   r"sát mặt|lướt qua mặt|ngay trước mặt", I)
_PATH = re.compile(r"\bfrom\b[^.,;]{1,60}?\b(?:to|toward|towards|into|until)\b|\bđi từ\b|\btừ [^.,;]{1,40} (?:đến|tới|sang)\b", I)
_NO_TOUCH = re.compile(r"\bnever (?:touch\w*|pass\w* through|hits?|contacts?)\b|\bdoes(?:n't| not) (?:touch|pass through|hit)\b|"
                       r"\bwithout touching\b|\bkeeps? (?:a )?(?:clear |safe )?distance\b|không chạm|không xuyên|không đụng", I)

# ---- (e)(f) luật người ↔ nhân vật không phải người; cặp đối nghịch -------------------------------------------------------
_HUMAN_EYES = re.compile(r"\bnatural human eyes\b|\bno glowing eyes\b|\bnormal human eyes\b|\beyes (?:do not|don't|never) glow\b|"
                         r"mắt người bình thường|không (?:có )?mắt phát sáng", I)
_GLOW_EYES = re.compile(r"\bglowing (?:red |white |blue |green |yellow )?eyes\b|\beyes?\b[^.;,]{0,12}?\bglow(?:ing|s)?\b|"
                        r"mắt (?:đỏ )?phát sáng|mắt đỏ rực", I)
_NAMED_EYES = re.compile(r"^\s*([^:]{1,160}?):\s*(?:natural|normal) human eyes\b", I)   # eyes_guard: "KELLY: natural human eyes"
NON_HUMAN_KINDS = ("creature", "monster", "animal", "non_human", "pet", "quai")
_CAM_STATIC = re.compile(r"\bstatic camera\b|\bcamera (?:is |stays |remains |holds )?(?:completely |fully |totally )?(?:static|locked)\b|"
                         r"\blocked[- ]off\b|máy (?:quay )?(?:đứng yên|tĩnh)", I)
_CAM_MOVE = re.compile(r"\bpush(?:es|ing)?[- ]in\b|\bdoll(?:y|ies|ying)\b|\borbit(?:s|ing)?\b|\bzoom(?:s|ing)? in\b|"
                       r"\bcamera (?:slowly |gently |then )?(?:pulls?|pushes|tracks|pans|tilts|zooms|moves|drifts|rises|cranes|orbits)\b|"
                       r"máy (?:quay )?(?:đẩy|lùi|lia|xoay|di chuyển)", I)
_NEG_OBJ = (re.compile(r"\bno ([a-z]+(?: [a-z]+)?) (?:in|inside|within) (?:the )?frame\b", I),
            re.compile(r"\b(?:the )?([a-z]+ [a-z]+) (?:is |stays |kept )?(?:out of frame|off[- ]frame|out of shot)\b", I))

# ---- (g) câu dính liền mất dấu chấm --------------------------------------------------------------------------------------
_RUNON = re.compile(r"\b([a-z]{3,}) ((?:[A-Z][A-Z0-9'’]+ ){1,3})(keeps|wears|has|is|stands|holds|looks|must|stays|remains|always|never|does|"
                    r"gets|sits|walks|turns|says)\b")
_RUNON_STOP = {"the", "and", "with", "from", "for", "her", "his", "their", "its", "into", "onto", "over", "under", "that", "this", "than",
               "worn", "wearing", "named", "called", "like", "who", "while", "when", "where", "but", "nor", "both", "only", "not", "then"}

# ---- (h) liệt kê vật cấm (F1-C, bài học L2 #22: nhắc chữ của lỗi kéo lỗi lại) --------------------------------------------
# "Do NOT add palm trees, grass fields, cars" / "never draw X, Y" / "no trees, no cars" / "no plaza, tower, sky or sea". Một phủ định đơn
# ("no legs or full body") và phủ định PHONG CÁCH/ảnh chú thích (anime, blur, chữ, người trong ảnh nền trống) không bị báo: có bằng chứng
# riêng (looks.py, #8 anime) và không phải vật trong cảnh.
_NEG_VERB = re.compile(r"\b(?:do not|don't|never|must not)\s+(?:add|draw|include|show|put|place|render|paint)\b[:\s]+"
                       r"([^.;]{3,200})", I)
_NEG_NO = re.compile(r"\bno\s+([a-z][a-z -]{1,40}?)\s*,\s*(no\s+)?([a-z][a-z -]{1,40}?)(?=\s*(?:,|\bor\b|\band\b|[.;]|$))", I)
_NEG_SAFE = re.compile(r"\b(?:anime|cartoon|2d|3d style|blur\w*|grading|grain|bokeh|photo\w*|still|style|shooter|cinematic|watermarks?|"
                       r"text|logos?|captions?|subtitles?|labels?|hud|ui|interface|sound|cuts?|people|persons?|characters?|humans?|"
                       r"legs|full body|glowing eyes|human eyes|sliding|foot sliding|morphing|distortion)\b", I)


def _neg_lists(prompt: str) -> List[str]:
    """The negated lists of things (≥ 2 items) the prompt names — style / annotation negations left out."""
    out = []
    for m in _NEG_VERB.finditer(prompt):
        items = [x.strip() for x in re.split(r",|\bor\b|\band\b", m.group(1)) if x.strip()]
        items = [x for x in items if not _NEG_SAFE.search(x)]
        if len(items) >= 2:
            out.append(m.group(0).strip())
    for m in _NEG_NO.finditer(prompt):
        items = [m.group(1), m.group(3)]
        if not m.group(2) and len(m.group(3).split()) > 3:
            continue                     # phiên sửa: "no clock tower in frame, cold moonlit fog at night" — the 2nd part describes
        if not any(_NEG_SAFE.search(x) for x in items):
            out.append(m.group(0).strip())
    return list(dict.fromkeys(out))


# ---- loại shot -----------------------------------------------------------------------------------------------------------
_DANCE = re.compile(r"\b(?:danc\w+|choreo\w*)\b|\bnhảy theo\b|vũ đạo|điệu nhảy", I)
_SKILL = re.compile(r"\bskill\b|kỹ năng|\bfx\b|\baura\b|\benergy (?:blast|wave|shield)\b|hiệu ứng", I)
_ACTION_KIND = re.compile(r"\b(?:run\w*|jump\w*|fall\w*|fight\w*|shoot\w*|punch\w*|kick\w*|dodg\w*|crawl\w*|lunge\w*|chase\w*)\b|"
                          r"\bchạy\b|\bnhảy\b|\bngã\b|\bbắn\b|\bđánh\b|\blao\b|\bbò\b|\bđuổi\b|\bnhào\b|\bvồ\b", I)
REF_KEYS = ("ref_video", "ref_video_path", "motion_ref", "dance_ref", "reference_video")


def enabled() -> bool:
    try:
        from . import features
        return features.on("prompt_formula")
    except Exception:  # noqa: BLE001 - an unreadable settings file never stops the pipeline; the default (on) holds
        return True


def _issue(level: str, part: str, msg: str, **extra) -> Dict:
    return {"level": level, "part": part, "msg": msg, **extra}


def _snip(m: Optional[re.Match]) -> str:
    return m.group(0).strip() if m else ""


def _names(data: Dict) -> List[str]:
    return [str(c) for c in data.get("characters") or [] if str(c).strip()]


def _shot_chars(data: Dict, chars: Optional[List[Dict]]) -> List[Dict]:
    names = set(_names(data))
    return [c for c in chars or [] if isinstance(c, dict) and (not names or c.get("name") in names)]


def _data_text(data: Dict, keys=("blocking", "start_frame", "action", "action_peak", "end_state")) -> str:
    parts = [str(data.get(k) or "") for k in keys]
    perf = data.get("performance")
    if isinstance(perf, dict):
        parts += [str(v) for v in perf.values() if isinstance(v, str)]
    return " ".join(p for p in parts if p)


def _looks_non_human(text: str) -> bool:
    from .assets import looks_non_human          # the ONE creature word list (F1 sửa #1)
    return looks_non_human(text)


def _profile_non_human(c: Dict) -> bool:
    """A character profile (characters row; `_human` = assets.is_human when read from the database) that is not a person."""
    if c.get("_human") is False or str(c.get("kind") or "").lower() in NON_HUMAN_KINDS:
        return True
    desc = _HUMAN_EYES.sub(" ", " ".join(str(c.get(k) or "") for k in ("description", "lock_rules")))
    return _looks_non_human(desc) or bool(_GLOW_EYES.search(desc))


def _text_non_human(data: Dict, chars: Optional[List[Dict]]) -> bool:
    """Shot kind only (creature): a character of the shot, or the shot's own words, is a creature / ghost / has glowing eyes."""
    if any(_profile_non_human(c) for c in _shot_chars(data, chars)):
        return True
    for t in (_HUMAN_EYES.sub(" ", _data_text(data)), " ".join(_names(data))):
        if _looks_non_human(t) or _GLOW_EYES.search(t):
            return True
    return False


def _eye_rule_on_non_human(prompt: str, data: Dict, chars: Optional[List[Dict]]) -> str:
    """F1 sửa #1 (09/10): who a human-eyes rule is written for and is not a person — '' when nobody. A named rule ("KELLY: natural
    human eyes", seedance_refs.eyes_guard) is judged on those names only; a general one on the shot's characters (data.characters) by
    their profile / name — never on the action's words ("the ghost streaks past" does not make Kelly a ghost)."""
    known = {n.lower(): n for n in _names(data)}
    targets: List[str] = []
    for s in _sentences(prompt):
        if not _HUMAN_EYES.search(s):
            continue
        m = _NAMED_EYES.match(s)
        named = [t.strip() for t in m.group(1).split(",") if t.strip()] if m else []
        targets += [known.get(t.lower(), t) for t in named] if named else _names(data)
    profiles = {str(c.get("name")): c for c in chars or [] if isinstance(c, dict)}
    for n in dict.fromkeys(targets):
        c = profiles.get(n)
        if (c is not None and _profile_non_human(c)) or _looks_non_human(n):
            return n
    return ""


def shot_kind(data: Dict, chars: Optional[List[Dict]] = None) -> str:
    """dialogue / action / dance_ref / object / establishing / creature / skill_fx / other — chọn bộ phần bắt buộc (F0 mục 1)."""
    data = data or {}
    action = _data_text(data, ("action", "action_peak", "blocking", "text"))
    has_people = bool(_names(data))
    if any(data.get(k) for k in REF_KEYS) or (has_people and _DANCE.search(action)):
        return "dance_ref"
    if _SKILL.search(action):
        return "skill_fx"
    if has_people and _text_non_human(data, chars):
        return "creature"
    if any(isinstance(d, dict) and str(d.get("text") or "").strip() for d in data.get("dialogue") or []):
        return "dialogue"
    if not has_people:
        if data.get("size") in CLOSE_SIZES or data.get("role") == "insert":
            return "object"
        if data.get("size") in WIDE_SIZES or data.get("size") == "GAME_TPS" or data.get("role") in ("establishing", "hook"):
            return "establishing"
        return "other"
    if data.get("role") == "action" or _ACTION_KIND.search(action):
        return "action"
    return "other"


# ---- (f) cặp đối nghịch ------------------------------------------------------------------------------------------------
def _find_static(t):
    return _snip(_CAM_STATIC.search(t))


def _find_move(t):
    return _snip(_CAM_MOVE.search(t))


def _find_human(t):
    return _snip(_HUMAN_EYES.search(t))


def _find_glow(t):
    return _snip(_GLOW_EYES.search(_HUMAN_EYES.sub(" ", t)))


PAIRS = (("máy quay", _find_static, _find_move, "giữ MỘT kiểu máy: tĩnh hoặc chuyển động (đẩy/lùi/xoay) — bỏ câu kia"),
         ("mắt", _find_glow, _find_human, "nhân vật mắt phát sáng thì bỏ câu luật mắt người; người thường thì bỏ câu mắt phát sáng"))


def _hidden_shown(a: str, b: str) -> List[Tuple[str, str]]:
    """'no clock tower in frame' in a ↔ 'clock tower … visible' in b."""
    out = []
    for rx in _NEG_OBJ:
        for m in rx.finditer(a):
            obj = m.group(1).lower()
            if obj in ("one", "other", "people", "person"):
                continue
            seen = re.search(rf"\b{re.escape(obj)}\b[^.;]{{0,40}}?(?<!not )(?<!never )\bvisible\b", b, I)
            if seen:
                out.append((m.group(0), seen.group(0)))
    return out


def contradictions(a: str, b: str) -> List[Tuple[str, str, str, str]]:
    """[(tên cặp, đoạn trong a, đoạn trong b, cách sửa)] — a == b kiểm trong một prompt."""
    out = []
    for name, fx, fy, fix in PAIRS:
        for f1, f2 in ((fx, fy), (fy, fx)):
            x, y = f1(a or ""), f2(b or "")
            if x and y:
                out.append((name, x, y, fix))
                break
    for x, y in _hidden_shown(a or "", b or "") + ([] if a == b else [(y, x) for x, y in _hidden_shown(b or "", a or "")]):
        out.append(("vật trong khung", x, y, "vật đã ghi 'không có trong khung' thì bỏ câu tả nó hiện ra (hoặc ngược lại)"))
    return out


# ---- kiểm chung cho ảnh + motion ----------------------------------------------------------------------------------------
def _sentences(text: str) -> List[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _common(prompt: str, data: Dict, chars: Optional[List[Dict]], kind_word: str, ff: Optional[bool] = None) -> List[Dict]:
    from . import looks
    out = []
    gore = looks.gore_search(prompt)
    if gore and not _RESTRAINT.search(prompt):      # ff False (another game): the FF rule is only a warning (F1 sửa #6)
        out.append(_issue("warn" if ff is False else "red", "luat_ff", f"Chi tiết ghê “{_snip(gore)}” không có câu tiết chế — luật mọi dự án Free Fire: chỉ gợi "
                                            "(only hinted / in shadow / out of focus / partly hidden), không 'everything in focus' trên nó; "
                                            "hoặc bỏ hẳn chi tiết đó."))
    for s in _sentences(prompt):
        rush, near = _RUSH.search(s), _NEAR.search(s)
        if rush and near:
            has_path, no_touch = bool(_PATH.search(s)), bool(_NO_TOUCH.search(prompt))
            if not has_path and not no_touch:
                out.append(_issue("red", "duong_di_vat_gan_nguoi",
                                  f"Vật/bóng lao sát nhân vật (“{_snip(rush)} … {_snip(near)}”) mà không có đường đi lẫn câu không chạm — "
                                  "model hay cho nó xuyên vào người (#24 shot 3 bản cao). Ghi điểm đầu → điểm cuối (from … to …), "
                                  "khoảng cách, và 'never touches or passes through her'."))
            elif not (has_path and no_touch):
                out.append(_issue("warn", "duong_di_vat_gan_nguoi",
                                  "Vật/bóng lao sát nhân vật: " + ("thiếu câu 'never touches or passes through …'" if has_path
                                                                   else "thiếu đường đi from … to … (điểm đầu → điểm cuối, khoảng cách)")))
            break
    human = _HUMAN_EYES.search(prompt)
    if human:
        what = _eye_rule_on_non_human(prompt, data, chars)
        if what:
            out.append(_issue("red", "loai_nhan_vat",
                              f"Luật của người “{_snip(human)}” áp cho nhân vật không phải người ({what}) — luật mắt người chỉ dành cho "
                              "người; nhân vật quái/yêu/ma giữ đặc điểm của nó. Bỏ câu luật người trong prompt " + kind_word + "."))
    for name, x, y, fix in contradictions(prompt, prompt):
        out.append(_issue("red", "mau_thuan", f"Prompt tự mâu thuẫn ({name}): “{x}” ↔ “{y}” — {fix}."))
    for neg in _neg_lists(prompt)[:2]:
        out.append(_issue("warn", "ta_cai_dung", f"Liệt kê vật cấm “{neg[:90]}” — nhắc tên thứ cấm hay kéo đúng thứ đó vào ảnh (bài học L2 "
                                                 "#22). Tả cái ĐÚNG thay vào (vd 'chỉ có cầu thang, tường, tháp, nhà 3 tầng như render 3D')."))
    for m in _RUNON.finditer(prompt):
        if m.group(1).lower() in _RUNON_STOP:
            continue
        out.append(_issue("warn", "cau_chu", f"Câu dính liền mất dấu chấm: “{m.group(0)}” — thêm dấu chấm trước "
                                             f"“{m.group(2).strip()}” (câu ghép thêm vào cuối, model đọc thành một câu)."))
    return out


def lint_image(prompt: str, data: Dict, chars: Optional[List[Dict]] = None, style_by_code: bool = False,
                ff: Optional[bool] = None) -> List[Dict]:
    """Prompt ảnh khung đầu: phần bắt buộc (a), khung ↔ tư thế (b), luật FF (c), vật lao sát người (d), luật người/quái (e),
    tự mâu thuẫn (f), câu dính (g). Phần code tự thêm khi dựng prompt (runner.build_image_prompt) không bị đòi trong câu của Đạo diễn:
    khung hình khi có `size` (framing_sentence), khoảnh khắc khi có `action_peak`/`performance`, phong cách khi `style_by_code` (dự án
    có look — looks.image_sentence)."""
    prompt, data = prompt or "", data or {}
    kind = shot_kind(data, chars)
    out = []
    if not style_by_code and not _STYLE.search(prompt):
        out.append(_issue("warn", "phong_cach", "Thiếu phong cách: thêm 'Free Fire in-game 3D render, stylized proportions, moderate "
                                                "texture detail, clear gameplay lighting'."))
    if not data.get("size") and not _FRAMING.search(prompt) and not _CLOSE_CS.search(prompt):
        out.append(_issue("warn", "khung_hinh", "Thiếu khung hình: ghi cỡ cảnh KÈM giới hạn cơ thể (vd 'medium close-up from mid-chest "
                                                "up, no legs' / 'wide shot, full bodies with feet visible') + góc máy."))
    if _names(data) and kind not in ("object", "establishing") and not data.get("action_peak") and not data.get("performance") and not any(
            m.group(0).lower() not in _ING_STOP for m in _MOMENT.finditer(prompt)):
        out.append(_issue("warn", "khoanh_khac", "Thiếu khoảnh khắc khung đầu: tả MỘT trạng thái đúng lúc mở clip (vd 'mid-step, "
                                                 "looking toward the bed off-screen right', 'leaning over the rim')."))
    if not _LIGHT.search(prompt):
        out.append(_issue("warn", "anh_sang", "Thiếu ánh sáng: ghi nguồn + hướng (vd 'soft window light from the side', 'cold "
                                              "moonlight from above')."))
    close = _CLOSE.search(prompt) or _CLOSE_CS.search(prompt)
    close_word = _snip(close) or (data.get("size") if data.get("size") in CLOSE_SIZES else "")
    if close_word:
        # F1 sửa #9: red only when the pose is in the prompt itself (or the acting the code writes into it); a pose only in the
        # blocking (often the whole sequence's positions) is a warning
        perf = data.get("performance")
        acting = " ".join(str(v) for v in perf.values() if isinstance(v, str)) if isinstance(perf, dict) else ""
        legs = _LEGS.search(prompt + " " + acting)
        side = None if legs else _LEGS.search(" ".join(str(data.get(k) or "") for k in ("blocking", "start_frame")))
        if legs or side:
            out.append(_issue("red" if legs else "warn", "khung_hinh",
                              f"Khung “{close_word}” (không thấy chân) mâu thuẫn tư thế “{_snip(legs or side)}” (cần thấy chân/cả người)"
                              + ("" if legs else " — tư thế chỉ ghi ở blocking") + " — đổi cỡ cảnh sang MS/WS, hoặc tả tư thế bằng "
                              "phần trên người (vai ngả ra sau, tay chống phía sau)."))
    out += outfit_issues(prompt + " " + _data_text(data, ("blocking", "start_frame", "action_peak")), data, chars)
    return out + _common(prompt, data, chars, "ảnh", ff)


def lint_motion(prompt: str, data: Dict, chars: Optional[List[Dict]] = None, ff: Optional[bool] = None) -> List[Dict]:
    """Prompt motion: điểm bắt đầu / hành động / máy quay (a), thoại / nguồn động tác / trạng thái cuối khi có, + (c)–(g)."""
    prompt, data = prompt or "", data or {}
    kind = shot_kind(data, chars)
    out = []
    if not _START.search(prompt):
        out.append(_issue("warn", "diem_bat_dau", "Thiếu điểm bắt đầu: 'The clip starts exactly on the pose and framing of the first "
                                                  "image'."))
    if kind not in ("establishing", "object") and not _ACTION.search(prompt):
        out.append(_issue("warn", "hanh_dong", "Thiếu hành động: chuỗi động từ có thứ tự + điểm dừng (vd 'spins once…, then lands a "
                                               "playful pose and holds it')."))
    if not _CAMERA.search(prompt):
        out.append(_issue("warn", "may_quay", "Thiếu máy quay: kiểu + mức + khung giữ (vd 'Static camera' / 'almost static, only a "
                                              "very slow tiny drift, holding the same framing')."))
    if any(isinstance(d, dict) and str(d.get("text") or "").strip() for d in data.get("dialogue") or []) and not _DIALOGUE.search(prompt):
        out.append(_issue("warn", "thoai", "Shot có thoại mà motion không nói ai nói: 'says his line…; his mouth moves only while he "
                                           "speaks'."))
    if kind == "dance_ref" and not _DANCE_SRC.search(prompt):
        out.append(_issue("warn", "nguon_dong_tac", "Có video mẫu mà không nói nguồn động tác: 'exactly the moves of the reference video, "
                                                    "beat by beat; the dancer only gives the motion — never take her face, clothes or "
                                                    "room'."))
    if str(data.get("end_state") or "").strip() and not _END.search(prompt):
        out.append(_issue("warn", "trang_thai_cuoi", f"Thiếu trạng thái cuối (Đạo diễn ghi: “{str(data['end_state'])[:80]}”) — thêm "
                                                     "'It ends with …' để clip có điểm dừng."))
    out += outfit_issues(prompt, data, chars)
    return out + _common(prompt, data, chars, "motion", ff)


# ---- giữa các shot: cùng món đồ khác màu -------------------------------------------------------------------------------
COLORS = ("red", "blue", "green", "black", "white", "yellow", "pink", "purple", "orange", "brown", "grey", "gray", "silver", "gold",
          "golden", "navy", "beige", "cyan", "teal")
ITEMS = ("horns?", "print", "cap", "hat", "hoodie", "jacket", "hair", "mask", "croptop", "crop top", "shirt", "t-shirt", "top", "pants",
         "trousers", "jeans", "shorts", "skirt", "shoes", "boots", "sneakers", "gloves", "sleeves", "dress", "scarf", "helmet", "hood",
         "vest", "coat", "belt", "backpack", "bob", "tracksuit", "track jacket", "track pants", "sandals", "slippers")
_COL = "|".join(COLORS)
# phiên sửa F1-C: a joined colour ("silver-grey", "red and black", "black/white") is ONE colour set — #22 MAXIM "silver-grey metallic
# leather bomber jacket" read as "grey" only, so "silver bomber jacket" (shots 1, 3) came out red
_COLSEQ = rf"(?:{_COL})(?:\s*(?:-|/|\band\b)\s*(?:{_COL}))*"
_ITEM_RX = re.compile(rf"\b({_COLSEQ})\b((?:[ -]+(?!(?:{_COL})\b)[a-z]+(?:-[a-z]+)?){{0,3}}?)[ -]+({'|'.join(ITEMS)})\b", I)
_SENT_END = re.compile(r"[.!?;\n]")
_OTHER_PEOPLE = re.compile(r"\b(?:man|men|woman|women|boy|boys|girl|girls|guy|guys|lady|ladies|kid|kids|npcs?|crowd|someone|somebody|"
                           r"stranger|strangers|passers?-?by|people|bystanders?)\b|\bngười\b", I)
_SIZE_WORDS = {"small", "big", "large", "tiny", "long", "short", "two", "three", "one", "little", "thin", "thick", "bright", "dark", "light",
               "pale", "deep", "solid", "and", "with", "a", "the"}
_SAME_COLOR = {"grey": "gray", "golden": "gold"}


def _owners(text: str, names: List[str]):
    """[(position, name)] of every mention of a cast name (full name, or its first word of ≥ 3 letters)."""
    marks = []
    for n in names:
        forms = {n.lower()} | ({n.split()[0].lower()} if len(n.split()[0]) >= 3 else set())
        for f in forms:
            marks += [(m.start(), n) for m in re.finditer(rf"\b{re.escape(f)}\b", text.lower())]
    return sorted(marks)


def _hits(text: str, names: List[str]) -> List[Dict]:
    """Every "colour(s) + ≤ 3 words + garment" of the text with its owner: the nearest cast name before it IN THE SAME SENTENCE
    (phiên sửa F1-C: "KELLY hands MAXIM a cup; behind them a man in a blue jacket" gave MAXIM the stranger's jacket); with one cast
    name and no name in the sentence, that name. `soft`: the sentence names someone else too, or the colour starts a costume NAME
    ("Red Dinosaur jacket") — only a warning then."""
    marks = _owners(text, names)
    out = []
    for m in _ITEM_RX.finditer(text):
        start = max((e.end() for e in _SENT_END.finditer(text, 0, m.start())), default=0)
        stop = _SENT_END.search(text, m.end())
        sentence = text[start:stop.start() if stop else len(text)]
        before = [n for pos, n in marks if start <= pos < m.start()]
        owner = before[-1] if before else (names[0] if len(names) == 1 else None)
        if owner is None:
            continue
        mods = [w for w in re.split(r"[ ]+", m.group(2).strip().lower()) if w and w not in _SIZE_WORDS]
        item = m.group(3).lower()
        item = "horns" if item == "horn" else item
        key = f"{mods[-1]} {item}" if mods else item
        colors = sorted({_SAME_COLOR.get(c, c) for c in re.findall(rf"\b(?:{_COL})\b", m.group(1).lower())})
        nxt = (m.group(2).strip().split() or m.group(3).split())[0]
        named = nxt[:1].isupper() and not nxt.isupper()
        out.append({"owner": owner, "key": key, "colors": colors, "soft": bool(named or _OTHER_PEOPLE.search(sentence))})
    return out


def _items(text: str, names: List[str]):
    for h in _hits(text, names):
        yield h["owner"], h["key"], "/".join(h["colors"])


# Hồ sơ OUTFIT tiếng Việt (phiên sửa F1-C): "Áo croptop đỏ in hình khủng long xanh lá" → "red croptop, green dinosaur print" so it is
# compared with the English prompt. Vietnamese puts the colour AFTER the garment; the words keep their marks ("đỏ" ≠ "đo").
_VI_MARKS = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", I)
_VI_ITEMS = (("áo croptop", "croptop"), ("áo crop top", "croptop"), ("áo khoác bomber", "bomber jacket"), ("áo khoác", "jacket"),
             ("áo hoodie", "hoodie"), ("áo thun", "t-shirt"), ("áo phông", "t-shirt"), ("áo sơ mi", "shirt"), ("áo vest", "vest"),
             ("áo gile", "vest"), ("áo choàng", "coat"), ("áo măng tô", "coat"), ("bộ đồ thể thao", "tracksuit"), ("tay áo", "sleeves"),
             ("croptop", "croptop"), ("hoodie", "hoodie"), ("áo", "top"),
             ("mũ trùm", "hood"), ("mũ bảo hiểm", "helmet"), ("mũ lưỡi trai", "cap"), ("mũ", "cap"), ("nón", "cap"),
             ("quần short", "shorts"), ("quần đùi", "shorts"), ("quần jean", "jeans"), ("quần bò", "jeans"), ("quần", "pants"),
             ("chân váy", "skirt"), ("váy", "dress"), ("đầm", "dress"), ("giày thể thao", "sneakers"), ("giày", "shoes"), ("ủng", "boots"),
             ("dép", "sandals"), ("khẩu trang", "mask"), ("mặt nạ", "mask"), ("găng tay", "gloves"), ("khăn quàng", "scarf"),
             ("khăn", "scarf"), ("thắt lưng", "belt"), ("ba lô", "backpack"), ("balo", "backpack"), ("sừng", "horns"), ("tóc", "hair"))
_VI_COLORS = (("xanh lá cây", "green"), ("xanh lá", "green"), ("xanh lục", "green"), ("xanh dương", "blue"), ("xanh nước biển", "blue"),
              ("xanh da trời", "blue"), ("xanh lam", "blue"), ("xanh navy", "navy"), ("xanh ngọc", "teal"), ("đỏ", "red"),
              ("vàng kim", "gold"), ("vàng", "yellow"), ("đen", "black"), ("trắng", "white"), ("bạc", "silver"), ("xám", "gray"),
              ("hồng", "pink"), ("tím", "purple"), ("cam", "orange"), ("nâu", "brown"))
_VI_PRINT_OBJ = (("khủng long", "dinosaur"), ("đầu lâu", "skull"), ("ngôi sao", "star"), ("trái tim", "heart"), ("rồng", "dragon"),
                 ("hoa", "flower"), ("mèo", "cat"), ("chó", "dog"), ("gấu", "bear"), ("lửa", "flame"), ("tim", "heart"), ("sao", "star"))


def _vi_alt(pairs) -> "re.Pattern":
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(a) for a, _ in sorted(pairs, key=lambda x: -len(x[0]))) + r")(?!\w)", I)


_VI_ITEM_RX, _VI_COLOR_RX, _VI_OBJ_RX = _vi_alt(_VI_ITEMS), _vi_alt(_VI_COLORS), _vi_alt(_VI_PRINT_OBJ)
_VI_PRINT_RX = re.compile(r"(?<!\w)(?:in hình|hình in|họa tiết|hoạ tiết|in)(?!\w)", I)


def vi_garments(text: str) -> str:
    """English "colour garment" phrases read from a Vietnamese costume profile ("" when it is not Vietnamese)."""
    if not text or not _VI_MARKS.search(text):
        return ""
    items, colors, objs = dict(_VI_ITEMS), dict(_VI_COLORS), dict(_VI_PRINT_OBJ)
    out = []
    for seg in re.split(r"[,.;:\n+()]|\bvà\b|\bvới\b|\bkèm\b|\bphối\b", text.lower()):
        events = [(m.start(), "item", items[m.group(1)]) for m in _VI_ITEM_RX.finditer(seg)]
        for m in _VI_PRINT_RX.finditer(seg):
            obj = _VI_OBJ_RX.search(seg, m.end())
            nxt = _VI_ITEM_RX.search(seg, m.end())
            name = objs[obj.group(1)] + " print" if obj and (nxt is None or obj.start() < nxt.start()) else "print"
            events.append((m.start(), "item", name))
        events += [(m.start(), "color", colors[m.group(1)]) for m in _VI_COLOR_RX.finditer(seg)]
        current, cols = None, []
        for _pos, kind, word in sorted(events):
            if kind == "item":
                if current and cols:
                    out.append(f"{'-'.join(dict.fromkeys(cols))} {current}")
                current, cols = word, []
            elif current:
                cols.append(word)
        if current and cols:
            out.append(f"{'-'.join(dict.fromkeys(cols))} {current}")
    return ", ".join(out)


def cross_shot(shots: Iterable[Dict]) -> List[Dict]:
    """shots = [{"idx", "image_prompt", "motion_prompt", "characters"}] → cùng món đồ của cùng nhân vật được tả khác màu (warn).
    #22: mũ Maxim 'two small WHITE horns' (shot 2, 4) ↔ 'small RED horns' (shot 7–9); in hình áo Kelly GREEN ↔ blue."""
    seen: Dict[Tuple[str, str], Dict[str, List]] = {}
    for s in shots or []:
        names = [str(c) for c in s.get("characters") or [] if str(c).strip()]
        for field in ("image_prompt", "motion_prompt"):
            for owner, key, color in _items(str(s.get(field) or ""), names):
                idxs = seen.setdefault((owner, key), {}).setdefault(color, [])
                if s.get("idx") not in idxs:
                    idxs.append(s.get("idx"))
    out = []
    for (owner, key), colors in seen.items():
        if len(colors) < 2:
            continue
        told = " ↔ ".join(f"{c} (shot {', '.join(str(i) for i in idxs)})" for c, idxs in colors.items())
        out.append(_issue("warn", "nhan_vat", f"{owner}: “{key}” khác màu giữa các shot — {told}. Lấy MỘT nguồn (hồ sơ Kho / ảnh OUTFIT) "
                                              "rồi sửa các shot lệch.",
                          shots=sorted({i for idxs in colors.values() for i in idxs}, key=lambda x: (x is None, x)), owner=owner, item=key))
    return out


# ---- trang phục một nguồn: hồ sơ Kho (F1-C) ------------------------------------------------------------------------------
# #22: hồ sơ / ảnh OUTFIT "GREEN dinosaur print" ↔ blocking "blue dinosaur print"; sừng mũ Maxim "white" ↔ "red". Tóc không xét ở đây
# (ảnh OUTFIT có người mẫu mang tóc khác — tóc lấy từ ảnh nhân vật).
_NOT_GARMENT = {"hair", "bob"}
_FREE_CLOTHES = re.compile(r"\b(?:outfits?|clothes|clothing|costumes?|garments?)\b|trang phục|quần áo", I)


def outfit_vs_profile(text: str, names: List[str], profiles: Dict[str, str]) -> List[Dict]:
    """Same garment of a character told in a colour its profile does not have → red. profiles = {name: profile words of the costume}
    (garment_profile). Uses cross_shot's "colour + ≤ 3 words + garment" reading and its owner rule (the nearest name before)."""
    out, said = [], set()
    known = {}
    for name in names:
        prof = profiles.get(name)
        if not prof:
            continue
        table: Dict[str, set] = {}
        vi = vi_garments(prof)                            # phiên sửa F1-C: a Vietnamese OUTFIT profile, read in English words
        for h in _hits(prof + (". " + vi if vi else ""), [name]):
            table.setdefault(h["key"], set()).update(h["colors"])
        if not any(k.split()[-1] not in _NOT_GARMENT for k in table):
            out.append(_issue("warn", "nhan_vat", f"{name}: hồ sơ trang phục không so được (không đọc ra món đồ + màu nào: "
                                                  f"“{str(prof)[:80]}”) — chữ màu trang phục trong prompt không được kiểm.", owner=name))
            continue
        known[name] = table
    if not known:
        return out
    for h in _hits(text or "", names):
        owner, key, colors = h["owner"], h["key"], set(h["colors"])
        table = known.get(owner) or {}
        if key.split()[-1] in _NOT_GARMENT or key not in table or colors & table[key]:
            continue
        color = "/".join(sorted(colors))
        if (owner, key, color) in said:
            continue
        said.add((owner, key, color))
        # a profile with ≥ 2 colours for the garment, someone else in the sentence, or a costume name → only a warning
        level = "warn" if h["soft"] or len(table[key]) >= 2 else "red"
        out.append(_issue(level, "nhan_vat", f"{owner}: “{color} {key}” khác hồ sơ Kho ({' / '.join(sorted(table[key]))} {key}) — "
                                             "trang phục lấy MỘT nguồn (hồ sơ / ảnh OUTFIT); sửa chữ màu trong prompt/blocking.",
                          owner=owner, item=key))
    return out


def outfit_issues(text: str, data: Dict, chars: Optional[List[Dict]]) -> List[Dict]:
    shot = _shot_chars(data, chars) if _names(data) else []
    profiles = {str(c.get("name")): c.get("_garments") for c in shot if c.get("_garments")}
    return outfit_vs_profile(text, [str(c.get("name")) for c in shot], profiles) if profiles else []


def garment_profile(conn, project_id: int, name: str) -> str:
    """The costume words a character is held to — the places runner.lock_note / prompts.lock_text read: with an OUTFIT picture, the
    OUTFIT resource's description + approved profile `must_keep`; otherwise the approved library profile (assets.standard_for) or the
    project's lock_rules `must_keep` — unless its `may_change` frees the clothes. "" when nothing is known."""
    from . import assets
    row = conn.execute("SELECT lock_rules, outfit_image_ids FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    if row is None:
        return ""
    ids = [int(x) for x in str(row["outfit_image_ids"] or "").split(",") if x.strip().isdigit()]
    if ids:
        marks = ",".join("?" * len(ids))
        words = []
        for r in conn.execute(f"SELECT DISTINCT a.id, a.description FROM asset_images i JOIN assets a ON a.id=i.asset_id "
                              f"WHERE i.id IN ({marks})", ids):
            words.append(str(r["description"] or "").split("[AI đọc ảnh]")[0])
            prof = assets.get_profile(conn, r["id"])
            if prof.get("approved") and prof.get("must_keep"):
                words.append(str(prof["must_keep"]))
        return " ".join(w for w in words if w.strip())
    rules = assets.standard_for(conn, project_id, name)
    if rules is None:
        try:
            rules = json.loads(row["lock_rules"]) if row["lock_rules"] else None
        except ValueError:
            rules = None
    if not isinstance(rules, dict) or _FREE_CLOTHES.search(str(rules.get("may_change") or "")):
        return ""
    return str(rules.get("must_keep") or "")


# ---- 4b: so với bản trước ------------------------------------------------------------------------------------------------
GROW_SHARE, GROW_SENTENCES, KEEP_SHARE = 0.2, 2, 0.9


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower()).rstrip(" .!?")


def growth_check(old: Optional[str], new: Optional[str]) -> List[Dict]:
    """new giữ gần như mọi câu của old và chỉ dài thêm (≥ 20 % hoặc ≥ 2 câu mới), không bỏ/thay câu nào → warn 'trồng thêm';
    câu MỚI mâu thuẫn câu CŨ còn giữ (bảng cặp như check (f)) → red. Bản viết lại thật (câu cũ đã thay) → không báo."""
    old, new = (old or "").strip(), (new or "").strip()
    if not old or not new or _norm(old) == _norm(new):
        return []
    old_s, new_s = [_norm(s) for s in _sentences(old)], [_norm(s) for s in _sentences(new)]
    new_set, old_set = set(new_s), set(old_s)
    kept = [s for s in old_s if s in new_set]
    added = [s for s in _sentences(new) if _norm(s) not in old_set]
    if not added or len(kept) < max(1, KEEP_SHARE * len(old_s)):
        return []
    out = []
    if len(new) >= (1 + GROW_SHARE) * len(old) or len(added) >= GROW_SENTENCES:
        out.append(_issue("warn", "viet_chong", f"Chỉ trồng thêm vào prompt ({len(added)} câu mới, {len(old)} → {len(new)} ký tự), câu cũ "
                                                "không được sửa — viết lại gọn theo khung công thức thay vì nối câu theo từng lỗi."))
    # F1 sửa #2: only the old sentences STILL in the new prompt — a sentence just replaced is gone, it contradicts nothing
    old_text, added_text = " ".join(s for s in _sentences(old) if _norm(s) in new_set), " ".join(added)
    for name, x, y, fix in contradictions(added_text, old_text):
        out.append(_issue("red", "mau_thuan", f"Câu mới mâu thuẫn câu cũ ({name}): mới “{x}” ↔ cũ “{y}” — {fix}."))
    return out


def review_shot(data: Dict, image_prompt: Optional[str], motion_prompt: Optional[str], chars: Optional[List[Dict]] = None,
                previous: Optional[Dict] = None, style_by_code: bool = False, ff: Optional[bool] = None) -> Dict:
    """Một shot: {"image", "motion", "growth", "red", "kind"}. previous = {"image": prompt cũ, "motion": prompt cũ} (bản trước của lượt
    Đạo diễn / người sửa) — chỉ kiểm 'trồng thêm' khi có."""
    previous = previous or {}
    image = lint_image(image_prompt, data, chars, style_by_code, ff) if (image_prompt or "").strip() else []
    motion = lint_motion(motion_prompt, data, chars, ff) if (motion_prompt or "").strip() else []
    growth = [dict(g, kind="image") for g in growth_check(previous.get("image"), image_prompt)]
    growth += [dict(g, kind="motion") for g in growth_check(previous.get("motion"), motion_prompt)]
    return {"kind": shot_kind(data, chars), "image": image, "motion": motion, "growth": growth,
            "red": any(i["level"] == "red" for i in image + motion + growth)}


# ---- báo cáo Đạo diễn ----------------------------------------------------------------------------------------------------
def warnings(shots) -> List[str]:
    """shots = [(cảnh, số shot, dict shot của câu trả lời Director)] → câu cảnh báo (kiểu plate_view_check.warnings)."""
    if not enabled():
        return []
    out, rows = [], []
    for scene, k, s in shots or []:
        if not isinstance(s, dict):
            continue
        data = dict(s, blocking=s.get("blocking") or s.get("start_frame"))
        try:
            found = lint_image(s.get("image_prompt"), data) if str(s.get("image_prompt") or "").strip() else []
        except Exception as e:  # noqa: BLE001 - a check, never a reason to lose the report
            found = [_issue("warn", "khung_hinh", f"không kiểm được: {type(e).__name__}: {e}")]
        for i in found:
            if i["part"] == "phong_cach":        # the look sentence is added by code from the project (not known here)
                continue
            out.append(f"Công thức prompt cảnh {scene} · shot {k}: {'[ĐỎ] ' if i['level'] == 'red' else ''}"
                       f"{PART_LABELS.get(i['part'], i['part'])} — {i['msg']}")
        rows.append({"idx": f"{scene}·{k}", "image_prompt": s.get("image_prompt"), "characters": s.get("characters") or []})
    out += [f"Công thức prompt: {i['msg']}" for i in cross_shot(rows)]
    return out


# ---- lưu vào scenes.data + diag ------------------------------------------------------------------------------------------
def _sha(text: Optional[str]) -> str:
    return hashlib.sha1((text or "").strip().encode("utf-8")).hexdigest()[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _key(data: Dict, idx) -> Tuple:
    return ("shot", data.get("story_scene"), data["shot_no"]) if data.get("shot_no") else ("idx", idx)


def _motion_of(conn, scene_id: int) -> Optional[str]:
    try:
        row = conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    except Exception:  # noqa: BLE001 - a database without the table: no motion yet
        return None
    return row["motion_prompt"] if row else None


def _style_by_code(conn, project_id: int) -> bool:
    try:
        from . import looks
        return bool(looks.of(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()))
    except Exception:  # noqa: BLE001 - unknown: ask for the style in the prompt (a warning, never a block)
        return False


def _chars(conn, project_id: int) -> List[Dict]:
    """The project's characters; `_human` = assets.is_human (profile + library resource: a pet, a creature)."""
    try:
        rows = [dict(r) for r in conn.execute("SELECT * FROM characters WHERE project_id=?", (project_id,))]
    except Exception:  # noqa: BLE001
        return []
    from . import assets
    for c in rows:
        try:
            c["_human"] = assets.is_human(conn, project_id, str(c.get("name") or ""))
        except Exception:  # noqa: BLE001 - unknown: judged by the profile words
            pass
        try:                                     # F1-C: the costume words of the profile (outfit_vs_profile)
            c["_garments"] = garment_profile(conn, project_id, str(c.get("name") or ""))
        except Exception:  # noqa: BLE001 - no profile readable: the costume is not checked against it
            c["_garments"] = ""
    return rows


def _is_ff(conn, project_id: int) -> Optional[bool]:
    try:
        from . import looks
        return looks.is_ff(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
    except Exception:  # noqa: BLE001 - unknown: the FF rule stays a stop (red)
        return None


def snapshot(conn, project_id: int) -> Dict[Tuple, Dict]:
    """Prompt hiện có của từng shot TRƯỚC khi Đạo diễn ghi đè (khóa: cảnh kịch bản + số shot, hoặc idx) — để so 'trồng thêm'."""
    out = {}
    if not enabled():
        return out
    try:
        for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=?", (project_id,)).fetchall():
            d = json.loads(r["data"] or "{}")
            out[_key(d, r["idx"])] = {"image": d.get("image_prompt"), "motion": _motion_of(conn, r["id"]),
                                      "growth": (d.get("formula_check") or {}).get("growth") or []}
    except Exception:  # noqa: BLE001 - no snapshot = no growth check this time, said by after_director's own diag
        return {}
    return out


def _say(conn, project_id, scene_id, label: str, fc: Dict) -> None:
    from . import diag
    issues = fc["image"] + fc["motion"] + fc["growth"] + fc.get("cross", [])
    if not issues:
        return
    reds = [i for i in issues if i["level"] == "red"]
    top = (reds or issues)[:3]
    msg = (f"Công thức prompt {label}: {len(reds)} lỗi đỏ, {len(issues) - len(reds)} cảnh báo — "
           + " | ".join(f"{PART_LABELS.get(i['part'], i['part'])}: {i['msg']}" for i in top))
    diag.record(conn, "director", "error" if reds else "warn", msg, "prompt_formula", project_id, scene_id=scene_id)


def _write(conn, scene_id: int, data: Dict, fc: Dict) -> None:
    data["formula_check"] = fc
    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), scene_id))


def _label(data: Dict, idx) -> str:
    return f"cảnh {data['story_scene']} · shot {data['shot_no']}" if data.get("shot_no") and data.get("story_scene") else f"shot {idx}"


def after_director(conn, project_id: int, before: Optional[Dict] = None) -> None:
    """Sau MỖI lượt Đạo diễn lưu kế hoạch (F0 mục 4b): kiểm từng shot + so bản trước + cùng món khác màu cả dự án → scenes.data
    ["formula_check"] + diag 'prompt_formula'. Không bao giờ ném lỗi (lỗi kiểm ghi diag, kế hoạch đã trả tiền vẫn giữ)."""
    if not enabled():
        return
    from . import diag
    before = before or {}
    try:
        rows = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
        chars, styled, ff = _chars(conn, project_id), _style_by_code(conn, project_id), _is_ff(conn, project_id)
        results, cross_rows = [], []
        for r in rows:
            data = json.loads(r["data"] or "{}")
            image, motion = data.get("image_prompt"), _motion_of(conn, r["id"])
            prev = before.get(_key(data, r["idx"])) or {}
            try:
                fc = review_shot(data, image, motion, chars, previous={"image": prev.get("image"), "motion": prev.get("motion")},
                                 style_by_code=styled, ff=ff)
            except Exception as e:  # noqa: BLE001 - one shot's check failing is said, the others still run
                diag.record(conn, "director", "warn", f"không kiểm được công thức prompt {_label(data, r['idx'])}: {type(e).__name__}: {e}",
                            "prompt_formula", project_id, scene_id=r["id"])
                continue
            if not fc["growth"] and prev and prev.get("image") == image and prev.get("motion") == motion:
                fc["growth"] = prev.get("growth") or []       # unchanged prompt: the earlier 'trồng thêm' finding still holds
            fc.update(image_sha=_sha(image), motion_sha=_sha(motion), at=_now())
            results.append((r, data, fc))
            cross_rows.append({"idx": r["idx"], "image_prompt": image, "motion_prompt": motion, "characters": data.get("characters") or []})
        cross = cross_shot(cross_rows)
        for r, data, fc in results:
            fc["cross"] = [i for i in cross if r["idx"] in i.get("shots", [])]
            _write(conn, r["id"], data, fc)
        conn.commit()
        warn_only = []
        for r, data, fc in results:
            if any(i["level"] == "red" for i in fc["image"] + fc["motion"] + fc["growth"]):
                _say(conn, project_id, r["id"], _label(data, r["idx"]), dict(fc, cross=[]))     # a stop: said per shot
            elif fc["image"] + fc["motion"] + fc["growth"]:
                warn_only.append((data, r["idx"], fc))
        if warn_only:       # F1 sửa: warnings only ("thiếu phần") — ONE line per saved plan, not one per shot (⚙ Chẩn đoán stays readable)
            parts_seen = list(dict.fromkeys(PART_LABELS.get(i["part"], i["part"])
                                            for _d, _x, fc in warn_only for i in fc["image"] + fc["motion"] + fc["growth"]))
            diag.record(conn, "director", "warn", f"Công thức prompt: {len(warn_only)} shot có cảnh báo (không chặn) — "
                        + ", ".join(_label(d, x) for d, x, _fc in warn_only[:8]) + ("…" if len(warn_only) > 8 else "")
                        + " · phần: " + ", ".join(parts_seen[:8]) + " — xem chi tiết ở từng shot (formula_check)",
                        "prompt_formula", project_id)
        for i in cross:
            diag.record(conn, "director", "warn", "Công thức prompt (giữa các shot): " + i["msg"], "prompt_formula", project_id)
    except Exception as e:  # noqa: BLE001 - a check, never a reason to lose the paid plan
        conn.rollback()
        diag.record(conn, "director", "warn", f"không kiểm được công thức prompt: {type(e).__name__}: {e}", "prompt_formula", project_id)


def on_prompt_saved(conn, scene_id: int, kind: str, old: Optional[str], new: Optional[str]) -> None:
    """Sau mỗi lần LƯU một prompt (Claude viết motion, Đạo diễn viết lại sau QC, người sửa tay): kiểm lại shot + so với bản cũ của
    chính prompt đó. Gọi SAU commit của người gọi; tự commit; không bao giờ ném lỗi."""
    if not enabled() or kind not in ("image", "motion"):
        return
    from . import diag
    project_id = None
    try:
        row = conn.execute("SELECT project_id, idx, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
        if row is None:
            return
        project_id = row["project_id"]
        data = json.loads(row["data"] or "{}")
        image, motion = data.get("image_prompt"), _motion_of(conn, scene_id)
        old_fc = data.get("formula_check") or {}
        fc = review_shot(data, image, motion, _chars(conn, project_id), previous={kind: old} if old != new else None,
                         style_by_code=_style_by_code(conn, project_id), ff=_is_ff(conn, project_id))
        fc["growth"] = [g for g in old_fc.get("growth") or [] if g.get("kind") != kind] + fc["growth"]
        fc["cross"] = old_fc.get("cross") or []
        fc["red"] = fc["red"] or any(i["level"] == "red" for i in fc["growth"])
        fc.update(image_sha=_sha(image), motion_sha=_sha(motion), at=_now())
        _write(conn, scene_id, data, fc)
        conn.commit()
        _say(conn, project_id, scene_id, _label(data, row["idx"]) + f" ({'ảnh' if kind == 'image' else 'motion'} vừa lưu)",
             dict(fc, image=fc["image"] if kind == "image" else [], motion=fc["motion"] if kind == "motion" else [],
                  growth=[g for g in fc["growth"] if g.get("kind") == kind], cross=[]))
    except Exception as e:  # noqa: BLE001 - never a reason to lose a saved prompt
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        diag.record(conn, "director", "warn", f"không kiểm được công thức prompt (shot #{scene_id}): {type(e).__name__}: {e}",
                    "prompt_formula", project_id, scene_id=scene_id)


FORMULA_MARK = "sai công thức"       # in the failure note of a job stopped here (runner._blocked) — autopilot / batch recognise it


def _gore_goes(conn, scene_id: int, proj, kind: str, text: str, gore_hinted) -> bool:
    """F1 sửa #5: the gore stop is lifted only when the restraint sentence REALLY goes with the shot. gore_hinted from the runner (bool, or
    a callable asked only when needed) knows the send path (group prompt, Kling multi_prompt entry, the prompt limit); without it: a
    picture always gets it (runner.build_image_prompt, no length limit), a one-shot motion when it fits the model's limit."""
    if gore_hinted is not None:
        return bool(gore_hinted() if callable(gore_hinted) else gore_hinted)
    if kind == "image":
        return True
    from . import looks
    try:
        from .adapters.clipai import PROMPT_LIMITS
        from . import model_router
        model = str(model_router.scene_choice(conn, scene_id).get("model") or "")
        limit = PROMPT_LIMITS.get(model) or (PROMPT_LIMITS["kling"] if "kling" in model.lower() else 4000)
    except Exception:  # noqa: BLE001 - unknown model: the common limit
        limit = 4000
    out = looks.gore_restraint(proj, text, video=True)
    return looks._GORE_TAG in out and len(out) + len(looks.video_sentence(proj)) + 1 <= limit


def group_red_issues(conn, scene_id: int, kind: str) -> List[str]:
    """red_issues of the shot and, for a clip (kind 'motion'), of every shot of its group (Kling multi-shot / camera set-up / Seedance
    group) — what autopilot and the requeue button look at before queueing a job stopped on the formula again (F1 sửa #7). Shot labels
    are added for the other shots."""
    ids = [scene_id]
    if kind == "motion":
        try:
            from . import seedance_refs, shots
            for g in (shots.group_of(conn, scene_id), seedance_refs.group_of(conn, scene_id)):
                ids += [r["id"] for r in g or [] if r["id"] not in ids]
        except Exception:  # noqa: BLE001 - no group known: the shot alone (the runner still checks the whole group before paying)
            pass
    out = []
    for sid in ids:
        out += [x if sid == scene_id else f"shot #{sid} {x}" for x in red_issues(conn, sid, kind)]
    return out


def red_issues(conn, scene_id: int, kind: Optional[str] = None, gore_hinted=None) -> List[str]:
    """Lỗi ĐỎ của shot (câu tiếng Việt, rỗng = qua) — cho ImageRunner._blocked (kind='image') / VideoRunner._blocked (kind='motion');
    kind=None = cả hai. F1 sửa #3: LUÔN kiểm lại từ prompt + kế hoạch hiện tại (regex, vài ms — kết quả phụ thuộc size/blocking/
    nhân vật/hồ sơ, không chỉ prompt); chỉ phần 'trồng thêm' lấy từ data['formula_check'] khi băm prompt khớp. Dự án FF: lỗi máu/xác
    bỏ qua khi câu tiết chế thật sự đi theo shot (_gore_goes); dự án khác: lỗi đó chỉ là cảnh báo. Cờ tắt → []."""
    if not enabled():
        return []
    row = conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return []
    data = json.loads(row["data"] or "{}")
    fc = data.get("formula_check") or {}
    texts = {"image": data.get("image_prompt"), "motion": _motion_of(conn, scene_id)}
    chars = proj = ff = None
    out = []
    for k in ("image", "motion") if kind is None else (kind,):
        text = texts[k]
        if not (text or "").strip():
            continue
        if chars is None:
            from . import looks
            chars = _chars(conn, row["project_id"])
            proj = conn.execute("SELECT * FROM projects WHERE id=?", (row["project_id"],)).fetchone()
            ff = looks.is_ff(proj)
        issues = (lint_image(text, data, chars, _style_by_code(conn, row["project_id"]), ff) if k == "image"
                  else lint_motion(text, data, chars, ff))
        if fc and fc.get(f"{k}_sha") == _sha(text):
            issues += [g for g in fc.get("growth") or [] if g.get("kind") == k]
        gore = [i for i in issues if i["part"] == "luat_ff" and i["level"] == "red"]
        if ff and gore and _gore_goes(conn, scene_id, proj, k, text, gore_hinted):
            issues = [i for i in issues if i not in gore]
        word = "Prompt ảnh" if k == "image" else "Prompt motion"
        out += [f"{word} · {PART_LABELS.get(i['part'], i['part'])}: {i['msg']}" for i in issues if i["level"] == "red"]
    return out
