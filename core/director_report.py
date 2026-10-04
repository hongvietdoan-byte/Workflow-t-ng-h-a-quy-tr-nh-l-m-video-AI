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
# director.md tầng 4: which tradeoff covers which sacrifice — a tradeoff about the music does not excuse a dropped line
# (TON_DONG A4 / R1: "đọc câu" is speaking time, not a dropped line; "khung hình" is the frame, not the length frame)
_GAVE_UP_WORDS = {"bỏ câu thoại": r"(?<!đọc )(?<!\w)câu(?!\w)|(?<!\w)thoại|(?<!\w)lời(?!\w)|\blines?\b|dialog",
                  "lệch khung thời lượng": r"thời lượng|khung(?!\s*(?:hình|cảnh|ảnh))|độ dài|dài hơn|ngắn hơn|(?<!\w)giây(?!\w)|\d\s*s\b|\blength\b|duration|"
                                           r"longer|shorter",
                  "shot thiếu thời gian nói": r"thời gian (nói|đọc)|đọc (câu|hết)|nói (hết|kịp)|đủ giây|\bspeech\b|speaking time|"
                                              r"time to (say|speak)",
                  "bỏ góc máy kịch bản ghi": r"góc máy|góc camera|\bangle\b|qua vai|sau vai|cận cảnh|toàn cảnh|\bots\b"}
# prompts 17/19/20: tradeoffs[].kind — one of these names the sacrifice without guessing from words
TRADEOFF_KINDS = {"dropped_line": "bỏ câu thoại", "length": "lệch khung thời lượng", "speech_time": "shot thiếu thời gian nói",
                  "script_angle": "bỏ góc máy kịch bản ghi"}
# prompt 17 "Kịch bản ghi rõ góc máy thì giữ đúng": the script's own camera words and the shot that honours them
_SCRIPT_ANGLES = ((re.compile(r"(?:sau|qua)\s+vai\s+(?:của\s+)?([A-ZÀ-Ỹa-zà-ỹ]+)", re.I), "ots"),
                  (re.compile(r"\bcận\s+cảnh\b", re.I), "close"),
                  (re.compile(r"\btoàn\s+cảnh\b", re.I), "wide"))


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
            if isinstance(d, dict) and not dialogue.is_non_speaker(str(d.get("speaker") or ""))
            and str(d.get("text") or "").strip()]


def script_angles(story, shots) -> List[Dict]:
    """Camera words the script wrote ("GÓC CAMERA SAU VAI KENTA", "CẬN CẢNH", "TOÀN CẢNH") that no shot of that scene honours:
    [{"scene", "wanted"}]. Rank 3 of the Director's scale — giving it up is allowed, not silently."""
    out = []
    for sc_i, sc in enumerate(story, 1):
        text = f"{sc.heading or ''}\n{sc.text or ''}"
        mine = [s for idx, _, s in shots if idx == sc_i]
        for rx, kind in _SCRIPT_ANGLES:
            for m in rx.finditer(text):
                if kind == "ots":
                    who = m.group(1).upper()
                    ok = any(s.get("angle") == "ots" and who in [str(c).upper() for c in s.get("characters") or []] for s in mine)
                    wanted = f"qua vai {who}"
                elif kind == "close":
                    ok, wanted = any(s.get("size") in ("CU", "ECU") for s in mine), "cận cảnh"   # prompt 17: "CẬN CẢNH" → CU
                else:
                    ok, wanted = any(s.get("size") in ("WS", "EWS") for s in mine), "toàn cảnh"
                if not ok and {"scene": sc_i, "wanted": wanted} not in out:
                    out.append({"scene": sc_i, "wanted": wanted})
    return out


def _uncovered(gave_up: List[tuple], trade: List[Dict]) -> List[str]:
    """The sacrifices no tradeoff speaks about: a tradeoff counts for a kind when its `kind` is that kind (TRADEOFF_KINDS) — or,
    with no kind, when what it GAVE UP names it (what it chose does not: "chose: giữ đủ giây cho câu thoại, gave_up: nhạc nền" gave up
    the music, not a line) — and its scene (when both say one) is the same."""
    out = []
    for kind, scenes in gave_up:
        rx = re.compile(_GAVE_UP_WORDS[kind], re.I)
        hits = [t for t in trade if TRADEOFF_KINDS.get(str(t.get("kind") or "")) == kind
                or (str(t.get("kind") or "") not in TRADEOFF_KINDS and rx.search(str(t.get("gave_up") or "")))]
        if scenes:
            hits = [t for t in hits if not str(t.get("scene") or "").strip() or _int(t.get("scene")) in scenes]
        if not hits:
            out.append(kind)
    return out


