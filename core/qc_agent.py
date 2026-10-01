"""The QC agent (flag qc_agent; docs/AGENT_QC_THIET_KE_2026-09-27.md).

Evidence (#8, 2026-09-27): one-shot Claude QC (per picture or per contact sheet) could not see what a person sees at a glance; an agent that
INVESTIGATES — looks at each frame in full, crops what is doubtful, lays the same detail of many frames side by side, compares with the
standard pictures, uses the code measures only as hints — found 11 real faults the person confirmed (a cap turned forward in every
back view, a character's left-arm armour mirrored, wrong gaze, a flashback looking like the present), then checked the redraws.

This module gives Claude those moves as tools in a multi-turn tool-use loop (AnthropicClient.converse), per script scene:
  view_frame(k, region?, zoom?) · strip(items[{k, region}]) · reference(what, region?) · measure(k) · record(...) · finish(summary)
It reads the playbook (knowledge/qc_playbook.md — faults already confirmed by people, with how to look for them), the Character Lock and
view notes, the shot table, and an INSPECTION PLAN built by code from the profiles (every one-sided detail → a strip across the frames of
that character, front and back views apart). Every frame must be recorded before `finish`. Verdicts are applied like qc_scene (not trusted
yet → notes for the person, every frame waits at the gate)."""
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from . import features

FEATURE = "qc_agent"
MAX_STEPS = 12            # tool turns per scene (#8 2026-09-28: 19 turns for a 4-frame scene, ~1 frame a minute; the agent in the
                          # working session did 33 frames in ~8 minutes, ~4 a minute). Target: a scene in ≤ 6 turns.
TEXT_LIMITS = {"description": 160, "evidence": 90, "fix_en": 260}   # a verdict is read by a person at the gate: short and exact
SCENE_CAP_BASE_USD = 0.10  # HARD lock per scene (llm_runner.spend_cap) = base + per frame to record, at most SCENE_CAP_MAX_USD:
SCENE_CAP_PER_FRAME_USD = 0.04   # #8 2026-09-28 one scene + half cost ~2 USD with no lock. At the cap the agent stops; the frames it
SCENE_CAP_MAX_USD = 0.50         # has not recorded wait for a person as "doubt" (a trade-off: fewer looks, never more money)
SCENE_CAP_USD = SCENE_CAP_BASE_USD + 4 * SCENE_CAP_PER_FRAME_USD     # a 4-frame scene (shown in docs / the estimate)
ANSWER_TOKENS = 3500      # one turn's answer (real turns: 200-3,000 tokens); the lock keeps room for the WHOLE answer, so a big
                          # ceiling stops the agent early (28/09: 6000 → ~0.06 USD kept back each turn). A cut answer → "fewer tools"
LOOKS_PER_TURN = 4        # pictures a turn may open (28/09: 46 pictures in 8 turns, nothing recorded)
RECORD_ONLY_AT = 0.5      # share of the scene's cap after which only record / finish are answered
CLOSING_TURNS = 3         # the last turns of a scene offer ONLY record / record_batch / finish (S7.1 01/10: cảnh 2 #8 twice spent all its
                          # turns looking — the "record now" text answers were ignored — and recorded nothing: 0,43 USD for 6 doubts)
RECORD_TOOLS = ("record", "record_batch", "finish")
RESERVE_TURNS = 2.5       # close when the scene's money left would not pay this many turns at the last turn's price (S7.1 01/10 lần 5:
                          # every turn resends the pictures, the price grew to ~0,10 USD, the cap ran out before the one record turn)
RECORD_EVERY = 4          # after this many turns without a new record, the next turn offers only the record tools (record as you go)
CASES_SHOWN = 4           # confirmed cases from the notebook (core/experience) shown before looking
CASE_EDGE = 512           # their pictures, small: a reminder, not a frame to judge


def max_steps(n_frames: int) -> int:
    """Turns for a scene: 2 per frame + 4, at least MAX_STEPS (a 6-frame, 3-person scene needs more than a 4-frame one)."""
    return max(MAX_STEPS, 2 * int(n_frames) + 4)
MAX_CUT_TURNS = 2


def _short(args: Dict) -> Dict:
    """Verdict texts cut to TEXT_LIMITS (a long answer is paid and read by nobody; 28/09 answers were cut at the token ceiling)."""
    def cut(s, n):
        s = " ".join(str(s or "").split())
        return s if len(s) <= n else s[: n - 1].rstrip() + "…"
    out = dict(args)
    out["issues"] = [dict(i, description=cut(i.get("description"), TEXT_LIMITS["description"]),
                          evidence=cut(i.get("evidence"), TEXT_LIMITS["evidence"])) for i in (args.get("issues") or []) if isinstance(i, dict)]
    if out.get("fix_en"):
        out["fix_en"] = cut(out["fix_en"], TEXT_LIMITS["fix_en"])
    return out


def scene_cap(n_frames: int) -> float:
    return round(min(SCENE_CAP_MAX_USD, SCENE_CAP_BASE_USD + SCENE_CAP_PER_FRAME_USD * max(1, n_frames)), 4)
VIEW_EDGE = 768           # a full frame at 768 px is enough to see (half the tokens of 1024); crops zoom in for detail
ZOOM_EDGE = 768
VERDICTS = ("pass", "minor", "block", "doubt")
_VI = re.compile(r"[ăâđêôơưàáạảãằắặẳẵầấậẩẫèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]", re.I)
CAUSES = ("prompt", "reference", "model", "plan", "none")

