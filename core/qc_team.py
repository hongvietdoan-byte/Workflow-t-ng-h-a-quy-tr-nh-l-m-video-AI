"""Tổ QC (docs/THIET_KE_TO_QC_2026-10-01.md) — GĐ2: code điều phối + chuyên viên C1 Nhân vật. Cờ `qc_team` (TẮT).

review_frame(): bộ dịch đặc tả (qc_spec) → tầng 0 (qc_measure) → C1 (1 lời gọi có cấu trúc, không vòng lặp) → bảng luật (qc_rules).
C2 Diễn xuất & hướng, C3 Cảnh & liền mạch, trọng tài (Opus 5.5) và Director duyệt cảnh: GĐ4–GĐ6 — ở GĐ2 các mệnh đề của họ chỉ có số đo code
(không kết luận "sai" nếu code chưa chắc).

Every model call goes through a client with `ask_json`; RecordingClient keeps the whole request (images by hash) and reply in
calls.jsonl, ReplayClient answers the same requests again for 0 USD (mục 15.2): a code change is replayed before any paid run.
"""
import hashlib
import json
import os
import tempfile
from typing import Dict, List, Optional

C1_MODEL_EDGE = 768           # the frame
CROP_EDGE = 384               # face crops / case pictures
C1_MAX_TOKENS_BASE = 400
C1_TOKENS_PER_ASSERTION = 170   # GĐ3 01/10: 300 + 110 × 13 cut job 333 (max_tokens is not part of the replay key)
CASES_SHOWN = 4
OBSERVE_FIELDS = {"side": ["facing", "seen_at"], "cap": ["cap_marks"], "count": ["extra_people"]}

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"},
            "answer": {"type": "string", "enum": ["true", "false", "unclear"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "note_vi": {"type": "string"},
            "fix_en": {"type": "string"},
            # observations (GĐ3 01/10) — "na" when the assertion does not ask for it; qc_rules.observed decides from them
            "facing": {"type": "string", "enum": ["front", "back", "profile_facing_image_left", "profile_facing_image_right",
                                                  "not_visible", "na"]},
            "seen_at": {"type": "string", "enum": ["image_left_of_body", "image_right_of_body", "near_side", "far_side",
                                                   "not_visible", "na"]},
            "cap_marks": {"type": "string", "enum": ["strap_or_buckle_at_forehead", "brim_at_forehead", "brim_at_nape",
                                                     "strap_or_buckle_at_nape", "no_cap", "not_visible", "na"]},
            "extra_people": {"type": "string", "enum": ["none", "partial_or_background", "clear", "missing", "na"]}},
            "required": ["id", "answer", "confidence", "note_vi", "fix_en", "facing", "seen_at", "cap_marks", "extra_people"],
            "additionalProperties": False}},
        "other_issues": {"type": "array", "items": {"type": "object", "properties": {
            "description_vi": {"type": "string"},
            "severity": {"type": "string", "enum": ["block", "minor"]}},
            "required": ["description_vi", "severity"], "additionalProperties": False}}},
    "required": ["answers", "other_issues"], "additionalProperties": False}

