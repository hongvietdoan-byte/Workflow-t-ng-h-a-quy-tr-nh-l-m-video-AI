"""💡 Ý tưởng thô → kịch bản (S11.1, docs/KE_HOACH_TINH_NANG_DIRECTOR_2026-10-01.md mục 2; cờ `idea_to_script`, TẮT tới khi qua bộ đo S11.2).

Step 1 only took a written script: a 2–3 line idea became one scene without dialogue and the Director invented everything inside the
Bible call, with nowhere for the person to approve what was invented (#8: "truyện cụt", 83 s of script for ~58 s of video). Here a
**Biên kịch** (knowledge/roles/screenwriter.md, prompts/23) works in 4 turns, each one approved by the person:

  1 questions(…)   what the idea has / lacks, ≤ 5 questions each with a default (a default used is written down — luật 1)
  2 directions(…)  3 really different loglines + a 3 s hook (+ an approved trend card only when the project's trend mode ≠ off)
  3 outline(…)     beats with seconds (hook → setup → turn → climax → ending); code checks length ± 10 % and dialogue per beat
  4 write(…)       the full script in Step 1's format; code re-parses it (script_parser) and checks it; nothing goes on until it parses
Then the person reads it beside the idea (what the Biên kịch added is marked), edits it, and `use_script` puts it into Step 1 exactly
like a pasted script — every later gate (Bible, storyboard, budget) is unchanged.

Money: stage `screenwriter` (counted with the Director in the project budget), a hard cap of RUN_CAP_USD per idea for all its turns
(llm_runner.spend_cap), the estimate shown before each paid turn. State per project in app_settings ('idea:<pid>').
"""
import json
import re
from typing import Dict, List, Optional

FEATURE = "idea_to_script"
STAGE = "screenwriter"
RUN_CAP_USD = 0.30              # plan: 4 Sonnet calls ≈ 0.1 USD / script; hard cap 0.3 per idea
TURN_USD = 0.03                 # estimate shown before a turn (≈ 6k tokens in, 1.5k out)
SPEECH_RATE = 2.86              # syllables / second, measured (tools/measure_speech_rate.py)
DURATIONS = (15, 30, 60)
PLATFORMS = ("TikTok", "Facebook Reels", "YouTube Shorts")
TREND_MODES = {"off": "Tắt", "suggest": "Gợi ý", "prefer": "Ưu tiên"}
BEATS = ("hook", "setup", "turn", "climax", "ending")
HOOK_MAX_S = 3.5
MAX_QUESTIONS = 5
_AGE = re.compile(r"\b([1-9]|1[0-7])\s*(tuổi|years?\s*old|yo)\b", re.I)
_HEADING_PLACE = re.compile(r"^\s*c[ảa]nh\s*\d+\s*[-–—:.]\s*(.*)$", re.I)


class IdeaError(ValueError):
    """Shown to the person as it is (a ValueError, so the dashboard's `act` shows it instead of crashing)."""


def enabled() -> bool:
    from . import features
    return features.on(FEATURE)


# ---- state --------------------------------------------------------------------------------------------------------------------------
def _key(pid: int) -> str:
    return f"idea:{pid}"


def get_state(conn, pid: int) -> Dict:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_key(pid),)).fetchone()
    try:
        return json.loads(row[0]) if row else {}
    except ValueError:
        return {}


def save_state(conn, pid: int, state: Dict) -> Dict:
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (_key(pid), json.dumps(state, ensure_ascii=False)))
    conn.commit()
    return state


def reset(conn, pid: int) -> None:
    conn.execute("DELETE FROM app_settings WHERE key=?", (_key(pid),))
    conn.commit()


def start(conn, pid: int, idea: str, duration_s: int = 30, aspect: str = "9:16", platform: str = "TikTok", tone: str = "",
          characters: Optional[List[str]] = None, cta: str = "", trend: str = "off") -> Dict:
    """A new idea (forgets the previous one's turns)."""
    idea = (idea or "").strip()
    if len(idea) < 10:
        raise IdeaError("Ý tưởng quá ngắn — viết ít nhất một câu: ai, ở đâu, chuyện gì")
    if trend not in TREND_MODES:
        raise IdeaError("chế độ trend không hợp lệ")
    state = {"inputs": {"idea": idea, "duration_s": int(duration_s), "aspect": aspect, "platform": platform, "tone": tone.strip(),
                        "characters": [str(c).upper() for c in characters or []], "cta": cta.strip(), "trend": trend},
             "spent": 0.0, "turn": 0}
    return save_state(conn, pid, state)