TOOLS = [
    {"name": "view_frame", "description": "Look at frame K in full, or a region of it (fractions x0,y0,x1,y1 of the frame) enlarged.",
     "input_schema": {"type": "object", "properties": {"k": {"type": "integer"}, "region": {"type": "array", "items": {"type": "number"},
                      "minItems": 4, "maxItems": 4}}, "required": ["k"]}},
    {"name": "strip", "description": "Lay the same kind of region of several frames side by side (e.g. the left shoulder of KENTA in every "
                                     "frame he is in) — the way systematic faults across frames show up.",
     "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
         "k": {"type": "integer"}, "region": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}},
         "required": ["k", "region"]}, "minItems": 2, "maxItems": 8}, "title": {"type": "string"}}, "required": ["items"]}},
    {"name": "reference", "description": "Look at a standard picture: a character name (their approved standard picture) or "
                                         "'establishing' (the scene's wide picture: the place and the light every frame must match).",
     "input_schema": {"type": "object", "properties": {"what": {"type": "string"}, "region": {"type": "array", "items": {"type": "number"},
                      "minItems": 4, "maxItems": 4}}, "required": ["what"]}},
    {"name": "measure", "description": "Code measures of frame K (shot size from the face height, eyes under the app's top bar, dark night "
                                       "face, face count, blank frame). HINTS ONLY — they can be wrong (a hand counted as a face).",
     "input_schema": {"type": "object", "properties": {"k": {"type": "integer"}}, "required": ["k"]}},
    {"name": "record", "description": "Record the verdict of frame K. block = must be redrawn before any video; minor = note; pass; doubt "
                                      "= cannot tell (say what to look at). Every issue with visible evidence.",
     "input_schema": {"type": "object", "properties": {
         "k": {"type": "integer"}, "verdict": {"type": "string", "enum": list(VERDICTS)},
         "issues": {"type": "array", "items": {"type": "object", "properties": {"type": {"type": "string"}, "description": {"type": "string"},
                    "evidence": {"type": "string"}, "severity": {"type": "string", "enum": ["block", "minor"]},
                    "side": {"type": "object", "description": "REQUIRED for a left/right (lateral-flip) issue: measurements, the code "
                             "decides the side — who, view (camera = face seen / behind = back of head seen), body_center_x and "
                             "detail_x (0..1 across the frame), detail (e.g. gauntlet), expected_arm (LEFT/RIGHT: the arm the profile "
                             "gives that detail)", "properties": {
                        "who": {"type": "string"}, "view": {"type": "string", "enum": ["camera", "behind"]},
                        "body_center_x": {"type": "number"}, "detail_x": {"type": "number"}, "detail": {"type": "string"},
                        "expected_arm": {"type": "string", "enum": ["LEFT", "RIGHT"]}}}},
                    "required": ["type", "description", "evidence", "severity"]}},
         "root_cause": {"type": "string", "enum": list(CAUSES)}, "fix_en": {"type": "string"}},
         "required": ["k", "verdict", "issues", "root_cause"]}},
    {"name": "record_batch", "description": "Record the verdicts of SEVERAL frames at once (same fields as record, one item per frame) "
                                            "— the fast way once the looking is done.",
     "input_schema": {"type": "object", "properties": {"items": {"type": "array", "minItems": 1, "items": {"type": "object"}}},
                      "required": ["items"]}},
    {"name": "finish", "description": "End the inspection of this scene (only after every frame is recorded).",
     "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}, "new_fault_types": {"type": "array",
                      "items": {"type": "string"}}}, "required": ["summary"]}},
]

SYSTEM = """Bạn là agent QC của một đoàn phim AI — giám sát liên tục kiêm kiểm lỗi hình. Đây là cổng cuối trước khi các khung thành video tốn
tiền. QC tốt là ĐIỀU TRA, không phải một lần phán: xem đầy đủ từng khung, cắt sát và phóng to chỗ nghi ngờ, GHÉP CÙNG MỘT CHI TIẾT QUA NHIỀU
KHUNG để thấy lỗi lặp có hệ thống, so với ảnh chuẩn và ảnh toàn cảnh. Bộ đo code chỉ là gợi ý. Tự nghĩ thêm loại lỗi mới ngoài sổ tay.
Mức: block (phải vẽ lại — lỗi nhìn thấy hoặc làm sai ý đồ shot), minor (ghi chú), pass, doubt. KHÔNG bắt bẻ vụn (sắc thái diễn nhỏ).
Mỗi lỗi block: nguyên nhân gốc (prompt / reference / model / plan = bảng shot tự sai) và MỘT câu sửa tiếng Anh. Ghi (record) mọi khung rồi mới
finish. Trả lời bằng tiếng Việt, câu sửa bằng tiếng Anh.
VIẾT NGẮN: mỗi lượt tối đa 3 dòng văn bản ngoài công cụ; mỗi issue: description 1 câu, evidence 1 cụm (vùng cắt / dải nào). Phân tích
nằm trong issue, không viết đoạn văn dài (câu trả lời quá dài bị cắt và tốn tiền)."""


def enabled() -> bool:
    return features.on(FEATURE)


