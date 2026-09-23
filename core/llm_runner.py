"""LLM runner (V1): call Claude through the Anthropic Messages API instead of pasting JSON by hand.

It sends the very same prompt bundles used in V0 (core/prompts.py) and feeds the JSON reply through the same
validators/persistence (core/llm_io.py), so a pasted answer and an API answer are interchangeable.

- Key: ANTHROPIC_API_KEY from the environment (never stored in the repo, never in error messages).
- Model: ANTHROPIC_MODEL (default claude-sonnet-5, needs image input for QC / motion).
- LLM_PROVIDER=mock uses a deterministic offline stand-in (demos, tests, no key, no cost).
- Invalid JSON is retried once with the validation error attached; failures are reported, not hidden.
"""
import base64
import functools
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import assets, diag, knowledge, llm_io, prompts
from .adapters.http import HttpResponse, Transport, clean_token, urllib_transport
from .pipeline import Pipeline

DEFAULT_BASE = "https://api.anthropic.com"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGES = 12


class LlmError(Exception):
    """Failure calling the LLM. Never contains the API key."""

    def __init__(self, message: str, code: Optional[str] = None, transient: bool = False):
        super().__init__(message)
        self.code = code
        self.transient = transient


@dataclass
class LlmReply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


def _media_type(content: bytes) -> str:
    if content[:3] == bytes([0xFF, 0xD8, 0xFF]):
        return "image/jpeg"
    if content[:4] == bytes([0x89]) + b"PNG":
        return "image/png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    raise LlmError("unsupported image format (need JPEG, PNG or WebP)", code="bad_image")


class AnthropicClient:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE,
                 transport: Transport = urllib_transport, max_tokens: int = 8000,
                 sleep: Callable[[float], None] = time.sleep, retries: int = 2):
        self._key = api_key
        self.model = model
        self.base = base_url.rstrip("/")
        self.transport = transport
        self.max_tokens = max_tokens
        self._sleep = sleep
        self.retries = retries

    @classmethod
    def from_env(cls, transport: Transport = urllib_transport) -> "AnthropicClient":
        key = clean_token(os.environ.get("ANTHROPIC_API_KEY", ""))
        if not key:
            raise LlmError("ANTHROPIC_API_KEY is not set (ask your admin for a Console API key; set it as an "
                           "environment variable, never commit it).", code="config")
        return cls(key, os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL,
                   os.environ.get("ANTHROPIC_API_BASE", DEFAULT_BASE).strip() or DEFAULT_BASE, transport)

    def _content(self, prompt: str, images: Sequence[Tuple[str, str]]) -> List[Dict]:
        blocks: List[Dict] = []
        for label, path in list(images)[:MAX_IMAGES]:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError as e:
                raise LlmError(f"cannot read image {label}: {e.strerror}", code="bad_image") from None
            if len(data) > MAX_IMAGE_BYTES:
                raise LlmError(f"image {label} is over 5 MB", code="bad_image")
            blocks.append({"type": "text", "text": label})
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": _media_type(data),
                                                       "data": base64.b64encode(data).decode("ascii")}})
        blocks.append({"type": "text", "text": prompt})
        return blocks

    def complete(self, prompt: str, images: Sequence[Tuple[str, str]] = ()) -> LlmReply:
        return self._request(prompt, images, None)

    def complete_with_search(self, prompt: str, max_uses: int = 3) -> LlmReply:
        """Like complete, with the Anthropic web search tool (a few searches, costs extra). Not verified against the live API."""
        return self._request(prompt, (), [{"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}])

    def _request(self, prompt: str, images: Sequence[Tuple[str, str]], tools) -> LlmReply:
        payload = {"model": self.model, "max_tokens": self.max_tokens,
                   "messages": [{"role": "user", "content": self._content(prompt, images)}]}
        if tools:
            payload["tools"] = tools
        body = json.dumps(payload).encode("utf-8")
        headers = {"x-api-key": self._key, "anthropic-version": API_VERSION, "content-type": "application/json",
                   "User-Agent": "AIVideoPipeline-LLM/0.1"}
        last: Optional[LlmError] = None
        for attempt in range(self.retries + 1):
            try:
                return self._parse(self.transport("POST", self.base + "/v1/messages", headers, body, 180))
            except LlmError as e:
                last = e
                if not e.transient or attempt == self.retries:
                    raise
                self._sleep(2 ** attempt * 2)
        raise last  # pragma: no cover

    @staticmethod
    def _parse(resp: HttpResponse) -> LlmReply:
        try:
            payload = json.loads(resp.body.decode("utf-8"))
        except ValueError:
            payload = {}
        message = ((payload.get("error") or {}).get("message") if isinstance(payload, dict) else None) or ""
        if resp.status == 401 or resp.status == 403:
            raise LlmError("Anthropic rejected the API key (HTTP %d)" % resp.status, code="auth")
        if resp.status == 429 or resp.status >= 500:
            raise LlmError(f"Anthropic temporarily unavailable (HTTP {resp.status}) {message}".strip(),
                           code="rate_limit" if resp.status == 429 else "server_error", transient=True)
        if resp.status >= 400:
            raise LlmError(f"Anthropic error HTTP {resp.status}: {message[:300]}", code="http_error")
        text = "".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
        usage = payload.get("usage") or {}
        return LlmReply(text, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))


# ---- JSON extraction + validated call ------------------------------------------------
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S | re.I)


def extract_json(text: str) -> Any:
    """Parse the JSON object in a model reply (handles ```json fences and chatter around it)."""
    candidates = [m.group(1) for m in _FENCE.finditer(text)] + [text]
    for candidate in candidates:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start:end + 1])
            except ValueError:
                continue
    raise ValueError("no valid JSON object found in the reply")


