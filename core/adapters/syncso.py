"""sync.so lip-sync adapter (post lip sync of a finished clip to our voice line; kế hoạch V4 GĐ3, docs/NGHIEN_CUU_KHOP_MOI.md).

API (sync.so docs, read 2026-09-25): POST https://api.sync.so/v2/generate, header `x-api-key`, body {model, input: [{type: "video",
url}, {type: "audio", url}], options: {sync_mode: bounce|loop|cut_off|silence|remap}}; GET /v2/generate/{id} -> status PENDING /
PROCESSING / COMPLETED / FAILED / REJECTED, `outputUrl`, `error`. A multipart form uploads local files, with input/options as JSON
strings — the docs do not name the file fields: `SYNC_FILE_FIELDS` (default "video,audio") is a guess until the first real call.
Needs SYNC_API_KEY (a sync.so plan with API access, from $5/month). Model: SYNC_MODEL (default lipsync-2-pro, ~$0.084/s).
"""
import json
import os
from typing import Optional

from ..providers import ProviderError, TaskStatus
from .http import ApiClient, Transport, clean_token, urllib_transport

DEFAULT_BASE = "https://api.sync.so"
USER_AGENT = "AIVideoPipeline-Sync/0.1"
_STATE = {"PENDING": "running", "PROCESSING": "running", "COMPLETED": "succeeded", "FAILED": "failed", "REJECTED": "failed"}


class SyncLipSync:
    name = "syncso"

    def __init__(self, key: str, base_url: str = DEFAULT_BASE, transport: Transport = urllib_transport, model: str = "lipsync-2-pro",
                 sync_mode: str = "cut_off"):
        self.client = ApiClient(base_url, key, USER_AGENT, transport, auth_header="x-api-key", auth_prefix="")
        self.model, self.sync_mode = model, sync_mode
        self._urls = {}

    @classmethod
    def from_env(cls, transport: Transport = urllib_transport) -> "SyncLipSync":
        key = clean_token(os.environ.get("SYNC_API_KEY", ""))
        if not key:
            raise ProviderError("SYNC_API_KEY chưa đặt (sync.so → API keys), khớp môi sau không chạy được", code="config")
        return cls(key, os.environ.get("SYNC_API_BASE", DEFAULT_BASE), transport, os.environ.get("SYNC_MODEL", "lipsync-2-pro"))

    def submit(self, video_path: str, audio_path: str) -> str:
        vf, af = (os.environ.get("SYNC_FILE_FIELDS", "video,audio").split(",") + ["video", "audio"])[:2]
        files = []
        for field, path in ((vf.strip(), video_path), (af.strip(), audio_path)):
            with open(path, "rb") as f:
                files.append((field, os.path.basename(path), f.read()))
        fields = {"model": self.model, "input": json.dumps([{"type": "video"}, {"type": "audio"}]),
                  "options": json.dumps({"sync_mode": self.sync_mode})}
        data = self.client.post_multipart("/v2/generate", fields, files, raw=True) or {}
        task = data.get("id")
        if not task:
            raise ProviderError(f"sync.so không trả id: {str(data)[:200]}", code="bad_response")
        return str(task)

    def status(self, task: str) -> TaskStatus:
        data = self.client.get(f"/v2/generate/{task}", None, raw=True) or {}
        state = _STATE.get(str(data.get("status", "")).upper(), "running")
        if state == "succeeded":
            if not data.get("outputUrl"):
                return TaskStatus("running")
            self._urls[task] = data["outputUrl"]
        if state == "failed":
            return TaskStatus("failed", data.get("errorCode") or "lipsync_failed", data.get("error") or "sync.so failed")
        return TaskStatus(state)

    def download(self, task: str, dest: str) -> str:
        url = self._urls.get(task) or (self.client.get(f"/v2/generate/{task}", None, raw=True) or {}).get("outputUrl")
        if not url:
            raise ProviderError("sync.so chưa có outputUrl", code="no_result")
        return self.client.download(url, dest)


def from_env_or_none() -> Optional[SyncLipSync]:
    try:
        return SyncLipSync.from_env()
    except ProviderError:
        return None
