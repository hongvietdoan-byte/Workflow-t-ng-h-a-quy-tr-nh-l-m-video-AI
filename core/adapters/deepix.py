"""Deepix image adapter (text-to-image through the Deepix gateway).

Contract source: the vendor skill/reference (deepix 1.4.1). Key facts encoded here:
- Auth: `Authorization: Bearer <DEEPIX_TOKEN>` from the environment.
- Create: POST /api/image-generator/conversation-create as multipart/form-data; `prompts` must be a
  JSON *string* [{"key":"positive_prompt","text":...}]; prompt_key 2 = text-to-image.
- Poll with `data.msg_id` (NOT `data.id`): GET /api/image-generator/message-status?message_id=...;
  the task state is `data.status` (nested), the result URL is `data.image_url`.
- Default model Seedream 5.0 Pro takes pixel sizes (WxH); both sides multiples of 16, within pixel bounds.
- There is no cancel endpoint for image tasks.
"""
import json
import os
from typing import Dict, Optional

from ..providers import ProviderError, TaskStatus
from .http import ApiClient, Transport, clean_token, urllib_transport

DEFAULT_BASE = "https://deepix.ingarena.net"
USER_AGENT = "AIVideoPipeline-Deepix/0.1"
PATH_CREATE = "/api/image-generator/conversation-create"
PATH_STATUS = "/api/image-generator/message-status"
DEFAULT_MODEL = "dola-seedream-5-0-pro-260628"
DEFAULT_SIZE = "2048x1152"  # 16:9, both sides multiples of 16, inside the Seedream Pro pixel bounds

_DONE = {"completed", "succeed", "success"}
_FAILED = {"failed", "error"}


def validate_seedream_size(size: str) -> None:
    try:
        w, h = (int(x) for x in size.lower().split("x"))
    except ValueError:
        raise ProviderError(f"size must look like 2048x1152, got '{size}'", code="bad_size") from None
    if w % 16 or h % 16 or max(w, h) / min(w, h) > 16:
        raise ProviderError("size sides must be multiples of 16 with aspect ratio at most 16:1", code="bad_size")
    if not 921_600 <= w * h <= 4_624_220:
        raise ProviderError("total pixels must be within 921,600-4,624,220 for Seedream 5.0 Pro", code="bad_size")


class DeepixImageProvider:
    name = "deepix"

    def __init__(self, token: str, base_url: str = DEFAULT_BASE, transport: Transport = urllib_transport,
                 model: str = DEFAULT_MODEL, size: str = DEFAULT_SIZE):
        self.client = ApiClient(base_url, token, USER_AGENT, transport)
        self.model = model
        self.size = size
        if model == DEFAULT_MODEL:
            validate_seedream_size(size)
        self._urls: Dict[str, str] = {}

    @classmethod
    def from_env(cls, transport: Transport = urllib_transport) -> "DeepixImageProvider":
        token = clean_token(os.environ.get("DEEPIX_TOKEN", ""))
        if not token:
            raise ProviderError("DEEPIX_TOKEN is not set. Deepix web -> sidebar 'Profile' -> Deepix Token, then set "
                                "it as an environment variable (never commit it).", code="config")
        return cls(token, os.environ.get("DEEPIX_API_BASE", DEFAULT_BASE).strip() or DEFAULT_BASE, transport,
                   os.environ.get("DEEPIX_MODEL", DEFAULT_MODEL), os.environ.get("DEEPIX_SIZE", DEFAULT_SIZE))

    def usage_info(self):
        return self.model, "image"

    def submit(self, prompt: str) -> str:
        if not prompt.strip():
            raise ProviderError("empty prompt", code="bad_prompt")
        fields = {"prompt_key": "2", "message_type": "text-to-image",
                  "prompts": json.dumps([{"key": "positive_prompt", "text": prompt}], ensure_ascii=False),
                  "model": self.model, "size": self.size, "quality": "high"}
        data = self.client.post_multipart(PATH_CREATE, fields, []) or {}
        message_id = data.get("msg_id") or data.get("id")
        if message_id is None:
            raise ProviderError("create returned no message id", code="bad_response")
        return str(message_id)

    def status(self, external_id: str) -> TaskStatus:
        data = self.client.get(PATH_STATUS, {"message_id": external_id}) or {}
        state = str(data.get("status", "")).lower()
        if state in _DONE:
            if not data.get("image_url"):
                return TaskStatus("running")
            self._urls[external_id] = data["image_url"]
            return TaskStatus("succeeded")
        if state in _FAILED:
            return TaskStatus("failed", "task_failed", data.get("msg") or "image generation failed")
        return TaskStatus("running")

    def download(self, external_id: str, dest_path: str) -> str:
        url = self._urls.get(external_id)
        if not url:
            data = self.client.get(PATH_STATUS, {"message_id": external_id}) or {}
            url = data.get("image_url")
        if not url:
            raise ProviderError("no image_url available for this task", code="no_result")
        return self.client.download(url, dest_path)

    def cancel(self, external_id: str) -> None:
        """Deepix exposes no cancel endpoint for image tasks; the local job is cancelled by the runner."""
        return None