def unknown_kinds(trade: List[Dict]) -> List[str]:
    """TON_DONG A4 / R1: a `kind` outside TRADEOFF_KINDS ("lines", "music"…) is not taken silently — it is reported, and the tradeoff
    is read by its words like one with no kind."""
    return sorted({str(t.get("kind")).strip() for t in trade if str(t.get("kind") or "").strip()
                   and str(t.get("kind")).strip() not in TRADEOFF_KINDS})


def _int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
    from . import continuity, performance, sound_intent
    in_target = bool(target and target[0] - 0.05 <= total <= target[1] + 0.05) if target else None
    trade = [t for t in (obj.get("tradeoffs") or []) if isinstance(t, dict)]
    bad_trade = [t for t in (obj.get("tradeoffs") or []) if not isinstance(t, dict) or not all(str(t.get(k) or "").strip()
                                                                                          for k in TRADEOFF_KEYS)]
    # director.md tầng 4: giving up something of lower rank is fine, keeping quiet about it is not (dropped lines, a length outside the
    # script's frame, a line squeezed into a shot too short to say it)
    angles = script_angles(story, shots)
    gave_up = [(kind, scenes) for kind, hit, scenes in (
        ("bỏ câu thoại", bool(dropped), {d["scene"] for d in dropped}),
        ("lệch khung thời lượng", in_target is False, set()),
        ("shot thiếu thời gian nói", bool(short_speech), {int(x["shot"].split("·")[0]) for x in short_speech}),
        ("bỏ góc máy kịch bản ghi", bool(angles), {a["scene"] for a in angles})) if hit]
    return {
        "shots": len(shots), "total_s": total, "target": target,
        "in_target": in_target,
        "sections": sections, "short_speech": short_speech, "silent_micro": silent_micro, "wide_short": wide_short,
        "lip_sync": lip, "void_background": void, "under_2s": under2, "dropped": dropped, "dropped_answered": sum(d["answered"] for d in dropped),
        "invented": invented, "tradeoffs": obj.get("tradeoffs") or [],
        "tradeoffs_bad": len(bad_trade), "unrecorded": _uncovered(gave_up, trade), "tradeoffs_unknown_kind": unknown_kinds(trade),
        "script_angles": angles,
        "acting": performance.warnings([s for _, _, s in shots]),
        "sound": sound_intent.warnings([s for _, _, s in shots]),
        "pacing": mid_hook_gaps([s for _, _, s in shots])
        + [f"cảnh {a['scene']}: kịch bản ghi \"{a['wanted']}\" mà không shot nào giữ" for a in angles] + retime_dropped(obj)
        + opening_and_product(obj),
        "payoff_unplanted": payoff_unplanted(obj),
        "turns_without_cause": turns_without_cause(obj) + moves_without_reason(obj),
        "continuity": continuity.axis_warnings(shots) + continuity.motif_warnings(shots)
        + continuity.lighting_warnings([sc for sc in obj.get("scenes") or [] if isinstance(sc, dict)]),
        "script_notes": [n for n in obj.get("script_notes") or [] if isinstance(n, dict) and str(n.get("note") or "").strip()],
        "paid_s": {"per_shot": per_shot, "per_scene": per_scene, "per_setup": per_setup, "setups": len(setups) or None},
        "paid_usd": {k: (round(v * usd, 2) if (v is not None and usd) else None)
                     for k, v in (("per_shot", per_shot), ("per_scene", per_scene), ("per_setup", per_setup))},
        "model": model,
    }


OPEN_HOOK_S, MID_HOOK_GAP, LONG_FILM = 3.0, 15.0, 20.0   # director.md Đ2: after the opening hook, a new open question every ~15 s


