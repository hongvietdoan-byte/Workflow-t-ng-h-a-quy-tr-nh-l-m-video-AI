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
MAX_STEPS = 24            # tool turns per scene (#8 2026-09-28: 19 turns for a 4-frame scene)
SCENE_CAP_BASE_USD = 0.10  # HARD lock per scene (llm_runner.spend_cap) = base + per frame to record, at most SCENE_CAP_MAX_USD:
SCENE_CAP_PER_FRAME_USD = 0.04   # #8 2026-09-28 one scene + half cost ~2 USD with no lock. At the cap the agent stops; the frames it
SCENE_CAP_MAX_USD = 0.50         # has not recorded wait for a person as "doubt" (a trade-off: fewer looks, never more money)
SCENE_CAP_USD = SCENE_CAP_BASE_USD + 4 * SCENE_CAP_PER_FRAME_USD     # a 4-frame scene (shown in docs / the estimate)
ANSWER_TOKENS = 6000      # one turn's answer (a real turn wrote 3,209 tokens); a cut answer → "fewer tools per turn", not a stop
MAX_CUT_TURNS = 2


def scene_cap(n_frames: int) -> float:
    return min(SCENE_CAP_MAX_USD, SCENE_CAP_BASE_USD + SCENE_CAP_PER_FRAME_USD * max(1, n_frames))
VIEW_EDGE = 1024
ZOOM_EDGE = 1024
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
                    "evidence": {"type": "string"}, "severity": {"type": "string", "enum": ["block", "minor"]}},
                    "required": ["type", "description", "evidence", "severity"]}},
         "root_cause": {"type": "string", "enum": list(CAUSES)}, "fix_en": {"type": "string"}},
         "required": ["k", "verdict", "issues", "root_cause"]}},
    {"name": "finish", "description": "End the inspection of this scene (only after every frame is recorded).",
     "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}, "new_fault_types": {"type": "array",
                      "items": {"type": "string"}}}, "required": ["summary"]}},
]

SYSTEM = """Bạn là agent QC của một đoàn phim AI — giám sát liên tục kiêm kiểm lỗi hình. Đây là cổng cuối trước khi các khung thành video tốn
tiền. QC tốt là ĐIỀU TRA, không phải một lần phán: xem đầy đủ từng khung, cắt sát và phóng to chỗ nghi ngờ, GHÉP CÙNG MỘT CHI TIẾT QUA NHIỀU
KHUNG để thấy lỗi lặp có hệ thống, so với ảnh chuẩn và ảnh toàn cảnh. Bộ đo code chỉ là gợi ý. Tự nghĩ thêm loại lỗi mới ngoài sổ tay.
Mức: block (phải vẽ lại — lỗi nhìn thấy hoặc làm sai ý đồ shot), minor (ghi chú), pass, doubt. KHÔNG bắt bẻ vụn (sắc thái diễn nhỏ).
Mỗi lỗi block: nguyên nhân gốc (prompt / reference / model / plan = bảng shot tự sai) và MỘT câu sửa tiếng Anh. Ghi (record) mọi khung rồi mới
finish. Trả lời bằng tiếng Việt, câu sửa bằng tiếng Anh."""


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
                        f"NGƯỜI, không theo mép khung; ghép dải cùng vùng (vai, tay) qua các khung để so")
        if re.search(r"backwards|ngược", text, re.I):
            plan.append(f"{n}: ghép dải vùng đầu qua các khung {ks} — phụ kiện đội ngược phải giữ chiều ở mọi hướng máy")
        if len(ks) < 2:
            plan = [x for x in plan if not x.startswith(f"{n}: ghép dải vùng đầu")]
    return plan


KEEP_IMAGE_TURNS = 2      # tool results whose pictures stay in the conversation after a pruning
MAX_HISTORY_IMAGES = 10   # pruning happens only once the conversation carries more pictures than this


def _images_in(messages: List[Dict]) -> int:
    n = 0
    for m in messages[1:]:
        for b in m["content"] if isinstance(m["content"], list) else []:
            if b.get("type") == "tool_result" and isinstance(b.get("content"), list):
                n += sum(1 for x in b["content"] if x.get("type") == "image")
    return n


