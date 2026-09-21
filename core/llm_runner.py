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

from . import diag, knowledge, llm_io, prompts
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


@_diagnosed("director", lambda p, i: i)
def run_director(p: Pipeline, project_id: int, client) -> Dict:
    obj, tin, tout = ask_json(client, prompts.build_director_bundle(p, project_id), llm_io.validate_scene_analysis,
                              note=_retry_note(p, "director", project_id))
    llm_io.store_scene_analysis(p, project_id, obj)
    return {"characters": len(obj["characters"]), "scenes": len(obj["scenes"]), "input_tokens": tin,
            "output_tokens": tout, "ip_risk_notes": obj.get("ip_risk_notes") or []}


def image_path(data_dir: str, project_id: int, job_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "images", f"job_{job_id}.png")


@_diagnosed("qc", lambda p, i: p.job(i)["project_id"])
def run_qc(p: Pipeline, job_id: int, client, data_dir: str) -> Dict:
    job = p.job(job_id)
    path = image_path(data_dir, job["project_id"], job_id)
    if not os.path.exists(path):
        raise LlmError("this job has no image file to check", code="no_image")
    criteria = prompts.qc_criteria()
    obj, tin, tout = ask_json(client, prompts.build_qc_bundle(p, job["scene_id"]),
                              lambda o: llm_io.validate_qc_result(o, criteria), [("Ảnh cần chấm điểm:", path)],
                              note=_retry_note(p, "qc", job["project_id"]))
    issues = "; ".join(str(i) for i in (obj.get("issues") or [])[:5]) or None
    decision = p.apply_qc(job_id, obj["criteria"], issues=issues)
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
def run_motion(p: Pipeline, project_id: int, client, data_dir: str) -> Dict:
    """Motion prompts for approved-image scenes that do not have one yet (existing/approved prompts are kept)."""
    rows = p.conn.execute(
        "SELECT s.idx, (SELECT j.id FROM jobs j WHERE j.scene_id=s.id AND j.type='image_gen' AND j.state='approved'"
        " ORDER BY j.id DESC LIMIT 1) AS jid FROM scenes s WHERE s.project_id=? AND NOT EXISTS"
        " (SELECT 1 FROM motion_prompts m WHERE m.scene_id=s.id) ORDER BY s.idx", (project_id,)).fetchall()
    todo = [r for r in rows if r["jid"]]
    if not todo:
        return {"scenes": 0, "input_tokens": 0, "output_tokens": 0}
    images = [(f"Ảnh cảnh {r['idx']}:", image_path(data_dir, project_id, r["jid"])) for r in todo
              if os.path.exists(image_path(data_dir, project_id, r["jid"]))]
    obj, tin, tout = ask_json(client, prompts.build_motion_bundle(p, project_id, only_missing=True),
                              llm_io.validate_motion_prompts, images, note=_retry_note(p, "motion", project_id))
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
        if "# Cảnh đã có ảnh được duyệt" in prompt:
            block = re.search(r"# Cảnh đã có ảnh được duyệt\s*```json\s*(.*?)```", prompt, re.S).group(1)
            scenes = json.loads(block)["scenes"]
            out = {"scenes": [{"idx": s["idx"], "motion_prompt": f"Slow push-in on the subject, scene {s['idx']}",
                               "camera": "push-in", "duration_sec": 5, "negative_prompt": ""} for s in scenes]}
        elif "Đính kèm ảnh cần chấm điểm" in prompt:
            out = {"criteria": {k: 0.9 for k in prompts.qc_criteria()}, "issues": []}
        else:
            idxs = sorted({int(n) for n in re.findall(r"### Cảnh (\d+)", prompt)}) or [1]
            out = {"characters": [{"name": "Nhân vật chính", "description": "mô tả mẫu (giả lập)"}],
                   "scenes": [{"idx": i, "location": "Bối cảnh mẫu", "time": "Ngày", "characters": ["Nhân vật chính"],
                               "mood": "trung tính", "lighting": "tự nhiên", "shot": "medium",
                               "image_prompt": f"scene {i}, cinematic still"} for i in idxs],
                   "ip_risk_notes": []}
        return LlmReply("```json\n" + json.dumps(out, ensure_ascii=False) + "\n```", 100, 50)


def client_from_env(transport: Transport = urllib_transport):
    """LLM_PROVIDER = anthropic | mock. Unset: anthropic when ANTHROPIC_API_KEY exists, else None."""
    kind = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if kind == "mock":
        return MockLlm()
    if kind == "anthropic" or (not kind and os.environ.get("ANTHROPIC_API_KEY", "").strip()):
        return AnthropicClient.from_env(transport)
    return None
