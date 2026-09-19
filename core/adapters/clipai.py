"""Clip AI video adapter (Kling Omni + Seedance through the Clip AI gateway).

Contract source: the vendor skill/reference (clipai 1.3.1). Key facts encoded here:
- Auth: `Authorization: Bearer <CLIPAI_TOKEN>` (token from the environment, never stored in the repo).
- Create: multipart `ctx` (JSON) + `image_files`; Kling -> /api/kling/omni-video-submit,
  Seedance -> /api/kling/seedance-video-submit. Seedance can return code 0 with a failed task inside.
- There is no per-task status endpoint: scan /api/kling/video-list (task_type 6 = Omni, 8 = Seedance).
  List `task_status` is numeric (0 submitted, 1 processing, 2 succeed, 3 failed, 4 pending); create returns strings.
- Delete: POST /api/kling/video-delete with the numeric row `id` (not the task_id).
- Use canonical `dreamina-seedance-*` names (never `doubao-*`).
- The public contract lists no negative-prompt field, so it is not sent unless CLIPAI_NEGATIVE=append.
"""
import json
import os
from typing import Dict, Optional, Tuple

from ..providers import RISK_CONTROL, ProviderError, TaskStatus
from .http import ApiClient, Transport, clean_token, urllib_transport

DEFAULT_BASE = "https://clipai.ingarena.net"
USER_AGENT = "AIVideoPipeline-ClipAI/0.1"

PATH_KLING = "/api/kling/omni-video-submit"
PATH_SEEDANCE = "/api/kling/seedance-video-submit"
PATH_LIST = "/api/kling/video-list"
PATH_DELETE = "/api/kling/video-delete"
TASK_TYPE = {"omni": 6, "seedance": 8}

MODEL_ALIASES = {
    "kling": "kling-v3-omni", "kling-o1": "kling-video-o1",
    "seedance": "dreamina-seedance-2-0-260128", "seedance-2.0": "dreamina-seedance-2-0-260128",
    "seedance-fast": "dreamina-seedance-2-0-fast-260128", "seedance-2.5": "dreamina-seedance-2-5-260628",
}
KLING_MODELS = {"kling-v3-omni", "kling-video-o1"}
SEEDANCE_MODELS = {"dreamina-seedance-2-5-260628", "dreamina-seedance-2-0-260128", "dreamina-seedance-2-0-fast-260128"}
PROMPT_LIMITS = {"kling": 2500, "dreamina-seedance-2-0-260128": 4000, "dreamina-seedance-2-0-fast-260128": 4000,
                 "dreamina-seedance-2-5-260628": 5000}
_RISK_HINTS = ("risk control", "risk-control", "风控", "content policy", "moderation", "copyright", "版权", "审核")
_UNSEEN_LIMIT = 12


def resolve_model(model: Optional[str]) -> Tuple[str, str]:
    """Return (canonical_model, family) where family is 'omni' or 'seedance'."""
    name = (model or "kling").strip().lower()
    if name == "minimax":
        raise ProviderError("MiniMax is not part of the Clip AI API contract we have (Kling and Seedance only)",
                            code="unsupported_model")
    canonical = MODEL_ALIASES.get(name, name)
    if canonical in KLING_MODELS:
        return canonical, "omni"
    if canonical in SEEDANCE_MODELS:
        return canonical, "seedance"
    raise ProviderError(f"unknown Clip AI model '{model}'. Allowed: {sorted(KLING_MODELS | SEEDANCE_MODELS)}",
                        code="unsupported_model")


def classify_failure(message: str) -> str:
    low = (message or "").lower()
    return RISK_CONTROL if any(h in low for h in _RISK_HINTS) else "task_failed"


def _state(task_status) -> str:
    if isinstance(task_status, str):
        s = task_status.lower()
        if s in ("succeed", "success", "completed"):
            return "succeeded"
        if s in ("failed", "error"):
            return "failed"
        return "running"
    return {2: "succeeded", 3: "failed"}.get(int(task_status), "running")


