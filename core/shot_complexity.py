"""Độ khó của một shot (N2, người dùng chốt 08/10 — docs/THIET_KE_2_BAC_CHAT_LUONG_VA_NHAC_2026-10-08.md 5a.4/5a.6/5a.7).

The Director's label (`difficulty` ∈ easy / complex / unknown + `difficulty_why`) is the main input; this module only CROSS-CHECKS it from
fields the shot already has (0 USD, no AI call): who is in the frame, the action words (dance / fight / big motion / hands), the camera
move, lip sync / spoken lines, a skill effect, a reference video, a 3D place. An "easy" label on a shot that scores high becomes
"unknown" with a note (a draft first is cheaper than a wasted high-tier clip); "complex" is never lowered — the Director may see a
difficulty the fields do not show.

N1 (the two-tier video, quality_tier.route) reads scenes.data["difficulty"]: easy (written by the Director, `difficulty_by` == "director"
with a `difficulty_why`, and no hard sign the code knows) → Seedance 2.5 720p straight away; complex / unknown / no Director label → a 480p
draft first (người dùng 15/10). Người dùng 15/10: điểm kiểm chéo KHÔNG ép đường đi — 'dễ' bị hạ 'chưa rõ' chỉ để hiển thị
(`difficulty_director` = "easy" giữ nhãn gốc).
09/10: Đạo diễn KHÔNG ghi nhãn → nhãn THỐNG KÊ theo kiểm chéo (điểm ≥ COMPLEX_MIN → complex, còn lại → easy) + `difficulty_by` = "check";
15/10 (người dùng): shot thiếu nhãn Đạo diễn đi đường KHÓ (nháp trước) — quality_tier.label_from_director bỏ qua nhãn "check". Kiểm chéo bớt gắt: nền 3D không cộng điểm (render được gửi
làm tham chiếu — giúp model, không làm khó; #24 shot 1–2 "một người đi, máy tĩnh" bị hạ oan), `camera_complexity` chỉ tính khi shot không
ghi `camera_move` (máy tĩnh / đẩy chậm mà ghi 'cảnh phức tạp' không còn bị cộng).
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional

LABELS = ("easy", "complex", "unknown")
_ALIASES = {"easy": "easy", "simple": "easy", "de": "easy", "dễ": "easy",
            "complex": "complex", "hard": "complex", "difficult": "complex", "phức tạp": "complex", "phuc tap": "complex", "khó": "complex",
            "unknown": "unknown", "unclear": "unknown", "chưa rõ": "unknown", "chua ro": "unknown"}

BIG_MOVES = ("track", "orbit", "crane", "whip")      # the camera travels / swings — static, push, pan, tilt, zoom, handheld are light
EASY_MAX = 1          # score ≤ this: nothing in the fields argues against "easy"
COMPLEX_MIN = 3       # score ≥ this: the fields alone call the shot complex

# (key, Vietnamese label, weight, regex over the action words). Weights are a reason, not a law: 2 = the things that made shots fail
# most in real runs (#8 lip-synced dialogue r̂ 1,0; #22 dance / skill r̂ 3,0; ≥ 2 people), 1 = adds risk on its own.
_WORDS = (
    ("dance", "nhảy / múa", 2, r"\bnhảy\b|\bmúa\b|\blộn\b|\b(dance|dancing|choreograph|flip|breakdance)"),
    ("fight", "đánh / bắn / va chạm", 2, r"\bđánh\b|\bđấm\b|tung cước|đá vào|\bbắn\b|va chạm|vật lộn|\b(fight|punch|kick|shoot|tackle)"),
    ("motion", "chuyển động lớn", 1, r"\bchạy\b|lao tới|lao vào|\bngã\b|\bté\b|\bđuổi\b|\b(run|sprint|jump|leap|fall|chase|roll)"),
    ("hands", "tay / ngón tay", 1, r"\btay\b|\bngón\b|\bcầm\b|\bnắm\b|\b(hand|finger|grab|grip|hold|pick up)"),
    ("skill_words", "kỹ năng / hiệu ứng", 2, r"kỹ năng|kĩ năng|\bchiêu\b|hiệu ứng|phát sáng|\bnổ\b|\b(skill|effect|vfx|explosion|glow|aura|beam)"),
)


def _fold(text: str) -> str:
    return unicodedata.normalize("NFC", str(text or "")).strip().lower()


def clean_label(value: Any) -> str:
    """easy / complex / unknown; Vietnamese or English spellings accepted; anything else (missing, wrong type) → unknown. Never raises."""
    if not isinstance(value, str):
        return "unknown"
    return _ALIASES.get(_fold(value), "unknown")


def clean_why(value: Any) -> Optional[str]:
    return value.strip()[:300] if isinstance(value, str) and value.strip() else None


def _speaks(data: Dict) -> bool:
    from .dialogue import is_non_speaker
    return any(isinstance(d, dict) and str(d.get("text") or "").strip() and not is_non_speaker(str(d.get("speaker") or ""))
               for d in data.get("dialogue") or [])


def score(scene_data: Dict, ref_video: bool = False) -> Dict:
    """{score, factors: [{key, label, weight}], suggest: easy|complex|unknown} from the fields a shot row already has."""
    d = scene_data or {}
    factors: List[Dict] = []

    def add(key, label, weight):
        factors.append({"key": key, "label": label, "weight": weight})

    cast = [c for c in d.get("characters") or [] if c]
    if len(cast) >= 3:
        add("people", f"{len(cast)} người", 3)
    elif len(cast) == 2:
        add("people", "2 người", 2)
    words = " ".join(_fold(d.get(k)) for k in ("action", "action_peak") if isinstance(d.get(k), str))
    if not words.strip() and isinstance(d.get("text"), str):    # a v2 scene row has only the script text
        words = _fold(d["text"])
    seen = set()
    for key, label, weight, rx in _WORDS:
        if re.search(rx, words):
            add(key, label, weight)
            seen.add(key)
    if d.get("skill_phase") or d.get("skill_phase_video"):
        if "skill_words" in seen:
            factors[:] = [f for f in factors if f["key"] != "skill_words"]
        add("skill", "kỹ năng (hồ sơ kỹ năng)", 2)
    if d.get("lip_sync") is True:
        add("lip_sync", "khớp môi", 2)
    elif _speaks(d):
        add("dialogue", "có thoại", 1)
    if d.get("camera_move") in BIG_MOVES:
        add("camera_big", f"máy di chuyển ({d['camera_move']})", 1)
    elif not d.get("camera_move") and d.get("camera_complexity") == "complex":
        add("camera_big", "máy / cảnh phức tạp", 1)
    if ref_video:
        add("ref_video", "video tham chiếu", 1)
    total = sum(f["weight"] for f in factors)
    suggest = "easy" if total <= EASY_MAX else ("complex" if total >= COMPLEX_MIN else "unknown")
    return {"score": total, "factors": factors, "suggest": suggest}


def reconcile(scene_data: Dict, ref_video: bool = False) -> Dict:
    """The fields to merge into a shot row: `difficulty` (the Director's label, cleaned; an "easy" that the fields contradict → "unknown"),
    `difficulty_why` (when written) and `difficulty_check` {score, factors, suggest, note?}."""
    # 15/10: nhãn code tự điền lần trước (`difficulty_by` = "check") không phải nhãn Đạo diễn — chấm lại như thiếu nhãn. Rà vòng
    # gop-1510 mục 3: dữ liệu trước 15/10 chưa có `difficulty_by` nhưng ghi chú "Đạo diễn chưa ghi độ khó…" cũng là nhãn code
    old_check = scene_data.get("difficulty_check")
    old_note = str(old_check.get("note") or "") if isinstance(old_check, dict) else ""
    by_check = scene_data.get("difficulty_by") == "check" or (not scene_data.get("difficulty_by")
                                                              and old_note.startswith("Đạo diễn chưa ghi độ khó"))
    label = clean_label(None if by_check else scene_data.get("difficulty"))
    if (label == "unknown" and scene_data.get("difficulty_by") == "director" and scene_data.get("difficulty_director") == "easy"):
        label = "easy"          # chấm lại một nhãn 'dễ' đã hạ hiển thị lần trước: vẫn là nhãn Đạo diễn 'dễ' (không mất khi lưu lại)
    why = clean_why(scene_data.get("difficulty_why"))
    s = score(scene_data, ref_video=ref_video)
    check = {"score": s["score"], "factors": [f["label"] for f in s["factors"]], "suggest": s["suggest"]}
    director_easy = False
    if label == "easy" and s["score"] > EASY_MAX:
        # quyết định người dùng 15/10: điểm kiểm chéo KHÔNG ép đường đi (2 người / thoại + tay không làm shot khó) — nhãn hiển thị
        # 'chưa rõ' + ghi chú giữ để người xem, `difficulty_director` giữ nhãn gốc cho quality_tier.label_from_director
        check["note"] = ("kiểm chéo: Đạo diễn ghi 'dễ' nhưng shot có " + " · ".join(check["factors"])
                         + f" (điểm {s['score']}) → hiển thị 'chưa rõ'; đường đi theo nhãn Đạo diễn + dấu hiệu khó code ép")
        label, director_easy = "unknown", True
    elif by_check or "difficulty" not in scene_data or scene_data.get("difficulty") in (None, ""):
        # nhãn THỐNG KÊ theo kiểm chéo; đường làm clip (quality_tier.route) coi shot thiếu nhãn Đạo diễn là KHÓ → nháp trước (15/10)
        label = "complex" if s["suggest"] == "complex" else "easy"
        check["note"] = ("Đạo diễn chưa ghi độ khó → theo kiểm chéo: " + (f"'phức tạp' (điểm {s['score']}: " + " · ".join(check["factors"])
                         + ")" if label == "complex" else f"'dễ' (điểm {s['score']})") + " — thiếu nhãn Đạo diễn nên vẫn nháp trước")
        out = {"difficulty": label, "difficulty_by": "check", "difficulty_check": check}
        if why:
            out["difficulty_why"] = why
        return out
    out = {"difficulty": label, "difficulty_by": "director", "difficulty_check": check}
    if director_easy:
        out["difficulty_director"] = "easy"
    if why:
        out["difficulty_why"] = why
    return out


def apply(data: Dict, ref_video: bool = False) -> Dict:
    """`data` with the reconciled difficulty fields (in place, also returned); a stale `difficulty_why` is dropped when none is written."""
    fields = reconcile(data, ref_video=ref_video)
    if "difficulty_why" not in fields:
        data.pop("difficulty_why", None)
    if "difficulty_director" not in fields:
        data.pop("difficulty_director", None)
    data.update(fields)
    return data
