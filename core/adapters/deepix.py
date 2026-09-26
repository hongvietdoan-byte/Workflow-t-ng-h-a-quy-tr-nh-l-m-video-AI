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
PATH_CUTOUT = "/ai/birefnet/predict"      # one-click background removal (BiRefNet), deepix-1.4.1 reference.md
DEFAULT_MODEL = "dola-seedream-5-0-pro-260628"
MAX_REFERENCES = 10          # Seedream 5.0 Pro takes at most 10 reference pictures
DEFAULT_SIZE = "2048x1152"  # 16:9, both sides multiples of 16, inside the Seedream Pro pixel bounds

_DONE = {"completed", "succeed", "success"}
_FAILED = {"failed", "error"}


MAX_REFERENCE_BYTES = 10 * 1024 * 1024


def reference_problem(path: str) -> Optional[str]:
    """Why this reference picture cannot be sent (Vietnamese, for the diag), or None."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return "không đọc được file"
    if size <= 0:
        return "file rỗng"
    if size > MAX_REFERENCE_BYTES:
        return f"{size / 1024 / 1024:.1f} MB > 10 MB"
    return None


def _read_references(references, model: str) -> list:
    """The files for `file[]`, in order. W10 / luật 1: a picture that cannot go (unreadable, > 10 MB, over the model's limit) is REFUSED
    here instead of dropped — the prompt numbers the pictures ("Image 2 is KELLY"), so sending fewer would shift every name."""
    from .. import image_models
    refs = list(references or [])
    cap = image_models.max_refs(model, MAX_REFERENCES)
    if len(refs) > cap:
        raise ProviderError(f"{len(refs)} reference pictures, the model takes at most {cap}", code="bad_reference")
    files = []
    for i, path in enumerate(refs, 1):
        problem = reference_problem(path)
        if problem is None:
            try:
                with open(path, "rb") as f:
                    content = f.read()
            except OSError:
                problem = "không đọc được file"
        if problem:
            raise ProviderError(f"reference picture {i} ({os.path.basename(path)}): {problem}", code="bad_reference")
        files.append((path, content))
    return files


def validate_seedream_size(size: str) -> None:
    try:
        w, h = (int(x) for x in size.lower().split("x"))
    except ValueError:
        raise ProviderError(f"size must look like 2048x1152, got '{size}'", code="bad_size") from None
    if w % 16 or h % 16 or max(w, h) / min(w, h) > 16:
        raise ProviderError("size sides must be multiples of 16 with aspect ratio at most 16:1", code="bad_size")
    if not 921_600 <= w * h <= 4_624_220:
        raise ProviderError("total pixels must be within 921,600-4,624,220 for Seedream 5.0 Pro", code="bad_size")


def flatten_transparency(content: bytes, filename: str):
    """A transparent PNG (cut-out character art) is sent on a light-grey background: the model would otherwise read the see-through pixels
    as black. Anything else is returned unchanged."""
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(content))
        if img.mode not in ("RGBA", "LA", "P") or (img.mode == "P" and "transparency" not in img.info):
            return content, filename
        rgba = img.convert("RGBA")
        if rgba.getchannel("A").getextrema()[0] == 255:
            return content, filename                            # has an alpha channel but nothing is transparent
        background = Image.new("RGB", rgba.size, (232, 232, 232))
        background.paste(rgba, mask=rgba.getchannel("A"))
        out = io.BytesIO()
        background.save(out, "PNG")
        return out.getvalue(), os.path.splitext(filename)[0] + ".png"
    except Exception:  # noqa: BLE001 - not a picture PIL can read: send as it is
        return content, filename


class DeepixImageProvider:
    name = "deepix"
    supports_aspect = True        # accepts size= per job (project frame format)
    supports_model = True         # accepts model= per job (the project's picture model, core.image_models)
    supports_storyboard = True    # accepts storyboard= per job (a frame of a scene storyboard, prompt_key 14 — core/scene_storyboard.py)

    def __init__(self, token: str, base_url: str = DEFAULT_BASE, transport: Transport = urllib_transport,
                 model: str = DEFAULT_MODEL, size: str = DEFAULT_SIZE):
        self.client = ApiClient(base_url, token, USER_AGENT, transport)
        self.model = model
        self.size = size
        self._check(model, size)
        self._urls: Dict[str, str] = {}

    @staticmethod
    def _check(model: str, size: Optional[str]) -> None:
        """W10: the model's size rule (data/provider_rules.json) before anything is sent."""
        from .. import image_models
        problem = image_models.size_problem(model, size)
        if problem:
            raise ProviderError(problem, code="bad_size")

    @classmethod
    def from_env(cls, transport: Transport = urllib_transport) -> "DeepixImageProvider":
        token = clean_token(os.environ.get("DEEPIX_TOKEN", ""))
        if not token:
            raise ProviderError("DEEPIX_TOKEN is not set. Deepix web -> sidebar 'Profile' -> Deepix Token, then set "
                                "it as an environment variable (never commit it).", code="config")
        return cls(token, os.environ.get("DEEPIX_API_BASE", DEFAULT_BASE).strip() or DEFAULT_BASE, transport,
                   os.environ.get("DEEPIX_MODEL", DEFAULT_MODEL), os.environ.get("DEEPIX_SIZE", DEFAULT_SIZE))

    def usage_info(self, model: Optional[str] = None):
        return model or self.model, "image"

    def submit(self, prompt: str, references=None, size: Optional[str] = None, model: Optional[str] = None,
               storyboard: Optional[Dict] = None) -> str:
        """Text-to-image, or image-to-image when reference picture paths are given (prompt_key 1, pictures in `file[]`, each up to 10 MB).
        `size` overrides the default (e.g. 1152x2048 for a vertical project; 'auto' lets a GPT model decide), `model` the provider's
        model (per project). Size and reference count are checked against the model's rules before sending."""
        if storyboard:
            return self.submit_storyboard_frame(prompt, references, storyboard["story_text"], storyboard["storyboard_id"],
                                                storyboard["frame_index"], storyboard["group_size"], storyboard["ref_mode"],
                                                storyboard.get("image_mapping", ""), size, model)
        from .. import image_models
        model = model or self.model
        size = size or self.size
        self._check(model, size)
        if not prompt.strip():
            raise ProviderError("empty prompt", code="bad_prompt")
        files = []
        for path, content in _read_references(references, model):   # refused (not dropped): the prompt numbers these pictures
            content, name = flatten_transparency(content, os.path.basename(path))
            files.append(("file[]", name, content))
        fields = {"prompt_key": "1" if files else "2", "message_type": "image-to-image" if files else "text-to-image",
                  "prompts": json.dumps([{"key": "positive_prompt", "text": prompt}], ensure_ascii=False),
                  "model": model, "quality": "high"}
        if str(size).lower() != "auto":                # 'auto': the field is left out (Deepix reference.md)
            fields["size"] = size
        data = self.client.post_multipart(PATH_CREATE, fields, files) or {}
        message_id = data.get("msg_id") or data.get("id")
        if message_id is None:
            raise ProviderError("create returned no message id", code="bad_response")
        return str(message_id)

    def submit_storyboard_frame(self, prompt: str, references, story_text: str, storyboard_id: str, frame_index: int,
                                group_size: int, ref_mode: str, image_mapping: str, size: Optional[str] = None,
                                model: Optional[str] = None) -> str:
        """One frame of a Deepix storyboard — the same call the web Weave Canvas makes for its Storyboard node (read from
        deepix.ingarena.net/weave/app.js, 2026-09-25): prompt_key 14, message_type "storyboard", and extra prompt keys that tell the
        server this frame belongs to a group (story_text, storyboard_id, frame_index, group_size, storyboard_size_profile, ref_mode,
        image_mapping). ref_mode "global" = shared references + frame 1 as the continuity anchor; "sequential" = frame 1 + previous."""
        from .. import image_models
        model = model or self.model
        size = size or self.size
        self._check(model, size)
        files = []
        for i, (path, content) in enumerate(_read_references(references, model)):
            content, name = flatten_transparency(content, os.path.basename(path))
            files.append(("file[]", f"ref_{i + 1}_{name}", content))
        prompts = [{"key": "positive_prompt", "text": prompt}, {"key": "story_text", "text": story_text},
                   {"key": "storyboard_id", "text": storyboard_id}, {"key": "frame_index", "text": str(frame_index)},
                   {"key": "group_size", "text": str(group_size)}, {"key": "storyboard_size_profile", "text": "clipai-video"},
                   {"key": "ref_mode", "text": ref_mode}]
        if image_mapping:
            prompts.append({"key": "image_mapping", "text": image_mapping})
        fields = {"prompt_key": "14", "message_type": "storyboard", "prompts": json.dumps(prompts, ensure_ascii=False),
                  "model": model, "quality": "high"}
        if str(size).lower() != "auto":
            fields["size"] = size
        data = self.client.post_multipart(PATH_CREATE, fields, files) or {}
        message_id = data.get("msg_id") or data.get("message_id") or data.get("id")
        if message_id is None:
            raise ProviderError("storyboard frame: create returned no message id", code="bad_response")
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


def cutout(provider: "DeepixImageProvider", path: str, dest_path: str, weights: str = "General-dynamic") -> str:
    """Transparent PNG of the person in `path` (Deepix one-click cutout, no polling). Used by the previz so the layout shows the
    real character instead of a coloured mannequin. Raises ProviderError."""
    import base64
    with open(path, "rb") as f:
        content = f.read()
    if len(content) > 10 * 1024 * 1024:
        raise ProviderError("ảnh lớn hơn 10 MB", code="too_large")
    data = provider.client.post_multipart(PATH_CUTOUT, {"weights_file": weights, "resolution": "1024x1024", "source": "AIVideoPipeline"},
                                          [("file", os.path.basename(path), content)], raw=True) or {}
    result = data.get("result") or {}
    if data.get("status") != "success" or not (result.get("processed_image_base64") or result.get("processed_image_url")):
        raise ProviderError(f"cutout failed: {str(data)[:200]}", code="cutout_failed")
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    if result.get("processed_image_base64"):
        raw = result["processed_image_base64"].split(",", 1)[-1]
        with open(dest_path, "wb") as f:
            f.write(base64.b64decode(raw))
        return dest_path
    return provider.client.download(result["processed_image_url"], dest_path)