C1_SYSTEM = """Bạn là CHUYÊN VIÊN NHÂN VẬT của tổ QC một xưởng phim AI (game Free Fire, nhân vật 3D in-game). Việc DUY NHẤT: trả lời từng
mệnh đề kiểm tra về NHÂN VẬT trong khung được giao (đúng người, trang phục, chi tiết một bên, phụ kiện có chiều, số người, kỹ năng).
Không chấm diễn xuất, ánh sáng, bối cảnh — tổ khác lo.

Cách trả lời mỗi mệnh đề (theo id): answer true (đúng như mệnh đề) / false (thấy rõ là sai) / unclear (không thấy được: bị che, quá nhỏ, ra
ngoài khung); confidence high / medium / low; note_vi 1 câu bằng chứng nhìn thấy (vùng nào, thấy gì); fix_en: khi false, 1 câu tiếng Anh
nói điều PHẢI đúng, còn lại để "".

MỆNH ĐỀ CÓ Ô "KHAI" (chi tiết một bên, mũ, số người): bạn CHỈ KHAI ĐIỀU NHÌN THẤY, KHÔNG tự suy ra trái/phải của thân hay chiều mũ — code
làm việc đó. Ô không được hỏi điền "na".
- Chi tiết một bên → `facing`: thân người đó quay về đâu (front = thấy ngực / mặt, kể cả nghiêng ba phần tư; back = thấy lưng / gáy, kể cả ba
  phần tư sau; profile_facing_image_left / _right = nghiêng hẳn, mặt hướng về mép TRÁI / PHẢI của ẢNH) theo THÂN, không theo đầu.
  `seen_at`: chi tiết nằm ở nửa nào CỦA THÂN NGƯỜI ĐÓ khi nhìn trên ẢNH — image_left_of_body / image_right_of_body (so đường giữa thân, theo
  trái / phải của ẢNH như bạn đang nhìn); khi nghiêng hẳn: near_side (phía gần máy) / far_side (phía xa, bị thân che một phần); không thấy →
  not_visible. Tìm đúng món đồ được tả (vd găng giáp bạc, băng quấn trắng) rồi khai chỗ của NÓ — không suy từ món khác.
- Mũ → `cap_marks`: thứ thấy ở TRÁN và ở GÁY: strap_or_buckle_at_forehead / brim_at_forehead / brim_at_nape / strap_or_buckle_at_nape /
  no_cap / not_visible.
- Số người → `extra_people`: none (đúng số) / partial_or_background (người thừa chỉ lộ một phần ở mép hoặc mờ phía sau) / clear (người thừa
  rõ) / missing (thiếu người).
Với các mệnh đề này vẫn điền `answer` theo bạn nghĩ (chỉ để đối chiếu) và note_vi tả đúng điều thấy.

Thứ tự ưu tiên khi thời gian / sự chú ý có hạn: đúng người → số người → chi tiết một bên & mũ → kỹ năng. Trả lời ĐỦ mọi id được giao.
other_issues: lỗi nhân vật rõ ràng ngoài danh sách (tối đa 3), không bắt bẻ vụn."""


def _img_key(block: Dict) -> str:
    if block.get("type") == "image":
        return "img:" + hashlib.sha256(block["source"]["data"].encode("ascii")).hexdigest()[:16]
    return block.get("text", "")


def request_key(messages: List[Dict], system: str, schema: Dict) -> str:
    """The same request (text, pictures by hash, schema, system) → the same key."""
    parts = [system, json.dumps(schema, sort_keys=True)]
    for m in messages:
        content = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
        parts.append(m["role"] + "|" + "|".join(_img_key(b) for b in content))
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


class RecordingClient:
    """Wraps a real client: every ask_json is written to `path` (one JSON line: key, model, reply text, tokens, stop)."""

    def __init__(self, inner, path: str):
        self.inner, self.path = inner, path
        self.model = getattr(inner, "model", "")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def ask_json(self, messages, system, schema, max_tokens, thinking=None, effort=None):
        reply = self.inner.ask_json(messages, system, schema, max_tokens, thinking=thinking, effort=effort)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": request_key(messages, system, schema), "model": self.model, "text": reply.text,
                                 "input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens,
                                 "cache_read_tokens": reply.cache_read_tokens, "cache_write_tokens": reply.cache_write_tokens,
                                 "stop_reason": reply.stop_reason}, ensure_ascii=False) + "\n")
        return reply


class ReplayClient:
    """Answers recorded requests again (0 USD). A request not in the record raises — the code change altered what is sent, so the
    old answer is no evidence (mục 15.2)."""
    name = "replay"

    def __init__(self, path: str):
        from .llm_runner import LlmReply
        self.model = "replay"
        self.calls = {}
        for line in open(path, encoding="utf-8"):
            if line.strip():
                d = json.loads(line)
                self.calls[d["key"]] = LlmReply(d["text"], d.get("input_tokens", 0), d.get("output_tokens", 0), d.get("stop_reason", ""),
                                                d.get("cache_write_tokens", 0), d.get("cache_read_tokens", 0))
        self.misses = 0

    def ask_json(self, messages, system, schema, max_tokens, thinking=None, effort=None):
        from .llm_runner import LlmError
        key = request_key(messages, system, schema)
        if key not in self.calls:
            self.misses += 1
            raise LlmError("replay: yêu cầu này chưa có trong bản ghi (code đã đổi điều gửi đi)", code="replay_miss")
        return self.calls[key]


def _image(path: str, edge: int) -> Dict:
    from .llm_runner import AnthropicClient
    return AnthropicClient.image_block(path, edge)


