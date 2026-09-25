"""Bàn đo Director (kế hoạch 2026-09-25, H4): score a Director answer with code only — no Claude call, no money.

Four real Director runs of "ANH CHỌN AI?" each showed a new fault (65 s for a 55–58 s script, lines squeezed into shots too short to
say them, lines dropped although the next line answers them, 0,5 s silent shots paid as 3 s clips). This report measures all of them,
so a prompt change or the shot normaliser (core/shot_normalize.py) is judged on saved answers (tests/fixtures/director_*.json) before
anything is paid for.

    report(director_json, script_text) -> dict      text(report) -> Vietnamese summary
"""
import json
import math
import os
import re
from typing import Dict, List, Optional

from . import dialogue, script_parser
from .storyboard_gate import lip_sync_risk

_PROFILES = os.path.join(os.path.dirname(__file__), "..", "data", "video_models.json")
_SECTION_TIME = re.compile(r"[–—-]\s*(\d{1,3})\s*[–—-]\s*(\d{1,3})\s*(giây|giay|s|sec|secs|seconds)\b", re.IGNORECASE)
SILENT_MIN = 1.0          # a silent shot shorter than this is paid as a whole minimum-length clip for nothing (inserts excepted)
WIDE_MIN = 1.5            # a wide shot shorter than this cannot be read
TRADEOFF_KEYS = ("chose", "gave_up", "why")   # director.md tầng 4: each sacrifice says what won, what lost and why
VOID = re.compile(r"\bvoid\b|black background|abstract (emotional )?space|empty darkness", re.IGNORECASE)


def model_limits(model: str = "kling") -> Dict[str, float]:
    with open(_PROFILES, encoding="utf-8") as f:
        prof = json.load(f)["models"][model]
    return {"min": float(prof.get("min_sec") or 3), "max": float(prof.get("max_sec") or 15), "usd": prof.get("usd_per_sec")}


def _paid(seconds: float, lim: Dict[str, float]) -> float:
    """Seconds a clip of this length is billed: never below the model's minimum, half up like the adapter (M11)."""
    return float(min(max(math.floor(seconds + 0.5), lim["min"]), lim["max"]))


def _chunks(durations: List[float], most: float) -> List[float]:
    """Consecutive shots packed into clips of at most `most` seconds (one multi-shot / one camera-setup clip each)."""
    out, cur = [], 0.0
    for d in durations:
        if cur and cur + d > most:
            out.append(cur)
            cur = 0.0
        cur += d
    return out + ([cur] if cur else [])


def _spoken(shot: Dict):
    return [(str(d.get("speaker") or "").strip().upper(), str(d.get("text") or "").strip()) for d in shot.get("dialogue") or []
            if isinstance(d, dict) and str(d.get("speaker") or "").strip().upper() not in dialogue.NOT_SPEAKERS
            and str(d.get("text") or "").strip()]


