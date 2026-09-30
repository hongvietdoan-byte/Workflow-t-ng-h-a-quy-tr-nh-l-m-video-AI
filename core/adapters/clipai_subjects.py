"""Clip AI Seedance Subject Library ("Kho chủ thể"): upload character images once, reuse them as `asset://` references.

Contract source: clipai 1.3.1 reference ("Personal Seedance subject workflow"):
- POST /api/kling/seedance-user-asset-upload (multipart `file` + `name`) returns an EMPTY success payload, so the new
  asset is found by snapshotting the existing asset ids first and, after the upload, polling the list for a NEW
  asset with exactly the same name.
- An asset is usable only when provider_status == "active" and both `asset_id` and `asset_uri` exist. `failed`
  carries `provider_status_msg` (never resubmitted automatically).
- Active assets have passed the library's real-person review; assets of games with a signed copyright agreement
  (Free Fire) also passed the copyright review. AOV/DF/others: real-person review only.
- Only the numeric list is used for lookups; an unverified id is never turned into an `asset://` uri.
"""
import hashlib
import os
import time
from typing import Callable, Dict, List, Optional

from ..providers import ProviderError
from .clipai import DEFAULT_BASE
from .http import ApiClient, Transport, clean_token, urllib_transport

USER_AGENT = "AIVideoPipeline-ClipAI-Subjects/0.1"
PATH_UPLOAD = "/api/kling/seedance-user-asset-upload"
PATH_LIST = "/api/kling/seedance-user-asset-list"
PATH_UPDATE = "/api/kling/seedance-user-asset-update"
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")
NAME_MAX = 128


def is_active(asset: Dict) -> bool:
    return asset.get("provider_status") == "active" and bool(asset.get("asset_id")) and bool(asset.get("asset_uri"))


class ClipAISubjectLibrary:
    name = "clipai-subjects"

    def __init__(self, token: str, base_url: str = DEFAULT_BASE, transport: Transport = urllib_transport,
                 sleep: Callable[[float], None] = time.sleep, poll_sec: float = 3.0, timeout_sec: float = 180.0):
        self.client = ApiClient(base_url, token, USER_AGENT, transport)
        self._sleep, self.poll_sec, self.timeout_sec = sleep, poll_sec, timeout_sec

    @classmethod
    def from_env(cls, transport: Transport = urllib_transport) -> "ClipAISubjectLibrary":
        token = clean_token(os.environ.get("CLIPAI_TOKEN", ""))
        if not token:
            raise ProviderError("CLIPAI_TOKEN is not set (same token as the video provider; never commit it).",
                                code="config")
        return cls(token, os.environ.get("CLIPAI_API_BASE", DEFAULT_BASE).strip() or DEFAULT_BASE, transport)

    # ---- read ----------------------------------------------------------
    def list_assets(self, asset_type: Optional[str] = None, page_size: int = 100, max_pages: int = 20) -> List[Dict]:
        """Every asset of this token's library (all pages — S4.7: one upload per storyboard frame fills page 1 fast, and an asset past
        it was "not found", so a cached id looked gone and the upload lookup could miss the new asset)."""
        size = min(max(page_size, 1), 100)
        out: List[Dict] = []
        for page in range(1, max(max_pages, 1) + 1):
            data = self.client.get(PATH_LIST, {"asset_type": asset_type, "page": page, "page_size": size}) or {}
            rows = list(data.get("assets") or [])
            out += rows
            count = data.get("count")
            if len(rows) < size or (isinstance(count, int) and len(out) >= count):
                break
        return out

    def get(self, asset_id: str) -> Optional[Dict]:
        return next((a for a in self.list_assets() if a.get("asset_id") == asset_id), None)

    # ---- write ---------------------------------------------------------
    def upload(self, path: str, name: str, wait: bool = True) -> Dict:
        """Upload one image/video as a subject and (by default) wait until the library made it active."""
        name = (name or "").strip()
        if not name or len(name) > NAME_MAX:
            raise ProviderError(f"subject name must be 1-{NAME_MAX} characters", code="bad_input")
        if os.path.splitext(path)[1].lower() not in IMAGE_EXT + (".mp4",):
            raise ProviderError("subject file must be JPG, JPEG, PNG, WEBP or MP4", code="bad_input")
        if not os.path.isfile(path):
            raise ProviderError(f"file not found: {path}", code="bad_input")
        with open(path, "rb") as f:
            content = f.read()
        before = {a.get("asset_id") for a in self.list_assets()}
        self.client.post_multipart(PATH_UPLOAD, {"name": name}, [("file", os.path.basename(path), content)])
        if not wait:
            return {}
        waited = 0.0
        while True:
            fresh = [a for a in self.list_assets() if a.get("asset_id") not in before and a.get("name") == name]
            if fresh:
                asset = fresh[0]
                status = asset.get("provider_status")
                if status == "failed":
                    raise ProviderError(asset.get("provider_status_msg") or "the library rejected this file",
                                        code="asset_failed")
                if is_active(asset):
                    return asset
            if waited >= self.timeout_sec:
                raise ProviderError("the library is still processing this subject; use 'refresh' in a minute",
                                    code="timeout", transient=True)
            self._sleep(self.poll_sec)
            waited += self.poll_sec

    def rename(self, asset_id: str, new_name: str) -> None:
        if self.get(asset_id) is None:
            raise ProviderError("asset not found in your library", code="not_found")
        self.client.post_json(PATH_UPDATE, {"asset_id": asset_id, "name": new_name.strip()})


class MockSubjectLibrary:
    """Offline stand-in: every upload is 'active' at once with a deterministic id (no state kept between runs)."""
    name = "mock-subjects"

    def list_assets(self, asset_type=None, page_size=100):
        return []

    def get(self, asset_id):
        if str(asset_id).startswith("asset-mock-"):
            return {"asset_id": asset_id, "asset_uri": f"asset://{asset_id}", "provider_status": "active", "name": asset_id}
        return None

    def upload(self, path, name, wait=True):
        if not name or not name.strip():
            raise ProviderError("subject name must not be empty", code="bad_input")
        asset_id = "asset-mock-" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
        return {"asset_id": asset_id, "asset_uri": f"asset://{asset_id}", "name": name, "provider_status": "active",
                "asset_type": "image"}

    def rename(self, asset_id, new_name):
        return None
