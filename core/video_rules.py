"""W10: rules of each video model (data/provider_rules.json `video_models`), checked before a clip is sent — a request that breaks
one is refused here, for free and with a clear Vietnamese reason, instead of being rejected by ClipAI (or silently clamped into a
different clip). Source of the numbers: skill clipai-1.3.1 SKILL.md "Constraints" + scripts/video.mjs (read 2026-09-25).

The same table is the one place the Director / DP knowledge reads model limits from (kế hoạch V4, 4.2 B8)."""
import json
import os
from typing import Dict, List, Optional

_RULES = os.path.join(os.path.dirname(__file__), "..", "data", "provider_rules.json")
_cache: Dict = {}


def models() -> Dict[str, Dict]:
    try:
        stamp = os.path.getmtime(_RULES)
    except OSError:
        return {}
    if _cache.get("stamp") != stamp:
        try:
            with open(_RULES, encoding="utf-8") as f:
                data = (json.load(f) or {}).get("video_models") or {}
        except (OSError, ValueError, AttributeError):
            data = {}
        _cache.update(stamp=stamp, data=data)
    return _cache["data"]


def rule(canonical: str) -> Dict:
    return models().get(canonical) or {}


def problems(canonical: str, duration: float, resolution: Optional[str] = None, kling_mode: Optional[str] = None,
             reference_video: bool = False, with_audio: bool = False, last_frame: bool = False, audios: int = 0,
             audio_seconds: float = 0.0) -> List[str]:
    """Why this request cannot be sent to `canonical` as asked ([] = fine; an unknown model is not judged here)."""
    r = rule(canonical)
    if not r:
        return []
    label = r.get("label") or canonical
    out = []
    span = r.get("duration") or {}
    if r.get("family") == "omni":
        cap = span.get("max_with_reference_video") if reference_video else span.get("max")
        if reference_video and cap and duration > cap + 1e-6:
            out.append(f"{label} có video tham chiếu chỉ làm tối đa {cap:g} s (shot này {duration:g} s) — bỏ video tham chiếu "
                       "hoặc chia shot")
        if kling_mode and r.get("modes") and kling_mode not in r["modes"]:
            out.append(f"{label} không có chế độ {kling_mode} (chỉ {', '.join(r['modes'])})")
        if kling_mode == "4k" and reference_video and not r.get("mode_4k_with_reference_video", True):
            out.append(f"{label}: chế độ 4k không đi cùng video tham chiếu")
        if with_audio and not r.get("sound", False):
            out.append(f"{label} không tự tạo âm thanh")
        if with_audio and reference_video and not r.get("sound_with_reference_video", True):
            out.append(f"{label}: âm thanh tự tạo không đi cùng video tham chiếu")
        allowed = r.get("end_frame_durations")
        if last_frame and allowed and int(round(duration)) not in allowed:
            out.append(f"{label} khung đầu + cuối chỉ làm {' hoặc '.join(str(a) for a in allowed)} s (shot này {duration:g} s)")
        if last_frame and not r.get("end_frame", False):
            out.append(f"{label} không nhận khung cuối")
    else:
        if resolution and r.get("resolutions") and resolution not in r["resolutions"]:
            out.append(f"{label} không có độ phân giải {resolution} (chỉ {', '.join(r['resolutions'])})")
        if last_frame and not r.get("last_frame", False):
            out.append(f"{label} không nhận khung cuối")
        if audios and audios > int(r.get("max_audios") or 0):
            out.append(f"{label} nhận tối đa {r.get('max_audios') or 0} file âm thanh tham chiếu (đang gửi {audios})")
        cap_s = r.get("max_audio_seconds")
        if cap_s and audio_seconds > cap_s + 1e-6:
            out.append(f"{label}: tổng âm thanh tham chiếu tối đa {cap_s:g} s (đang gửi {audio_seconds:g} s)")
    return out


def summary_lines() -> List[str]:
    """One line per model for the knowledge the Director / DP read (kế hoạch V4 GĐ4: Q4 comes from this table)."""
    lines = []
    for canonical, r in models().items():
        span = r.get("duration") or {}
        bits = [f"clip {span.get('min', '?')}–{span.get('max', '?')} s", f"prompt ≤ {r.get('prompt_limit', '?')} ký tự"]
        if r.get("family") == "omni":
            if span.get("max_with_reference_video"):
                bits.append(f"có video tham chiếu ≤ {span['max_with_reference_video']} s")
            if r.get("multi_shot"):
                bits.append(f"multi-shot, mỗi shot ≤ {r.get('shot_prompt_limit', 512)} ký tự")
            langs = r.get("speech_languages")
            if langs:                                  # S0.14 T1: the official Kling 3.0 guide — no Vietnamese
                bits.append("thoại gốc chỉ " + "/".join(langs) + (" (không tiếng Việt → giọng Việt là TTS ghép sau)"
                                                                   if "vi" not in langs else ""))
        else:
            bits.append("độ phân giải " + "/".join(r.get("resolutions") or []))
            if r.get("refs_with_first_frame") is False:
                bits.append("không trộn khung đầu với ảnh tham chiếu")
            bits.append(f"≤ {r.get('max_audios', 0)} audio tham chiếu")
        lines.append(f"- {r.get('label') or canonical}: " + "; ".join(bits))
    return lines
