"""Cờ `motion_prose` (thử D6 14/10 #28 vs #29): phần chuyển động của prompt video do CODE viết (seedance_refs.shot_motion — đường dùng
khi D6 `chat_prompts` tắt / vượt trần / câu trả lời bị chặn) viết gần cách Claude viết ở #29.

Căn cứ: #28 (code ghép) shot 1 chạy cầu thang optical flow 5,8 vs #29 (Claude) 13,0. Khác ở chữ chuyển động: B kể liền câu, máy nói
CHIỀU ("camera tracks backward holding the same distance"); A là nhãn rời ("Acting — face: …; eyes: …") + "camera track" không chiều —
model không biết máy lùi hay tiến nên dễ giữ người giữa khung, chạy ngắn bước. #29 shot 3–4 rơi về code ghép (diag chat_prompt_cap)
cũng gần đứng hình như #28 → đường code ghép phải tự tốt, không trông vào D6.

Hai việc, không thêm dữ kiện mới (chỉ đổi cách nói dữ kiện Đạo diễn đã có):
- acting_sentence: diễn xuất thành MỘT câu kể, thân trước (thứ làm chuyển động) rồi mặt / mắt — bỏ nhãn "face:", "eyes:".
- camera_phrase: máy track / follow / dolly + MỘT nhân vật chạy / đi + chữ shot nói chiều (travel_truth.camera_mode: chạy VỀ PHÍA máy →
  máy lùi trước mặt; máy sau lưng → bám sau). Không đủ chữ để biết → trả None, giữ "camera track" như cũ (không đoán).
  Rà 14/10: "lead" chỉ khi có ĐỘNG TỪ di chuyển + "toward the camera" hoặc chữ máy lùi ("glancing at the camera" không tính);
  ≥ 2 nhân vật → None (không biết ai chạy); máy sau lưng mà chữ chỉ nói chạy trái/phải → None ("follows behind" dễ xoay người chạy
  vào sâu khung); bỏ "truck" (máy đi ngang, không lùi / bám sau).
0 USD, không gọi model."""
import re
from typing import Dict, List, Optional

FLAG = "motion_prose"
_TRACKING = ("track", "tracking", "follow", "dolly")       # không "truck": máy đi ngang, nói "lùi / bám sau" là sai chiều
_GO = r"(?:run|runs|running|ran|sprint\w*|dash\w*|jog\w*|walk\w*|rush\w*|hurr\w*|charg\w*|climb\w*|heads?|heading|comes?|coming|moves?|moving)"
# chạy VỀ PHÍA máy: động từ di chuyển rồi (≤ 8 chữ) "toward the camera" — không lấy "(at|into) the camera" (liếc / nhìn máy)
_RUN_TOWARD = re.compile(r"(?<!\w)" + _GO + r"(?:\s+[\w'-]+){0,8}?\s+towards? (?:the )?(?:camera|lens|viewer)(?!\w)|"
                         r"(?:chạy|lao|bước|đi)(?:\s+\w+){0,6}?\s+về phía (?:máy|camera)", re.I)
# hướng đi trái / phải (chạy ngang) và hướng đi xa / về phía trước (máy sau lưng thật sự bám theo)
_SIDEWAYS = re.compile(r"(?<!\w)(?:to(?:wards?)? the (?:left|right)|" + _GO + r"(?:\s+\w+){0,3}?\s+(?:left|right)|"
                       r"from (?:frame-)?(?:left|right) to (?:frame-)?(?:left|right)|sang (?:trái|phải)|ngang)(?!\w)", re.I)
_AWAY = re.compile(r"away from (?:the )?camera|(?<!\w)(?:forward|straight ahead|into the distance|xa (?:dần )?máy|về phía trước|"
                   r"thẳng về phía trước)(?!\w)", re.I)


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def who_of(names: List[str]) -> str:
    names = [n for n in names if n]
    if not names:
        return "the character"
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def acting_sentence(who: str, perf: Dict[str, str]) -> str:
    """{"face", "eyes", "body", "timing"} (already filtered: a back view has no face / eyes) → one told sentence, or ""."""
    move = ", ".join(str(perf[k]).strip().rstrip(".") for k in ("body", "timing") if perf.get(k))
    face = str(perf.get("face") or "").strip().rstrip(".")
    eyes = str(perf.get("eyes") or "").strip().rstrip(".")
    look = (f"the face shows {face}" if face else "") + (", " if face and eyes else "") + (f"eyes {eyes}" if eyes else "")
    if not move and not look:
        return ""
    verb = "act" if " and " in who else "acts"          # "KELLY and MAXIM act it out"
    if move and look:
        return f"{who} {verb} it out — {move}; {look}."
    return f"{who} {verb} it out — {move or look}."


def camera_phrase(data: Dict, who: str) -> Optional[str]:
    """The camera words with their direction ("tracks backward ahead of KELLY, …"), or None to keep `camera <move>` as it was."""
    move = str(data.get("camera_move") or "").strip().lower().replace("_", " ")
    if move not in _TRACKING:
        return None
    if len({str(n) for n in data.get("characters") or [] if n}) >= 2:
        return None                                   # rà 14/10: who runs is not known from the fields — never guess the subject
    from . import motion_physics, travel_truth
    en = data.get("motion_en") if isinstance(data.get("motion_en"), dict) else {}
    action = " ".join(str(x) for x in (data.get("action"), en.get("action")) if x)
    if not motion_physics.moves_through_space(action):
        return None                                   # nobody runs / walks: nothing to say about following a runner
    probe = dict(data, text=" ".join(str(x) for x in (data.get("text"), en.get("action")) if x))   # the English action counts too
    mode = travel_truth.camera_mode(probe)
    words = travel_truth._words(probe)
    cam_words = " ".join(str(data.get(k) or "") for k in ("shot", "camera_setup"))
    if mode.get("mode") == "lead":
        backs = (travel_truth._said(travel_truth._LEAD_CAM, cam_words)
                 or travel_truth._said(travel_truth._LEAD_WORDS, words + " " + cam_words))
        if not (backs or travel_truth._said(_RUN_TOWARD, words)):
            return None                               # "toward" came from a look ("glancing at the camera"), not from the run
        return f"tracks backward ahead of {who}, holding the same distance as {who} comes toward it"
    if mode.get("mode") == "follow":
        if travel_truth._said(_SIDEWAYS, words) and not travel_truth._said(_AWAY, words):
            return None                               # runs left / right with the camera behind: the direction on screen is not known
        return f"follows behind {who}, moving along with {who} at the same distance"
    return None