def prune(messages: List[Dict]) -> bool:
    """Every turn resends the whole conversation, so old pictures are dropped — but IN A BATCH, once more than MAX_HISTORY_IMAGES are
    carried: every pruning changes the start of the conversation and the provider's prompt cache is lost for that turn (#8 2026-09-28:
    pruning at every turn made 736k input tokens uncached, ~2 USD). What was SEEN stays in the agent's own words (text, record calls);
    it can call the tool again to look again. Returns True when it pruned."""
    if _images_in(messages) <= MAX_HISTORY_IMAGES:
        return False
    seen = 0
    for m in reversed(messages[1:]):
        if m["role"] != "user" or not isinstance(m["content"], list):
            continue
        results = [b for b in m["content"] if b.get("type") == "tool_result"]
        if not results:
            continue
        seen += 1
        if seen <= KEEP_IMAGE_TURNS:
            continue
        for r in results:
            if isinstance(r.get("content"), list) and any(b.get("type") == "image" for b in r["content"]):
                r["content"] = [b for b in r["content"] if b.get("type") != "image"] + [
                    {"type": "text", "text": "(ảnh đã xem ở lượt trước — gọi lại công cụ nếu cần xem lại)"}]
    return True


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
        self._n = 0

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
            flags = qc_scene.check_frame(f["path"], f["data"]) if f else []
            return [{"type": "text", "text": json.dumps(flags, ensure_ascii=False) or "[]"}]
        if name == "record":
            k = int(args["k"])
            if k not in self.by_k:
                return [{"type": "text", "text": f"không có khung K{k}"}]
            if args.get("verdict") not in VERDICTS or args.get("root_cause") not in CAUSES:
                return [{"type": "text", "text": f"verdict ∈ {VERDICTS}, root_cause ∈ {CAUSES}"}]
            issues = args.get("issues") or []
            if args["verdict"] in ("block", "minor", "doubt") and not issues:
                return [{"type": "text", "text": "verdict khác pass phải có ít nhất một issue kèm evidence"}]
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
        limits = (f"# Giới hạn (khóa cứng, không nâng được)\nTối đa {MAX_STEPS} lượt và ${scene_cap(len(self._must())):.2f} cho cảnh này. "
                  f"Phải ghi (record) các khung: {[f['k'] for f in self._must()]}. Mỗi lượt gọi NHIỀU "
                  "công cụ cùng lúc; dùng strip để soi một chi tiết của nhiều khung trong một ảnh; record ngay khi đủ bằng chứng. Hết giới "
                  "hạn thì khung chưa record thành 'doubt' cho người xem.")
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
        from . import layout
        from .llm_runner import LlmError, tagged
        overview = layout.storyboard([(f["path"], f"K{f['k']}") for f in self.frames], os.path.join(self.work, "overview.png"),
                                     cols=min(6, len(self.frames)), cell=(256, 455))
        messages = [{"role": "user", "content": [{"type": "text", "text": self._brief()}, {"type": "text", "text": "Tấm tổng quan các khung:"},
                                                 self._img(overview)]}]
        messages[0]["content"][-1]["cache_control"] = {"type": "ephemeral"}   # brief + overview are resent every turn: cache them
        from .llm_runner import spend_cap
        stopped, cuts = "", 0
        self.blocked = False
        if not hasattr(self.client, "converse"):
            raise LlmError(f"trình gọi Claude '{getattr(self.client, 'name', '?')}' không hỗ trợ agent (cần Claude API: LLM_PROVIDER=anthropic)",
                           code="config")
        cap_usd = scene_cap(len(self._must()))
        with tagged("qc_agent", self.pid), spend_cap(cap_usd, f"agent QC cảnh {self.story}") as cap:
            while self.summary is None and self.steps < MAX_STEPS:
                prune(messages)
                mark_cache(messages)
                try:
                    reply = self.client.converse(messages, TOOLS, SYSTEM, max_tokens=ANSWER_TOKENS)
                except Exception as e:  # noqa: BLE001 - a lock, the network, the provider: stop here and KEEP what was recorded
                    stopped = f"dừng: {e}"
                    self.blocked = not self.records and getattr(e, "code", None) in ("budget", "auth", "config")
                    break
                self.steps += 1
                blocks = [b for b in (reply.blocks or []) if b.get("type") != "tool_use" or isinstance(b.get("input"), dict)]
                if reply.stop_reason == "max_tokens" or not blocks:
                    cuts += 1                  # a cut or empty answer is not sent back (an empty assistant turn is a 400)
                    if cuts > MAX_CUT_TURNS:
                        stopped = "dừng: câu trả lời bị cắt nhiều lần"
                        break
                    messages[-1]["content"].append({"type": "text", "text": "(Lượt trước bị cắt / rỗng — gọi ÍT công cụ hơn mỗi lượt, "
                                                                            f"ghi ngắn. Còn chưa ghi: {self._left()})"})
                    continue
                messages.append({"role": "assistant", "content": blocks})
                uses = [b for b in blocks if b.get("type") == "tool_use"]
                if not uses:
                    messages.append({"role": "user", "content": [{"type": "text", "text": f"Tiếp tục bằng công cụ. Còn chưa ghi: {self._left()}"}]})
                    continue
                results = []
                for u in uses:
                    try:
                        content = self.tool(u["name"], u.get("input") or {})
                    except Exception as e:  # noqa: BLE001 - a bad tool call is answered, the loop goes on
                        content = [{"type": "text", "text": f"lỗi công cụ: {type(e).__name__}: {e}"}]
                    results.append({"type": "tool_result", "tool_use_id": u["id"], "content": content})
                messages.append({"role": "user", "content": results})
        if self.summary is None:
            left = self._left()
            why = stopped or f"hết {MAX_STEPS} lượt"
            for k in left:                                     # out of steps / money: the unchecked frames wait for a person, said
                self.records[k] = {"k": k, "verdict": "doubt", "issues": [{"type": "chưa soi", "description": f"agent {why} trước khi soi khung",
                                   "evidence": "-", "severity": "minor"}], "root_cause": "none", "shot": self.by_k[k]["label"],
                                   "job": self.by_k[k]["job_id"]}
            self.summary = {"summary": f"{why} — {len(left)} khung chưa soi", "new_fault_types": []}
        out = {"scene": self.story, "steps": self.steps, "usd": round(cap["spent"], 4), "cap_usd": cap_usd, "stopped": stopped,
               "blocked": self.blocked, "records": [self.records[f["k"]] for f in self._must()], "summary": self.summary}
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
