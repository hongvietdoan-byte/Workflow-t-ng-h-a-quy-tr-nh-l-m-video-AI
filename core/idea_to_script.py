"""💡 Ý tưởng thô → kịch bản (S11.1, docs/KE_HOACH_TINH_NANG_DIRECTOR_2026-10-01.md mục 2; cờ `idea_to_script`, BẬT mặc định từ 06/10 — cổng S11.2 đạt TB 4,20 phiếu 05d).

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
from . import access
import json
import re
from typing import Dict, List, Optional

FEATURE = "idea_to_script"
STAGE = "screenwriter"
RUN_CAP_USD = 0.40              # S14.31: was 0.30; 4 turns × TURN_USD 0.045 + the biggest turn estimate must fit (real ≈ 0.15 / idea)
TURN_USD = 0.045                # estimate shown before a turn; S14.31: real ≈ 0.037 / turn (05/10 record, was 0.03 = 23 % low)
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


def missing_anchors(anchors) -> List[str]:
    from . import idea_buildable
    return idea_buildable.missing_anchors(anchors)


def buildable_blocks(conn, pid: int, inputs: Dict, extra: str = "") -> str:
    """S14.31: the rules of "chỉ viết thứ dựng được" + the kit (not the whole Kho) + the person's key points — right after CHUNG.
    S14.43 mục 1: `extra` (answers, wishes, chosen direction) is searched too for Kho entries named by another name."""
    from . import idea_buildable
    return idea_buildable.blocks(conn, pid, inputs, extra)


def _said_text(state: Dict, wish: str = "") -> str:
    """What the person said after the idea (answers, wishes, the chosen direction + note) — where a Kho name may also appear."""
    parts = [f"{a.get('q', '')} {a.get('a', '')}" for a in state.get("answers") or []]
    parts += [str(v) for v in (state.get("wishes") or {}).values()] + ([wish] if wish else [])
    if state.get("chosen") is not None and state.get("directions"):
        d = state["directions"][state["chosen"]]
        parts.append(" ".join(str(d.get(k) or "") for k in ("title", "logline", "hook_3s", "payoff")))
    parts.append(str(state.get("choice_note") or ""))
    return "\n".join(p for p in parts if p.strip())


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
          characters: Optional[List[str]] = None, cta: str = "", trend: str = "off", p=None,
          anchors: Optional[Dict] = None) -> Dict:
    """A new idea (forgets the previous one's turns). `anchors` = the key points the person fixes (S14.31 ý 6): characters, costume, place,
    plot, ending, gameplay_ui — while one is missing the Biên kịch is not called (`_ask`), 0 USD."""
    from . import idea_buildable
    if p is not None:                                   # rà S14.21: a viewer must not spend on (or change) the Biên kịch
        access.need_edit(p, pid, "chạy Biên kịch")
    idea = (idea or "").strip()
    if len(idea) < 10:
        raise IdeaError("Ý tưởng quá ngắn — viết ít nhất một câu: ai, ở đâu, chuyện gì")
    if trend not in TREND_MODES:
        raise IdeaError("chế độ trend không hợp lệ")
    if anchors and not characters:                       # one list of people (rà S14.31): the key points' characters are the chosen ones
        characters = list(idea_buildable.clean_anchors(anchors)["characters"])
    state = {"inputs": {"idea": idea, "duration_s": int(duration_s), "aspect": aspect, "platform": platform, "tone": tone.strip(),
                        "characters": [str(c).upper() for c in characters or []], "cta": cta.strip(), "trend": trend,
                        "anchors": idea_buildable.clean_anchors(anchors)},
             "spent": 0.0, "turn": 0}
    if classify(idea)["kind"] == "script":              # S14.43 mục 5: a thin script / outline to write out — only then (idea prompts unchanged)
        state["inputs"]["from_script"] = True
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


def wish_block(state: Dict, turn: int, wish: str = "") -> str:
    """S14.21 (Đợt 3): the person's free "nói thêm" of this turn and of the earlier ones (state["wishes"] = {"2": "…"}), same shape as
    core/sfx_plan.py `wish`. Nothing said → "" → the prompt stays byte-identical (C3: the S11.2 replay keys on sha256(prompt))."""
    wishes = {str(k): str(v).strip() for k, v in (state.get("wishes") or {}).items() if str(v).strip()}
    if wish.strip():
        wishes[str(turn)] = wish.strip()
    said = sorted((int(k), v) for k, v in wishes.items() if k.isdigit() and int(k) <= turn)
    if not said:
        return ""
    return ("## Yêu cầu thêm của người dùng (ưu tiên làm theo)\n" + _section("YÊU CẦU THÊM") + "\n"
            + "\n".join(f"- (lượt {n}) {v}" for n, v in said))


PATTERN_FILE = ("knowledge", "craft", "khuon_hai.md")
PATTERN_TURNS = (2, 3)          # the turns that pick the shape of the story; turn 1 (questions) and 4 (follows the outline) do not need it


def pattern_block() -> str:
    """S14.43 mục 6: the reusable comedy patterns (knowledge/craft/khuon_hai.md), as SUGGESTIONS. A missing file is said (CHUAN luật 1)."""
    from .prompts import _read
    text = (_read(*PATTERN_FILE) or "").strip()
    if not text:
        raise IdeaError("không đọc được knowledge/craft/khuon_hai.md (kho khuôn hài của Biên kịch) — khôi phục file")
    return "## Kho khuôn hài (GỢI Ý — trộn được, không bắt buộc)\n" + text


def build_prompt(conn, pid: int, state: Dict, turn: int, wish: str = "") -> str:
    from .prompts import _read
    inp = state["inputs"]
    parts = [f"# Biên kịch — Lượt {turn}", _section("CHUNG"), buildable_blocks(conn, pid, inp, _said_text(state, wish)), "## Vai của bạn", _read("knowledge", "roles", "screenwriter.md"),
             "## Viết thoại", _read("knowledge", "dialogue_craft.md"), "## Thể loại", _read("knowledge", "genre_guides.md"),
             "## Đầu vào của người dùng",
             f"Ý tưởng: {inp['idea']}\nThời lượng mục tiêu: {inp['duration_s']} s · khung {inp['aspect']} · nền tảng {inp['platform']}"
             + (f"\nGiọng điệu: {inp['tone']}" if inp.get("tone") else "")
             + (f"\nNhân vật người dùng chọn: {', '.join(inp['characters'])}" if inp.get("characters") else "")
             + (f"\nCTA (đúng chữ, ở cảnh cuối): {inp['cta']}" if inp.get("cta") else "")
             + ("\nĐầu vào là KỊCH BẢN / DÀN Ý SƠ SÀI người dùng đã viết (có tiêu đề cảnh), nhờ viết bổ sung cho chi tiết: giữ thứ tự cảnh, nơi, "
                "nhân vật, diễn biến và thoại có sẵn (được sửa chữ cho tự nhiên); thêm mô tả hành động + thoại cho đủ thời lượng, không đổi chuyện."
                if inp.get("from_script") else ""),
             ]
    from . import chat_refs
    refs = chat_refs.block(conn, pid)                   # 09/10: tư liệu thả vào chat (vai, tên, ghi chú) — chữ; không có → prompt như cũ
    if refs:
        parts.append(refs)
    tb = trend_block(conn, inp.get("trend", "off"))
    if tb:
        parts.append(tb)
    from . import knowledge
    kelly = knowledge.kelly_blocks("screenwriter")      # S14.34 (flag kelly_knowledge): suggestions only; off → [] → prompt byte-identical
    if kelly:
        parts.insert(3, "## Gợi ý từ kênh Kelly (trộn được, không bắt buộc)\n" + kelly[0])
    if turn in PATTERN_TURNS:                           # S14.43 mục 6: comedy patterns where the shape is chosen (directions + outline)
        parts.append(pattern_block())
    if turn >= 2 and state.get("answers"):
        parts.append("## Trả lời của người dùng (câu ghi [mặc định] = người dùng để trống, dùng đáp án mặc định)\n" + "\n".join(
            f"- {a['q']} → {a['a']}" + (" [mặc định]" if a.get("defaulted") else "") for a in state["answers"]))
    if turn >= 3 and state.get("chosen") is not None:
        d = state["directions"][state["chosen"]]
        parts.append(f"## Hướng người dùng chọn\n{d['title']}: {d['logline']} — hook 3 s: {d['hook_3s']} — chốt: {d['payoff']}"
                     + (f"\nGhi chú của người dùng: {state['choice_note']}" if state.get("choice_note") else ""))
    if turn >= 4 and state.get("beats"):
        parts.append("## Dàn ý đã duyệt\n" + json.dumps(state["beats"], ensure_ascii=False, indent=0))
    wb = wish_block(state, turn, wish)
    if wb:                                          # CHỈ khi có chữ (C3) — y như sfx_plan.py `if wish.strip()`
        parts.append(wb)
    parts.append(_section(f"LƯỢT {turn}"))
    return "\n\n".join(parts)


# ---- the turns ----------------------------------------------------------------------------------------------------------------------
def _keep_wish(state: Dict, turn: int, wish: str) -> None:
    """This turn's wish is stored; the wishes of LATER turns belonged to the path being redone and are dropped."""
    kept = {k: v for k, v in (state.get("wishes") or {}).items() if str(k).isdigit() and int(k) < turn}
    if wish.strip():
        kept[str(turn)] = wish.strip()
    if kept:
        state["wishes"] = kept
    else:
        state.pop("wishes", None)


def _ask(conn, pid: int, state: Dict, turn: int, client, validate, wish: str = ""):
    from . import llm_runner
    from . import idea_buildable
    why = idea_buildable.gate(conn, pid, state.get("inputs") or {})
    if why:                                             # S14.31 ý 6: ask again for what is missing — nothing is sent, 0 USD
        raise IdeaError("; ".join(why))
    left = round(RUN_CAP_USD - float(state.get("spent") or 0), 4)
    if left < TURN_USD / 2:
        raise IdeaError(f"đã dùng hết trần {RUN_CAP_USD} USD cho ý tưởng này — bấm 'Ý tưởng mới' để làm lại từ đầu")
    _keep_wish(state, turn, wish)
    cap = {}
    try:
        with llm_runner.tagged(STAGE, pid), llm_runner.spend_cap(left, "Biên kịch") as cap:
            obj, _, _ = llm_runner.ask_json(client, build_prompt(conn, pid, state, turn), validate)
    except Exception:
        # S14.4 C1b: a turn that failed after paid calls (2 bad answers…) still counts toward this idea's cap, and is saved
        if float(cap.get("spent") or 0):
            fresh = get_state(conn, pid)
            fresh["spent"] = round(float(fresh.get("spent") or 0) + float(cap["spent"]), 4)
            save_state(conn, pid, fresh)
        raise
    state["spent"] = round(float(state.get("spent") or 0) + float(cap.get("spent") or 0), 4)
    state["turn"] = turn
    return obj


def _need(obj, key, kind):
    if not isinstance(obj, dict) or not isinstance(obj.get(key), kind):
        raise ValueError(f"cần trường `{key}`")
    return obj[key]


def questions(conn, pid: int, client, wish: str = "", p=None) -> Dict:
    if p is not None:                                   # rà S14.21: a viewer must not spend on (or change) the Biên kịch
        access.need_edit(p, pid, "chạy Biên kịch")
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
    obj = _ask(conn, pid, state, 1, client, ok, wish)
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


def directions_input_changed(state: Dict, replies: List[str], wish: str = "") -> bool:
    """C8: "↻ Hỏi lại 3 hướng khác" is only worth paying for when what turn 2 reads changed — a new wish, or other answers."""
    if wish.strip() and wish.strip() != str((state.get("wishes") or {}).get("2") or ""):
        return True
    qs = state.get("questions") or []
    now = [((replies[i] if i < len(replies) else "").strip() or q["default"]) for i, q in enumerate(qs)]
    return now != [a.get("a") for a in state.get("answers") or []]


def directions(conn, pid: int, client, wish: str = "", p=None) -> Dict:
    if p is not None:                                   # rà S14.21: a viewer must not spend on (or change) the Biên kịch
        access.need_edit(p, pid, "chạy Biên kịch")
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
    obj = _ask(conn, pid, state, 2, client, ok, wish)
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
    from . import clean_dialogue
    for b in beats:                                     # S14.41: lời thoại sạch already at the outline (the 05c run had "Của tao!" here)
        hits = clean_dialogue.find("\n".join(str(d.get("line") or "") for d in b.get("dialogue") or [] if isinstance(d, dict)))
        if hits:
            out.append({"level": "block", "text": f"nhịp {b.get('name')}: {clean_dialogue.describe(hits)}"})
    from .dialogue import syllables
    for b in beats:
        n = sum(syllables(str(d.get("line") or "")) for d in b.get("dialogue") or [] if isinstance(d, dict))
        span = float(b.get("end") or 0) - float(b.get("start") or 0)
        need = n / SPEECH_RATE
        if n and need > span + 0.05:
            out.append({"level": "warn", "text": f"nhịp {b.get('name')}: thoại {n} âm tiết cần ≈ {need:.1f} s, khung {span:g} s"})
    return out


def outline(conn, pid: int, client, choice: int, note: str = "", wish: str = "", p=None) -> Dict:
    if p is not None:                                   # rà S14.21: a viewer must not spend on (or change) the Biên kịch
        access.need_edit(p, pid, "chạy Biên kịch")
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
    obj = _ask(conn, pid, state, 3, client, ok, wish)
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


CLASSIFY_KINDS = ("script", "idea", "unsure")
IDEA_MAX_CHARS, IDEA_MAX_LINES, UNSURE_MIN_CHARS = 400, 6, 1500


def classify(text: str) -> Dict:
    """S14.21 (Đợt 3): is this a written SCRIPT (→ the old 0 USD split) or an IDEA (→ the Biên kịch, paid turns behind priced buttons)?
    0 USD, the same test the Biên kịch's own output must pass (parse → real scene headings). Grey zone → "unsure": the screen asks, it
    never guesses (luật 3). {"kind", "scenes", "why": [...]}."""
    from .script_parser import _DIALOGUE
    body = (text or "").strip()
    if not body:
        return {"kind": "unsure", "scenes": 0, "why": ["chưa có chữ"]}
    try:
        scenes, _ = parse(body)
    except Exception:  # noqa: BLE001 - unreadable → ask
        scenes = []
    if scenes and not (len(scenes) == 1 and scenes[0].heading == "Mở đầu"):
        heads = [s for s in scenes if s.heading != "Mở đầu"]
        return {"kind": "script", "scenes": len(scenes), "why": [f"thấy {len(heads)} tiêu đề cảnh"]}
    lines = [ln for ln in body.splitlines() if ln.strip()]
    talk = sum(1 for ln in lines if _DIALOGUE.match(ln))
    if talk >= 2 or len(body) > UNSURE_MIN_CHARS:
        why = ([f"{talk} dòng thoại"] if talk >= 2 else []) + ([f"{len(body)} ký tự"] if len(body) > UNSURE_MIN_CHARS else [])
        return {"kind": "unsure", "scenes": 0, "why": ["không có tiêu đề cảnh"] + why}
    if len(body) < IDEA_MAX_CHARS and len(lines) < IDEA_MAX_LINES and talk == 0:
        return {"kind": "idea", "scenes": 0, "why": ["không có tiêu đề cảnh", f"{len(lines)} dòng ngắn, không có thoại"]}
    return {"kind": "unsure", "scenes": 0, "why": ["không có tiêu đề cảnh", f"{len(body)} ký tự · {len(lines)} dòng"]}


# ---- S14.43 mục 5: a script with headings that is still thin → offer the Biên kịch (0 USD to detect; paid only behind the priced turns) ----
# Căn cứ (đo 06/10 bằng split_scenes + dialogue.lines, chữ mô tả = dòng không phải thoại, không tính tiêu đề):
#   kịch bản người viết trong samples/ (script_demo_1/2, anh_chon_ai, kenta_…): TB 21–82 chữ mô tả / cảnh, cảnh mỏng nhất 15 chữ;
#   kịch bản Biên kịch được chấm TB 4,20 (phiếu 05d): TB 33–131 chữ / cảnh, cảnh mỏng nhất 29 chữ; các phiếu 05/05b/05c: cảnh mỏng nhất 17.
# → SPARSE_AVG_WORDS = 12 (≈ một nửa trung bình của kịch bản người viết mỏng nhất, 21) và một cảnh "trơ" = < 10 chữ mô tả VÀ không thoại
#   (dưới 2/3 cảnh mỏng nhất từng thấy, 15): sơ sài khi TB < 12 hoặc ≥ một nửa số cảnh trơ. Một dàn ý "CẢNH n + 1 câu" có TB 2–5 chữ.
#   Rà 06/10: độ dày một cảnh = chữ mô tả + chữ THOẠI (lời nói cũng là nội dung quay được; kịch bản 3 cảnh × 2–3 câu thoại ≈ 15–20 chữ / cảnh
#   không phải dàn ý). Các mốc trên đo bằng chữ mô tả nên cộng thoại chỉ làm kịch bản thật dày thêm — không bắt nhầm thêm.
SPARSE_AVG_WORDS = 12
BARE_SCENE_WORDS = 10


def sparse(text: str) -> Dict:
    """{"sparse", "why": [Vietnamese reasons with numbers], "scenes", "avg_words", "bare", "talk"} — only a SCRIPT (scene headings) can be
    sparse; an idea goes to the Biên kịch anyway (classify)."""
    from .dialogue import lines
    out = {"sparse": False, "why": [], "scenes": 0, "avg_words": 0.0, "bare": 0, "talk": 0}
    if classify(text)["kind"] != "script":
        return out
    scenes, _ = parse(text)
    scenes = [s for s in scenes if s.heading != "Mở đầu" or s.text.strip()]
    if not scenes:
        return out
    words, bare, talk = [], 0, 0
    for s in scenes:
        rows = [r for r in s.text.splitlines() if r.strip()]
        said = [r for r in rows if lines(r)]
        n = sum(len(r.split()) for r in rows if r not in said)
        spoken = sum(len(x.split()) for r in said for _, x in lines(r))
        words.append(n + spoken)                        # rà 7: what is said fills a scene too — a dialogue script is not an outline
        talk += len(said)
        bare += 1 if n < BARE_SCENE_WORDS and not said else 0
    avg = sum(words) / len(words)
    out.update(scenes=len(scenes), avg_words=round(avg, 1), bare=bare, talk=talk)
    why = []
    if avg < SPARSE_AVG_WORDS:
        why.append(f"trung bình {avg:.0f} chữ mô tả + thoại / cảnh (kịch bản đủ chi tiết thường ≥ 21; ngưỡng {SPARSE_AVG_WORDS})")
    if bare * 2 >= len(scenes):
        why.append(f"{bare}/{len(scenes)} cảnh chỉ có tiêu đề + dưới {BARE_SCENE_WORDS} chữ, không thoại")
    if why:
        why.append(f"{talk} dòng thoại cả kịch bản")
    out.update(sparse=bool(why), why=why)
    return out


def expand_usd() -> float:
    """What writing it out costs at most as estimated before: the 4 paid turns (each shown again on its own button), within RUN_CAP_USD."""
    return round(4 * TURN_USD, 4)


_EXPAND_VERB = re.compile(r"^(?:(?:hay|giup|nho|ban|claude|vui long|lam on|minh muon|toi muon|em muon|can)\s+(?:minh|toi|em|ban|claude)?\s*)*"
                          r"(?:viet|phat trien|mo rong|trien khai|chi tiet hoa|lam chi tiet|bo sung|lam ro)\b")
_EXPAND_WHAT = re.compile(r"chi tiet|day du|cu the|bo sung|dan y|thanh kich ban|outline|dai hon")
# rà 06/10: must point at an EXISTING outline — "kịch bản" + (dàn ý / này / trên), or "dàn ý" + (này / trên). "Viết kịch bản chi tiết: <ý
# mới>" or "Mình muốn viết một kịch bản đầy đủ về …" is a new idea (classify), not this request.
_EXPAND_THIS = re.compile(r"(\bkich ban\b.*\b(dan y|nay|tren)\b)|(\b(dan y|nay|tren)\b.*\bkich ban\b)|(\bdan y\b.*\b(nay|tren)\b)")


def expand_request(text: str) -> Optional[Dict]:
    """S14.43 mục 5: the person typed "viết kịch bản chi tiết từ dàn ý này" (0 USD, by rule — no model). Only the FIRST line is read, and it
    must start with the request (a scene heading, a dialogue line or an idea that merely contains 'viết' is not one).
    → {"rest": the text after that line (the outline pasted with it, may be "")} or None."""
    body = (text or "").strip()
    if not body:
        return None
    first, _, rest = body.partition("\n")
    from .dialogue import lines
    from .script_parser import is_heading
    if is_heading(first) or lines(first):
        return None
    ask, colon, after = first.partition(":")                        # rà: "…dàn ý này: <dàn ý>" — what follows ':' is the outline
    if len(ask) > 120:
        return None
    t = " ".join(re.sub(r"[^0-9a-z]+", " ", _fold(ask)).split())
    if not (_EXPAND_VERB.match(t) and _EXPAND_WHAT.search(t) and _EXPAND_THIS.search(t)):
        return None
    return {"rest": "\n".join(x for x in (after.strip(), rest.strip()) if x)}


def _on_screen(name: str) -> bool:
    """B4 01/10 + S14.4 C1b: "CTA_TEXT: …" is a line of text on the screen, not a person — one list in core.dialogue."""
    from .dialogue import is_non_speaker
    return is_non_speaker(name)


def _clean_scenes(scenes, blocked: List[Dict]) -> List[str]:
    """S14.41: a scene with mày/tao or swearing is blocked (scene + words shown), appended to `blocked` like check_scenes."""
    from . import clean_dialogue
    out = []
    for s in scenes:
        hits = clean_dialogue.find(s.heading + "\n" + s.text)
        if hits:
            why = clean_dialogue.describe(hits)
            row = next((b for b in blocked if b["scene"] == s.idx), None)
            if row:
                row["why"].append(why)
            else:
                blocked.append({"scene": s.idx, "why": [why]})
            out.append(f"cảnh {s.idx}: {why}")
    return out


def check_script(conn, pid: int, script: str, inputs: Dict) -> Dict:
    """{"ok", "scenes", "problems": [block texts], "flags": [notes for the person], "blocked_scenes": [{scene, why}]} — 0 USD."""
    from . import idea_buildable
    problems, flags, blocked = [], [], []
    try:
        scenes, _ = parse(script)
    except Exception as e:  # noqa: BLE001 - shown as it is
        return {"ok": False, "scenes": 0, "problems": [f"không đọc được: {e}"], "flags": [], "blocked_scenes": []}
    if not scenes or (len(scenes) == 1 and scenes[0].heading == "Mở đầu"):
        problems.append("không tách được cảnh — mỗi cảnh cần tiêu đề 'CẢNH n - <thời gian>, <nơi>'")
    lib = library(conn, pid)
    known = {_fold(n) for n in lib["characters"]}
    for name in sorted({c for s in scenes for c in s.characters}):
        if _on_screen(name):
            continue
        if _fold(name) not in known:
            flags.append(f"nhân vật mới — cần ảnh: {name}")
    places = [_fold(p) for p in lib["places"]]
    for s in scenes:
        m = _HEADING_PLACE.match(s.heading)
        where = (m.group(1) if m else "").split(",", 1)[-1].strip()
        if where and not any(p and (p in _fold(where) or _fold(where) in p) for p in places):
            flags.append(f"nơi ngoài Kho — AI vẽ, ~70 % giống: {where}")
    if scenes and not (len(scenes) == 1 and scenes[0].heading == "Mở đầu"):
        anchors = inputs.get("anchors")
        k = idea_buildable.kit(conn, pid)
        need = idea_buildable.place_state(conn, pid, k, anchors)["state"] == "needs_scene"      # S14.35: a set to make, not a block
        pr, fl, blocked = idea_buildable.check_scenes(scenes, k, anchors,
                                                      idea_buildable.clean_anchors(anchors)["place"] if need else "")
        problems += pr
        flags += fl
        problems += idea_buildable.check_anchors(scenes, anchors)
        problems += _clean_scenes(scenes, blocked)                        # S14.41: lời thoại sạch, blocked like check_scenes
        if not any(idea_buildable.clean_anchors(anchors).values()):       # rà: said, not a silent pass
            flags.append("không có điểm then chốt nào để đối chiếu (ý tưởng tạo trước S14.31 hoặc kịch bản dán) — chưa kiểm được nhân vật / nơi / "
                         "diễn biến / cú chốt")
    if inputs.get("cta") and scenes and _fold(inputs["cta"]) not in _fold(scenes[-1].heading + " " + scenes[-1].text):
        problems.append(f"CTA \"{inputs['cta']}\" chưa có ở cảnh cuối")
    if _AGE.search(script):
        problems.append("có số tuổi dưới 18 — bỏ đi (luật cứng)")
    from .dialogue import lines, syllables
    talk = sum(syllables(said) for s in scenes for who, said in lines(s.text)
               if not _on_screen(who)) / SPEECH_RATE
    if talk > float(inputs.get("duration_s") or 0):
        flags.append(f"tổng thoại ≈ {talk:.0f} s > thời lượng {inputs.get('duration_s')} s — video sẽ dài hơn mục tiêu")
    return {"ok": not problems, "scenes": len(scenes), "problems": problems, "flags": sorted(set(flags)), "blocked_scenes": blocked}


def write(conn, pid: int, client, wish: str = "", p=None) -> Dict:
    if p is not None:                                   # rà S14.21: a viewer must not spend on (or change) the Biên kịch
        access.need_edit(p, pid, "chạy Biên kịch")
    state = get_state(conn, pid)
    if not state.get("beats"):
        raise IdeaError("duyệt dàn ý trước")

    def ok(obj):
        text = _need(obj, "script", str)
        scenes, _ = parse(text)
        if not scenes or (len(scenes) == 1 and scenes[0].heading == "Mở đầu"):
            raise ValueError("kịch bản không tách được cảnh: mỗi cảnh phải có tiêu đề bắt đầu bằng 'CẢNH <số> - '")
        return obj
    obj = _ask(conn, pid, state, 4, client, ok, wish)
    state["script"], state["added"], state["notes"] = obj["script"].strip(), obj.get("added") or [], obj.get("notes") or ""
    from . import scene_merge                       # S14.35 ý 3: merge by code after the writing turn (prompt 23 untouched)
    merged, rep = scene_merge.merge_script(state["script"])
    state["merge"] = rep
    if merged != state["script"]:                   # joined scenes and/or continuity notes at the cuts that stay
        state["script_unmerged"], state["script"] = state["script"], merged
    else:
        state.pop("script_unmerged", None)
    state["script_checks"] = check_script(conn, pid, state["script"], state["inputs"])
    return save_state(conn, pid, state)


def edit(conn, pid: int, script: str, p=None) -> Dict:
    """The person's own edit of the script: kept, checked again (0 USD)."""
    if p is not None:                                   # rà S14.21: a viewer must not spend on (or change) the Biên kịch
        access.need_edit(p, pid, "chạy Biên kịch")
    state = get_state(conn, pid)
    state["script"] = (script or "").strip()
    state["edited"] = True
    state["script_checks"] = check_script(conn, pid, state["script"], state["inputs"])
    return save_state(conn, pid, state)


def use_script(p, pid: int) -> int:
    """Put the approved script into Step 1 exactly like a pasted script. Refused while the checks block. Returns the scene count."""
    access.need_edit(p, pid, "dùng kịch bản")
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
