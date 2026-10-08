"""Công thức prompt (F1-A, 09/10/2026) — code kiểm PHẦN của prompt ảnh khung đầu / motion, không kiểm câu chữ, không gọi model.

Nguồn: docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md (người dùng đã duyệt) mục 1–4b; sổ công thức knowledge/formula/ (anh_khung_dau.md,
motion.md) giải thích từng phần: bắt buộc khi nào, lấy từ trường nào của scenes.data, ví dụ #22, lý do, code kiểm gì.

Vì sao: #22 đẹp nhờ câu viết tay (khóa nền, trang phục từng món, khóa tóc…) — không câu nào quay về hệ thống; #24 hỏng vì prompt là
nhiều câu nối dần theo từng lỗi, có câu tự mâu thuẫn (trung cận ↔ ngồi bệt; luật mắt người ↔ yêu nữ mắt đỏ), từ ghê không tiết chế,
bóng lao sát mặt không có đường đi. Code chỉ báo ĐÚNG những điều đó; phần sáng tạo của Đạo diễn để nguyên.

    shot_kind(data, chars=None) -> dialogue | action | dance_ref | object | establishing | creature | skill_fx | other
    check_image(prompt, data, chars=None) / check_motion(prompt, data, chars=None) -> [{"level": "red"|"warn", "part", "msg"}]
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
                   r"\bfull[- ]bod(?:y|ies)\b|\bfeet (?:are )?visible\b|\b(?:whole|entire) body\b|\bhead to toe\b|ngồi bệt|thấy chân|"
                   r"duỗi chân|sõng soài|\bcả người\b", I)

# ---- (c) chi tiết ghê — luật tầng 1 cho mọi dự án Free Fire (người dùng chốt 09/10) ----------------------------------------
_GORE = re.compile(r"\b(?:blood\w*|gore|gory|wounds?|wounded|corpses?|dead bod(?:y|ies)|severed|guts|entrails|decapitat\w*|dismember\w*|"
                   r"bleed\w*|carcass\w*)\b|\bmáu\b|xác chết|thi thể|vết thương|nội tạng|đứt lìa", I)
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
_NON_HUMAN = re.compile(r"\b(?:creature|demon\w*|ghost\w*|monster\w*|zombie\w*|undead|wraith|beast|faceless)\b|yêu nữ|(?<!kỳ )\bquái\b|"
                        r"\bquỷ\b|\bma nữ\b|hồn ma|bóng ma|sinh vật", I)
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


def _non_human(prompt: str, data: Dict, chars: Optional[List[Dict]]) -> str:
    """The first sign that a character of the shot is not human (glowing eyes, demon, yêu nữ…) — '' when none."""
    if any(str(c.get("kind") or "").lower() in NON_HUMAN_KINDS for c in _shot_chars(data, chars)):
        return "loại nhân vật trong hồ sơ"
    texts = [_HUMAN_EYES.sub(" ", prompt or ""), _HUMAN_EYES.sub(" ", _data_text(data)), " ".join(_names(data))]
    texts += [_HUMAN_EYES.sub(" ", f"{c.get('description') or ''} {c.get('wardrobe') or ''}") for c in _shot_chars(data, chars)]
    for t in texts:
        m = _GLOW_EYES.search(t) or _NON_HUMAN.search(t)
        if m:
            return _snip(m)
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
    if has_people and _non_human("", data, chars):
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


def _common(prompt: str, data: Dict, chars: Optional[List[Dict]], kind_word: str) -> List[Dict]:
    out = []
    gore = _GORE.search(prompt)
    if gore and not _RESTRAINT.search(prompt):
        out.append(_issue("red", "luat_ff", f"Chi tiết ghê “{_snip(gore)}” không có câu tiết chế — luật mọi dự án Free Fire: chỉ gợi "
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
        what = _non_human(prompt, data, chars)
        if what:
            out.append(_issue("red", "loai_nhan_vat",
                              f"Luật của người “{_snip(human)}” áp cho nhân vật không phải người ({what}) — luật mắt người chỉ dành cho "
                              "người; nhân vật quái/yêu/ma giữ đặc điểm của nó. Bỏ câu luật người trong prompt " + kind_word + "."))
    for name, x, y, fix in contradictions(prompt, prompt):
        out.append(_issue("red", "mau_thuan", f"Prompt tự mâu thuẫn ({name}): “{x}” ↔ “{y}” — {fix}."))
    for m in _RUNON.finditer(prompt):
        if m.group(1).lower() in _RUNON_STOP:
            continue
        out.append(_issue("warn", "cau_chu", f"Câu dính liền mất dấu chấm: “{m.group(0)}” — thêm dấu chấm trước "
                                             f"“{m.group(2).strip()}” (câu ghép thêm vào cuối, model đọc thành một câu)."))
    return out


def check_image(prompt: str, data: Dict, chars: Optional[List[Dict]] = None, style_by_code: bool = False) -> List[Dict]:
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
        pose_text = prompt + " " + _data_text(data, ("blocking", "start_frame"))
        legs = _LEGS.search(pose_text)
        if legs:
            out.append(_issue("red", "khung_hinh",
                              f"Khung “{close_word}” (không thấy chân) mâu thuẫn tư thế “{_snip(legs)}” (cần thấy chân/cả người) — "
                              "đổi cỡ cảnh sang MS/WS, hoặc tả tư thế bằng phần trên người (vai ngả ra sau, tay chống phía sau)."))
    return out + _common(prompt, data, chars, "ảnh")


def check_motion(prompt: str, data: Dict, chars: Optional[List[Dict]] = None) -> List[Dict]:
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
    return out + _common(prompt, data, chars, "motion")


# ---- giữa các shot: cùng món đồ khác màu -------------------------------------------------------------------------------
COLORS = ("red", "blue", "green", "black", "white", "yellow", "pink", "purple", "orange", "brown", "grey", "gray", "silver", "gold",
          "golden", "navy", "beige", "cyan", "teal")
ITEMS = ("horns?", "print", "cap", "hat", "hoodie", "jacket", "hair", "mask", "croptop", "crop top", "shirt", "t-shirt", "top", "pants",
         "trousers", "jeans", "shorts", "skirt", "shoes", "boots", "sneakers", "gloves", "sleeves", "dress", "scarf", "helmet", "hood",
         "vest", "coat", "belt", "backpack", "bob")
_COL = "|".join(COLORS)
_ITEM_RX = re.compile(rf"\b({_COL})\b((?:[ -]+(?!(?:{_COL})\b)[a-z]+(?:-[a-z]+)?){{0,3}}?)[ -]+({'|'.join(ITEMS)})\b", I)
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


def _items(text: str, names: List[str]):
    marks = _owners(text, names)
    for m in _ITEM_RX.finditer(text):
        before = [n for pos, n in marks if pos < m.start()]
        owner = before[-1] if before else (names[0] if len(names) == 1 else None)
        if owner is None:
            continue
        mods = [w for w in re.split(r"[ ]+", m.group(2).strip().lower()) if w and w not in _SIZE_WORDS]
        item = m.group(3).lower()
        item = "horns" if item == "horn" else item
        key = f"{mods[-1]} {item}" if mods else item
        color = m.group(1).lower()
        yield owner, key, _SAME_COLOR.get(color, color)


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
    old_text, added_text = " ".join(s for s in _sentences(old)), " ".join(added)
    for name, x, y, fix in contradictions(added_text, old_text):
        out.append(_issue("red", "mau_thuan", f"Câu mới mâu thuẫn câu cũ ({name}): mới “{x}” ↔ cũ “{y}” — {fix}."))
    return out


def review_shot(data: Dict, image_prompt: Optional[str], motion_prompt: Optional[str], chars: Optional[List[Dict]] = None,
                previous: Optional[Dict] = None, style_by_code: bool = False) -> Dict:
    """Một shot: {"image", "motion", "growth", "red", "kind"}. previous = {"image": prompt cũ, "motion": prompt cũ} (bản trước của lượt
    Đạo diễn / người sửa) — chỉ kiểm 'trồng thêm' khi có."""
    previous = previous or {}
    image = check_image(image_prompt, data, chars, style_by_code) if (image_prompt or "").strip() else []
    motion = check_motion(motion_prompt, data, chars) if (motion_prompt or "").strip() else []
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
            found = check_image(s.get("image_prompt"), data) if str(s.get("image_prompt") or "").strip() else []
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
    try:
        return [dict(r) for r in conn.execute("SELECT name, description, wardrobe FROM characters WHERE project_id=?", (project_id,))]
    except Exception:  # noqa: BLE001
        return []


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
        chars, styled = _chars(conn, project_id), _style_by_code(conn, project_id)
        results, cross_rows = [], []
        for r in rows:
            data = json.loads(r["data"] or "{}")
            image, motion = data.get("image_prompt"), _motion_of(conn, r["id"])
            prev = before.get(_key(data, r["idx"])) or {}
            try:
                fc = review_shot(data, image, motion, chars, previous={"image": prev.get("image"), "motion": prev.get("motion")},
                                 style_by_code=styled)
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
        for r, data, fc in results:
            _say(conn, project_id, r["id"], _label(data, r["idx"]), dict(fc, cross=[]))
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
                         style_by_code=_style_by_code(conn, project_id))
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


def red_issues(conn, scene_id: int, kind: Optional[str] = None) -> List[str]:
    """Lỗi ĐỎ của shot (câu tiếng Việt, rỗng = qua) — cho ImageRunner._blocked (kind='image') / VideoRunner._blocked (kind='motion');
    kind=None = cả hai. Đọc data['formula_check']; prompt đã đổi từ lần kiểm (sửa qua đường không có móc) → kiểm lại ngay từ prompt
    hiện tại (0 USD), không tin kết quả cũ. Cờ tắt → []."""
    if not enabled():
        return []
    row = conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return []
    data = json.loads(row["data"] or "{}")
    fc = data.get("formula_check") or {}
    texts = {"image": data.get("image_prompt"), "motion": _motion_of(conn, scene_id)}
    chars = None
    ff = None
    out = []
    for k in ("image", "motion") if kind is None else (kind,):
        text = texts[k]
        if not (text or "").strip():
            continue
        if fc and fc.get(f"{k}_sha") == _sha(text):
            issues = list(fc.get(k) or []) + [g for g in fc.get("growth") or [] if g.get("kind") == k]
        else:
            if chars is None:
                chars = _chars(conn, row["project_id"])
            issues = (check_image(text, data, chars, _style_by_code(conn, row["project_id"])) if k == "image"
                      else check_motion(text, data, chars))
        if ff is None:
            from . import looks
            ff = looks.is_ff(conn.execute("SELECT * FROM projects WHERE id=?", (row["project_id"],)).fetchone())
        if ff:      # F1-B: a Free Fire shot gets the restraint sentence from the code when it is sent (looks.gore_restraint) — not a stop
            issues = [i for i in issues if not str(i.get("msg", "")).startswith("Chi tiết ghê")]
        word = "Prompt ảnh" if k == "image" else "Prompt motion"
        out += [f"{word} · {PART_LABELS.get(i['part'], i['part'])}: {i['msg']}" for i in issues if i["level"] == "red"]
    return out