def ask_json(client, prompt: str, validate: Callable[[Any], Any], images: Sequence[Tuple[str, str]] = (),
             note: Optional[Callable[[str], None]] = None):
    """Ask, parse, validate; on a bad answer retry once telling the model what was wrong.
    Returns (validated object, total input tokens, total output tokens)."""
    tin = tout = 0
    error = ""
    for attempt in range(2):
        text = prompt if not error else (
            prompt + f"\n\n---\n\nCâu trả lời trước không hợp lệ ({error}). Trả lại **một JSON hợp lệ duy nhất**, "
                     "đúng định dạng yêu cầu, không thêm chữ nào khác.")
        reply = client.complete(text, images)
        tin, tout = tin + reply.input_tokens, tout + reply.output_tokens
        try:
            obj = extract_json(reply.text)
            validate(obj)
            return obj, tin, tout
        except (ValueError, llm_io.SchemaError) as e:
            error = str(e)[:300]
            if note is not None and attempt == 0:
                note(f"câu trả lời lần 1 không hợp lệ, đã hỏi lại: {error}")   # a silent retry that costs tokens
    raise LlmError(f"the model did not return valid JSON twice: {error}", code="bad_json")


def ask_text(client, prompt: str, validate: Callable[[str], str]):
    """Like ask_json but for plain text (Markdown): validate returns the cleaned text or raises ValueError.
    One retry that tells the model what was wrong. Returns (text, input tokens, output tokens)."""
    tin = tout = 0
    error = ""
    for attempt in range(2):
        text = prompt if not error else (prompt + f"\n\n---\n\nBản trước không đạt ({error}). Viết lại đúng yêu cầu, "
                                                   "chỉ trả về nội dung cẩm nang.")
        reply = client.complete(text)
        tin, tout = tin + reply.input_tokens, tout + reply.output_tokens
        try:
            return validate(reply.text), tin, tout
        except ValueError as e:
            error = str(e)[:300]
    raise LlmError(f"the model did not return a usable playbook twice: {error}", code="bad_text")


def run_distill(group: str, client, include_builtin: bool = False) -> Dict:
    """Read every document of a step once and store a short, sectioned playbook that the step then uses instead of
    the raw documents."""
    bundle = knowledge.build_distill_bundle(group, include_builtin)
    text, tin, tout = ask_text(client, bundle, lambda t: knowledge.validate_distilled(group, t))
    record = knowledge.store_distilled(group, text, include_builtin, use=True)
    return {"chars": len(record["text"]), "source_chars": record["source_chars"], "input_tokens": tin,
            "output_tokens": tout}