def report(obj: Dict, script_text: str, model: str = "kling") -> Dict:
    lim = model_limits(model)
    _, story = script_parser.split_end_card(script_parser.split_scenes([r for r in script_text.splitlines() if r.strip()]))
    from .prompts import target_seconds
    target = target_seconds(script_text)
    shots = [(sc["idx"], k, s) for sc in obj.get("scenes") or [] for k, s in enumerate(sc.get("shots") or [], 1)]
    used = {dialogue.norm(t) for _, _, s in shots for _, t in _spoken(s)}
    script_lines = [(sc_i, who, said) for sc_i, sc in enumerate(story, 1) for who, said in dialogue.lines(sc.text)]
    known = {dialogue.norm(said) for _, _, said in script_lines}

    short_speech, silent_micro, wide_short, lip, under2, void = [], [], [], [], 0, []
    for idx, k, s in shots:
        dur = float(s.get("duration_s") or 0)
        lines = _spoken(s)
        need = dialogue.needed_seconds(lines)
        tag = f"{idx}·{k}"
        under2 += dur < 2
        if need and need > dur + 0.05:
            short_speech.append({"shot": tag, "need": need, "dur": dur})
        if not lines and dur < SILENT_MIN and s.get("role") != "insert":
            silent_micro.append({"shot": tag, "dur": dur})
        if s.get("size") in ("WS", "EWS") and dur < WIDE_MIN:
            wide_short.append({"shot": tag, "dur": dur})
        if lip_sync_risk(s):
            lip.append(tag)
        if VOID.search(str(s.get("image_prompt") or "")):   # 2A: "black void" opening looked unfinished
            void.append(tag)

    dropped = []
    for i, (sc_i, who, said) in enumerate(script_lines):
        if dialogue.norm(said) in used:
            continue
        nxt = script_lines[i + 1] if i + 1 < len(script_lines) and script_lines[i + 1][0] == sc_i else None
        dropped.append({"scene": sc_i, "speaker": who, "text": said,
                        "answered": bool(nxt and nxt[1] != who and dialogue.norm(nxt[2]) in used)})
    invented = sorted({t for _, _, s in shots for _, t in _spoken(s) if dialogue.norm(t) not in known})

    sections = []
    for sc_i, sc in enumerate(story, 1):
        m = _SECTION_TIME.search(sc.heading or "")
        planned = int(m.group(2)) - int(m.group(1)) if m else None
        got = round(sum(float(s.get("duration_s") or 0) for idx, _, s in shots if idx == sc_i), 1)
        sections.append({"scene": sc_i, "heading": sc.heading, "planned": planned, "shots_s": got,
                         "speech_s": round(sum(dialogue.needed_seconds([r]) for r in dialogue.lines(sc.text)), 1)})

    total = round(sum(float(s.get("duration_s") or 0) for _, _, s in shots), 1)
    per_shot = sum(_paid(float(s.get("duration_s") or 0), lim) for _, _, s in shots)
    per_scene = 0.0
    for sc in obj.get("scenes") or []:
        per_scene += sum(_paid(c, lim) for c in _chunks([float(s.get("duration_s") or 0) for s in sc.get("shots") or []], lim["max"]))
    setups: Dict = {}
    for idx, _, s in shots:
        if s.get("camera_setup"):
            setups.setdefault((idx, str(s["camera_setup"])), []).append(float(s.get("duration_s") or 0))
    per_setup = (sum(_paid(c, lim) for ds in setups.values() for c in _chunks(ds, lim["max"])) if setups else None)
    usd = lim["usd"]
    from . import performance
    in_target = bool(target and target[0] - 0.05 <= total <= target[1] + 0.05) if target else None
    trade = [t for t in (obj.get("tradeoffs") or []) if isinstance(t, dict)]
    bad_trade = [t for t in (obj.get("tradeoffs") or []) if not isinstance(t, dict) or not all(str(t.get(k) or "").strip()
                                                                                          for k in TRADEOFF_KEYS)]
    # director.md tầng 4: giving up something of lower rank is fine, keeping quiet about it is not (dropped lines, a length outside the
    # script's frame, a line squeezed into a shot too short to say it)
    gave_up = [why for why, hit in (("bỏ câu thoại", bool(dropped)), ("lệch khung thời lượng", in_target is False),
                                    ("shot thiếu thời gian nói", bool(short_speech))) if hit]
    return {
        "shots": len(shots), "total_s": total, "target": target,
        "in_target": in_target,
        "sections": sections, "short_speech": short_speech, "silent_micro": silent_micro, "wide_short": wide_short,
        "lip_sync": lip, "void_background": void, "under_2s": under2, "dropped": dropped, "dropped_answered": sum(d["answered"] for d in dropped),
        "invented": invented, "tradeoffs": obj.get("tradeoffs") or [],
        "tradeoffs_bad": len(bad_trade), "unrecorded": gave_up if gave_up and not trade else [],
        "acting": performance.warnings([s for _, _, s in shots]),
        "payoff_unplanted": payoff_unplanted(obj),
        "script_notes": [n for n in obj.get("script_notes") or [] if isinstance(n, dict) and str(n.get("note") or "").strip()],
        "paid_s": {"per_shot": per_shot, "per_scene": per_scene, "per_setup": per_setup, "setups": len(setups) or None},
        "paid_usd": {k: (round(v * usd, 2) if (v is not None and usd) else None)
                     for k, v in (("per_shot", per_shot), ("per_scene", per_scene), ("per_setup", per_setup))},
        "model": model,
    }


def payoff_unplanted(obj: Dict) -> List[int]:
    """director.md Đ1 (việc code V1): scenes whose `beat.payoff` has no `beat.plant` in any scene before them — a twist nobody set up."""
    planted, out = False, []
    for sc in obj.get("scenes") or []:
        beat = sc.get("beat") if isinstance(sc.get("beat"), dict) else {}
        if str(beat.get("payoff") or "").strip() and not planted:
            out.append(sc.get("idx"))
        planted = planted or bool(str(beat.get("plant") or "").strip())
    return out