def entity_blocks(p, pid: int, names: List[str], views: List[str], frame_jobs: List[int], data_dir: str,
                  frame_shots: List[str] = ()) -> List[Dict]:
    """The cached part: each person's standard picture + confirmed cases (sổ kinh nghiệm) with their pictures."""
    from . import assets, experience
    blocks: List[Dict] = [{"type": "text", "text": "# Ảnh chuẩn từng người trong cảnh"}]
    for n in names:
        linked = assets.link_characters(p.conn, pid, [n]).get(n) or {}
        ref = linked.get("ref")
        if ref and ref.get("path") and os.path.exists(ref["path"]):
            blocks += [{"type": "text", "text": f"Ảnh chuẩn {n}:"}, _image(ref["path"], CROP_EDGE)]
        else:
            blocks.append({"type": "text", "text": f"{n}: không có ảnh chuẩn trong Kho"})
        if "behind" in views and linked:          # 01/10: the back of the standard (3D render / in-game) — compare the same side
            back = assets.view_picture(linked, "back")
            if back and os.path.exists(back["path"]):
                blocks += [{"type": "text", "text": f"Ảnh chuẩn {n} — nhìn từ SAU LƯNG (so khung quay lưng với ảnh này):"},
                           _image(back["path"], CROP_EDGE)]
    try:
        experience.refresh(p.conn, data_dir)
        cases = experience.relevant(p.conn, ("qc_image",), names, views, limit=CASES_SHOWN, exclude_jobs=frame_jobs,
                                    exclude_shots=[(pid, s) for s in frame_shots])   # never another take of a shot judged now
    except Exception as e:  # noqa: BLE001 - the notebook helps; a broken one never stops the check
        cases = []
        blocks.append({"type": "text", "text": f"(Sổ kinh nghiệm không đọc được: {type(e).__name__})"})
    if cases:
        blocks.append({"type": "text", "text": "# Ca đã phán (người xác nhận) — cùng nhân vật / hướng máy"})
        for k, c in enumerate(cases, 1):
            blocks.append({"type": "text", "text": f"Ca {k}: {experience.text_line(c)}"})
            if c.get("evidence") and os.path.exists(c["evidence"]):
                blocks.append(_image(c["evidence"], CROP_EDGE))
    blocks[-1] = dict(blocks[-1], cache_control={"type": "ephemeral"})
    return blocks


def face_blocks(path: str, code: Dict) -> List[Dict]:
    from .qc_agent import _crop
    out = []
    for k, (l, t, r, b) in enumerate(code.get("_faces", {}).get("boxes") or [], 1):
        w, h = r - l, b - t
        region = [max(0.0, l - w * 0.6), max(0.0, t - h * 0.9), min(1.0, r + w * 0.6), min(1.0, b + h * 0.4)]
        work = os.path.join(tempfile.gettempdir(), "qc_team_crops")      # never next to the project's pictures
        os.makedirs(work, exist_ok=True)
        crop = _crop(path, region, os.path.join(work, os.path.splitext(os.path.basename(path))[0] + f"__face{k}.jpg"), CROP_EDGE)
        out += [{"type": "text", "text": f"Mặt {k} (code cắt sẵn, vùng {[round(x, 2) for x in region]}):"}, _image(crop, CROP_EDGE)]
    return out


def c1_request(frame: Dict, assertions: List[Dict], code: Dict, entity: List[Dict]) -> List[Dict]:
    lines = []
    for a in assertions:
        c = code.get(a["id"]) or {}
        if a.get("observe") in OBSERVE_FIELDS:      # neither the expected side nor the shot table's view: the model only reports
            lines.append({"id": a["id"], "người": a["subject"], "khai": OBSERVE_FIELDS[a["observe"]], "question": a["question_en"]})
            continue
        lines.append({"id": a["id"], "người": a["subject"], "hướng máy": a.get("view") or "không rõ", "mệnh đề": a["claim_vi"],
                      "question": a["question_en"], "số đo code": c.get("note", "")})
    data = frame["data"]
    head = (f"# Khung {frame.get('label') or frame['job_id']} — bảng shot: người {data.get('characters')}, cỡ {data.get('size')}, góc "
            f"{data.get('angle')}\nBlocking: {str(data.get('blocking') or '')[:300]}\n# Mệnh đề cần trả lời (đủ mọi id)\n"
            + json.dumps(lines, ensure_ascii=False, indent=0))
    return [{"role": "user", "content": entity + [{"type": "text", "text": head}, {"type": "text", "text": "Khung đầy đủ:"},
                                                  _image(frame["path"], C1_MODEL_EDGE)] + face_blocks(frame["path"], code)}]


