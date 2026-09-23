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
- Reference video for motion (not appearance): Kling `video_list: [{video_url, refer_type, keep_original_sound}]`
  uploaded as multipart field `video_files` (`refer_type` "feature" = copy the motion/style into a NEW clip,
  "base" = edit the given clip; mutually exclusive with `sound: "on"`). Seedance instead takes a `content[]` item
  `{type: "video_url", video_url: {...}, role: "reference_video"}`, also uploaded as `video_files`; Seedance has
  no feature/base distinction, the reference is always a motion example. See docs/CLIPAI_FEATURES.md #18.
"""
import json
import os
from typing import Dict, List, Optional, Tuple

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


def _upload_name(path: str, content: bytes) -> str:
    """Name the upload after its real format (Deepix returns JPEG even though we save it as .png)."""
    stem = os.path.splitext(os.path.basename(path))[0]
    if content[:3] == bytes([0xFF, 0xD8, 0xFF]):
        return stem + ".jpg"
    if content[:4] == bytes([0x89]) + b"PNG":
        return stem + ".png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return stem + ".webp"
    return os.path.basename(path)


def effective_duration(canonical: str, family: str, duration: float) -> int:
    """Duration actually requested from the API (clamped to what each model family accepts)."""
    if family == "omni":
        return int(min(max(round(duration), 3), 15))
    limit = 30 if canonical == "dreamina-seedance-2-5-260628" else 15
    return int(min(max(round(duration), 4), limit))


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
    supports_aspect = True        # accepts aspect_ratio= / resolution= per job (project frame format, per-scene model tier)

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

    def usage_info(self, model: Optional[str] = None, duration: float = 5, resolution: Optional[str] = None):
        """(canonical model, quality tier, billed seconds) for the cost ledger."""
        canonical, family = resolve_model(model)
        tier = self.kling_mode if family == "omni" else (resolution or self.resolution)
        return canonical, tier, effective_duration(canonical, family, duration)

    # ---- submit ---------------------------------------------------------
    def submit(self, image_path: str, prompt: str, negative_prompt: Optional[str], duration_sec: float,
               model: Optional[str] = None, with_audio: bool = False, subjects: Optional[list] = None,
              image_references: Optional[list] = None, reference_video: Optional[dict] = None,
              aspect_ratio: Optional[str] = None, resolution: Optional[str] = None,
              multi_prompt: Optional[list] = None, last_frame: Optional[str] = None) -> str:
        """aspect_ratio / resolution override the provider defaults for this job (project frame format, per-scene tier).
        image_references: this project's own resource-library pictures (local files, [{"path","label","role"}], from
        `assets.scene_references`) — no separate Subject Library upload/approval needed. `subjects`: Subject Library entries
        already hosted on Clip AI ([{"name","uri"}]). Seedance only; both share one reference-image budget, local pictures first.
        reference_video: {"path": local file, "refer_type": "feature"|"base"} — a video the generator copies MOTION from
        (identity/appearance still comes only from `image_path`/`image_references`, never from this video). `refer_type`
        only applies to Kling (Omni/O1); Seedance always treats the video as a motion example. Mutually exclusive with
        `with_audio` on Kling (the vendor API rejects `sound=on` together with a reference video).
        last_frame: a local picture the clip must END on (Seedance `role: last_frame`; v3 shots that continue into the next shot).
        It is sent as a first+last frame clip, without the extra reference pictures (the two frames already show the characters);
        still to be confirmed on the real API (plan v3, GĐ6)."""
        canonical, family = resolve_model(model)
        if with_audio and canonical == "kling-video-o1":
            raise ProviderError("kling-video-o1 does not support generated sound (use kling-v3-omni or Seedance)",
                                code="unsupported_option")
        if reference_video and with_audio and family == "omni":
            raise ProviderError("Kling rejects a reference video together with generated sound (sound=on); turn "
                                "audio off or drop the reference video", code="unsupported_option")
        video_files: List[Tuple[str, bytes]] = []
        if reference_video:
            vpath = reference_video["path"]
            if not os.path.exists(vpath):
                raise ProviderError(f"reference video not found: {vpath}", code="missing_video")
            with open(vpath, "rb") as f:
                vcontent = f.read()
            video_files.append((_upload_name(vpath, vcontent), vcontent))
        text = prompt.strip()
        if self.negative == "append" and negative_prompt:
            text += f"\nAvoid: {negative_prompt}"
        extra_files: List[Tuple[str, bytes]] = []
        content_refs: List[Dict] = []                     # [{"note_label", "note_role"}] in the order attached, for the @Image note
        if last_frame and family == "seedance":           # first + last frame clip: the two frames carry the characters
            text += " The clip starts on the first image and must end exactly on the last image (same people, place and light)."
        elif family == "seedance":
            cap = 29 if canonical == "dreamina-seedance-2-5-260628" else 8  # image cap minus the first-frame image
            for ref in (image_references or [])[:cap]:
                try:
                    with open(ref["path"], "rb") as f:
                        data = f.read()
                except OSError:
                    continue                               # a missing/unreadable file must not fail the whole submit
                if not data:
                    continue
                extra_files.append((_upload_name(ref["path"], data), data))
                content_refs.append({"kind": "local", "label": ref["label"], "role": ref.get("role", "character")})
            remaining = cap - len(content_refs)
            for s in (subjects or [])[:max(remaining, 0)]:
                if not s.get("uri"):
                    continue
                content_refs.append({"kind": "hosted", "uri": s["uri"], "label": s["name"], "role": "character"})
            if content_refs:  # Seedance wants every reference to have a stated job (@Image 1 is the first frame, so refs start at 2)
                people = [r for r in content_refs if r["role"] != "location"]
                text += "\n" + " ".join(
                    f"@Image {i} is the location {r['label']}: keep the look of this environment" if r["role"] == "location"
                    else f"@Image {i} is {r['label']}: keep exactly this person's face, hair and outfit; do not swap or blend with other people in the scene"
                    for i, r in enumerate(content_refs, start=2))
                if len(people) > 1:
                    text += ". Each person keeps only the look of their own reference image."
        limit = PROMPT_LIMITS["kling" if family == "omni" else canonical]
        if len(text) > limit:
            raise ProviderError(f"prompt is {len(text)} characters; {canonical} allows at most {limit}",
                                code="prompt_too_long")
        if not os.path.exists(image_path):
            raise ProviderError(f"reference image not found: {image_path}", code="missing_image")
        with open(image_path, "rb") as f:
            content = f.read()
        image = (_upload_name(image_path, content), content)
        if multi_prompt and family != "omni":
            raise ProviderError("multi-shot chỉ có ở Kling Omni", code="unsupported_option")
        end_image = None
        if last_frame and family == "seedance":
            if not os.path.exists(last_frame):
                raise ProviderError(f"last frame image not found: {last_frame}", code="missing_image")
            with open(last_frame, "rb") as f:
                end_bytes = f.read()
            end_image = (_upload_name(last_frame, end_bytes), end_bytes)
        if family == "omni":
            ctx = {"model_name": canonical, "multi_shot": 0, "prompt": text, "sound": "on" if with_audio else "off",
                   "image_list": [{"image_url": "", "type": "first_frame"}], "mode": self.kling_mode,
                   "aspect_ratio": aspect_ratio or self.aspect_ratio, "duration": str(effective_duration(canonical, family, duration_sec)),
                   "video_num": 1}
            if reference_video:
                ctx["video_list"] = [{"video_url": "", "refer_type": reference_video.get("refer_type", "feature"),
                                      "keep_original_sound": "no"}]
            if multi_prompt:                   # experiment: several shots in one generation (reference.md Text2VideoO1SubmitRequest)
                shots = [{"index": i, "prompt": str(sh["prompt"])[:2500], "duration": str(effective_duration(canonical, family, sh["duration"]))}
                         for i, sh in enumerate(multi_prompt, 1)]
                ctx.update(multi_shot=1, shot_type="customize", multi_prompt=shots,
                           duration=str(sum(int(sh["duration"]) for sh in shots)))
                ctx.pop("prompt", None)
            path = PATH_KLING
        else:
            ctx = {"model_name": canonical,
                   "content": [{"type": "text", "text": text},
                               {"type": "image_url", "image_url": {"url": ""}, "role": "first_frame"}]
                   + ([{"type": "image_url", "image_url": {"url": ""}, "role": "last_frame"}] if end_image else [])
                   + [{"type": "image_url", "image_url": {"url": "" if r["kind"] == "local" else r["uri"]}, "role": "reference_image"}
                      for r in content_refs]
                   + ([{"type": "video_url", "video_url": {"url": ""}, "role": "reference_video"}] if reference_video else []),
                   "resolution": resolution or self.resolution, "ratio": aspect_ratio or self.aspect_ratio,
                   "duration": effective_duration(canonical, family, duration_sec), "generate_audio": bool(with_audio),
                   "camera_fixed": False, "seed": -1, "video_num": 1}
            path = PATH_SEEDANCE
        files = ([("image_files", image[0], image[1])] + ([("image_files", end_image[0], end_image[1])] if end_image else [])
                 + [("image_files", name, data) for name, data in extra_files]
                + [("video_files", name, data) for name, data in video_files])
        data = self.client.post_multipart(path, {"ctx": json.dumps(ctx, ensure_ascii=False)}, files)
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