def mid_hook_gaps(shots: List[Dict]) -> List[str]:
    """director.md Đ2 "móc nhỏ giữa video" (giả thuyết, đo dần): in a film longer than LONG_FILM s, stretches of more than MID_HOOK_GAP s
    between the opening hook and the last 5 s with no shot marked `hook_mid` (or a hook / a peak of intensity 5 that itself pulls
    the viewer on). Soft — the code cannot tell which detail is really left open, the Director marks it."""
    total = sum(float(s.get("duration_s") or 0) for s in shots)
    if total <= LONG_FILM:
        return []
    marks, t = [OPEN_HOOK_S], 0.0
    for s in shots:
        p = s.get("performance") if isinstance(s.get("performance"), dict) else {}
        if s.get("hook_mid") is True or (t >= OPEN_HOOK_S and (s.get("role") == "hook" or p.get("intensity") == 5)):
            marks.append(t)
        t += float(s.get("duration_s") or 0)
    marks = sorted(set(marks)) + [max(total - 5.0, OPEN_HOOK_S)]
    return [f"{a:.0f}–{b:.0f} s: {b - a:.0f} s không có móc giữa video (`hook_mid`) — người xem có thể lướt đi; đặt một chi tiết dở dang"
            for a, b in zip(marks, marks[1:]) if b - a > MID_HOOK_GAP]


def with_current_shots(raw: Dict, rows: List[Dict]) -> Dict:
    """The Director's answer with each scene's shots replaced by the shot rows as they are now (Step 1 hand edits included) — the
    checks then judge what will be made, not the first answer. rows: [{"data": {...story_scene...}}] in film order."""
    by_scene: Dict[int, List[Dict]] = {}
    for r in rows:
        d = dict(r["data"])
        if d.get("story_scene"):
            d.setdefault("start_frame", d.get("blocking") or "")
            d.setdefault("hero", d.get("shot_role") == "hero")
            by_scene.setdefault(int(d["story_scene"]), []).append(d)
    if not by_scene:
        return raw
    out = dict(raw)
    out["scenes"] = [dict(sc, shots=by_scene.get(int(sc.get("idx") or 0), sc.get("shots") or [])) for sc in raw.get("scenes") or []]
    return out


def retime_dropped(obj: Dict) -> List[str]:
    """Fields the code dropped from the answer instead of using them — said, not silent (CHUAN_XAY_DUNG luật 1)."""
    from .shots import KNOWLEDGE_GAPS, SPEED_MAX, SPEED_MIN
    out = []
    for sc in obj.get("scenes") or []:
        gap = sc.get("knowledge_gap")
        if gap not in (None, "") and gap not in KNOWLEDGE_GAPS:
            out.append(f"cảnh {sc.get('idx')}: knowledge_gap \"{gap}\" không phải ahead/same/behind — bỏ")
        for k, s in enumerate(sc.get("shots") or [], 1):
            if not isinstance(s, dict) or (s.get("speed") is None and s.get("freeze_end_s") is None):
                continue
            speaks = any(isinstance(d, dict) and str(d.get("text") or "").strip() for d in s.get("dialogue") or [])
            speed = s.get("speed")
            if speaks or s.get("lip_sync"):
                out.append(f"shot {sc.get('idx')}·{k}: speed/freeze ở shot có thoại/khớp môi — bỏ (giọng chậm lại là sai)")
            elif speed is not None and not (isinstance(speed, (int, float)) and SPEED_MIN <= speed <= SPEED_MAX):
                out.append(f"shot {sc.get('idx')}·{k}: speed {speed} ngoài {SPEED_MIN}–{SPEED_MAX} — bỏ")
    return out


def opening_and_product(obj: Dict) -> List[str]:
    """director.md Đ2 / Đ10: no shot of role hook starting in the first OPEN_HOOK_S s; no `money_shot` in a promotional video (genre
    COMMERCIAL — TON_DONG A5 / R3: a drama has no product moment to show; the cover then falls back to the ⭐ climax); a money_shot that
    is not true/false (dropped)."""
    out, t, hook, money = [], 0.0, False, False
    for sc in obj.get("scenes") or []:
        for k, s in enumerate(sc.get("shots") or [], 1):
            if not isinstance(s, dict):
                continue
            if s.get("role") == "hook" and t < OPEN_HOOK_S:
                hook = True
            if s.get("money_shot") is True:
                money = True
            elif s.get("money_shot") not in (None, False):
                out.append(f"shot {sc.get('idx')}·{k}: money_shot \"{s.get('money_shot')}\" không phải true/false — bỏ")
            t += float(s.get("duration_s") or 0)
    if t and not hook:
        out.append(f"không shot nào `role: hook` bắt đầu trong {OPEN_HOOK_S:g} s đầu — người xem quyết ở lại hay lướt ở đây (Đ2)")
    if t and not money and str(obj.get("genre") or "").strip().upper() == "COMMERCIAL":
        out.append("chưa có `money_shot` — ảnh bìa sẽ lấy shot ⭐ cao trào (video quảng bá nên chỉ rõ khoảnh khắc sản phẩm, Đ10)")
    return out