def parse_answers(text: str, assertions: List[Dict]) -> Dict:
    """{"answers": {id: answer}, "other_issues": [...], "problems": [...]} — ids not asked are dropped, missing ids are listed."""
    try:
        obj = json.loads(text)
    except ValueError:
        return {"answers": {}, "other_issues": [], "problems": ["câu trả lời không phải JSON"]}
    asked = {a["id"] for a in assertions}
    answers = {x["id"]: x for x in obj.get("answers") or [] if isinstance(x, dict) and x.get("id") in asked}
    missing = sorted(asked - set(answers))
    return {"answers": answers, "other_issues": obj.get("other_issues") or [],
            "problems": [f"thiếu câu trả lời: {', '.join(missing)}"] if missing else []}


def review_frame(p, pid: int, data_dir: str, frame: Dict, client, entity: Optional[List[Dict]] = None, roles=("C1",),
                 profiles: Optional[Dict[str, Dict]] = None) -> Dict:
    """One frame through GĐ2: spec → code → C1 → rules. frame: {"job_id", "path", "data", "label"?}. Returns the verdict and every
    piece of evidence (assertions, code results, answers)."""
    from . import qc_measure, qc_rules, qc_spec
    spec = qc_spec.compile_frame(p.conn, pid, frame["job_id"], frame["data"], profiles=profiles)
    code = qc_measure.measure_frame(frame["path"], frame["data"], spec["assertions"])
    from . import palette                    # S14.48 (cờ palette_check): màu chính nhân vật đo bằng code — ghi chú, không quyết
    palette.attach(code, p.conn, pid, frame["path"], frame["data"])
    # an assertion of a role not running yet still counts when the code alone is certain (GĐ3 01/10: #8 job 325 — the code measured a
    # certain wrong gaze, the frame passed because gaze belongs to C2)
    mine = [a for a in spec["assertions"] if a["role"] in roles or a["role"] == "T0"
            or (code.get(a["id"]) or {}).get("status") in ("certain_ok", "certain_fail")]
    ask = [a for a in mine if a["role"] in roles and (code.get(a["id"]) or {}).get("status") != "certain_ok"]
    answers: Dict = {}
    other, problems, usage = [], [], {}
    if ask:
        if entity is None:
            names = sorted({str(c).upper() for c in frame["data"].get("characters") or []})
            views = sorted({a["view"] for a in mine if a.get("view")})
            d = frame["data"]
            entity = entity_blocks(p, pid, names, views, [frame["job_id"]], data_dir,
                                   [f"S{d.get('story_scene')}·{d.get('shot_no')}"])
        msgs = c1_request(frame, ask, code, entity)
        reply = client.ask_json(msgs, C1_SYSTEM, ANSWER_SCHEMA, C1_MAX_TOKENS_BASE + C1_TOKENS_PER_ASSERTION * len(ask),
                                thinking={"type": "disabled"})
        parsed = parse_answers(reply.text, ask)
        answers, other, problems = parsed["answers"], parsed["other_issues"], parsed["problems"]
        usage = {"input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens, "cache_read_tokens": reply.cache_read_tokens,
                 "cache_write_tokens": reply.cache_write_tokens}
    verdict = qc_rules.frame_verdict(mine, answers, code)
    return {"job_id": frame["job_id"], "verdict": verdict["verdict"], "arbiter": verdict["arbiter"], "fails": verdict["fails"],
            "plan_conflicts": spec["plan_conflicts"], "missing_profiles": spec["missing_profiles"], "other_issues": other,
            "problems": problems, "usage": usage, "asked": [a["id"] for a in ask],
            "code": {k: v for k, v in code.items() if not k.startswith("_")},
            "palette": code.get("_palette")}          # S14.48: kept apart — the "_" keys above are dropped


def estimate_usd(n_frames: int, assertions_per_frame: int = 12, model_in: float = 2.0, model_out: float = 10.0) -> float:
    """Mục 16 for C1 alone: ≈ 4 000 new input tokens + 10 000 cache reads + (300 + 110 / assertion) output per frame (no thinking)."""
    per = (4000 * model_in + 10000 * model_in * 0.1 + (C1_MAX_TOKENS_BASE + C1_TOKENS_PER_ASSERTION * assertions_per_frame) * model_out) / 1e6
    return round(per * n_frames, 4)