# ---- the three Claude steps -------------------------------------------------------------
def _diagnosed(stage: str, project_of: Callable):
    """Report every LlmError of a step to the diagnostics log, then raise it unchanged."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(p, ident, *a, **k):
            try:
                return fn(p, ident, *a, **k)
            except LlmError as e:
                diag.record(p.conn, stage, "warn" if e.transient else "error", str(e), e.code, project_of(p, ident))
                raise
        return wrapper
    return deco


def _retry_note(p: Pipeline, stage: str, project_id: int):
    return lambda message: diag.record(p.conn, stage, "warn", message, "bad_json_retry", project_id)


def _director_references(conn, project_id: int) -> List[Tuple[str, str]]:
    """One picture per character/pet resource already attached to the project, so the Director writes the
    Character Bible from the real design instead of inventing a plausible-sounding but wrong appearance (wrong
    hair colour/style, missing accessories) that QC then has to unlearn one retry at a time, unevenly across
    scenes (found by comparing a rejected job's `retry_reason` history against the resource's own reference
    picture: the first attempt repeated the invented text almost verbatim)."""
    out = []
    for a in assets.project_assets(conn, project_id):
        if a["kind"] in ("character", "pet") and a["images"]:
            out.append((f"Ảnh tham chiếu — {a['name']}:", assets.thumbnail(assets.best_reference(a)["path"], 900)))
    return out


@_diagnosed("director", lambda p, i: i)
def run_director(p: Pipeline, project_id: int, client) -> Dict:
    obj, tin, tout = ask_json(client, prompts.build_director_bundle(p, project_id), llm_io.validate_scene_analysis,
                              _director_references(p.conn, project_id), note=_retry_note(p, "director", project_id))
    llm_io.store_scene_analysis(p, project_id, obj)
    return {"characters": len(obj["characters"]), "scenes": len(obj["scenes"]), "input_tokens": tin,
            "output_tokens": tout, "ip_risk_notes": obj.get("ip_risk_notes") or []}


def image_path(data_dir: str, project_id: int, job_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "images", f"job_{job_id}.png")


@_diagnosed("qc", lambda p, i: p.job(i)["project_id"])
def run_qc(p: Pipeline, job_id: int, client, data_dir: str, autofix: bool = False) -> Dict:
    """Score one generated picture against the scene spec AND the chosen resources' reference pictures. autofix: a faulty picture is
    regenerated automatically (up to the project's max_retry_count) instead of waiting for the person."""
    job = p.job(job_id)
    path = image_path(data_dir, job["project_id"], job_id)
    if not os.path.exists(path):
        raise LlmError("this job has no image file to check", code="no_image")
    criteria = prompts.qc_criteria()
    row = p.conn.execute("SELECT idx, data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()
    refs = prompts.qc_references(p, job["project_id"], row["idx"], json.loads(row["data"] or "{}"), data_dir)
    images = [("Ảnh cần chấm điểm:", path)] + [(f"Ảnh tham chiếu {i} — {r['label']}:", assets.thumbnail(r["path"], 900)) for i, r in enumerate(refs, 1)]
    obj, tin, tout = ask_json(client, prompts.build_qc_bundle(p, job["scene_id"], data_dir),
                              lambda o: llm_io.validate_qc_result(o, criteria), images,
                              note=_retry_note(p, "qc", job["project_id"]))
    issues = "; ".join(str(i) for i in (obj.get("issues") or [])[:5]) or None
    decision = p.apply_qc(job_id, obj["criteria"], issues=issues, autofix=autofix)
    return {"decision": decision, "input_tokens": tin, "output_tokens": tout, "issues": issues}


def run_qc_batch(p: Pipeline, project_id: int, client, data_dir: str) -> Dict:
    """QC every generated image that has not been scored yet (state 'succeeded')."""
    jobs = p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'"
                          " ORDER BY id", (project_id,)).fetchall()
    summary: Dict[str, Any] = {"checked": 0, "failed": [], "decisions": {}, "input_tokens": 0, "output_tokens": 0}
    for j in jobs:
        try:
            r = run_qc(p, j["id"], client, data_dir)
        except LlmError as e:
            summary["failed"].append((j["id"], str(e)))
            if e.code in ("auth", "config"):
                break
            continue
        summary["checked"] += 1
        summary["decisions"][r["decision"]] = summary["decisions"].get(r["decision"], 0) + 1
        summary["input_tokens"] += r["input_tokens"]
        summary["output_tokens"] += r["output_tokens"]
    return summary


@_diagnosed("motion", lambda p, i: i)
def run_motion(p: Pipeline, project_id: int, client, data_dir: str, only_idx=None) -> Dict:
    """Motion prompts for approved-image scenes that do not have one yet (existing/approved prompts are kept).
    only_idx: rewrite exactly these scenes (e.g. the ones whose prompt is outdated because the image or the scene changed)."""
    from . import shots
    rows = [dict(r) for r in p.conn.execute(
        "SELECT s.id, s.idx, EXISTS (SELECT 1 FROM motion_prompts m WHERE m.scene_id=s.id) AS has_mp"
        " FROM scenes s WHERE s.project_id=? ORDER BY s.idx", (project_id,)).fetchall()]
    for r in rows:                     # v3 multi-shot: a later shot of a group works from the group's first picture
        j = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                           (shots.image_scene(p.conn, r["id"]),)).fetchone()
        r["jid"] = j["id"] if j else None
    if only_idx is not None:
        todo = [r for r in rows if r["jid"] and r["idx"] in set(only_idx)]
    else:
        todo = [r for r in rows if r["jid"] and not r["has_mp"]]
    if not todo:
        return {"scenes": 0, "input_tokens": 0, "output_tokens": 0}
    images = [(f"Ảnh cảnh {r['idx']}:", image_path(data_dir, project_id, r["jid"])) for r in todo
              if os.path.exists(image_path(data_dir, project_id, r["jid"]))]
    bundle = (prompts.build_motion_bundle(p, project_id, only_idx={r["idx"] for r in todo}) if only_idx is not None
              else prompts.build_motion_bundle(p, project_id, only_missing=True))
    obj, tin, tout = ask_json(client, bundle, llm_io.validate_motion_prompts, images, note=_retry_note(p, "motion", project_id))
    wanted = {r["idx"] for r in todo}
    obj["scenes"] = [s for s in obj["scenes"] if s["idx"] in wanted]
    llm_io.store_motion_prompts(p, project_id, obj)
    return {"scenes": len(obj["scenes"]), "input_tokens": tin, "output_tokens": tout}