def problems(r: Dict) -> int:
    """How many measured faults (0 = the answer passes every check the code can make)."""
    return (len(r["short_speech"]) + len(r["silent_micro"]) + len(r["wide_short"]) + len(r["lip_sync"]) + r["dropped_answered"]
            + len(r["invented"]) + len(r.get("void_background") or []) + (0 if r["in_target"] in (None, True) else 1)
            + (1 if r.get("unrecorded") else 0) + len(r.get("payoff_unplanted") or []))


def text(r: Dict) -> str:
    t = r["target"]
    rows = [f"Shot: {r['shots']} · tổng {r['total_s']:g}s" + (f" (khung {t[0]}–{t[1]}s: {'đạt' if r['in_target'] else 'LỆCH'})" if t else ""),
            f"Shot thiếu thời gian nói: {len(r['short_speech'])}"
            + (" — " + ", ".join(f"{x['shot']} cần {x['need']:g}s/có {x['dur']:g}s" for x in r["short_speech"][:6]) if r["short_speech"] else ""),
            f"Shot im lặng < {SILENT_MIN:g}s: {len(r['silent_micro'])} · toàn cảnh < {WIDE_MIN:g}s: {len(r['wide_short'])} · "
            f"shot < 2s: {r['under_2s']}/{r['shots']}",
            f"Cận mặt người đang nói: {len(r['lip_sync'])}" + (" — " + ", ".join(r["lip_sync"]) if r["lip_sync"] else ""),
            f"Nền đen trơn / void: {len(r.get('void_background') or [])}" + (" — " + ", ".join(r["void_background"]) if r.get("void_background") else ""),
            f"Câu bị bỏ: {len(r['dropped'])} (có câu đáp lại ngay sau: {r['dropped_answered']}) · câu không có trong kịch bản: {len(r['invented'])}"]
    for d in r["dropped"]:
        rows.append(f"  ✂ cảnh {d['scene']} {d['speaker']}: “{d['text']}”" + (" ⚠ câu sau đáp lại" if d["answered"] else ""))
    for s in r["sections"]:
        rows.append(f"  Cảnh {s['scene']} ({s['heading']}): shot {s['shots_s']:g}s"
                    + (f" / kịch bản {s['planned']}s" if s["planned"] is not None else "") + f" · thoại cần ~{s['speech_s']:g}s")
    p, u = r["paid_s"], r["paid_usd"]
    rows.append(f"Giây video trả tiền ({r['model']}): từng shot {p['per_shot']:g}s" + (f" ≈ ${u['per_shot']:g}" if u["per_shot"] else "")
                + f" · gom theo cảnh {p['per_scene']:g}s" + (f" ≈ ${u['per_scene']:g}" if u["per_scene"] else "")
                + (f" · theo vị trí máy ({p['setups']} setup) {p['per_setup']:g}s" + (f" ≈ ${u['per_setup']:g}" if u["per_setup"] else "")
                   if p["per_setup"] is not None else ""))
    if r["tradeoffs"]:
        rows.append("Đánh đổi Director ghi lại: " + "; ".join(str(x.get("chose") if isinstance(x, dict) else x)[:80] for x in r["tradeoffs"][:5])
                    + (f" ({r['tradeoffs_bad']} mục thiếu chose/gave_up/why)" if r.get("tradeoffs_bad") else ""))
    if r.get("unrecorded"):
        rows.append("⚠ Director đã hy sinh (" + ", ".join(r["unrecorded"]) + ") mà không ghi `tradeoffs`")
    if r.get("payoff_unplanted"):
        rows.append("⚠ Cảnh gặt lại điều chưa được gieo ở cảnh nào trước: " + ", ".join(map(str, r["payoff_unplanted"])))
    for w in r.get("acting") or []:
        rows.append(f"  🎭 {w}")
    if r.get("script_notes"):
        rows.append(f"Ghi chú kịch bản cho người viết: {len(r['script_notes'])} (chỉ đề xuất — thoại không bị sửa)")
    rows.append(f"Tổng lỗi đo được: {problems(r)}")
    return "\n".join(rows)