# ---- in the pipeline (cờ qc_team): layer 1 of the per-scene QC --------------------------------------------------------------------
FEATURE = "qc_team"
FRAME_USD = 0.03          # GĐ3 01/10 measured 0.019–0.020 USD / frame (C1); + the same-side picture of people seen from behind


def enabled() -> bool:
    from . import features
    return features.on(FEATURE)


def note_of(res: Dict) -> str:
    """One line for the person at the storyboard gate."""
    parts = [f"Tổ QC (thử, chưa nghiệm thu): {res['verdict']}"]
    if res["fails"]:
        parts.append("; ".join(f"{f['claim_vi']} — {f['why']}" for f in res["fails"])[:420])
    side = [a for a in res.get("arbiter") or [] if "#asym:" in a]
    if side:
        parts.append(f"trái/phải cần người xem ({len(side)})")
    if res.get("plan_conflicts"):
        parts.append("bảng shot tự mâu thuẫn: " + "; ".join(res["plan_conflicts"]))
    from . import palette
    colour = palette.note(res)                # S14.48: only when a colour may be off
    if colour:
        parts.append(colour)
    return " · ".join(parts)[:600]


def review_scene(p, pid: int, story_scene, client, data_dir: str, frames: List[Dict], focus: Optional[List[int]] = None) -> Dict:
    """Run C1 + the code layer on the scene's frames to look at (`focus` = job ids; None = all). Not trusted yet: every frame is held
    for the person with the verdict as a note — nothing is approved or redrawn on its own. Results kept in qc_scene/team.json.
    {"applied": {Kk: text}, "results": {job: result}} or {"stopped": reason, "blocked": bool} when the money lock / Claude says no."""
    from . import llm_runner, project_budget, qc_scene, qc_spec
    if not hasattr(client, "ask_json"):
        return {"stopped": "Claude chưa sẵn sàng cho trả lời có cấu trúc (LLM_PROVIDER=anthropic)", "blocked": True}
    todo = [r for r in frames if focus is None or r["job_id"] in focus]
    from . import money_policy             # S14.16: the project's QC amount only warns — the frames are still looked at
    money_policy.note(p.conn, project_budget.warning(p.conn, pid, "claude_qc", FRAME_USD * len(todo)), stage="qc", project_id=pid,
                      key=f"qc_team:{pid}")
    names = sorted({str(c).upper() for r in frames for c in r["data"].get("characters") or []})
    views = sorted({qc_spec.view_of(r["data"], n) or "" for r in frames for n in r["data"].get("characters") or []} - {""})
    shots = [f"S{r['data'].get('story_scene')}·{r['data'].get('shot_no')}" for r in frames]
    entity = entity_blocks(p, pid, names, views, [r["job_id"] for r in frames], data_dir, shots)
    applied, results = {}, {}
    from . import palette                  # S14.48 (cờ palette_check): khung cùng cảnh so màu với nhau (cùng ánh sáng) — ghi chú
    scene_colours = palette.scene_check([r for r in frames if os.path.exists(r["path"])]) if palette.on() else {}
    with llm_runner.tagged("qc_team", pid):
        for k, r in enumerate(frames, 1):
            if r not in todo:
                continue
            if p.job(r["job_id"])["state"] not in ("succeeded", "pending_review"):
                applied[f"K{k}"] = f"giữ nguyên ({p.job(r['job_id'])['state']})"
                continue
            frame = {"job_id": r["job_id"], "path": r["path"], "data": r["data"], "label": shots[k - 1]}
            try:
                res = review_frame(p, pid, data_dir, frame, client, entity=entity)
            except llm_runner.LlmError as e:
                if e.code in ("out_of_credit", "ledger", "auth", "config"):
                    return {"stopped": llm_runner.fail_text(e), "blocked": True, "applied": applied, "results": results}
                applied[f"K{k}"] = f"lỗi Claude: {e}"
                continue
            if scene_colours.get(r["job_id"]):
                res["palette_scene"] = scene_colours[r["job_id"]]
            results[r["job_id"]] = res
            qc_scene._hold(p, r["job_id"], note_of(res))
            applied[f"K{k}"] = f"giữ cho người ({res['verdict']})"
    store = qc_scene._load(data_dir, pid, "team.json")
    for job, res in results.items():
        store[str(job)] = res
    qc_scene._save(data_dir, pid, "team.json", store)
    return {"applied": applied, "results": {str(k): v["verdict"] for k, v in results.items()}}