# ---- what the Biên kịch reads ------------------------------------------------------------------------------------------------------
def library(conn, pid: int, game: str = "FF") -> Dict[str, List[str]]:
    """Names in the FF library (shared + this project's): characters and places — the Biên kịch prefers them (B6), the code flags others."""
    from . import assets
    out = {"characters": [], "places": []}
    for a in assets.list_assets(conn, game, None, pid):
        names = [a["name"]] + [x.strip() for x in str(a.get("aliases") or "").split(",") if x.strip()]
        if a["kind"] in ("character", "pet"):
            out["characters"] += names
        elif a["kind"] == "location":
            out["places"] += names
    return out


def trend_block(conn, mode: str) -> str:
    """The approved, unexpired, non-high-copyright trend cards — only when the project's mode is not off (Q1). Trend cards come with S11.3;
    until then there are none and the Biên kịch is told so (it must not invent a trend)."""
    if mode == "off":
        return ""
    try:
        rows = conn.execute("SELECT id, title, meaning_vi, how_used, fit_ff FROM trend_cards WHERE status='approved' AND "
                            "copyright_level != 'high' AND (expires_at IS NULL OR expires_at > datetime('now')) LIMIT 8").fetchall()
    except Exception:  # noqa: BLE001 - no trend table yet (S11.3)
        rows = []
    if not rows:
        return f"## Xu hướng dùng được (chế độ {TREND_MODES[mode]})\nChưa có thẻ trend nào được duyệt — KHÔNG dùng trend, không bịa trend."
    lines = [f"## Xu hướng dùng được (chế độ {TREND_MODES[mode]})"]
    for r in rows:
        lines.append(f"- [{r[0]}] {r[1]}: {r[2]} — cách dùng: {r[3]} — hợp FF: {r[4]}")
    return "\n".join(lines)