class ClipAIVideoProvider:
    name = "clipai"

    def __init__(self, token: str, base_url: str = DEFAULT_BASE, transport: Transport = urllib_transport,
                 aspect_ratio: str = "16:9", kling_mode: str = "pro", resolution: str = "720p",
                 negative: str = "ignore"):
        self.client = ApiClient(base_url, token, USER_AGENT, transport)
        self.aspect_ratio, self.kling_mode, self.resolution, self.negative = aspect_ratio, kling_mode, resolution, negative
        self._urls: Dict[str, str] = {}
        self._unseen: Dict[str, int] = {}

    @classmethod
    def from_env(cls, transport: Transport = urllib_transport) -> "ClipAIVideoProvider":
        token = clean_token(os.environ.get("CLIPAI_TOKEN", ""))
        if not token:
            raise ProviderError("CLIPAI_TOKEN is not set. Log in to clipai.ingarena.net -> avatar -> API Token, "
                                "then set it as an environment variable (never commit it).", code="config")
        return cls(token, os.environ.get("CLIPAI_API_BASE", DEFAULT_BASE).strip() or DEFAULT_BASE, transport,
                   os.environ.get("CLIPAI_ASPECT_RATIO", "16:9"), os.environ.get("CLIPAI_KLING_MODE", "pro"),
                   os.environ.get("CLIPAI_RESOLUTION", "720p"), os.environ.get("CLIPAI_NEGATIVE", "ignore"))

    # ---- submit ---------------------------------------------------------
    def submit(self, image_path: str, prompt: str, negative_prompt: Optional[str], duration_sec: float,
               model: Optional[str] = None) -> str:
        canonical, family = resolve_model(model)
        text = prompt.strip()
        if self.negative == "append" and negative_prompt:
            text += f"\nAvoid: {negative_prompt}"
        limit = PROMPT_LIMITS["kling" if family == "omni" else canonical]
        if len(text) > limit:
            raise ProviderError(f"prompt is {len(text)} characters; {canonical} allows at most {limit}",
                                code="prompt_too_long")
        if not os.path.exists(image_path):
            raise ProviderError(f"reference image not found: {image_path}", code="missing_image")
        with open(image_path, "rb") as f:
            image = (os.path.basename(image_path), f.read())
        if family == "omni":
            ctx = {"model_name": canonical, "multi_shot": 0, "prompt": text, "sound": "off",
                   "image_list": [{"image_url": "", "type": "first_frame"}], "mode": self.kling_mode,
                   "aspect_ratio": self.aspect_ratio, "duration": str(int(min(max(round(duration_sec), 3), 15))),
                   "video_num": 1}
            path = PATH_KLING
        else:
            max_duration = 30 if canonical == "dreamina-seedance-2-5-260628" else 15
            ctx = {"model_name": canonical,
                   "content": [{"type": "text", "text": text},
                               {"type": "image_url", "image_url": {"url": ""}, "role": "first_frame"}],
                   "resolution": self.resolution, "ratio": self.aspect_ratio,
                   "duration": int(min(max(round(duration_sec), 4), max_duration)), "generate_audio": False,
                   "camera_fixed": False, "seed": -1, "video_num": 1}
            path = PATH_SEEDANCE
        data = self.client.post_multipart(path, {"ctx": json.dumps(ctx, ensure_ascii=False)},
                                          [("image_files", image[0], image[1])])
        tasks = (data or {}).get("tasks") or []
        if not tasks:
            raise ProviderError("create returned no task", code="bad_response")
        first = tasks[0]
        if _state(first.get("task_status", "submitted")) == "failed":
            message = first.get("task_status_msg") or "task creation failed"
            raise ProviderError(message, code=classify_failure(message))
        return f"{family}:{first['task_id']}"

    # ---- status ---------------------------------------------------------
    def _find(self, external_id: str) -> Tuple[Optional[dict], str]:
        family, _, task_id = external_id.partition(":")
        if family not in TASK_TYPE or not task_id:
            raise ProviderError(f"malformed external id '{external_id}'", code="bad_id")
        data = self.client.get(PATH_LIST, {"page": 1, "pageSize": 50, "task_type": TASK_TYPE[family],
                                           "order_by_desc": 1})
        rows = (data or {}).get("data") or []
        return next((t for t in rows if str(t.get("task_id")) == task_id), None), task_id

    def status(self, external_id: str) -> TaskStatus:
        task, _ = self._find(external_id)
        if task is None:
            self._unseen[external_id] = self._unseen.get(external_id, 0) + 1
            if self._unseen[external_id] >= _UNSEEN_LIMIT:
                return TaskStatus("failed", "not_found", "task not found in the first list page")
            return TaskStatus("running")
        self._unseen.pop(external_id, None)
        state = _state(task.get("task_status"))
        if state == "succeeded":
            if not task.get("video_url"):
                return TaskStatus("running")
            self._urls[external_id] = task["video_url"]
            return TaskStatus("succeeded")
        if state == "failed":
            message = task.get("task_status_msg") or "task failed"
            return TaskStatus("failed", classify_failure(message), message)
        return TaskStatus("running")

    # ---- download / cancel ---------------------------------------------
    def download(self, external_id: str, dest_path: str) -> str:
        url = self._urls.get(external_id)
        if not url:
            task, _ = self._find(external_id)
            url = (task or {}).get("video_url")
        if not url:
            raise ProviderError("no video_url available for this task", code="no_result")
        return self.client.download(url, dest_path)

    def cancel(self, external_id: str) -> None:
        task, _ = self._find(external_id)
        if task is not None and task.get("id") is not None:
            self.client.post_json(PATH_DELETE, {"id": int(task["id"])})