def payoff_unplanted(obj: Dict) -> List[int]:
    """director.md Đ1 (việc code V1): scenes whose `beat.payoff` has no `beat.plant` in any scene before them — a twist nobody set up."""
    planted, out = False, []
    for sc in obj.get("scenes") or []:
        beat = sc.get("beat") if isinstance(sc.get("beat"), dict) else {}
        if str(beat.get("payoff") or "").strip() and not planted:
            out.append(sc.get("idx"))
        planted = planted or bool(str(beat.get("plant") or "").strip())
    return out


def moves_without_reason(obj: Dict) -> List[str]:
    """S3.5, adjusted by the research (2026-09-29): the reference drama keeps the camera still 98 % of the time and cuts close-ups back to
    back, so the plan's "≤ 2 same size in a row / a move in every scene" would be a fixed rule the films do not follow. What stays: a
    camera that MOVES says why (dp.md Q5 — a move needs a motive in the story; the meaning is the situation's, not the move's)."""
    out = []
    for sc in obj.get("scenes") or []:
        for k, s in enumerate(sc.get("shots") or [], 1):
            if isinstance(s, dict) and str(s.get("camera_move") or "static") != "static" and not str(s.get("why") or "").strip():
                out.append(f"shot {sc.get('idx')}·{k}: máy {s.get('camera_move')} mà chưa ghi `why` — chuyển động này phục vụ gì ở đây?")
    return out


def turns_without_cause(obj: Dict) -> List[str]:
    """S3.1 (kế hoạch sau #8 — Maxim hit, no shooter shown): scenes whose `beat.turn` says what turns but not `beat.cause` (what makes
    it turn and where the viewer sees it, or "giấu tới …" when hidden on purpose). Soft: there is more than one way to tell a story;
    the code only asks the Director to say which (knowledge/craft — no fixed structure)."""
    out = []
    for sc in obj.get("scenes") or []:
        beat = sc.get("beat") if isinstance(sc.get("beat"), dict) else {}
        if str(beat.get("turn") or "").strip() and not str(beat.get("cause") or "").strip():
            out.append(f"cảnh {sc.get('idx')}: có cú xoay (\"{str(beat['turn'])[:50]}\") mà chưa ghi `cause` — người xem thấy nguyên nhân ở đâu?")
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
    if r.get("tradeoffs_unknown_kind"):
        rows.append("⚠ `tradeoffs.kind` không thuộc danh sách (" + ", ".join(r["tradeoffs_unknown_kind"]) + ") — đọc theo chữ ở gave_up; "
                    "loại hợp lệ: " + ", ".join(TRADEOFF_KINDS))
    if r.get("unrecorded"):
        rows.append("⚠ Director đã hy sinh (" + ", ".join(r["unrecorded"]) + ") mà không ghi `tradeoffs`")
    if r.get("payoff_unplanted"):
        rows.append("⚠ Cảnh gặt lại điều chưa được gieo ở cảnh nào trước: " + ", ".join(map(str, r["payoff_unplanted"])))
    for w in r.get("turns_without_cause") or []:
        rows.append(f"  💡 {w}")
    for w in r.get("continuity") or []:
        rows.append(f"  🧭 {w}")
    for w in r.get("acting") or []:
        rows.append(f"  🎭 {w}")
    for w in r.get("sound") or []:
        rows.append(f"  🔊 {w}")
    for w in r.get("pacing") or []:
        rows.append(f"  ⏱ {w}")
    if r.get("script_notes"):
        rows.append(f"Ghi chú kịch bản cho người viết: {len(r['script_notes'])} (chỉ đề xuất — thoại không bị sửa)")
    rows.append(f"Tổng lỗi đo được: {problems(r)}")
    return "\n".join(rows)