# ---- offline stand-in ---------------------------------------------------------------------
class MockLlm:
    """Deterministic fake model: valid JSON for each step without any API call."""
    name = "mock-llm"

    def complete_with_search(self, prompt: str, max_uses: int = 3) -> LlmReply:
        topic = prompt.split("về: ", 1)[-1][:40].strip()
        out = {"findings": [{"title": f"Mẹo mới (giả lập): {topic}", "rule": "Quy tắc mẫu từ nghiên cứu giả lập.",
                             "url": "https://example.com/guide"}]}
        return LlmReply("```json\n" + json.dumps(out, ensure_ascii=False) + "\n```", 100, 50)

    def complete(self, prompt: str, images: Sequence[Tuple[str, str]] = ()) -> LlmReply:
        v2 = self._v2(prompt)
        if v2 is not None:
            return LlmReply("```json\n" + json.dumps(v2, ensure_ascii=False) + "\n```", 90, 50)
        if prompt.startswith("# Phân tích ảnh nền (previz 2D)"):
            out = {"camera": "eye", "horizon_y": 0.4, "camera_height_m": 1.7, "ground": [[0, 0.55], [1, 0.55], [1, 1], [0, 1]],
                   "landmarks": [], "light": "nắng trưa (giả lập)", "notes": "bối cảnh giả lập"}
            return LlmReply(json.dumps(out, ensure_ascii=False), 80, 40)
        if prompt.startswith("# Dựng layout từng shot (previz 2D)"):
            specs = json.loads(prompt.split("# Các cảnh\n", 1)[1])
            shots = [{"idx": s["idx"], "background": s["backgrounds"][0], "redraw": False, "redraw_note": "",
                      "people": [{"name": n, "foot": [round((i + 1) / (len(s["characters"]) + 1), 3), 0.85],
                                  "facing": "right" if i % 2 == 0 else "left", "pose": ""} for i, n in enumerate(s["characters"])]}
                     for s in specs]
            return LlmReply(json.dumps({"shots": shots}, ensure_ascii=False), 120, 80)
        if prompt.startswith("# Rà storyboard (previz 2D)"):
            return LlmReply(json.dumps({"ok": True, "issues": []}), 60, 10)
        if "Dịch phụ đề cho video game" in prompt:
            lang = re.search(r"sang (.+?)\. Giữ nguyên", prompt).group(1)
            block = prompt.split("# Phụ đề cần dịch", 1)[1]
            cues = json.loads(re.search(r"```json\s*(.*?)```", block, re.S).group(1))
            out = {"cues": [{"id": c["id"], "text": f"[{lang}] {c['text']}"} for c in cues]}
            return LlmReply("```json\n" + json.dumps(out, ensure_ascii=False) + "\n```", 60, 40)
        if "Chuyên viên sound design" in prompt:
            scenes = json.loads(re.search(r"# Các cảnh.*?```json\s*(.*?)```", prompt, re.S).group(1))
            sounds = json.loads(re.search(r"# Hiệu ứng có sẵn\s*```json\s*(.*?)```", prompt, re.S).group(1))
            cues = [{"at": s["start"], "scene": s["scene"], "id": sounds[i % len(sounds)]["id"], "volume": 0.8,
                     "reason": f"điểm chuyển sang cảnh {s['scene']} (giả lập)"} for i, s in enumerate(scenes[1:] or scenes)]
            out = {"summary": "Đặt hiệu ứng ở các điểm chuyển cảnh (giả lập).", "cues": cues}
            return LlmReply("```json\n" + json.dumps(out, ensure_ascii=False) + "\n```", 90, 60)
        if "Chuyên gia phong cách hình ảnh" in prompt:
            out = {"render_style": "Hoạt hình 3D mềm (giả lập): không viền, chuyển sắc liên tục",
                   "palette": "Tím lam chủ đạo, vàng ấm điểm nhấn ở nguồn sáng; no bloom, no oversaturation",
                   "texture_finish": "Hạt phim rất nhẹ, tương phản vừa, chất ống kính thật", "lighting_logic": None,
                   "candidate_elements": [{"label": "Bụi mịn", "prose": "a fine haze of dust catching light",
                                           "evidence": "ảnh 1", "density_hint": "nhạt"}],
                   "evidence_notes": ["bản nháp giả lập"], "confidence": "medium", "check_flags": [],
                   "plain_note": "Tông chung giả lập cho thử nghiệm."}
            return LlmReply("```json\n" + json.dumps(out, ensure_ascii=False) + "\n```", 80, 60)
        if "Biên tập viên bài học" in prompt:
            return LlmReply("Quy tắc mẫu (giả lập): kiểm tra kỹ lỗi này khi viết prompt và chấm ảnh.", 50, 20)
        if "Biên tập viên kiến thức" in prompt:
            block = prompt.split("# Mục bắt buộc", 1)[1].split("# Độ dài mục tiêu", 1)[0]
            names = re.findall(r"^\d+\. (.+)$", block, flags=re.M)
            body = "\n\n".join(f"## {n}\n- (tóm tắt giả lập) quy tắc chính về {n.lower()}" for n in names)
            return LlmReply(body, 200, 80)
        if "NGUỒN THẬT DUY NHẤT" in prompt:
            body = ("### Nhận dạng nhân vật\n- Trang phục và vũ khí như thấy trong khung hình (giả lập). [OBSERVED]\n\n"
                    "### Kỹ năng / hiệu ứng đang dùng (nếu khung hình cho thấy)\n"
                    "- Hiệu ứng hình học/màu như thấy trong khung hình (giả lập). [OBSERVED]\n\n"
                    "### Không xác nhận được\n- Sát thương, thời gian hồi, tầm (giả lập). [UNKNOWN]")
            return LlmReply(body, 150, 60)
        if "# Cảnh đã có ảnh được duyệt" in prompt:
            block = re.search(r"# Cảnh đã có ảnh được duyệt\s*```json\s*(.*?)```", prompt, re.S).group(1)
            scenes = json.loads(block)["scenes"]
            out = {"scenes": [{"idx": s["idx"], "motion_prompt": f"Slow push-in on the subject, scene {s['idx']}",
                               "camera": "push-in", "duration_sec": max(5, int(s.get("duration_s") or 5)), "negative_prompt": "",
                               "spatial_state": f"everyone holds position at the end of scene {s['idx']} (mock)",
                               "check_flags": []} for s in scenes]}
        elif "Đính kèm ảnh cần chấm điểm" in prompt:
            out = {"criteria": {k: 0.9 for k in prompts.qc_criteria()}, "issues": []}
        else:
            from . import dialogue as _dlg
            blocks = re.split(r"^### Cảnh (\d+)[^\n]*$", prompt.split("# Kịch bản đã tách cảnh", 1)[-1], flags=re.M)
            texts = {int(blocks[i]): blocks[i + 1] for i in range(1, len(blocks) - 1, 2)}
            idxs = sorted(texts) or [1]
            lines = {i: _dlg.lines(texts.get(i, "")) for i in idxs}
            names = sorted({who for rows in lines.values() for who, _ in rows}) or ["Nhân vật chính"]
            out = {"genre": "SHORT_FORM",
                   "characters": [{"name": n, "description": f"mô tả mẫu của {n} (giả lập)",
                                   "lock": {"must_keep": "same face, hair and outfit colours (mock)", "may_change": "pose, expression",
                                            "forbidden": "outfit swapped with others (mock)"}} for n in names],
                   "scenes": [{"idx": i, "location": "Bối cảnh mẫu", "time": "Ngày",
                               "characters": sorted({w for w, _ in lines[i]}) or names[:1],
                               "mood": "trung tính", "lighting": "tự nhiên", "shot": "medium",
                               "image_prompt": f"scene {i}, cinematic still", "emotional_intent": "người xem tò mò (giả lập)",
                               "beat": {"want": "đi tiếp", "obstacle": "trời tối", "turn": "quyết định lên đường"},
                               "camera_complexity": "complex" if i % 3 == 0 else "simple",
                               "shot_role": "hero" if i == idxs[-1] else "normal",
                               "dialogue": [{"speaker": w, "text": t} for w, t in lines[i]], "duration_s": 5} for i in idxs],
                   "ip_risk_notes": []}
            if "# Phân shot (dự án chia shot" in prompt:        # v3: split every scene into shots (core.shots)
                for sc in out["scenes"]:
                    sc["shots"] = _mock_shots(sc, first=sc["idx"] == idxs[0], last=sc["idx"] == idxs[-1])
        return LlmReply("```json\n" + json.dumps(out, ensure_ascii=False) + "\n```", 100, 50)


