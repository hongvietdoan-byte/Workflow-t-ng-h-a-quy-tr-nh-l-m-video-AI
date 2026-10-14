"""Cờ `motion_prose` (thử D6 14/10 #28 vs #29): phần chuyển động của prompt video do CODE viết (seedance_refs.shot_motion — đường dùng
khi D6 `chat_prompts` tắt / vượt trần / câu trả lời bị chặn) viết gần cách Claude viết ở #29.

Căn cứ: #28 (code ghép) shot 1 chạy cầu thang optical flow 5,8 vs #29 (Claude) 13,0. Khác ở chữ chuyển động: B kể liền câu, máy nói
CHIỀU ("camera tracks backward holding the same distance"); A là nhãn rời ("Acting — face: …; eyes: …") + "camera track" không chiều —
model không biết máy lùi hay tiến nên dễ giữ người giữa khung, chạy ngắn bước. #29 shot 3–4 rơi về code ghép (diag chat_prompt_cap)
cũng gần đứng hình như #28 → đường code ghép phải tự tốt, không trông vào D6.

Hai việc, không thêm dữ kiện mới (chỉ đổi cách nói dữ kiện Đạo diễn đã có):
- acting_sentence: diễn xuất thành MỘT câu kể, thân trước (thứ làm chuyển động) rồi mặt / mắt — bỏ nhãn "face:", "eyes:".
- camera_phrase: máy track / follow / dolly / truck + shot có người chạy / đi + chữ shot nói chiều (travel_truth.camera_mode: chạy VỀ
  PHÍA máy → máy lùi trước mặt; máy sau lưng → bám sau). Không đủ chữ để biết → trả None, giữ "camera track" như cũ (không đoán).
0 USD, không gọi model."""
from typing import Dict, List, Optional

FLAG = "motion_prose"
_TRACKING = ("track", "tracking", "follow", "dolly", "truck")


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
    if move and look:
        return f"{who} acts it out — {move}; {look}."
    return f"{who} acts it out — {move or look}."


def camera_phrase(data: Dict, who: str) -> Optional[str]:
    """The camera words with their direction ("tracks backward ahead of KELLY, …"), or None to keep `camera <move>` as it was."""
    move = str(data.get("camera_move") or "").strip().lower().replace("_", " ")
    if move not in _TRACKING:
        return None
    from . import motion_physics, travel_truth
    en = data.get("motion_en") if isinstance(data.get("motion_en"), dict) else {}
    action = " ".join(str(x) for x in (data.get("action"), en.get("action")) if x)
    if not motion_physics.moves_through_space(action):
        return None                                   # nobody runs / walks: nothing to say about following a runner
    probe = dict(data, text=" ".join(str(x) for x in (data.get("text"), en.get("action")) if x))   # the English action counts too
    mode = travel_truth.camera_mode(probe)
    if mode.get("mode") == "lead":
        return f"tracks backward ahead of {who}, holding the same distance as {who} comes toward it"
    if mode.get("mode") == "follow":
        return f"follows behind {who}, moving along with {who} at the same distance"
    return None
