"""LLM runner (V1): call Claude through the Anthropic Messages API instead of pasting JSON by hand.

It sends the very same prompt bundles used in V0 (core/prompts.py) and feeds the JSON reply through the same
validators/persistence (core/llm_io.py), so a pasted answer and an API answer are interchangeable.

- Key: ANTHROPIC_API_KEY from the environment (never stored in the repo, never in error messages).
- Model: ANTHROPIC_MODEL (default claude-sonnet-5, needs image input for QC / motion).
- LLM_PROVIDER=mock uses a deterministic offline stand-in (demos, tests, no key, no cost).
- Invalid JSON is retried once with the validation error attached; failures are reported, not hidden.
"""
from . import access
import base64
import contextlib
import functools
import io
import json
import os
import re
import sys
import threading
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
MAX_IMAGE_EDGE = 1568                 # Claude reads at most this long edge; bigger pictures are shrunk before sending
DEFAULT_MAX_TOKENS = 32000            # the Director's shot plan of a 26-shot script is ~10-20k tokens (8000 cut it off)
REQUEST_TIMEOUT = 900                 # a long answer takes minutes without streaming
MAX_IMAGES = 12
IMAGE_EDGE = int(os.environ.get("LLM_IMAGE_EDGE", "1024") or 1024)   # C3: long edge of pictures sent to Claude (token cost ~ w*h/750)
CACHE_BREAK = prompts.CACHE_BREAK      # C2: end of a prompt part that repeats between calls (written once, then read at 1/10 price)


def plain(prompt: str) -> str:
    """The prompt without cache marks (clients without caching, text shown to people)."""
    return prompt.replace(CACHE_BREAK, "\n\n---\n\n")