def _mock_shots(scene: Dict, first: bool, last: bool) -> List[Dict]:
    """Offline stand-in for the Director's shot split: a wide setup shot, one medium close-up per spoken line (sized to the
    line), a reaction after every second line, an ending shot at the end of the film."""
    from . import dialogue as _dlg
    cast = scene["characters"]
    out = [{"size": "WS", "angle": "eye", "camera_move": "static", "role": "hook" if first else "setup", "duration_s": 1.5,
            "action": f"toàn cảnh {scene['location']} (giả lập)", "start_frame": "everyone in frame, wide (mock)",
            "image_prompt": f"wide shot of scene {scene['idx']}, all characters (mock)", "characters": cast}]
    for k, d in enumerate(scene["dialogue"], 1):
        need = _dlg.needed_seconds([(d["speaker"], d["text"])])
        out.append({"size": "MCU", "angle": "eye", "camera_move": "push_in" if k % 3 == 0 else "static", "role": "dialogue",
                    "duration_s": round(max(1.0, need + 0.2), 1), "action": f"{d['speaker']} nói (giả lập)",
                    "start_frame": f"{d['speaker']} centre frame (mock)", "image_prompt": f"medium close-up of {d['speaker']} speaking (mock)",
                    "characters": [d["speaker"]] if d["speaker"] in cast else cast[:1], "dialogue": [d]})
        if k % 2 == 0:
            other = [c for c in cast if c != d["speaker"]] or cast
            out.append({"size": "CU", "angle": "eye", "camera_move": "static", "role": "reaction", "duration_s": 1.0,
                        "action": f"{other[0]} phản ứng (giả lập)", "image_prompt": f"close-up reaction of {other[0]} (mock)",
                        "characters": other[:1]})
    if last:
        out.append({"size": "MS", "angle": "low", "camera_move": "push_in", "role": "ending", "duration_s": 2.0, "hero": True,
                    "action": "tạo dáng kết (giả lập)", "image_prompt": "final pose, low angle (mock)", "characters": cast})
    return out