def _section(name: str) -> str:
    from .prompts import _read
    text = _read("prompts", "23_idea_to_script.md")
    m = re.search(rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        raise IdeaError(f"prompts/23 thiếu khối {name}")
    return m.group(1).strip()


def build_prompt(conn, pid: int, state: Dict, turn: int) -> str:
    from .prompts import _read
    inp = state["inputs"]
    lib = library(conn, pid)
    parts = [f"# Biên kịch — Lượt {turn}", _section("CHUNG"), "## Vai của bạn", _read("knowledge", "roles", "screenwriter.md"),
             "## Viết thoại", _read("knowledge", "dialogue_craft.md"), "## Thể loại", _read("knowledge", "genre_guides.md"),
             "## Đầu vào của người dùng",
             f"Ý tưởng: {inp['idea']}\nThời lượng mục tiêu: {inp['duration_s']} s · khung {inp['aspect']} · nền tảng {inp['platform']}"
             + (f"\nGiọng điệu: {inp['tone']}" if inp.get("tone") else "")
             + (f"\nNhân vật người dùng chọn: {', '.join(inp['characters'])}" if inp.get("characters") else "")
             + (f"\nCTA (đúng chữ, ở cảnh cuối): {inp['cta']}" if inp.get("cta") else ""),
             "## Kho FF (ưu tiên dùng)\nNhân vật: " + (", ".join(sorted(set(lib["characters"]))) or "(trống)")
             + "\nNơi: " + (", ".join(sorted(set(lib["places"]))) or "(trống)")]
    tb = trend_block(conn, inp.get("trend", "off"))
    if tb:
        parts.append(tb)
    if turn >= 2 and state.get("answers"):
        parts.append("## Trả lời của người dùng (câu ghi [mặc định] = người dùng để trống, dùng đáp án mặc định)\n" + "\n".join(
            f"- {a['q']} → {a['a']}" + (" [mặc định]" if a.get("defaulted") else "") for a in state["answers"]))
    if turn >= 3 and state.get("chosen") is not None:
        d = state["directions"][state["chosen"]]
        parts.append(f"## Hướng người dùng chọn\n{d['title']}: {d['logline']} — hook 3 s: {d['hook_3s']} — chốt: {d['payoff']}"
                     + (f"\nGhi chú của người dùng: {state['choice_note']}" if state.get("choice_note") else ""))
    if turn >= 4 and state.get("beats"):
        parts.append("## Dàn ý đã duyệt\n" + json.dumps(state["beats"], ensure_ascii=False, indent=0))
    parts.append(_section(f"LƯỢT {turn}"))
    return "\n\n".join(parts)


# ---- the turns ----------------------------------------------------------------------------------------------------------------------
def _ask(conn, pid: int, state: Dict, turn: int, client, validate):
    from . import llm_runner
    left = round(RUN_CAP_USD - float(state.get("spent") or 0), 4)
    if left < TURN_USD / 2:
        raise IdeaError(f"đã dùng hết trần {RUN_CAP_USD} USD cho ý tưởng này — bấm 'Ý tưởng mới' để làm lại từ đầu")
    with llm_runner.tagged(STAGE, pid), llm_runner.spend_cap(left, "Biên kịch") as cap:
        obj, _, _ = llm_runner.ask_json(client, build_prompt(conn, pid, state, turn), validate)
    state["spent"] = round(float(state.get("spent") or 0) + float(cap.get("spent") or 0), 4)
    state["turn"] = turn
    return obj


def _need(obj, key, kind):
    if not isinstance(obj, dict) or not isinstance(obj.get(key), kind):
        raise ValueError(f"cần trường `{key}`")
    return obj[key]


def questions(conn, pid: int, client) -> Dict:
    state = get_state(conn, pid)
    if not state.get("inputs"):
        raise IdeaError("chưa nhập ý tưởng")

    def ok(obj):
        qs = _need(obj, "questions", list)
        if len(qs) > MAX_QUESTIONS:
            raise ValueError(f"tối đa {MAX_QUESTIONS} câu hỏi")
        for q in qs:
            if not (isinstance(q, dict) and str(q.get("q") or "").strip() and str(q.get("default") or "").strip()):
                raise ValueError("mỗi câu hỏi cần `q` và `default`")
        return obj
    obj = _ask(conn, pid, state, 1, client, ok)
    state.update(have=obj.get("have") or [], missing=obj.get("missing") or [], questions=obj["questions"])
    for k in ("answers", "directions", "chosen", "beats", "outline_checks", "script", "added", "script_checks"):
        state.pop(k, None)
    return save_state(conn, pid, state)


def answer(conn, pid: int, replies: List[str]) -> Dict:
    """The person's answers; an empty one takes the default and says so."""
    state = get_state(conn, pid)
    qs = state.get("questions") or []
    state["answers"] = [{"q": q["q"], "a": (replies[i] if i < len(replies) else "").strip() or q["default"],
                         "defaulted": not (replies[i] if i < len(replies) else "").strip()} for i, q in enumerate(qs)]
    return save_state(conn, pid, state)


def directions(conn, pid: int, client) -> Dict:
    state = get_state(conn, pid)
    if "answers" not in state:
        state = answer(conn, pid, [])

    def ok(obj):
        ds = _need(obj, "directions", list)
        if len(ds) != 3:
            raise ValueError("cần đúng 3 hướng")
        for d in ds:
            if not all(str(d.get(k) or "").strip() for k in ("title", "logline", "hook_3s", "payoff")):
                raise ValueError("mỗi hướng cần title, logline, hook_3s, payoff")
        if state["inputs"].get("trend") == "off" and any(str(d.get("trend_card") or "").strip() for d in ds):
            raise ValueError("chế độ trend Tắt: trend_card phải để trống")
        return obj
    obj = _ask(conn, pid, state, 2, client, ok)
    state["directions"] = obj["directions"]
    state.pop("chosen", None)
    return save_state(conn, pid, state)


def check_outline(beats: List[Dict], duration_s: float) -> List[Dict]:
    """[{level: block / warn, text}] — the measurable parts of a beat outline."""
    out = []
    if not beats:
        return [{"level": "block", "text": "dàn ý trống"}]
    names = [b.get("name") for b in beats]
    if names[0] != "hook" or float(beats[0].get("start") or 0) != 0:
        out.append({"level": "block", "text": "nhịp đầu phải là hook, bắt đầu ở 0 s"})
    elif float(beats[0].get("end") or 0) > HOOK_MAX_S:
        out.append({"level": "warn", "text": f"hook dài {beats[0].get('end')} s (nên ≤ {HOOK_MAX_S:g} s)"})
    if "ending" not in names:
        out.append({"level": "block", "text": "thiếu nhịp kết (ending)"})
    if "turn" not in names:
        out.append({"level": "warn", "text": "không có điểm xoay (turn) — video dễ phẳng"})
    for a, b in zip(beats, beats[1:]):
        if abs(float(b.get("start") or 0) - float(a.get("end") or 0)) > 0.05:
            out.append({"level": "warn", "text": f"nhịp {b.get('name')} không nối liền nhịp {a.get('name')}"})
    total = float(beats[-1].get("end") or 0)
    if abs(total - duration_s) > 0.1 * duration_s:
        out.append({"level": "block", "text": f"tổng {total:g} s, mục tiêu {duration_s:g} s ± 10 %"})
    from .dialogue import syllables
    for b in beats:
        n = sum(syllables(str(d.get("line") or "")) for d in b.get("dialogue") or [] if isinstance(d, dict))
        span = float(b.get("end") or 0) - float(b.get("start") or 0)
        need = n / SPEECH_RATE
        if n and need > span + 0.05:
            out.append({"level": "warn", "text": f"nhịp {b.get('name')}: thoại {n} âm tiết cần ≈ {need:.1f} s, khung {span:g} s"})
    return out


def outline(conn, pid: int, client, choice: int, note: str = "") -> Dict:
    state = get_state(conn, pid)
    if not state.get("directions") or not 0 <= choice < len(state["directions"]):
        raise IdeaError("chọn một trong 3 hướng trước")
    state["chosen"], state["choice_note"] = choice, (note or "").strip()

    def ok(obj):
        beats = _need(obj, "beats", list)
        for b in beats:
            if not isinstance(b, dict) or b.get("name") not in BEATS or not isinstance(b.get("start"), (int, float)) \
                    or not isinstance(b.get("end"), (int, float)):
                raise ValueError(f"mỗi nhịp cần name ∈ {BEATS}, start, end (số)")
        return obj
    obj = _ask(conn, pid, state, 3, client, ok)
    state["beats"], state["question"] = obj["beats"], obj.get("question") or ""
    state["outline_checks"] = check_outline(obj["beats"], state["inputs"]["duration_s"])
    return save_state(conn, pid, state)


def _fold(text: str) -> str:
    from .assets import fold
    return fold(text)


def parse(script: str):
    from . import script_parser, script_reader
    res = script_reader.from_text(script)
    return script_parser.split_scenes(res.paragraphs), res


_ON_SCREEN_SPEAKERS = {"cta", "cta text", "cta_text", "chu", "text", "chu tren man", "chu man hinh", "title", "super", "caption"}


def check_script(conn, pid: int, script: str, inputs: Dict) -> Dict:
    """{"ok", "scenes", "problems": [block texts], "flags": [notes for the person]} — 0 USD."""
    problems, flags = [], []
    try:
        scenes, _ = parse(script)
    except Exception as e:  # noqa: BLE001 - shown as it is
        return {"ok": False, "scenes": 0, "problems": [f"không đọc được: {e}"], "flags": []}
    if not scenes or (len(scenes) == 1 and scenes[0].heading == "Mở đầu"):
        problems.append("không tách được cảnh — mỗi cảnh cần tiêu đề 'CẢNH n - <thời gian>, <nơi>'")
    lib = library(conn, pid)
    known = {_fold(n) for n in lib["characters"]}
    for name in sorted({c for s in scenes for c in s.characters}):
        if _fold(name) in _ON_SCREEN_SPEAKERS:         # B4 01/10: "CTA_TEXT: …" is a line of text on the screen, not a person
            continue
        if _fold(name) not in known:
            flags.append(f"nhân vật mới — cần ảnh: {name}")
    places = [_fold(p) for p in lib["places"]]
    for s in scenes:
        m = _HEADING_PLACE.match(s.heading)
        where = (m.group(1) if m else "").split(",", 1)[-1].strip()
        if where and not any(p and (p in _fold(where) or _fold(where) in p) for p in places):
            flags.append(f"nơi ngoài Kho — AI vẽ, ~70 % giống: {where}")
    if inputs.get("cta") and scenes and _fold(inputs["cta"]) not in _fold(scenes[-1].heading + " " + scenes[-1].text):
        problems.append(f"CTA \"{inputs['cta']}\" chưa có ở cảnh cuối")
    if _AGE.search(script):
        problems.append("có số tuổi dưới 18 — bỏ đi (luật cứng)")
    from .dialogue import lines, syllables
    talk = sum(syllables(said) for s in scenes for who, said in lines(s.text)
               if _fold(who) not in _ON_SCREEN_SPEAKERS) / SPEECH_RATE
    if talk > float(inputs.get("duration_s") or 0):
        flags.append(f"tổng thoại ≈ {talk:.0f} s > thời lượng {inputs.get('duration_s')} s — video sẽ dài hơn mục tiêu")
    return {"ok": not problems, "scenes": len(scenes), "problems": problems, "flags": sorted(set(flags))}


def write(conn, pid: int, client) -> Dict:
    state = get_state(conn, pid)
    if not state.get("beats"):
        raise IdeaError("duyệt dàn ý trước")

    def ok(obj):
        text = _need(obj, "script", str)
        scenes, _ = parse(text)
        if not scenes or (len(scenes) == 1 and scenes[0].heading == "Mở đầu"):
            raise ValueError("kịch bản không tách được cảnh: mỗi cảnh phải có tiêu đề bắt đầu bằng 'CẢNH <số> - '")
        return obj
    obj = _ask(conn, pid, state, 4, client, ok)
    state["script"], state["added"], state["notes"] = obj["script"].strip(), obj.get("added") or [], obj.get("notes") or ""
    state["script_checks"] = check_script(conn, pid, state["script"], state["inputs"])
    return save_state(conn, pid, state)


def edit(conn, pid: int, script: str) -> Dict:
    """The person's own edit of the script: kept, checked again (0 USD)."""
    state = get_state(conn, pid)
    state["script"] = (script or "").strip()
    state["edited"] = True
    state["script_checks"] = check_script(conn, pid, state["script"], state["inputs"])
    return save_state(conn, pid, state)


def use_script(p, pid: int) -> int:
    """Put the approved script into Step 1 exactly like a pasted script. Refused while the checks block. Returns the scene count."""
    from . import script_parser
    state = get_state(p.conn, pid)
    checks = check_script(p.conn, pid, state.get("script") or "", state.get("inputs") or {})
    if not checks["ok"]:
        raise IdeaError("kịch bản chưa đạt: " + "; ".join(checks["problems"]))
    scenes, res = parse(state["script"])
    script_parser.import_scenes(p, pid, scenes, full_text="\n\n".join(res.paragraphs))
    state["used"] = True
    save_state(p.conn, pid, state)
    return len(scenes)


# ---- what the Biên kịch added (for the 2-column review) -----------------------------------------------------------------------------
def _words(text: str) -> str:
    return " ".join(re.sub(r"[^0-9a-z]+", " ", _fold(text)).split())


def _in(idea_words: str, text: str) -> bool:
    """Whole words: "Ủa" is not inside "Quân" (01/10 demo: a plain substring test hid a new line)."""
    w = _words(text)
    return bool(w) and f" {w} " in f" {idea_words} "


def marked_lines(idea: str, script: str) -> List[Dict]:
    """[{text, kind: heading / line / text, new: bool, new_words: [...]}] — a line is 'new' when the idea did not contain it; in a heading
    the place, in a dialogue line the speaker, are listed when the idea never named them."""
    from .script_parser import _DIALOGUE, is_heading
    idea_w = _words(idea)
    out = []
    for raw in (script or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            out.append({"text": "", "kind": "blank", "new": False, "new_words": []})
            continue
        if is_heading(line):
            m = _HEADING_PLACE.match(line)
            where = (m.group(1) if m else line).split(",", 1)[-1].strip()
            out.append({"text": line, "kind": "heading", "new": bool(where) and not _in(idea_w, where),
                        "new_words": [where] if where and not _in(idea_w, where) else []})
            continue
        m = _DIALOGUE.match(line)
        if m:
            speaker, said = m.group(1).strip(), line.split(":", 1)[1].strip()
            out.append({"text": line, "kind": "line", "new": not _in(idea_w, said),
                        "new_words": [speaker] if not _in(idea_w, speaker) else []})
            continue
        out.append({"text": line, "kind": "text", "new": not _in(idea_w, line), "new_words": []})
    return out