class LlmError(Exception):
    """Failure calling the LLM. Never contains the API key. `partial`: the text of a paid answer that was cut off (kept to see where
    the tokens went)."""

    def __init__(self, message: str, code: Optional[str] = None, transient: bool = False, partial: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.transient = transient
        self.partial = partial


class FailText(str):
    """The text of a failed Claude call that keeps LlmError.code. The `failed` lists of the QC batches are (id, text) pairs read as
    text everywhere; autopilot._stop_if_claude_blocked reads `.code` instead of guessing from words in the text (S14.3 B1b)."""
    code: Optional[str] = None


def fail_text(e: BaseException, text: Optional[str] = None) -> "FailText":
    out = FailText(str(e) if text is None else text)
    out.code = getattr(e, "code", None)
    return out


_CLI_LIMIT = ("hit your session limit", "hit your usage limit", "usage limit", "session limit", "rate limit")


def cli_error_code(detail: str) -> str:
    """The code of a Claude Code (CLI) failure, read once where the error is born: 'auth' (log in again), 'usage_limit' (the plan's
    limit reached — the automatic run stops until it resets), else 'cli_error'."""
    low = str(detail or "").lower()
    if "authenticate" in low or "oauth" in low:
        return "auth"
    if any(h in low for h in _CLI_LIMIT):
        return "usage_limit"
    return "cli_error"


# C4: how hard Claude thinks and how long it may answer, per stage (usage_events.stage). Thinking tokens count against max_tokens and
# are billed as output: the Director at the default effort ran out of 32k tokens on a 58-second per-shot script (2026-09-24).
# Override one stage with CLAUDE_EFFORT_<STAGE> / CLAUDE_MAX_TOKENS_<STAGE> (e.g. CLAUDE_EFFORT_DIRECTOR=high).
STAGE_SETTINGS: Dict[str, Dict[str, Any]] = {
    "director": {"effort": "medium", "max_tokens": 64000},     # shot plan of a whole script: long answer
    "motion": {"effort": "medium", "max_tokens": 48000},
    "translate": {"effort": "low", "max_tokens": 8000},        # the Director's Vietnamese fields → short English (28/09: the default
                                                              # ceiling made the call's worst case 0.33 USD and the motion cap refused it)
    "qc": {"effort": "low", "max_tokens": 16000},              # scoring against a checklist: short JSON
    "video": {"effort": "low", "max_tokens": 16000},
    "music": {"effort": "low"}, "sfx": {"effort": "low"}, "subtitles": {"effort": "low"}, "lessons": {"effort": "low"},
    "devsys": {"effort": "low", "max_tokens": 16000},        # AI Development System scorer: fixed rubric, JSON (no temperature on these models)
    "editor": {"effort": "low", "max_tokens": 12000},         # P2 (KE_HOACH_DUYET_BAN_THO): Biên tập viên / Đạo diễn duyệt bản thô — JSON ≤ 6 đề xuất;
                                                              # own entry so the 32k default never makes its worst case refuse on a locked project (B1 01/10)
    "screenwriter": {"effort": "medium", "max_tokens": 8000},   # S11.1 Biên kịch: one turn's JSON (a 60 s script ≈ 2-4k). 01/10 S11.2: the
                                                              # default 32k made turn 1's estimate 0.43 USD > the 0.3 USD per-idea cap
}
# 01/10 B1: a stage with no entry above used the client default (32k) → worst case ≈ 0.36 USD per call, over the whole "Claude — khác"
# line of a locked project (0.20): music / sfx / style / subtitles / layout / lessons / distill / research … were refused for ever.
# Every other named stage now answers at most this many tokens (one stage that needs more gets its own entry in STAGE_SETTINGS).
DEFAULT_STAGE_MAX_TOKENS = 8000
EFFORT_MODELS = ("claude-sonnet-5", "claude-opus-5", "claude-fable-5", "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6",
                 "claude-sonnet-4-6")                       # models that take output_config.effort (Haiku 4.5 refuses it)


def stage_settings(stage: str) -> Dict[str, Any]:
    out = dict(STAGE_SETTINGS.get(stage) or {})
    if stage and stage != "other" and "max_tokens" not in out:   # untagged calls (stage "other") have no project lock: client default
        out["max_tokens"] = DEFAULT_STAGE_MAX_TOKENS
    effort = os.environ.get(f"CLAUDE_EFFORT_{stage.upper()}", "").strip().lower()
    if effort in ("low", "medium", "high", "xhigh", "max"):
        out["effort"] = effort
    try:
        out["max_tokens"] = int(os.environ[f"CLAUDE_MAX_TOKENS_{stage.upper()}"])
    except (KeyError, ValueError):
        pass
    return out


@dataclass
class LlmReply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    web_searches: int = 0          # server-side web search requests (billed per search, not per token)
    blocks: Optional[list] = None  # the raw content blocks (tool use: core/qc_agent.py)


# ---- what each paid call is for (C1/C7): stage + project go into the cost ledger ----------------------------------------------
_TAG = threading.local()


@contextlib.contextmanager
def tagged(stage: str, project_id: Optional[int] = None):
    """Label the Claude calls made inside this block (this thread only): usage_events.stage / project_id. Nested blocks keep the
    outer project when they do not name one."""
    prev = getattr(_TAG, "value", None)
    _TAG.value = (stage, project_id if project_id is not None else (prev[1] if prev else None))
    try:
        yield
    finally:
        _TAG.value = prev


def current_tag() -> Tuple[str, Optional[int]]:
    return getattr(_TAG, "value", None) or ("other", None)


# ---- hard spending locks (trial #8 2026-09-28: the QC agent spent ~2 USD on 1.5 scenes — estimate was 0.3-0.8 — and emptied the
# Claude cap; nothing capped one task). Checked BEFORE each paid call; none of them can be raised by the model:
#   1. one call   : its worst case (every input token paid as a cache write, the whole max_tokens answer) over MAX_CALL_USD -> refused
#   2. one task   : spend_cap(usd, what) -> refused when spent + the next call's expected cost x TASK_MARGIN would pass the cap. The
#                   expected cost counts the prefix already sent as a cache read and the new part as a cache write, plus the whole
#                   max_tokens answer, never less than the last call. A cache miss can make one call dearer than expected: the cap can
#                   be passed by at most that one call's difference (the next estimate then starts from that dearer call).
#   3. the project: the Claude cap of core.budget and the project's approved budget for the stage (core.project_budget), with
#                   the WORST case of this call AND of every call in flight in ANY process (holds in the database) added —
#                   the caps are never crossed.
# A network error / timeout (the provider may have billed a call we never saw) counts the call's worst case on locks 2 (review
# 2026-09-28: before, a timeout went round every lock and the agent lost its records).
MAX_CALL_USD = float(os.environ.get("CLAUDE_MAX_CALL_USD") or 1.0)
TASK_MARGIN = 1.25
CHARS_PER_TOKEN = 1.5         # measured on the agent brief 28/09: Vietnamese ~1.9 characters a token — 1.5 stays above it
TOOL_USE_TOKENS = 400         # the tool-use system part the API adds when tools are sent
_CAPS = threading.local()


@contextlib.contextmanager
def spend_cap(usd: float, what: str):
    """Lock 2: Claude calls inside this block (this thread) may not spend more than `usd` in total."""
    stack = list(getattr(_CAPS, "stack", None) or [])
    entry = {"cap": float(usd), "spent": 0.0, "last": 0.0, "calls": 0, "what": what, "prev_tokens": 0}
    _CAPS.stack = stack + [entry]
    try:
        yield entry
    finally:
        _CAPS.stack = stack


def _price(model: str, tier: str, n: float) -> float:
    from . import budget, cost
    return budget.token_price(cost.load_pricing(), model, tier, n) or 0.0


def reply_usd(model: str, reply: "LlmReply") -> float:
    return sum(_price(model, t, n) for t, n in (("input", reply.input_tokens), ("output", reply.output_tokens),
                                                ("cache_write", reply.cache_write_tokens), ("cache_read", reply.cache_read_tokens),
                                                ("web_search", reply.web_searches)) if n)


def _image_tokens(block: Dict) -> int:
    try:
        from PIL import Image
        w, h = Image.open(io.BytesIO(base64.b64decode(block["source"]["data"]))).size
        return max(100, int(w * h / 750) + 1)
    except Exception:  # noqa: BLE001 - unreadable here: count the largest picture the API takes
        return 1600


def input_tokens(payload: Dict) -> int:
    """Upper count of the input tokens of a request: the whole JSON of system / messages / tools (keys included, picture data left
    out) at CHARS_PER_TOKEN, the pictures from their size, the tool-use part."""
    images = []

    def strip(x):
        if isinstance(x, dict):
            if x.get("type") == "image":
                images.append(x)
                return {"type": "image"}
            return {k: strip(v) for k, v in x.items() if k != "cache_control"}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return x
    text = json.dumps(strip({k: v for k, v in payload.items() if k in ("system", "messages", "tools")}), ensure_ascii=False)
    return int(len(text) / CHARS_PER_TOKEN) + sum(_image_tokens(b) for b in images) + (TOOL_USE_TOKENS if payload.get("tools") else 0)


def worst_usd(model: str, payload: Dict) -> float:
    """Upper bound of one call: every input token paid as a cache write (dearer than plain input) + the whole max_tokens answer."""
    n = input_tokens(payload)
    inp = max(_price(model, "cache_write", n), _price(model, "input", n) * 1.25)
    return inp + _price(model, "output", int(payload.get("max_tokens") or 0))


def expected_usd(model: str, payload: Dict, prev_tokens: int) -> float:
    """The next call of a conversation that grows (the agent): the part sent before read from the cache, the new part written."""
    n = input_tokens(payload)
    out = _price(model, "output", int(payload.get("max_tokens") or 0))
    if not prev_tokens or n < prev_tokens:           # first call, or the conversation was pruned: nothing cached
        return worst_usd(model, payload)
    cached, new = prev_tokens, n - prev_tokens
    return (_price(model, "cache_read", cached) + max(_price(model, "cache_write", new), _price(model, "input", new) * 1.25) + out)


def _check_caps(model: str, payload: Dict) -> Optional[str]:
    worst = worst_usd(model, payload)
    if worst > MAX_CALL_USD:
        return (f"một lời gọi Claude có thể tốn tới ≈ ${worst:.2f} > khóa ${MAX_CALL_USD:.2f}/lời gọi — không gửi (hạ max_tokens của "
                "khâu này, hoặc người dùng nâng CLAUDE_MAX_CALL_USD)")
    n = input_tokens(payload)
    for e in getattr(_CAPS, "stack", None) or []:
        nxt = max(e["last"], expected_usd(model, payload, e["prev_tokens"])) * TASK_MARGIN
        if e["spent"] + nxt > e["cap"] + 1e-9:
            return (f"chạm trần '{e['what']}': đã dùng ≈ ${e['spent']:.3f}, lượt kế ≈ ${nxt:.3f}, trần ${e['cap']:.2f} — dừng "
                    "(khóa cứng, không tự nâng)")
        e["_next_tokens"] = n
    return None


def _count_caps(usd: float) -> None:
    for e in getattr(_CAPS, "stack", None) or []:
        e["spent"] += usd
        e["last"] = max(usd, e["last"] * 0.5)
        e["calls"] += 1
        e["prev_tokens"] = e.pop("_next_tokens", e["prev_tokens"])


def _media_type(content: bytes) -> str:
    if content[:3] == bytes([0xFF, 0xD8, 0xFF]):
        return "image/jpeg"
    if content[:4] == bytes([0x89]) + b"PNG":
        return "image/png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    raise LlmError("unsupported image format (need JPEG, PNG or WebP)", code="bad_image")


def _fit(data: bytes, edge: int) -> bytes:
    """C3: a picture larger than `edge` on its long side as a JPEG of that size (unchanged when smaller or unreadable)."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        if max(img.size) <= edge:
            return data
        img = img.convert("RGB")
        img.thumbnail((edge, edge))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=90)
        return out.getvalue()
    except Exception:  # noqa: BLE001 - sent as it is; the 5 MB check still applies
        return data


def _shrink(data: bytes) -> Optional[bytes]:
    """A picture over the API's 5 MB limit (e.g. the contact sheet of a whole project) as a JPEG no longer than MAX_IMAGE_EDGE —
    the size Claude reads anyway. None when it cannot be done."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=88)
        small = out.getvalue()
        return small if len(small) <= MAX_IMAGE_BYTES else None
    except Exception:  # noqa: BLE001 - reported by the caller as "over 5 MB"
        return None


class AnthropicClient:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE,
                 transport: Transport = urllib_transport, max_tokens: int = DEFAULT_MAX_TOKENS,
                 sleep: Callable[[float], None] = time.sleep, retries: int = 2, ledger: Optional[str] = None):
        self.ledger = ledger          # database file: every call is written to the cost ledger and checked against the Claude cap
        self._key = api_key
        self.model = model
        self.base = base_url.rstrip("/")
        self.transport = transport
        self.max_tokens = max_tokens
        self._sleep = sleep
        self.retries = retries
        self.unrecorded = 0           # calls paid but not written to the ledger: the next call is refused until someone looks

    @classmethod
    def from_env(cls, transport: Transport = urllib_transport, ledger: Optional[str] = None) -> "AnthropicClient":
        key = clean_token(os.environ.get("ANTHROPIC_API_KEY", ""))
        if not key:
            raise LlmError("ANTHROPIC_API_KEY is not set (ask your admin for a Console API key; set it as an "
                           "environment variable, never commit it).", code="config")
        return cls(key, os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL,
                   os.environ.get("ANTHROPIC_API_BASE", DEFAULT_BASE).strip() or DEFAULT_BASE, transport, ledger=ledger)

    def _content(self, prompt: str, images: Sequence[Tuple[str, str]]) -> List[Dict]:
        """[repeating prompt parts, each cached] + pictures + the part that changes every call. Up to 3 cache marks are used."""
        if len(images) > MAX_IMAGES:   # Q1: never drop pictures silently (the caller must split the work)
            raise LlmError(f"{len(images)} ảnh cho một lời gọi Claude, tối đa {MAX_IMAGES} — chia nhỏ việc", code="too_many_images")
        parts = prompt.split(CACHE_BREAK)
        fixed, rest = parts[:-1], parts[-1]
        if len(fixed) > 3:
            fixed = fixed[:2] + ["\n\n---\n\n".join(fixed[2:])]
        blocks: List[Dict] = [{"type": "text", "text": t, "cache_control": {"type": "ephemeral"}} for t in fixed if t.strip()]
        for label, path in list(images)[:MAX_IMAGES]:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError as e:
                raise LlmError(f"cannot read image {label}: {e.strerror}", code="bad_image") from None
            data = _fit(data, IMAGE_EDGE)
            if len(data) > MAX_IMAGE_BYTES:
                data = _shrink(data)
                if data is None:
                    raise LlmError(f"image {label} is over 5 MB", code="bad_image")
            blocks.append({"type": "text", "text": label})
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": _media_type(data),
                                                       "data": base64.b64encode(data).decode("ascii")}})
        blocks.append({"type": "text", "text": rest})
        return blocks

    def complete(self, prompt: str, images: Sequence[Tuple[str, str]] = ()) -> LlmReply:
        return self._request(prompt, images, None)

    def converse(self, messages: List[Dict], tools: List[Dict], system: str = "", max_tokens: Optional[int] = None,
                 force_tool: Optional[str] = None) -> LlmReply:
        """One turn of a multi-turn tool-use conversation (the QC agent, core/qc_agent.py): the caller keeps `messages` and answers every
        tool_use with a tool_result. Same budget check, ledger and retries as `complete`; `reply.blocks` holds the content blocks."""
        self._last_prompt = system + "\n".join(b.get("text", "") for m in messages[:1] for b in (m["content"] if isinstance(m["content"], list)
                                                                                                  else [{"text": m["content"]}]))
        payload = {"model": self.model, "max_tokens": int(max_tokens or self.max_tokens), "messages": messages, "tools": tools}
        if system:
            payload["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        if force_tool:                       # S7.1 01/10: the agent ignored "record now" on its last turn; a forced call cannot be
            payload["tool_choice"] = {"type": "tool", "name": force_tool}   # ignored. Forced tool use does not go with thinking (Claude
            payload["thinking"] = {"type": "disabled"}                       # Sonnet 5 accepts both; 5.5 / Opus 5.5 / Fable 5.1 reject a
        self._last_max_tokens = payload["max_tokens"]                         # forced choice — the caller then records a doubt)
        body = json.dumps(payload).encode("utf-8")
        headers = {"x-api-key": self._key, "anthropic-version": API_VERSION, "content-type": "application/json",
                   "User-Agent": "AIVideoPipeline-LLM/0.1"}
        held = self._check_budget(payload)
        try:
            return self._send(headers, body, payload, check=lambda r: None)   # a cut answer comes back: the agent says "fewer tools"
        finally:
            self._release(held)

    def ask_json(self, messages: List[Dict], system: str, schema: Dict, max_tokens: int, thinking: Optional[Dict] = None,
                 effort: Optional[str] = None) -> LlmReply:
        """One call whose answer must follow `schema` (structured outputs: output_config.format json_schema — every object needs
        additionalProperties false; enum works, min/max do not, so the caller still checks). Tổ QC (core/qc_team.py): no tool loop,
        the answer is reply.text (JSON). `thinking` is sent as given ({"type": "disabled"} for the Sonnet 5 specialists; omitted for
        Opus 5.5, which cannot turn it off); same budget check, ledger and retries as `complete`."""
        self._last_prompt = system + "\n".join(b.get("text", "") for m in messages[:1] for b in (m["content"] if isinstance(m["content"], list)
                                                                                                  else [{"text": m["content"]}]))
        payload: Dict = {"model": self.model, "max_tokens": int(max_tokens), "messages": messages,
                         "output_config": {"format": {"type": "json_schema", "schema": schema}}}
        if effort:
            payload["output_config"]["effort"] = effort
        if thinking:
            payload["thinking"] = thinking
        if system:
            payload["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        self._last_max_tokens = payload["max_tokens"]
        body = json.dumps(payload).encode("utf-8")
        headers = {"x-api-key": self._key, "anthropic-version": API_VERSION, "content-type": "application/json",
                   "User-Agent": "AIVideoPipeline-LLM/0.1"}
        held = self._check_budget(payload)
        try:
            return self._send(headers, body, payload, check=self._check_stop)
        finally:
            self._release(held)

    @staticmethod
    def image_block(path: str, edge: Optional[int] = None) -> Dict:
        """A picture as a content block (fitted to `edge`, default IMAGE_EDGE; ≤ 5 MB)."""
        with open(path, "rb") as f:
            data = f.read()
        data = _fit(data, edge or IMAGE_EDGE)
        if len(data) > MAX_IMAGE_BYTES:
            data = _shrink(data) or data
        return {"type": "image", "source": {"type": "base64", "media_type": _media_type(data), "data": base64.b64encode(data).decode("ascii")}}

    def complete_with_search(self, prompt: str, max_uses: int = 3) -> LlmReply:
        """Like complete, with the Anthropic web search tool (a few searches, costs extra). Not verified against the live API."""
        return self._request(prompt, (), [{"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}])

    def _request(self, prompt: str, images: Sequence[Tuple[str, str]], tools) -> LlmReply:
        self._last_prompt = prompt                      # llm_calls.sources: the skill files found in the text really sent
        settings = stage_settings(current_tag()[0])
        max_tokens = int(settings.get("max_tokens") or self.max_tokens)
        payload = {"model": self.model, "max_tokens": max_tokens,
                   "messages": [{"role": "user", "content": self._content(prompt, images)}]}
        if settings.get("effort") and self.model.startswith(EFFORT_MODELS):
            payload["output_config"] = {"effort": settings["effort"]}
        if tools:
            payload["tools"] = tools
        self._last_max_tokens = max_tokens
        body = json.dumps(payload).encode("utf-8")
        headers = {"x-api-key": self._key, "anthropic-version": API_VERSION, "content-type": "application/json",
                   "User-Agent": "AIVideoPipeline-LLM/0.1"}
        held = self._check_budget(payload)
        try:
            return self._send(headers, body, payload, check=self._check_stop)
        finally:
            self._release(held)

    def _send(self, headers, body, payload, check) -> LlmReply:
        """POST with retries. A network error / timeout is a transient LlmError (it was a ProviderError that went round the retries,
        the locks and the agent's error handling — review 2026-09-28) and counts the call's worst case on the task locks: the provider
        may have billed it."""
        from .adapters.http import ProviderError
        last: Optional[LlmError] = None
        for attempt in range(self.retries + 1):
            try:
                try:
                    resp = self.transport("POST", self.base + "/v1/messages", headers, body, REQUEST_TIMEOUT)
                except ProviderError as e:
                    _count_caps(worst_usd(self.model, payload))
                    raise LlmError(f"lỗi mạng khi gọi Claude: {e}", code="network", transient=True) from None
                reply = self._parse(resp)
                self._record(reply)
                check(reply)
                return reply
            except LlmError as e:
                last = e
                if e.code == "out_of_credit" and self.ledger:     # Data Pack P5: every later Claude call is refused until reopened
                    try:
                        conn = self._ledger_conn()
                        try:
                            from . import budget as _budget
                            _budget.halt(conn, "anthropic", str(e))
                        finally:
                            conn.close()
                    except Exception:  # noqa: BLE001 - the error itself still reaches the person
                        pass
                if not e.transient or attempt == self.retries:
                    raise
                if attempt < self.retries and payload is not None:
                    reason = _check_caps(self.model, payload)         # a retry is a new paid call: the locks again
                    if reason:
                        raise LlmError(reason, code="budget") from None
                self._sleep(2 ** attempt * 2)
        raise last  # pragma: no cover

    def _ledger_conn(self):
        import sqlite3
        conn = sqlite3.connect(self.ledger, timeout=60)
        conn.row_factory = sqlite3.Row
        return conn

    def _release(self, hold_id) -> None:
        if not hold_id or not self.ledger:
            return
        try:
            from . import budget
            conn = self._ledger_conn()
            try:
                budget.release_hold(conn, hold_id)
            finally:
                conn.close()
        except Exception:  # noqa: BLE001 - a hold not released expires after budget.HOLD_MINUTES
            pass

    def _check_budget(self, payload: Optional[Dict] = None):
        """Refuse before paying: locks 1-2 (one call, one task — see spend_cap), then lock 3 — the Claude cap (core.budget) and the
        project's approved budget for this stage (core.project_budget) — with the worst case of this call and of every call in flight
        in any process (holds in the database). Returns the hold id (release it after the call)."""
        reason = _check_caps(self.model, payload) if payload is not None else None
        if reason:
            raise LlmError(reason, code="budget")
        if not self.ledger:
            return None
        from . import budget, cost
        if self.unrecorded:
            raise LlmError(f"{self.unrecorded} lời gọi Claude đã trả tiền nhưng không ghi được vào sổ chi — kiểm tra CSDL rồi mở lại "
                           "Dashboard (không gọi tiếp khi sổ chi không ghi được)", code="budget")
        if budget.token_price(cost.load_pricing(), self.model, "input", 1) is None:
            raise LlmError(f"model Claude '{self.model}' chưa có giá trong data/pricing.json (per_million_tokens) — thêm giá trước "
                           "khi dùng, nếu không sổ chi tính $0 và trần không chặn", code="budget")
        hid = None
        try:
            from . import project_budget
            stage, project_id = current_tag()
            part = project_budget.claude_stage(stage)
            mine = worst_usd(self.model, payload) if payload is not None else 0.0
            conn = self._ledger_conn()
            try:
                reason, hid = budget.hold_llm(conn, mine, project_id, part,
                                              extra_check=(lambda c: project_budget.check(c, project_id, part, mine)) if project_id else None)
            finally:
                conn.close()
        except Exception as e:  # noqa: BLE001 - unknown spend means no call (a cap that cannot be read does not protect)
            reason = f"không đọc được sổ chi để kiểm trần Claude ({type(e).__name__}: {e})"
        if reason:
            raise LlmError(reason, code="budget")
        return hid

    def _record(self, reply: LlmReply) -> None:
        """Tokens of one call into usage_events (kind 'llm', tier input/output) — priced by core.budget; counted on the task locks."""
        _count_caps(reply_usd(self.model, reply))
        if not self.ledger:
            return
        from .cost import record_usage
        stage, project_id = current_tag()
        for attempt in range(3):
            try:
                conn = self._ledger_conn()
                try:
                    for tier, n in (("input", reply.input_tokens), ("output", reply.output_tokens),
                                    ("cache_write", reply.cache_write_tokens), ("cache_read", reply.cache_read_tokens),
                                    ("web_search", reply.web_searches)):
                        if n:
                            record_usage(conn, None, "llm", self.name, self.model, tier, n,
                                         "search" if tier == "web_search" else "token", project_id=project_id, stage=stage)
                    from .llm_sources import in_text
                    try:                             # which skill files this call carried (rà soát 2026-09-27)
                        conn.execute("INSERT INTO llm_calls (at, project_id, stage, model, sources, input_tokens, output_tokens,"
                                     " cache_read_tokens, cache_write_tokens) VALUES (datetime('now'),?,?,?,?,?,?,?,?)",
                                     (project_id, stage, self.model, json.dumps(in_text(getattr(self, "_last_prompt", "")),
                                                                                ensure_ascii=False), reply.input_tokens,
                                      reply.output_tokens, reply.cache_read_tokens, reply.cache_write_tokens))
                        conn.commit()
                    except Exception:  # noqa: BLE001 - an older ledger without the table: the tokens are recorded already
                        pass
                finally:
                    conn.close()
                return
            except Exception as e:  # noqa: BLE001 - never lose the paid answer; a busy ledger is retried, then the next call refused
                last = e
                self._sleep(0.5 * (attempt + 1))
        self.unrecorded += 1
        print(f"[llm] could not write Claude usage to the ledger: {last}", file=sys.stderr)

    def _check_stop(self, reply: LlmReply) -> None:
        """C5: a cut or refused answer is paid for but useless; asking again the same way pays again for the same cut."""
        if reply.stop_reason == "max_tokens":
            cap = getattr(self, "_last_max_tokens", self.max_tokens)
            raise LlmError(f"câu trả lời của Claude bị cắt ở giới hạn {cap} token (đã tính tiền; {len(reply.text)} ký tự chữ, phần còn "
                           "lại là suy nghĩ) — chia nhỏ việc (ít cảnh hơn mỗi lần) hoặc giảm effort thay vì hỏi lại",
                           code="truncated", partial=reply.text)
        if reply.stop_reason == "refusal":
            raise LlmError("Claude từ chối trả lời yêu cầu này (đã tính tiền phần đã đọc)", code="refusal")

    @staticmethod
    def _parse(resp: HttpResponse) -> LlmReply:
        try:
            payload = json.loads(resp.body.decode("utf-8"))
        except ValueError:
            payload = {}
        message = ((payload.get("error") or {}).get("message") if isinstance(payload, dict) else None) or ""
        if resp.status == 401 or resp.status == 403:
            raise LlmError("Anthropic rejected the API key (HTTP %d)" % resp.status, code="auth")
        from .adapters.http import out_of_credit
        if resp.status == 402 or (resp.status >= 400 and out_of_credit(message)):     # Data Pack P5
            raise LlmError(f"Hết tiền trên tài khoản Anthropic (HTTP {resp.status}): {message[:200]}", code="out_of_credit")
        if resp.status == 429 or resp.status >= 500:
            raise LlmError(f"Anthropic temporarily unavailable (HTTP {resp.status}) {message}".strip(),
                           code="rate_limit" if resp.status == 429 else "server_error", transient=True)
        if resp.status >= 400:
            raise LlmError(f"Anthropic error HTTP {resp.status}: {message[:300]}", code="http_error")
        text = "".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
        usage = payload.get("usage") or {}
        return LlmReply(text, int(usage.get("input_tokens", 0) or 0), int(usage.get("output_tokens", 0) or 0),
                        str(payload.get("stop_reason") or ""), int(usage.get("cache_creation_input_tokens", 0) or 0),
                        int(usage.get("cache_read_input_tokens", 0) or 0),
                        int((usage.get("server_tool_use") or {}).get("web_search_requests", 0) or 0),
                        payload.get("content") or [])


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
    raise LlmError(f"Claude trả lời sai định dạng 2 lần liền ({error}). Cách xử lý: bấm chạy lại; nếu vẫn lỗi, rút gọn kịch bản / ghi chú của bước này hoặc gửi báo cáo chẩn đoán (⚙ Chẩn đoán).", code="bad_json")


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
    raise LlmError(f"Claude trả cẩm nang không dùng được 2 lần liền ({error}). Cách xử lý: bấm chắt lọc lại; nếu vẫn lỗi, tắt bớt "
                   "tài liệu dài của bước này rồi thử lại.", code="bad_text")


def run_distill(group: str, client, include_builtin: bool = False) -> Dict:
    """Read every document of a step once and store a short, sectioned playbook that the step then uses instead of
    the raw documents."""
    bundle = knowledge.build_distill_bundle(group, include_builtin)
    with tagged("distill"):
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
            project_id = project_of(p, ident)
            try:
                with tagged(stage, project_id):
                    return fn(p, ident, *a, **k)
            except LlmError as e:
                diag.record(p.conn, stage, "warn" if e.transient else "error", str(e), e.code, project_id)
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
    out, blind = [], []
    for a in assets.project_assets(conn, project_id):
        if a["kind"] not in ("character", "pet"):
            continue
        if a["images"]:
            out.append((f"Ảnh tham chiếu — {a['name']}:", assets.thumbnail(assets.best_reference(a)["path"], 900)))
        elif conn.execute("SELECT 1 FROM asset_images WHERE asset_id=? AND status IS NOT 'removed'", (a["id"],)).fetchone():   # S14.4: not the Kho trash
            blind.append(a["name"])            # the library has pictures of it, but none can be read
    if blind:                                  # A1/R1: never let the Director describe a known character blind (it invents one)
        raise LlmError(f"Director cần ảnh của {', '.join(blind)} nhưng không đọc được file ảnh trong Kho tài nguyên — kiểm tra thư mục "
                       "data/assets (📊 Theo dõi liệt kê ảnh thiếu) rồi chạy lại. Chưa gọi Claude, chưa tốn tiền.", code="missing_reference")
    return out


@_diagnosed("director", lambda p, i: i)
def run_director(p: Pipeline, project_id: int, client, resume: bool = False) -> Dict:
    """The Director: one call for the whole script (Bible + scenes + shots), or — feature director_two_pass on a shot project — Tầng A
    Đạo diễn + one Tầng B Quay phim call per scene + code review (core/director_two_pass.py; same stored shape). resume (two passes
    only): reuse the paid Tầng A answer and the scenes that passed in a failed run."""
    access.need_edit(p, project_id, "chạy Director")
    from . import assets, director_two_pass
    auto = assets.auto_attach(p.conn, project_id)            # the library resources the script names — no click needed (2026-09-27)
    if auto["attached"] or auto["ambiguous"]:
        diag.record(p.conn, "director", "warn" if auto["ambiguous"] else "info",
                    ("Tự gắn tài nguyên kịch bản nhắc tới: " + ", ".join(auto["attached"]) if auto["attached"] else "")
                    + (" · Tên khớp nhiều tài nguyên, cần chọn tay ở Bước 1 🧰: " + ", ".join(auto["ambiguous"]) if auto["ambiguous"] else ""),
                    "auto_attach", project_id)
    if director_two_pass.enabled(p.project(project_id)):
        return director_two_pass.run(p, project_id, client, resume=resume)
    refs = _director_references(p.conn, project_id)
    diag.record(p.conn, "director", "info", f"Director xem {len(refs)} ảnh nhân vật/thú cưng: "
                + (", ".join(label.split("—", 1)[-1].strip(" :") for label, _ in refs) or "không có (nhân vật không gắn tài nguyên)"),
                "director_refs", project_id)
    try:
        obj, tin, tout = ask_json(client, prompts.build_director_bundle(p, project_id), llm_io.validate_for_project(p, project_id),
                                  refs, note=_retry_note(p, "director", project_id))
    except LlmError as e:
        if e.partial is not None:                          # paid for: keep what came back, to see where the tokens went
            p.set_project_field(project_id, "director_raw", json.dumps({"truncated": True, "error": str(e), "text": e.partial},
                                                                       ensure_ascii=False))
        raise
    from . import project_defaults                 # S3.8: which places (text + pictures) the plan was made with
    obj["places_at_plan"] = project_defaults.places_fingerprint(p.conn, project_id)
    p.set_project_field(project_id, "director_raw", json.dumps(obj, ensure_ascii=False))   # paid for: kept even if saving fails
    llm_io.store_scene_analysis(p, project_id, obj)
    director_two_pass.forget(p, project_id)       # a stored two-pass intent no longer matches this plan ("↻ Chia shot lại" must not use it)
    return {"characters": len(obj["characters"]), "scenes": len(obj["scenes"]), "input_tokens": tin,
            "output_tokens": tout, "ip_risk_notes": obj.get("ip_risk_notes") or []}


@_diagnosed("director", lambda p, i: i)
def run_director_scene(p: Pipeline, project_id: int, scene_idx: int, client, note: str = "") -> Dict:
    """1.4 "↻ Chia shot lại cảnh này": one Claude call for ONE script scene (the shared prompt is cached), merged into the stored plan,
    normalised and line-checked as a whole, then only that scene and the later ones are rewritten (earlier scenes keep their work).
    ~1/6 of a whole Director answer: a few cents instead of ~$0,3."""
    access.need_edit(p, project_id, "chia shot lại")
    from . import director_two_pass, shots
    if director_two_pass.enabled(p.project(project_id)) and director_two_pass.load_raw(p, project_id).get("done"):
        return director_two_pass.replan_scene(p, project_id, scene_idx, client, note)   # GĐ5: the DP re-splits from the stored intent
    raw = json.loads(p.project(project_id)["director_raw"] or "{}")
    if not raw.get("scenes") or raw.get("truncated"):
        raise LlmError("chưa có kế hoạch Director đầy đủ để chia lại một cảnh — chạy Director cho cả kịch bản trước", code="config")
    raw.pop("normalized", None)
    merged_box: Dict = {}
    check_all = llm_io.validate_for_project(p, project_id)

    def check(part):
        part = llm_io._load(part)
        new = [s for s in part.get("scenes") or [] if isinstance(s, dict) and s.get("idx") == scene_idx]
        if len(new) != 1:
            raise llm_io.SchemaError(f"scenes: cần đúng một phần tử là cảnh {scene_idx}")
        merged = dict(raw, scenes=[new[0] if s.get("idx") == scene_idx else s for s in raw["scenes"]])
        merged_box["obj"] = check_all(merged)       # normaliser + every rule of a whole answer
        return merged_box["obj"]

    with tagged("director", project_id):
        _, tin, tout = ask_json(client, prompts.build_director_bundle(p, project_id, only_scene=scene_idx, note=note), check,
                                note=_retry_note(p, "director", project_id))
    obj = merged_box["obj"]
    n = shots.replace_from(p, project_id, obj["scenes"], scene_idx)
    p.set_project_field(project_id, "director_raw", json.dumps(obj, ensure_ascii=False))
    return {"scene": scene_idx, "rows": n, "input_tokens": tin, "output_tokens": tout, "normalized": obj.get("normalized") or []}


def image_path(data_dir: str, project_id: int, job_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "images", f"job_{job_id}.png")


@_diagnosed("qc", lambda p, i: p.job(i)["project_id"])
def run_qc(p: Pipeline, job_id: int, client, data_dir: str, autofix: bool = False) -> Dict:
    """Score one generated picture against the scene spec AND the chosen resources' reference pictures. autofix: a faulty picture is
    regenerated automatically (up to the project's max_retry_count) instead of waiting for the person."""
    access.need_edit_job(p, job_id, "chạy QC")
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
    _no_feet_in_frame(json.loads(row["data"] or "{}"), obj)
    issues = "; ".join(str(i) for i in (obj.get("issues") or [])[:5]) or None
    decision = p.apply_qc(job_id, obj["criteria"], issues=issues, autofix=autofix)
    return {"decision": decision, "input_tokens": tin, "output_tokens": tout, "issues": issues}


NO_FEET_SIZES = ("ECU", "CU", "MCU", "MS")
_FEET = re.compile(r"\bfeet\b|\bfoot\b|ground(ed|ing)?\b|contact shadow|sandals|shoes|chân chạm", re.IGNORECASE)


def _no_feet_in_frame(shot: Dict, obj: Dict) -> None:
    """Trial 2A: QC marked medium shots down for "feet cropped, not grounded" — a medium shot is cut above the knees by design. For
    framings without feet `grounding` does not apply (scored as met) and feet-only issues are dropped, so they never trigger a redo."""
    if str(shot.get("size") or "").upper() not in NO_FEET_SIZES:
        return
    if "grounding" in (obj.get("criteria") or {}):
        obj["criteria"]["grounding"] = 1.0
    parts = [s.strip() for i in obj.get("issues") or [] for s in re.split(r";\s*", str(i)) if s.strip()]
    obj["issues"] = [s for s in parts if not _FEET.search(s)]


def run_qc_batch(p: Pipeline, project_id: int, client, data_dir: str) -> Dict:
    """QC every generated image that has not been scored yet (state 'succeeded')."""
    access.need_edit(p, project_id, "chạy QC hàng loạt")
    jobs = p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'"
                          " ORDER BY id", (project_id,)).fetchall()
    summary: Dict[str, Any] = {"checked": 0, "failed": [], "decisions": {}, "input_tokens": 0, "output_tokens": 0}
    for j in jobs:
        try:
            r = run_qc(p, j["id"], client, data_dir)
        except LlmError as e:
            summary["failed"].append((j["id"], fail_text(e)))
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
    access.need_edit(p, project_id, "viết motion prompt")
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
    missing = [r["idx"] for r in todo if not os.path.exists(image_path(data_dir, project_id, r["jid"]))]
    if missing:                        # rule 1 (docs/CHUAN_XAY_DUNG.md): say what Claude will not see
        diag.record(p.conn, "motion", "warn", f"ảnh đã duyệt của cảnh {missing} không có file — Claude viết motion không nhìn ảnh",
                    "missing_image", project_id)
    batches = _motion_batches(todo)
    done = tin = tout = 0
    for batch in batches:              # C6/M20: one picture per multi-shot group, never more than MAX_IMAGES per call (no silent cut)
        by_job: Dict[int, List[int]] = {}
        for r in batch:
            if r["idx"] not in missing:
                by_job.setdefault(r["jid"], []).append(r["idx"])
        images = [(f"Ảnh cảnh {', '.join(map(str, idxs))}" + (" (ảnh đầu nhóm multi-shot, dùng chung):" if len(idxs) > 1 else ":"),
                   image_path(data_dir, project_id, jid)) for jid, idxs in by_job.items()]
        wanted = {r["idx"] for r in batch}
        bundle = (prompts.build_motion_bundle(p, project_id, only_idx=wanted) if only_idx is not None or len(batches) > 1
                  else prompts.build_motion_bundle(p, project_id, only_missing=True))
        if len(batches) == 1:
            bundle = plain(bundle)     # one call: nothing to reuse, a cache write would only cost more
        obj, i, o = ask_json(client, bundle, llm_io.validate_motion_prompts, images, note=_retry_note(p, "motion", project_id))
        obj["scenes"] = [s for s in obj["scenes"] if s["idx"] in wanted]
        llm_io.store_motion_prompts(p, project_id, obj)
        done, tin, tout = done + len(obj["scenes"]), tin + i, tout + o
    return {"scenes": done, "input_tokens": tin, "output_tokens": tout, "calls": len(batches)}


def _motion_batches(todo: List[Dict]) -> List[List[Dict]]:
    """Scenes in order, cut so that each call carries at most MAX_IMAGES distinct pictures."""
    batches: List[List[Dict]] = [[]]
    for r in todo:
        jobs = {x["jid"] for x in batches[-1]}
        if r["jid"] not in jobs and len(jobs) >= MAX_IMAGES:
            batches.append([])
        batches[-1].append(r)
    return batches


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
        prompt = plain(prompt)
        v2 = self._v2(prompt)
        if v2 is not None:
            return LlmReply("```json\n" + json.dumps(v2, ensure_ascii=False) + "\n```", 90, 50)
        if prompt.startswith("# Biên kịch — Lượt"):                      # S11.1 (core/idea_to_script.py)
            return LlmReply("```json\n" + json.dumps(_mock_screenwriter(prompt), ensure_ascii=False) + "\n```", 120, 60)
        if prompt.startswith("# Biên tập viên — duyệt bản dựng thô"):    # P2 rough-cut review (core/editor_review.py): one proposal
            clock = json.loads(re.search(r"# Đồng hồ shot[^\n]*\n```json\s*(.*?)```", prompt, re.S).group(1))
            free = [s for s in clock if s["n"] > 1 and not s["dialogue"] and not s["lip_sync"] and s["seconds"] >= 1.5]
            out = {"summary": "Bản dựng giả lập: nhịp ổn, một shot hơi dài.", "findings": ([] if not free else [
                {"at_s": free[0]["start"], "scene": free[0]["story_scene"], "observed": "drag", "evidence": f"shot {free[0]['n']} dài {free[0]['seconds']} s (giả lập)",
                 "action": "shorten_shot", "target_shot": free[0]["n"], "amount": 0.5, "value": "", "why": "shot kéo dài hơn việc nó kể (giả lập)"}])}
            return LlmReply("```json\n" + json.dumps(out, ensure_ascii=False) + "\n```", 120, 60)
        if prompt.startswith("# Đạo diễn — trả lời đề xuất của Biên tập viên"):
            found = json.loads(re.search(r"# Đề xuất của Biên tập viên\s*```json\s*(.*?)```", prompt, re.S).group(1))
            out = {"verdicts": [{"id": f["id"], "verdict": "agree", "reason": "", "amount": 0, "value": ""} for f in found]}
            return LlmReply("```json\n" + json.dumps(out, ensure_ascii=False) + "\n```", 80, 30)
        if prompt.startswith("# Đạo diễn — Tầng A"):                    # GĐ5 two-pass Director (core/director_two_pass.py)
            return LlmReply("```json\n" + json.dumps(_mock_intent(prompt), ensure_ascii=False) + "\n```", 100, 40)
        if "# Việc lần này: Quay phim chia shot Cảnh" in prompt:
            return LlmReply("```json\n" + json.dumps(_mock_dp_scene(prompt), ensure_ascii=False) + "\n```", 60, 30)
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
        if prompt.startswith("# Kiểm Character Bible so với ảnh tài nguyên"):
            names = re.findall(r"^- \*\*(.+?)\*\*:", prompt.split("# Nhân vật cần kiểm", 1)[1], flags=re.M)
            out = {"characters": [{"name": n, "ok": True, "mismatches": [], "fixed_description": ""} for n in names]}
            return LlmReply(json.dumps(out, ensure_ascii=False), 60, 20)
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


def _mock_screenwriter(prompt: str) -> Dict:
    """A fixed, valid answer for each turn of the Biên kịch (demo / tests without the API)."""
    turn = int(re.match(r"# Biên kịch — Lượt (\d)", prompt).group(1))
    if turn == 1:
        return {"have": ["Kelly và Maxim", "một trận bo cuối"], "missing": ["ai thắng", "giọng điệu"],
                "questions": [{"q": "Kết vui hay bất ngờ?", "default": "bất ngờ", "why": "đổi cú chốt"},
                              {"q": "Có Kenta không?", "default": "không", "why": "đổi số nhân vật"}]}
    if turn == 2:
        return {"directions": [{"title": t, "logline": f"Kelly và Maxim tranh thùng thính ({t}, giả lập).", "hook_3s": "Thùng thính rơi giữa hai người.",
                                "payoff": "Thùng thính trống trơn.", "trend_card": ""} for t in ("Hài", "Hồi hộp", "Ấm áp")]}
    if turn == 3:
        m = re.search(r"Thời lượng mục tiêu: (\d+) s", prompt)
        d = int(m.group(1)) if m else 30
        cut = [0, 3, round(d * .35), round(d * .65), round(d * .85), d]
        names = ["hook", "setup", "turn", "climax", "ending"]
        return {"beats": [{"name": n, "start": cut[i], "end": cut[i + 1], "place": "Đảo Quân Sự", "who": ["KELLY", "MAXIM"],
                           "what": f"{n} (giả lập)", "dialogue": [{"speaker": "KELLY", "line": "Của tôi!"}] if n == "hook" else []}
                          for i, n in enumerate(names)], "total_s": d, "question": "Ai lấy được thùng thính?"}
    return {"script": "CẢNH 1 - NGÀY, ĐẢO QUÂN SỰ\nThùng thính rơi giữa Kelly và Maxim.\nKELLY: Của tôi!\nMAXIM: Còn lâu!\n\n"
                      "CẢNH 2 - NGÀY, ĐẢO QUÂN SỰ\nHai người mở thùng — trống trơn.\nKELLY: Ủa?",
            "added": [{"kind": "line", "text": "MAXIM: Còn lâu!"}], "notes": "giả lập"}


def _mock_intent(prompt: str) -> Dict:
    """Offline Tầng A (Đạo diễn): the Bible from the speakers, every line kept, a seconds frame that fits the mock DP's shots."""
    from . import dialogue as _dlg
    blocks = re.split(r"^### Cảnh (\d+)[^\n]*$", prompt.split("# Kịch bản đã tách cảnh", 1)[-1], flags=re.M)
    texts = {int(blocks[i]): blocks[i + 1] for i in range(1, len(blocks) - 1, 2)}
    idxs = sorted(texts) or [1]
    lines = {i: _dlg.lines(texts.get(i, "")) for i in idxs}
    names = sorted({who for rows in lines.values() for who, _ in rows}) or ["Nhân vật chính"]
    scenes = []
    for i in idxs:
        cast = sorted({w for w, _ in lines[i]}) or names[:1]
        proto = {"idx": i, "location": "Bối cảnh mẫu", "characters": cast, "dialogue": [{"speaker": w, "text": t} for w, t in lines[i]]}
        target = round(sum(float(s["duration_s"]) for s in _mock_shots(proto, first=i == idxs[0], last=i == idxs[-1])), 1)
        scenes.append({"idx": i, "location": "Bối cảnh mẫu", "time": "Ngày", "characters": cast, "mood": "trung tính",
                       "lighting": "tự nhiên", "emotional_intent": "người xem tò mò (giả lập)",
                       "beat": {"want": "đi tiếp", "obstacle": "trời tối", "turn": "quyết định lên đường"},
                       "camera_complexity": "simple", "shot_role": "hero" if i == idxs[-1] else "normal",
                       "focus": cast[0], "peak": 4 if i == idxs[-1] else 3, "target_s": max(1.0, target),
                       "dialogue": proto["dialogue"], "dp_notes": "cho người xem thấy ai nói với ai (giả lập)",
                       "editor_notes": ""})
    return {"genre": "SHORT_FORM",
            "characters": [{"name": n, "description": f"mô tả mẫu của {n} (giả lập)",
                            "lock": {"must_keep": "same face, hair and outfit colours (mock)", "may_change": "pose, expression",
                                     "forbidden": "outfit swapped with others (mock)"}} for n in names],
            "scenes": scenes, "tradeoffs": [], "script_notes": [], "ip_risk_notes": []}


def _mock_dp_scene(prompt: str) -> Dict:
    """Offline Tầng B (Quay phim): the mock shot split of the one scene the task names, with exactly the kept lines."""
    head = re.search(r"# Việc lần này: Quay phim chia shot Cảnh (\d+)([^\n]*)", prompt)
    scene = json.loads(re.search(r"# Ý đồ cảnh này\s*```json\s*(.*?)```", prompt, re.S).group(1))
    return {"idx": int(head.group(1)), "tradeoffs": [],
            "shots": _mock_shots(scene, first="cảnh ĐẦU phim" in head.group(2), last="cảnh CUỐI phim" in head.group(2))}


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
    if prompt.startswith("# Người xem lần đầu"):
        film = json.loads(re.search(r"# Phim \(theo thứ tự trên màn hình\)\s*```json\s*(.*?)```", prompt, re.S).group(1))
        return {"summary": f"{len(film)} shot (giả lập)", "who_wants_what": "giả lập",
                "turns": [{"at": film[-1]["shot"], "what": "giả lập", "understood": True, "why": "giả lập"}] if film else [],
                "confusing": [{"at": film[0]["shot"], "question": "ai đây? (giả lập)"}] if film else [], "ending": "giả lập",
                "understood": 4}
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


def db_file(conn) -> Optional[str]:
    """The file behind a SQLite connection (the Claude cost ledger of client_from_env); None for an in-memory database."""
    return next((r[2] for r in conn.execute("PRAGMA database_list") if r[1] == "main"), "") or None


def ledger_factory(ledger: Optional[str]) -> Callable:
    """A client factory bound to the cost ledger (background workers: auto QC, library reading, research) — no Claude API call
    may bypass the ledger and the Claude cap (C1)."""
    return lambda: client_from_env(ledger=ledger)


def client_from_env(transport: Transport = urllib_transport, ledger: Optional[str] = None):
    """LLM_PROVIDER = anthropic | claude_cli (Claude Code on this PC, no key) | mock. Unset: anthropic when ANTHROPIC_API_KEY exists, else None.
    ledger: the database file where Claude API calls are recorded and checked against the Claude cap (core.budget)."""
    kind = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if kind == "mock":
        return MockLlm()
    if kind in ("claude_cli", "claude-cli", "cli"):
        return ClaudeCliClient.from_env()
    if kind == "anthropic" or (not kind and os.environ.get("ANTHROPIC_API_KEY", "").strip()):
        return AnthropicClient.from_env(transport, ledger=ledger)
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
            prompt = plain(prompt)
            text = prompt
            if images:
                if len(images) > MAX_IMAGES:
                    raise LlmError(f"{len(images)} ảnh cho một lời gọi Claude, tối đa {MAX_IMAGES} — chia nhỏ việc", code="too_many_images")
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
                code = cli_error_code(detail)
                hint = " Mở Claude Code (lệnh `claude`) một lần để đăng nhập lại rồi thử lại." if code == "auth" else ""
                raise LlmError(f"Claude Code báo lỗi: {detail}.{hint}", code=code)
            usage = out.get("usage") or {}
            tokens_in = sum(int(usage.get(k, 0) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
            return LlmReply(str(out["result"]), tokens_in, int(usage.get("output_tokens", 0)))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def complete_with_search(self, prompt: str, max_uses: int = 3) -> LlmReply:
        raise LlmError("Nghiên cứu hàng tháng cần Claude API (tìm kiếm web); chế độ Claude Code trên máy chưa hỗ trợ.", code="config")