def _mock_v2(prompt: str):
    """Answers of the offline stand-in for the v2 Claude tasks (core.claude_tasks); None for other prompts."""
    if prompt.startswith("# Rà thoại"):
        return {"summary": "Thoại ổn, một câu hơi văn viết (giả lập).", "lines": [], "split": []}
    if prompt.startswith("# Rà motion prompt"):
        idxs = [int(n) for n in re.findall(r'"idx":\s*(\d+)', prompt.split("# Motion prompt cần rà", 1)[-1])]
        return {"scenes": [{"idx": i, "ok": True, "issues": [], "revised_prompt": ""} for i in sorted(set(idxs))]}
    if prompt.startswith("# QC Agent — chấm clip video"):
        return {"criteria": {"identity": 0.9, "physics": 0.88, "motion_match": 0.9, "artifacts": 0.9}, "issues": ""}
    if prompt.startswith("# QC đồng bộ cả bộ ảnh"):
        return {"ok": True, "summary": "Các ảnh đồng bộ (giả lập).", "issues": []}
    if prompt.startswith("# Character Lock từ ảnh"):
        return {"must_keep": "same face, hair colour and outfit colour blocks (mock)", "may_change": "pose, expression, camera",
                "forbidden": "hair colour change, missing accessories (mock)"}
    if prompt.startswith("# Chọn giọng cho nhân vật"):
        chars = json.loads(re.search(r"# Nhân vật\s*```json\s*(.*?)```", prompt, re.S).group(1))
        voices = json.loads(re.search(r"# Giọng có sẵn\s*```json\s*(.*?)```", prompt, re.S).group(1))
        return {"cast": [{"name": c["name"], "voice_id": voices[i % len(voices)]["id"], "why": "giả lập",
                          "persona": "câu ngắn, thẳng (giả lập)"} for i, c in enumerate(chars)] if voices else []}
    if prompt.startswith("# Phân tích shot video tham khảo"):
        shots = json.loads(re.search(r"# Các shot\s*```json\s*(.*?)```", prompt, re.S).group(1))
        roles = ("hook", "setup", "action", "reaction", "insert", "action", "dialogue", "ending")
        sizes = ("WS", "MS", "CU", "GAME_TPS", "ECU", "MCU")
        return {"shots": [{"i": s["i"], "size": sizes[k % len(sizes)], "angle": "eye", "camera_move": "static",
                           "role": "hook" if k == 0 else "ending" if k == len(shots) - 1 else roles[k % len(roles)],
                           "subject": f"shot {s['i']} (giả lập)", "text_on_screen": k == 0, "game_ui": False, "vfx": k % 4 == 3,
                           "transition_in": "cut", "note": ""} for k, s in enumerate(shots)],
                "overall": {"style_guess": "INGAME", "structure": {"open": "mở bằng nhân vật + tiêu đề (giả lập)",
                                                                  "body": "gameplay xen chèn hiệu ứng (giả lập)",
                                                                  "close": "kết bằng câu kêu gọi (giả lập)"},
                            "look": "màu game tươi (giả lập)", "dialogue_handling": "", "notable": ["giả lập"]}}
    if prompt.startswith("# Director — Music Brief"):
        return {"genre": "cinematic", "tempo_bpm": 110, "mood": "căng rồi bùng nổ", "instruments": ["drums", "synth"],
                "instrumental": True, "duration_sec": 30, "structure": "0-10s dựng, 10-25s tăng, 25-30s chốt",
                "prompt": "Instrumental cinematic game trailer music (mock), building tension then a final hit."}
    return None