def _crop(path: str, region, out: str, edge: int = ZOOM_EDGE) -> str:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if region:
        w, h = im.size
        x0, y0, x1, y1 = [max(0.0, min(1.0, float(v))) for v in region]
        if x1 - x0 < 0.02 or y1 - y0 < 0.02:
            raise ValueError("vùng quá nhỏ")
        im = im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    im.thumbnail((edge, edge)) if max(im.size) > edge else None
    if max(im.size) < edge // 2:                     # a small crop is enlarged: the point of cropping is to see detail
        s = (edge // 2) / max(im.size)
        im = im.resize((int(im.size[0] * s), int(im.size[1] * s)))
    im.save(out, quality=90)
    return out


def _strip(paths: List[Tuple[str, str]], out: str, height: int = 512) -> str:
    from PIL import Image, ImageDraw
    ims = []
    for path, label in paths:
        im = Image.open(path).convert("RGB")
        im = im.resize((max(1, int(im.size[0] * height / im.size[1])), height))
        ImageDraw.Draw(im).rectangle([0, 0, 90, 22], fill="black")
        ImageDraw.Draw(im).text((4, 4), label, fill="yellow")
        ims.append(im)
    sheet = Image.new("RGB", (sum(i.size[0] for i in ims) + 6 * (len(ims) - 1), height), "white")
    x = 0
    for im in ims:
        sheet.paste(im, (x, 0))
        x += im.size[0] + 6
    if sheet.size[0] > 2048:
        sheet = sheet.resize((2048, int(height * 2048 / sheet.size[0])))
    sheet.save(out, quality=90)
    return out


_LATERAL = re.compile(r"lateral|flip|lật|trái.{0,12}phải|phải.{0,12}trái|left.{0,12}right|right.{0,12}left|sai bên|wrong side|mirror", re.I)


def lateral_issue(issue: Dict) -> bool:
    return bool(_LATERAL.search(f"{issue.get('type') or ''} {issue.get('description') or ''}"))


def arm_from_side(side: Dict) -> Optional[str]:
    """The character's own arm a detail is on, from where it sits against the body's centre line: seen from behind the body's left is
    on the frame-left of its centre, facing the camera it is on the frame-right. S7.1 01/10: the agent twice judged by the frame edge
    ("the near arm, frame-right") and blocked #8 S1·2 / S1·3 whose star shoulder sat frame-left of Kenta's body seen from behind =
    his LEFT arm = correct — so code, not the agent, turns positions into LEFT / RIGHT."""
    try:
        c, x = float(side["body_center_x"]), float(side["detail_x"])
    except (KeyError, TypeError, ValueError):
        return None
    if side.get("view") not in ("camera", "behind") or abs(x - c) < 0.02:
        return None                                   # on the centre line: no side can be read
    left_of_centre = x < c
    return ("LEFT" if left_of_centre else "RIGHT") if side["view"] == "behind" else ("RIGHT" if left_of_centre else "LEFT")


def lateral_problem(issue: Dict) -> Optional[str]:
    """Why a left/right issue cannot be recorded as stated (None = it stands): no measurements, or measurements that show the detail
    on the arm the profile gives it."""
    side = issue.get("side") if isinstance(issue.get("side"), dict) else None
    if side is None or arm_from_side(side) is None or side.get("expected_arm") not in ("LEFT", "RIGHT"):
        return ("lỗi trái/phải phải kèm `side` đo được: view (camera = thấy mặt / behind = thấy gáy), body_center_x và detail_x (0..1 "
                "theo bề ngang khung, cách nhau rõ), detail, expected_arm (tay mà hồ sơ gán chi tiết đó) — code tự suy ra tay nào; "
                "không đo được thì ghi doubt")
    arm = arm_from_side(side)
    if arm == side["expected_arm"]:
        where = "trái" if float(side["detail_x"]) < float(side["body_center_x"]) else "phải"
        seen = "nhìn từ sau" if side["view"] == "behind" else "quay mặt vào máy"
        return (f"theo số đo của bạn, {side.get('detail') or 'chi tiết'} nằm bên {where}-khung so với tâm thân {side.get('who') or ''} "
                f"({seen}) = tay {arm} — ĐÚNG tay hồ sơ gán ({side['expected_arm']}), không phải lỗi lật. Bên theo THÂN người, không "
                f"theo mép khung hay 'tay gần máy'. Ghi lại khung này không có lỗi trái/phải (hoặc đo lại)")
    return None


def inspection_plan(conn, pid: int, frames: List[Dict]) -> List[str]:
    """Strips the agent MUST make, built by code (playbook A1/A2): every one-sided or view-dependent detail of each character's profile,
    across the frames that character is in — so a systematic fault never depends on the agent thinking of it."""
    from . import assets
    plan = []
    names = []
    for f in frames:
        for n in f["data"].get("characters") or []:
            if str(n) not in names:
                names.append(str(n))
    for n in names:
        rules = assets.standard_for(conn, pid, n) or {}
        text = f"{rules.get('must_keep') or ''} {json.dumps(rules.get('view_notes') or {}, ensure_ascii=False)}"
        ks = [f["k"] for f in frames if n in (f["data"].get("characters") or [])]
        if not ks:
            continue
        if rules.get("view_notes") or re.search(r"\b(left|right)\b", text, re.I):
            # review 2026-09-28: a regex cut of the view notes dropped "Seen from behind" and handed the agent a sentence that is
            # wrong for the facing frames — the plan only says HOW to look; the rule itself stays whole in "Ghi chú theo hướng nhìn"
            plan.append(f"{n}: với MỖI khung {ks} — xác định quay mặt vào máy hay quay lưng (thấy mặt / thấy gáy), vạch đường giữa thân "
                        f"người, rồi áp NGUYÊN VĂN view_notes.facing_camera hoặc .from_behind (mục 'Ghi chú theo hướng nhìn') theo BÊN THÂN "
                        f"NGƯỜI, không theo mép khung; ghép dải cùng vùng (vai, tay) qua các khung để so. XÁC NHẬN TỪNG CHI TIẾT MỘT "
                        f"(găng, băng tay, huy hiệu vai, tab…) riêng ở từng khung — một chi tiết đúng bên không nói gì về chi tiết kia "
                        f"(#8 28/09: S6·5 găng đúng bên nhưng huy hiệu vai lật, agent cho qua); khung ôm / bị che: ghi rõ chi tiết nào "
                        f"không thấy → doubt, không pass. Muốn ghi lỗi trái/phải: kèm `side` (view, body_center_x, detail_x, detail, "
                        f"expected_arm) — code tự tính tay nào từ số đo, không tự kết luận theo mép khung")
        if re.search(r"backwards|ngược", text, re.I):
            plan.append(f"{n}: ghép dải vùng đầu qua các khung {ks} — phụ kiện đội ngược phải giữ chiều ở mọi hướng máy")
        if len(ks) < 2:
            plan = [x for x in plan if not x.startswith(f"{n}: ghép dải vùng đầu")]
    return plan


MAX_SESSION_IMAGES = 16   # past this many pictures the conversation is restarted from the brief + a recap (S7.0)


def _images_in(messages: List[Dict]) -> int:
    n = 0
    for m in messages[1:]:
        for b in m["content"] if isinstance(m["content"], list) else []:
            if b.get("type") == "tool_result" and isinstance(b.get("content"), list):
                n += sum(1 for x in b["content"] if x.get("type") == "image")
    return n


def too_long(messages: List[Dict]) -> bool:
    """S7.0 (caching docs, checked 2026-09-29): changing or removing an EARLIER picture invalidates the cache of everything after it, so
    old pictures are never cut mid-conversation (the old batch pruning did exactly that — PH 45). The conversation only grows: new
    pictures always come after the last cache point and the rest is read at 0.1x. Once it carries more than MAX_SESSION_IMAGES the
    session ends and a new one starts from the (cached) brief + a recap: one new cache write instead of a rewrite every few turns."""
    return _images_in(messages) > MAX_SESSION_IMAGES


def restart(messages: List[Dict], recap: str) -> List[Dict]:
    """A new session: the first message (brief + overview, its cache mark kept, so that prefix is still read from the cache) followed by
    the recap of what the agent saw and recorded, then what the tools answered last (not yet seen by the agent — it asked for it)."""
    last = messages[-1] if len(messages) > 1 and messages[-1]["role"] == "user" else {"content": []}
    latest = []
    for b in last["content"] if isinstance(last["content"], list) else []:
        if b.get("type") == "tool_result":
            latest += [dict(x) for x in b.get("content") or [] if isinstance(x, dict)]
        elif b.get("type") in ("text", "image"):
            latest.append(dict(b))
    for x in latest:
        x.pop("cache_control", None)
    return [{"role": "user", "content": list(messages[0]["content"]) + [{"type": "text", "text": recap}] + (
        [{"type": "text", "text": "Kết quả công cụ bạn vừa gọi:"}] + latest if latest else [])}]


def mark_cache(messages: List[Dict]) -> None:
    """Rolling cache breakpoints on the two newest user messages: next turn the conversation so far is read from the cache (0.1x the
    price) instead of paid again as fresh input. Two, not one: the provider looks back only ~20 content blocks from a breakpoint, and a
    turn with many tool calls has more (review 2026-09-28). With the system prompt and the first message: 4, the API's maximum."""
    for m in messages[1:]:
        for b in m["content"] if isinstance(m["content"], list) else []:
            b.pop("cache_control", None)
    users = [m for m in messages[1:] if m["role"] == "user" and isinstance(m["content"], list) and m["content"]]
    for m in users[-2:]:
        m["content"][-1]["cache_control"] = {"type": "ephemeral"}

class QcAgent:
    def __init__(self, p, pid: int, data_dir: str, client, frames: List[Dict], story_scene=None, work_dir: Optional[str] = None,
                 focus: Optional[List[int]] = None):
        """frames: the whole scene (context: overview, shot table, strips); focus: the job ids that must be recorded (after a redraw, the
        new frames and their neighbours) — None = every frame (review 2026-09-28: a subset alone lost the context and the K numbers)."""
        from . import qc_scene
        self.p, self.pid, self.data_dir, self.client = p, pid, data_dir, client
        self.frames = [dict(f, k=k, label=f.get("label") or f"S{f['data'].get('story_scene')}·{f['data'].get('shot_no')} {f['data'].get('size') or ''}")
                       for k, f in enumerate(frames, 1)]
        self.by_k = {f["k"]: f for f in self.frames}
        self.story = story_scene if story_scene is not None else frames[0]["data"].get("story_scene")
        self.work = work_dir or os.path.join(qc_scene._store(data_dir, pid), f"agent_scene_{self.story}")
        os.makedirs(self.work, exist_ok=True)
        self.focus = set(focus) if focus else set()
        self.records: Dict[int, Dict] = {}
        self.summary = None
        self.steps = 0
        self.sessions = 1
        self._n = 0
        self.cases: List[str] = []           # notebook cases shown (keys) — kept in the result so a run says what it learnt from

    def _must(self) -> List[Dict]:
        return [f for f in self.frames if not self.focus or f["job_id"] in self.focus]

    def _left(self) -> List[int]:
        return [f["k"] for f in self._must() if f["k"] not in self.records]

    # ---- tools ------------------------------------------------------------------------------------------------------------
    def _img(self, path: str):
        from .llm_runner import AnthropicClient
        return AnthropicClient.image_block(path, VIEW_EDGE)

    def _out(self, name: str) -> str:
        self._n += 1
        return os.path.join(self.work, f"{self._n:03d}_{name}.jpg")

    def _case_blocks(self) -> List[Dict]:
        """Sổ kinh nghiệm (core/experience): the confirmed cases of the same characters / view — false alarms and misses first — with
        their pictures, before the agent looks (S7.1 01/10: the relabelled Kenta-from-behind frames were in the repo, never shown)."""
        from . import experience
        from .runner import seen_from_behind
        try:
            experience.refresh(self.p.conn, self.data_dir)
            names = sorted({str(n).upper() for f in self.frames for n in f["data"].get("characters") or []})
            views = {"behind" if seen_from_behind(f["data"], n) else "camera" for f in self.frames for n in f["data"].get("characters") or []}
            cases = experience.relevant(self.p.conn, ("qc_image",), names, views, limit=CASES_SHOWN,
                                        exclude_jobs=[f.get("job_id") for f in self.frames])
        except Exception as e:  # noqa: BLE001 - the notebook helps; a broken one never stops the check (said in the brief)
            return [{"type": "text", "text": f"(Sổ kinh nghiệm không đọc được: {type(e).__name__}: {e})"}]
        if not cases:
            return []
        out = [{"type": "text", "text": "# Ca đã phán (người xác nhận) — cùng nhân vật / hướng máy. Đặc biệt các ca BÁO NHẦM: đừng lặp."}]
        for n, c in enumerate(cases, 1):
            out.append({"type": "text", "text": f"Ca {n}: {experience.text_line(c)}"})
            if c.get("evidence") and os.path.exists(c["evidence"]):
                out.append(self._img(_crop(c["evidence"], None, self._out(f"case{n}"), CASE_EDGE)))
        self.cases = [c["key"] for c in cases]
        return out

    def _log(self, use: Dict, content: List[Dict]) -> None:
        """Every tool call and its short answer, one line each (S7.1 01/10: two paid runs recorded nothing and left no trace of why)."""
        try:
            text = " ".join(b.get("text", "") for b in content if b.get("type") == "text")[:300]
            with open(os.path.join(self.work, "tool_log.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"step": self.steps, "tool": use.get("name"), "input": json.dumps(use.get("input") or {},
                                     ensure_ascii=False)[:400], "answer": text}, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def tool(self, name: str, args: Dict) -> List[Dict]:
        """The tool's result as content blocks (text / image)."""
        from . import assets, qc_scene, scene_establish
        if name == "view_frame":
            f = self.by_k.get(int(args["k"]))
            if f is None:
                return [{"type": "text", "text": f"không có khung K{args['k']}"}]
            out = _crop(f["path"], args.get("region"), self._out(f"k{f['k']}"))
            return [{"type": "text", "text": f"K{f['k']} {f['label']}" + (f" vùng {args['region']}" if args.get("region") else "")}, self._img(out)]
        if name == "strip":
            items = []
            for it in args.get("items") or []:
                f = self.by_k.get(int(it["k"]))
                if f is not None:
                    items.append((_crop(f["path"], it.get("region"), self._out(f"s{f['k']}"), 768), f"K{f['k']}"))
            if len(items) < 2:
                return [{"type": "text", "text": "cần ít nhất 2 khung hợp lệ"}]
            out = _strip(items, self._out("strip"))
            return [{"type": "text", "text": "Dải: " + (args.get("title") or "") + " — " + " | ".join(lab for _, lab in items)}, self._img(out)]
        if name == "reference":
            what = str(args.get("what") or "")
            if what.lower() == "establishing":
                path = scene_establish.picture(self.data_dir, self.pid, self.story)
            else:
                ref = (assets.link_characters(self.p.conn, self.pid, [what]).get(what) or {}).get("ref")
                path = ref.get("path") if ref else None
            if not path or not os.path.exists(path):
                return [{"type": "text", "text": f"không có ảnh chuẩn cho '{what}'"}]
            out = _crop(path, args.get("region"), self._out(f"ref_{re.sub(r'[^A-Za-z0-9]', '', what) or 'x'}"))
            return [{"type": "text", "text": f"Ảnh chuẩn: {what}"}, self._img(out)]
        if name == "measure":
            f = self.by_k.get(int(args["k"]))
            flags = qc_scene.check_frame(f["path"], f["data"], bool(f.get("flat_place"))) if f else []
            return [{"type": "text", "text": json.dumps(flags, ensure_ascii=False) or "[]"}]
        if name == "record_batch":
            out = []
            for item in args.get("items") or []:
                out += self.tool("record", item if isinstance(item, dict) else {})
            return [{"type": "text", "text": " · ".join(b["text"] for b in out)}] if out else [{"type": "text", "text": "không có mục nào"}]
        if name == "record":
            args = _short(args)
            k = int(args["k"])
            if k not in self.by_k:
                return [{"type": "text", "text": f"không có khung K{k}"}]
            if args.get("verdict") not in VERDICTS or args.get("root_cause") not in CAUSES:
                return [{"type": "text", "text": f"verdict ∈ {VERDICTS}, root_cause ∈ {CAUSES}"}]
            issues = args.get("issues") or []
            if args["verdict"] in ("block", "minor", "doubt") and not issues:
                return [{"type": "text", "text": "verdict khác pass phải có ít nhất một issue kèm evidence"}]
            for issue in issues if args["verdict"] in ("block", "minor") else []:     # a doubt is always recordable (S7.1 01/10:
                if isinstance(issue, dict) and lateral_issue(issue):                    # refusing it looped cảnh 2 to the end)
                    why = lateral_problem(issue)
                    if why:
                        return [{"type": "text", "text": f"K{k} chưa ghi: {why}"}]
            if args["verdict"] == "block" and args["root_cause"] == "none":
                return [{"type": "text", "text": "block cần root_cause (prompt / reference / model / plan)"}]
            fix = str(args.get("fix_en") or "")
            if args["verdict"] == "block" and args["root_cause"] != "plan" and (len(fix) < 15 or _VI.search(fix)):
                return [{"type": "text", "text": "block cần fix_en là MỘT câu tiếng Anh (không dấu tiếng Việt)"}]
            if self.focus and self.by_k[k]["job_id"] not in self.focus:
                return [{"type": "text", "text": f"K{k} là khung tham khảo (đã xét trước) — chỉ ghi các khung mới: {self._left()}"}]
            self.records[k] = dict(args, shot=self.by_k[k]["label"], job=self.by_k[k]["job_id"])
            return [{"type": "text", "text": f"đã ghi K{k}. Còn chưa ghi: {self._left()}"}]
        if name == "finish":
            left = self._left()
            if left:
                return [{"type": "text", "text": f"chưa được kết thúc: còn khung chưa ghi {left}"}]
            self.summary = args
            return [{"type": "text", "text": "đã kết thúc"}]
        return [{"type": "text", "text": f"không có công cụ {name}"}]

    # ---- the loop ---------------------------------------------------------------------------------------------------------
    def _recap(self, messages: List[Dict]) -> str:
        """What a new session needs from the old one: the agent's own notes (what it SAW, in its words), what it recorded, what is left.
        The pictures are not carried over — it can call the tool again to look again."""
        notes = [b["text"].strip() for m in messages[1:] if m["role"] == "assistant"
                 for b in m["content"] if b.get("type") == "text" and b.get("text", "").strip()]
        done = [f"K{k}: {r['verdict']}" + (" — " + "; ".join(str(i.get("description") or i.get("type")) for i in r.get("issues") or [])
                                            if r.get("issues") else "") for k, r in sorted(self.records.items())]
        text = "\n".join(notes)[-3000:]
        return ("# Phiên mới (hội thoại cũ quá dài nên được thay bằng bản tóm này; ảnh đã xem không còn — gọi lại công cụ nếu cần xem lại)\n"
                + ("## Ghi chú của chính bạn ở phiên trước\n" + text + "\n" if text else "")
                + ("## Đã ghi\n" + "\n".join(done) + "\n" if done else "")
                + f"## Còn phải ghi\n{self._left()}\nTiếp tục: điều tra khung còn lại, record_batch, rồi finish.")

    def _brief(self) -> str:
        from . import prompts
        from .claude_tasks import _read
        names = []
        for f in self.frames:
            for n in f["data"].get("characters") or []:
                if str(n) not in names:
                    names.append(str(n))
        table = [{"K": f["k"], "ghi": "PHẢI ghi" if (not self.focus or f["job_id"] in self.focus) else "tham khảo (đã xét)",
                  "shot": f["label"], "size": f["data"].get("size"), "angle": f["data"].get("angle"), "time": f["data"].get("time"),
                  "characters": f["data"].get("characters"), "action": (f["data"].get("action") or "")[:160],
                  "blocking": (f["data"].get("blocking") or "")[:220]} for f in self.frames]
        views = {}
        from . import assets
        for n in names:
            v = (assets.standard_for(self.p.conn, self.pid, n) or {}).get("view_notes")
            if v:
                views[n] = v
        plan = inspection_plan(self.p.conn, self.pid, self.frames)
        place = ""
        try:
            loc = assets.scene_location(self.p.conn, self.pid, self.frames[0]["data"])
            place = assets.location_text(self.p.conn, loc) if loc is not None else ""
        except Exception:  # noqa: BLE001 - the brief goes without it
            place = ""
        limits = (f"# Giới hạn (khóa cứng, không nâng được)\nTối đa {max_steps(len(self._must()))} lượt và ${scene_cap(len(self._must())):.2f} cho cảnh này; "
                  f"tối đa {LOOKS_PER_TURN} ảnh mỗi lượt; quá {int(RECORD_ONLY_AT * 100)} % ngân sách thì CHỈ còn được ghi. "
                  f"Phải ghi (record) các khung: {[f['k'] for f in self._must()]}.\n"
                  "Cách làm (mục tiêu ≤ 6 lượt): lượt 1 — từ tấm tổng quan chọn khung nghi ngờ + làm các dải bắt buộc của kế hoạch soi "
                  "(strip gom nhiều khung vào MỘT ảnh); lượt 2–3 — cắt sát chỗ nghi; lượt 3–4 — record_batch MỌI khung (khung không nghi "
                  "ngờ ghi pass ngay từ tấm tổng quan), rồi finish. Hết ngân sách thì khung chưa ghi thành 'doubt' cho người xem.\n"
                  "Kết luận NGẮN, CHUẨN: description 1 câu (ai, chi tiết gì, sai thế nào so với luật nào), evidence = công cụ + vùng đã "
                  "xem, fix_en 1 câu mệnh lệnh tiếng Anh nói điều PHẢI đúng (không nói điều cấm).")
        return "\n\n".join(x for x in [
            limits,
            ("# Bối cảnh — mô tả bản đồ thật (so nền của MỌI khung với mô tả này và ảnh 'establishing'; sổ tay mục G)\n" + place) if place else "",
            "# Sổ tay kiểm tra (lỗi đã được người xác nhận — làm đủ các thao tác 'Cách soi' áp dụng được)\n" + _read("knowledge", "qc_playbook.md"),
            prompts.lock_text(self.p.conn, self.pid, names),
            ("# Ghi chú theo hướng nhìn\n```json\n" + json.dumps(views, ensure_ascii=False, indent=1) + "\n```") if views else "",
            f"# Cảnh kịch bản {self.story} — bảng shot\n```json\n" + json.dumps(table, ensure_ascii=False, indent=1) + "\n```",
            ("# Kế hoạch soi bắt buộc (do code lập từ hồ sơ)\n" + "\n".join(f"- {x}" for x in plan)) if plan else "",
            "Bắt đầu: xem tấm tổng quan, rồi điều tra từng khung bằng công cụ; record mọi khung; finish."] if x)

    def run(self) -> Dict:
        import time
        from . import layout
        from .llm_runner import LlmError, tagged
        t0 = time.time()
        overview = layout.storyboard([(f["path"], f"K{f['k']}") for f in self.frames], os.path.join(self.work, "overview.png"),
                                     cols=min(6, len(self.frames)), cell=(256, 455))
        messages = [{"role": "user", "content": [{"type": "text", "text": self._brief()}, {"type": "text", "text": "Tấm tổng quan các khung:"},
                                                 self._img(overview)] + self._case_blocks()}]
        messages[0]["content"][-1]["cache_control"] = {"type": "ephemeral"}   # brief + overview are resent every turn: cache them
        from .llm_runner import spend_cap
        stopped, cuts = "", 0
        self.blocked = False
        if not hasattr(self.client, "converse"):
            raise LlmError(f"trình gọi Claude '{getattr(self.client, 'name', '?')}' không hỗ trợ agent (cần Claude API: LLM_PROVIDER=anthropic)",
                           code="config")
        cap_usd = scene_cap(len(self._must()))
        steps_max = max_steps(len(self._must()))
        last_cost, spent_before, last_record_step, recorded = 0.0, 0.0, 0, 0
        with tagged("qc_agent", self.pid), spend_cap(cap_usd, f"agent QC cảnh {self.story}") as cap:
            while self.summary is None and self.steps < steps_max:
                if too_long(messages):
                    messages = restart(messages, self._recap(messages))
                    self.sessions += 1
                mark_cache(messages)
                closing = (self.steps >= steps_max - CLOSING_TURNS or cap["spent"] >= RECORD_ONLY_AT * cap_usd
                           or cap_usd - cap["spent"] < RESERVE_TURNS * last_cost
                           or (self.steps - last_record_step >= RECORD_EVERY and len(self.records) < len(self._must())))
                tools = [t for t in TOOLS if t["name"] in RECORD_TOOLS] if closing else TOOLS
                try:
                    reply = self.client.converse(messages, tools, SYSTEM, max_tokens=ANSWER_TOKENS)
                except Exception as e:  # noqa: BLE001 - a lock, the network, the provider: stop here and KEEP what was recorded
                    stopped = f"dừng: {e}"
                    self.blocked = not self.records and getattr(e, "code", None) in ("budget", "auth", "config")
                    break
                self.steps += 1
                last_cost, spent_before = max(cap["spent"] - spent_before, 0.0), cap["spent"]
                blocks = [b for b in (reply.blocks or []) if b.get("type") != "tool_use" or isinstance(b.get("input"), dict)]
                cut = reply.stop_reason == "max_tokens"
                if cut:                                # 28/09: a cut answer was thrown away WITH the records already complete in it —
                    cuts += 1                          # keep its whole tool calls (a half-written one is refused by its own checks)
                    blocks = [b for b in blocks if b.get("type") == "tool_use"]
                if not blocks:                         # an empty assistant turn is a 400: nothing is sent back
                    cuts += 0 if cut else 1
                    if cuts > MAX_CUT_TURNS:
                        stopped = "dừng: câu trả lời bị cắt / rỗng nhiều lần"
                        break
                    messages[-1]["content"].append({"type": "text", "text": "(Lượt trước bị cắt / rỗng — KHÔNG viết phân tích dài, gọi "
                                                                            f"công cụ ngay. Còn chưa ghi: {self._left()})"})
                    continue
                if cut and cuts > MAX_CUT_TURNS + 2:
                    stopped = "dừng: câu trả lời bị cắt nhiều lần"
                    break
                messages.append({"role": "assistant", "content": blocks})
                uses = [b for b in blocks if b.get("type") == "tool_use"]
                if not uses:
                    messages.append({"role": "user", "content": [{"type": "text", "text": f"Tiếp tục bằng công cụ. Còn chưa ghi: {self._left()}"}]})
                    continue
                results, looks = [], 0
                record_only = closing or cap["spent"] >= RECORD_ONLY_AT * cap_usd
                for u in uses:
                    looking = u["name"] in ("view_frame", "strip", "reference")
                    try:
                        if looking and record_only:
                            content = [{"type": "text", "text": "HẾT phần điều tra (đã dùng quá nửa ngân sách cảnh) — GHI NGAY kết luận "
                                                                "mọi khung còn lại theo những gì đã thấy; khung chưa đủ bằng chứng → doubt."}]
                        elif looking and looks >= LOOKS_PER_TURN:
                            content = [{"type": "text", "text": f"tối đa {LOOKS_PER_TURN} ảnh mỗi lượt — ghi kết luận các khung đã đủ bằng chứng trước"}]
                        else:
                            looks += looking
                            content = self.tool(u["name"], u.get("input") or {})
                    except Exception as e:  # noqa: BLE001 - a bad tool call is answered, the loop goes on
                        content = [{"type": "text", "text": f"lỗi công cụ: {type(e).__name__}: {e}"}]
                    results.append({"type": "tool_result", "tool_use_id": u["id"], "content": content})
                    self._log(u, content)
                left = self._left()                    # where it stands, every turn (28/09: 8 turns spent looking, nothing recorded)
                results[-1]["content"] = list(results[-1]["content"]) + [{"type": "text", "text": (
                    f"[Trạng thái] đã dùng ${cap['spent']:.3f} / ${cap_usd:.2f}, lượt {self.steps}/{steps_max}; chưa ghi: {left}"
                    + (" — CHỈ còn được ghi (record_batch) / kết thúc." if closing else
                       " — ghi (record) khung nào đã đủ bằng chứng NGAY lượt này."))}]
                if len(self.records) > recorded:
                    recorded, last_record_step = len(self.records), self.steps
                messages.append({"role": "user", "content": results})
        if self.summary is None:
            left = self._left()
            why = stopped or f"hết {steps_max} lượt"
            for k in left:                                     # out of steps / money: the unchecked frames wait for a person, said
                self.records[k] = {"k": k, "verdict": "doubt", "issues": [{"type": "chưa soi", "description": f"agent {why} trước khi soi khung",
                                   "evidence": "-", "severity": "minor"}], "root_cause": "none", "shot": self.by_k[k]["label"],
                                   "job": self.by_k[k]["job_id"]}
            self.summary = {"summary": f"{why} — {len(left)} khung chưa soi", "new_fault_types": []}
        seen = sum(1 for r in self.records.values() if not any(i.get("type") == "chưa soi" for i in r.get("issues") or []))
        minutes = max((time.time() - t0) / 60, 1e-6)
        out = {"scene": self.story, "steps": self.steps, "usd": round(cap["spent"], 4), "cap_usd": cap_usd, "stopped": stopped,
               "sessions": self.sessions, "cases_shown": self.cases,
               "blocked": self.blocked, "speed": {"minutes": round(minutes, 2), "frames_judged": seen,
                                                   "frames_per_minute": round(seen / minutes, 2),
                                                   "usd_per_frame": round(cap["spent"] / seen, 4) if seen else None},
               "records": [self.records[f["k"]] for f in self._must()], "summary": self.summary}
        with open(os.path.join(self.work, "result.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        return out


def review_scene(p, pid: int, story_scene, client, data_dir: str, frames: Optional[List[Dict]] = None,
                 focus: Optional[List[int]] = None) -> Dict:
    """Run the agent on one scene (all its frames as context, `focus` = the job ids to record) and apply its verdicts the qc_scene way
    (not trusted yet → every frame held with the verdict as note). A frame already APPROVED that the agent blocks or doubts is said
    (diag warn) — the playbook F1 asks to look at them again (review 2026-09-28: it went only to reviews.json)."""
    from . import diag, qc_scene
    frames = frames or qc_scene.scene_frames(p, pid, story_scene, data_dir)
    if not frames:
        raise ValueError(f"cảnh {story_scene} chưa đủ khung")
    for f in frames:
        d = f["data"]
        f["label"] = f"S{d.get('story_scene')}·{d.get('shot_no')} {d.get('size') or ''}"
    agent = QcAgent(p, pid, data_dir, client, frames, story_scene, focus=focus)
    res = agent.run()
    frames = agent._must()
    for r in res["records"]:
        if r["verdict"] in ("block", "doubt") and p.job(r["job"])["state"] == "approved":
            diag.record(p.conn, "image_gen", "warn", f"Agent QC: khung đã duyệt {r['shot']} (job {r['job']}) bị {r['verdict']} — "
                        + "; ".join(i.get("description", "") for i in r.get("issues") or [])[:300], code="qc_agent_approved_flag",
                        project_id=pid)
    mapped = {"frames": [], "scene": {"ok": True, "notes": res["summary"].get("summary", "")}}
    for r in res["records"]:
        r = dict(r, k=len(mapped["frames"]) + 1)
        verdict = {"block": "fix", "minor": "pass", "pass": "pass", "doubt": "doubt"}[r["verdict"]]
        checks = {c: {"ok": True, "evidence": "agent QC"} for c in qc_scene.CHECKS}
        problem = "; ".join(f"{i['type']}: {i['description']} ({i['evidence']})" for i in r.get("issues") or [])
        if verdict != "pass":
            checks["artifacts"] = {"ok": False, "evidence": problem or "agent QC"}
        mapped["frames"].append({"k": r["k"], "shot": r["shot"], "seen": "", "checks": checks, "verdict": verdict,
                                 "root_cause": r.get("root_cause") or "none", "problem": problem, "fix": r.get("fix_en") or "",
                                 "note": f"lỗi nhỏ: {problem}" if r["verdict"] == "minor" and problem else ""})
    applied = qc_scene.apply(p, pid, frames, mapped, data_dir)
    return {**res, "applied": applied}