MockLlm._v2 = staticmethod(_mock_v2)


def client_from_env(transport: Transport = urllib_transport):
    """LLM_PROVIDER = anthropic | claude_cli (Claude Code on this PC, no key) | mock. Unset: anthropic when ANTHROPIC_API_KEY exists, else None."""
    kind = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if kind == "mock":
        return MockLlm()
    if kind in ("claude_cli", "claude-cli", "cli"):
        return ClaudeCliClient.from_env()
    if kind == "anthropic" or (not kind and os.environ.get("ANTHROPIC_API_KEY", "").strip()):
        return AnthropicClient.from_env(transport)
    return None


class ClaudeCliClient:
    """Uses the Claude Code installed on this PC (`claude -p`, logged in with the person's own account) instead of an API key.

    For trying the pipeline before an API key exists: it spends the plan's usage, runs one call at a time and is slower than the API.
    Images are handed over as files that Claude reads. Failures (not logged in, not installed, time-out) are reported, not hidden.
    """
    name = "claude-cli"

    @staticmethod
    def clean_env() -> Dict[str, str]:
        """The environment for `claude`: without the markers of a parent Claude session (desktop app / SDK). A dashboard started from inside another
        Claude session inherits them, and the CLI then believes it is a child that must borrow that session's login instead of using the
        person's own (`claude` logged in from a terminal)."""
        drop = ("CLAUDE_CODE", "CLAUDECODE", "CLAUDE_AGENT_SDK", "CLAUDE_PID", "CLAUDE_PREVIEW")
        return {k: v for k, v in os.environ.items() if not k.startswith(drop)}

    def __init__(self, model: str = "", timeout: int = 600, run=None):
        import subprocess
        self.model = model
        self.timeout = timeout
        self._run = run or subprocess.run

    @classmethod
    def from_env(cls) -> "ClaudeCliClient":
        import shutil
        if not shutil.which("claude"):
            raise LlmError("Không tìm thấy lệnh `claude` (Claude Code) trên máy này.", code="config")
        try:
            timeout = int(os.environ.get("CLAUDE_CLI_TIMEOUT", "600"))
        except ValueError:
            timeout = 600
        return cls(os.environ.get("CLAUDE_CLI_MODEL", "").strip(), timeout)

    def complete(self, prompt: str, images: Sequence[Tuple[str, str]] = ()) -> LlmReply:
        """One retry when Claude Code times out (a slow turn is common with several pictures); other errors are reported."""
        try:
            return self._complete_once(prompt, images)
        except LlmError as e:
            if e.code != "timeout":
                raise
            return self._complete_once(prompt, images)

    def _complete_once(self, prompt: str, images: Sequence[Tuple[str, str]] = ()) -> LlmReply:
        import shutil
        import subprocess
        import tempfile
        work = tempfile.mkdtemp(prefix="claude_cli_")
        try:
            args = [shutil.which("claude") or "claude", "-p", "--output-format", "json", "--no-session-persistence"]
            if self.model:
                args += ["--model", self.model]
            text = prompt
            if images:
                lines, folders = [], []
                for label, path in list(images)[:MAX_IMAGES]:
                    if not os.path.exists(path):
                        raise LlmError(f"cannot read image {label}", code="bad_image")
                    lines.append(f"- {label}: {os.path.abspath(path)}")
                    folder = os.path.dirname(os.path.abspath(path))
                    if folder not in folders:
                        folders.append(folder)
                text = ("Các ảnh đính kèm là file trên máy, hãy mở và xem từng ảnh (công cụ Read) trước khi trả lời:\n"
                        + "\n".join(lines) + "\n\n" + prompt)
                args += ["--allowedTools", "Read"]
                for folder in folders:
                    args += ["--add-dir", folder]
            try:
                proc = self._run(args, input=text, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=self.timeout, cwd=work,
                                 env=self.clean_env())
            except subprocess.TimeoutExpired:
                raise LlmError("Claude Code trả lời quá lâu (quá thời gian chờ).", code="timeout", transient=True)
            except OSError as e:
                raise LlmError(f"Không chạy được Claude Code: {e}", code="config")
            try:
                out = json.loads(proc.stdout or "{}")
            except ValueError:
                out = {}
            if proc.returncode != 0 or out.get("is_error") or "result" not in out:
                detail = str(out.get("result") or proc.stderr or proc.stdout or "")[:300].strip()
                hint = " Mở Claude Code (lệnh `claude`) một lần để đăng nhập lại rồi thử lại." if "authenticate" in detail.lower() or "oauth" in detail.lower() else ""
                raise LlmError(f"Claude Code báo lỗi: {detail}.{hint}", code="auth" if hint else "cli_error")
            usage = out.get("usage") or {}
            tokens_in = sum(int(usage.get(k, 0) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
            return LlmReply(str(out["result"]), tokens_in, int(usage.get("output_tokens", 0)))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def complete_with_search(self, prompt: str, max_uses: int = 3) -> LlmReply:
        raise LlmError("Nghiên cứu hàng tháng cần Claude API (tìm kiếm web); chế độ Claude Code trên máy chưa hỗ trợ.", code="config")
