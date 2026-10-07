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
import math
import os
import time
from typing import Dict, List, Optional, Tuple

from ..providers import RISK_CONTROL, ProviderError, TaskStatus
from .http import ApiClient, Transport, clean_token, urllib_transport

DEFAULT_BASE = "https://clipai.ingarena.net"
USER_AGENT = "AIVideoPipeline-ClipAI/0.1"

PATH_KLING = "/api/kling/omni-video-submit"
PATH_SEEDANCE = "/api/kling/seedance-video-submit"
# Seedance refuses a first frame together with reference pictures ("first/last frame content cannot be mixed with reference media
# content", real run 2026-09-24): the approved start picture (drawn from the character references) carries the people instead.
SEEDANCE_REFS_WITH_FIRST_FRAME = False
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
MIN_REFERENCE_VIDEO_S = 3.0      # ClipAI refused a 2.2 s reference video (thử #11, 2026-09-30): "Video duration can not less than 3s"
REFERENCE_VIDEO_WIDTH = (700, 4553)   # "The video width should not be less than 700px and larger than 4553px" (thử #11, 30/09)


def _video_width(path: str) -> Optional[int]:
    return _probe(path)[0]


def _probe(path: str) -> Tuple[Optional[int], Optional[str]]:
    """(width, sample aspect ratio "1:1" …) of a video's first stream; (None, None) when ffprobe cannot tell."""
    info = _probe_video(path)
    return info.get("width"), info.get("sar")


def _probe_video(path: str) -> Dict:
    """{width, height, sar, fps, duration} of a video's first stream (keys missing when ffprobe cannot tell)."""
    import subprocess
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height,sample_aspect_ratio,r_frame_rate:format=duration", "-of", "json", path],
                             capture_output=True, text=True, timeout=30).stdout
        data = json.loads(out or "{}")
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}
    st = (data.get("streams") or [{}])[0]
    info = {}
    if st.get("width"):
        info["width"], info["height"] = int(st["width"]), int(st.get("height") or 0)
    if st.get("sample_aspect_ratio"):
        info["sar"] = st["sample_aspect_ratio"]
    num, _, den = str(st.get("r_frame_rate") or "").partition("/")
    try:
        info["fps"] = float(num) / float(den or 1)
    except ValueError:
        pass
    try:
        info["duration"] = float((data.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        pass
    return info


# Reference-video rules per service (official docs read 2026-09-30 — docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md — plus ClipAI's own
# answers in test #11: < 3 s, < 700 px and non-square pixels were refused).
VIDEO_RULES = {
    "omni": {"count": 1, "seconds": (3.0, 15.5), "side": (700, 4553), "pixels": (0, 8_294_400), "fps": (24, 60)},
    "seedance": {"count": 3, "count_2_5": 10, "seconds": (2.0, 30.0), "total": 30.0, "side": (300, 6000),
                 "pixels": (407_696, 8_295_044), "fps": (24, 60)},
}


# S4.12: the source clip of a Seedance 2.5 video edit (web app limits, bundle 3634, 2026-10-01: 2.5 edit needs ≥ 4 s; ≤ 30 s;
# 409 600 – 2 086 876 pixels per frame; aspect 0.4 – 2.5).
VIDEO_EDIT_RULES = {"seconds": (4.0, 30.0), "pixels": (409_600, 2_086_876), "ratio": (0.4, 2.5)}


def video_edit_problems(info: Dict) -> List[str]:
    """Why ClipAI would refuse this clip as the master of a video edit ([] = fine). A clip ffprobe cannot read is a problem (luật 1)."""
    out = []
    r = VIDEO_EDIT_RULES
    d = info.get("duration")
    if d is None:
        out.append("không đo được độ dài clip (ffprobe)")
    elif not r["seconds"][0] <= d <= r["seconds"][1]:
        out.append(f"clip dài {d:.2f} s, cần {r['seconds'][0]:.0f}–{r['seconds'][1]:.0f} s")
    w, h = info.get("width"), info.get("height")
    if not w or not h:
        out.append("không đo được cỡ khung (ffprobe)")
    else:
        if not r["pixels"][0] <= w * h <= r["pixels"][1]:
            out.append(f"khung {w}×{h} = {w * h} điểm ảnh, cần {r['pixels'][0]}–{r['pixels'][1]}")
        if not r["ratio"][0] <= w / h <= r["ratio"][1]:
            out.append(f"tỉ lệ khung {w}×{h} ngoài {r['ratio'][0]}–{r['ratio'][1]}")
    return out


IMAGE_RULES = {"omni": {"side": (300, 100_000), "ratio": (0.4, 2.5)}, "seedance": {"side": (300, 6000), "ratio": (0.4, 2.5)}}


def reference_image_problems(family: str, sizes: List[Tuple[int, int]], sides: bool = True) -> List[str]:
    """What ClipAI would refuse in reference pictures: width / height 0.4–2.5 (Kling 1:2.5–2.5:1; Seedance 2.5 — refused a 3.74-wide
    skill sheet in test T4 30/09), sides ≥ 300 px (Seedance ≤ 6000)."""
    r = IMAGE_RULES["omni" if family == "omni" else "seedance"]
    out = []
    for k, (w, h) in enumerate(sizes, 1):
        if not (w and h):
            continue
        if not r["ratio"][0] - 1e-3 <= w / h <= r["ratio"][1] + 1e-3:
            out.append(f"ảnh {k} ({w}×{h}) tỉ lệ {w / h:.2f} — cần {r['ratio'][0]}–{r['ratio'][1]}")
        if sides and (min(w, h) < r["side"][0] or max(w, h) > r["side"][1]):
            out.append(f"ảnh {k} ({w}×{h}) — cạnh cần {r['side'][0]}–{r['side'][1]} px")
    return out


def image_sizes_of(blobs: List[bytes]) -> List[Tuple[int, int]]:
    """(width, height) of picture bytes ((0, 0) = unreadable, not judged)."""
    import io
    out = []
    for b in blobs:
        try:
            from PIL import Image as _Im
            with _Im.open(io.BytesIO(b)) as im:
                out.append(im.size)
        except Exception:  # noqa: BLE001 - not a picture PIL knows: the server says it
            out.append((0, 0))
    return out


def reference_video_problems(family: str, canonical: str, infos: List[Dict]) -> List[str]:
    """What ClipAI would refuse in these reference videos ({width, height, sar, fps, duration} each; missing keys are not judged)."""
    r = VIDEO_RULES["omni" if family == "omni" else "seedance"]
    out = []
    cap = r.get("count_2_5", r["count"]) if canonical == "dreamina-seedance-2-5-260628" else r["count"]
    if len(infos) > cap:
        out.append(f"{len(infos)} video tham chiếu — {canonical} nhận tối đa {cap}")
    total = 0.0
    for k, v in enumerate(infos, 1):
        tag = f"video {k}"
        d = v.get("duration")
        if d is not None:
            total += d
            if not r["seconds"][0] - 0.05 <= d <= r["seconds"][1] + 0.05:
                out.append(f"{tag} dài {d:.1f} s — cần {r['seconds'][0]:g}–{r['seconds'][1]:g} s")
        w, h = v.get("width"), v.get("height")
        if w and not r["side"][0] <= w <= r["side"][1]:
            out.append(f"{tag} rộng {w} px — cần {r['side'][0]}–{r['side'][1]} px")
        if h and not r["side"][0] <= h <= r["side"][1]:
            out.append(f"{tag} cao {h} px — cần {r['side'][0]}–{r['side'][1]} px")
        if w and h and not r["pixels"][0] <= w * h <= r["pixels"][1]:
            out.append(f"{tag} {w}×{h} = {w * h} điểm ảnh — cần {r['pixels'][0]}–{r['pixels'][1]}")
        f = v.get("fps")
        if f and not r["fps"][0] - 0.5 <= f <= r["fps"][1] + 0.5:
            out.append(f"{tag} {f:g} khung/giây — cần {r['fps'][0]}–{r['fps'][1]}")
        if v.get("sar") not in (None, "1:1", "0:1", "N/A"):
            out.append(f"{tag} điểm ảnh không vuông (SAR {v['sar']}) — xuất lại với setsar=1")
    if r.get("total") and total > r["total"] + 0.05:
        out.append(f"tổng video tham chiếu {total:.1f} s — tối đa {r['total']:g} s")
    return out


PROMPT_LIMITS = {"kling": 2500, "dreamina-seedance-2-0-260128": 4000, "dreamina-seedance-2-0-fast-260128": 4000,
                 "dreamina-seedance-2-5-260628": 5000}
_RISK_HINTS = ("risk control", "risk-control", "风控", "content policy", "moderation", "copyright", "版权", "审核")
_UNSEEN_LIMIT = 12
# A task_id ClipAI answered with but never lists: the order was accepted and dropped (real runs 2026-09-22/24: 16 Kling tasks marked
# "not found" were absent from the account's WHOLE list — 136 tasks — so nothing was generated or kept). After this many polls without
# ever seeing it the job is reported as NOT_CREATED: nothing to wait for and nothing billed, so it can be sent again at once.
NOT_CREATED = "not_created"
_NOT_CREATED_LIMIT = 6
STATUS_PAGES = 3          # list pages scanned per status check (50 tasks each): a running task can sit below the first page
DEEP_PAGES = 12           # one deeper look before calling a task "not created" when newer tasks fill the first pages


class RamTaskMemory:
    """Per-task counters kept in this object only (tests, one-off scripts). sent_at unknown -> the pages read are trusted."""

    def __init__(self):
        self._seen, self._unseen = set(), {}

    def state(self, external_id: str):
        return external_id in self._seen, self._unseen.get(external_id, 0), float("inf")

    def unseen(self, external_id: str) -> int:
        self._unseen[external_id] = self._unseen.get(external_id, 0) + 1
        return self._unseen[external_id]

    def seen(self, external_id: str) -> None:
        self._seen.add(external_id)
        self._unseen.pop(external_id, None)


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


def _with_avoid(prompt: str, avoid: str) -> str:
    """M19: a multi-shot request drops the single prompt (and the "Avoid: …" appended to it) — each shot carries it instead when it
    still fits the 512 characters of a shot prompt (the shot's own words come first)."""
    prompt = _shorten(prompt, KLING_SHOT_PROMPT_LIMIT)
    return prompt + avoid if avoid and len(prompt) + len(avoid) <= KLING_SHOT_PROMPT_LIMIT else prompt


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
        return int(min(max(math.floor(duration + 0.5), 3), 15))
    limit = 30 if canonical == "dreamina-seedance-2-5-260628" else 15
    return int(min(max(math.floor(duration + 0.5), 4), limit))       # M11: half up (round() made 4.5 s into 4 s)


KLING_SHOT_PROMPT_LIMIT = 512   # each shot of a Kling multi-shot request (API: "multiPrompt[0].prompt: size must be between 0 and 512")


def _shorten(text: str, limit: int) -> str:
    """At most `limit` characters, cut after the last full sentence (or word) that fits."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(".\n"))
    return cut[:end + 1] if end > limit // 2 else cut[:cut.rfind(" ")].rstrip(",;: ")


REAL_PERSON = "real_person"   # Seedance refuses a start picture that looks like a real person (privacy filter)
_REAL_PERSON_HINTS = ("may contain real person", "privacyinformation")


def classify_failure(message: str) -> str:
    low = (message or "").lower()
    if any(h in low for h in _REAL_PERSON_HINTS):
        return REAL_PERSON
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
    supports_subjects = True      # S4.7: reference_only entries may be Subject Library assets {"uri": "asset://…"}

    def __init__(self, token: str, base_url: str = DEFAULT_BASE, transport: Transport = urllib_transport,
                 aspect_ratio: str = "16:9", kling_mode: str = "pro", resolution: str = "720p",
                 negative: str = "ignore", list_ttl: float = 0, status_pages: int = STATUS_PAGES):
        self.client = ApiClient(base_url, token, USER_AGENT, transport)
        self.aspect_ratio, self.kling_mode, self.resolution, self.negative = aspect_ratio, kling_mode, resolution, negative
        self._urls: Dict[str, str] = {}
        self.memory = RamTaskMemory()                # per-task "seen / polls unseen / sent at"; the runner swaps in the database one
        self.list_ttl, self.status_pages = list_ttl, max(1, int(status_pages))
        self._pages: Dict[Tuple[str, int], Tuple[float, list]] = {}   # one list read serves every job polled in the same round

    @classmethod
    def from_env(cls, transport: Transport = urllib_transport) -> "ClipAIVideoProvider":
        token = clean_token(os.environ.get("CLIPAI_TOKEN", ""))
        if not token:
            raise ProviderError("CLIPAI_TOKEN is not set. Log in to clipai.ingarena.net -> avatar -> API Token, "
                                "then set it as an environment variable (never commit it).", code="config")
        return cls(token, os.environ.get("CLIPAI_API_BASE", DEFAULT_BASE).strip() or DEFAULT_BASE, transport,
                   os.environ.get("CLIPAI_ASPECT_RATIO", "16:9"), os.environ.get("CLIPAI_KLING_MODE", "pro"),
                   os.environ.get("CLIPAI_RESOLUTION", "720p"), os.environ.get("CLIPAI_NEGATIVE", "ignore"),
                   float(os.environ.get("CLIPAI_LIST_TTL", "5")), int(os.environ.get("CLIPAI_STATUS_PAGES", STATUS_PAGES)))

    def usage_info(self, model: Optional[str] = None, duration: float = 5, resolution: Optional[str] = None):
        """(canonical model, quality tier, billed seconds) for the cost ledger."""
        canonical, family = resolve_model(model)
        tier = ((resolution if resolution in ("std", "pro", "4k") else self.kling_mode) if family == "omni"
                else (resolution if resolution not in ("std", "pro", "4k") else None) or self.resolution)
        return canonical, tier, effective_duration(canonical, family, duration)

    # ---- submit ---------------------------------------------------------
    def submit(self, image_path: str, prompt: str, negative_prompt: Optional[str], duration_sec: float,
               model: Optional[str] = None, with_audio: bool = False, subjects: Optional[list] = None,
              image_references: Optional[list] = None, reference_video=None,
              aspect_ratio: Optional[str] = None, resolution: Optional[str] = None,
              multi_prompt: Optional[list] = None, last_frame: Optional[str] = None, kling_mode: Optional[str] = None,
              kling_image_refs: bool = False,
              reference_audio: Optional[list] = None, reference_only: Optional[list] = None, draft: bool = False) -> str:
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
        still to be confirmed on the real API (plan v3, GĐ6).
        reference_audio: local audio files (the shot's own voice line, padded to the clip) the character must speak to — Seedance only
        (content role "reference_audio", files in multipart `audio_files`, like `image_files`; skill clipai-1.3.1 video.mjs; the web
        Weave Canvas sends the same). Lip sync at generation time (kế hoạch V4 GĐ3).
        reference_only: Seedance "reference to video" — local pictures sent ONLY as `reference_image` (no first frame; `image_path` is not
        sent). Seedance refuses first/last frames mixed with reference pictures (real run 2026-09-24), so this is the way to give every
        shot of a grouped generation its own storyboard picture (docs/PHAN_TICH_GOP_SHOT_2026-09-27.md, P2). The caller's prompt names
        each picture ("Image 1 … Image N"). 2.0: ≤ 9 pictures; 2.5: ≤ 30.
        draft: 07/10 restored S4.11 for an explicit comparison: 480p sample, then separately paid 1080p final."""
        canonical, family = resolve_model(model)
        if draft:
            self._check_sample_mode(canonical)
            resolution = "480p"
        videos = reference_video if isinstance(reference_video, list) else ([reference_video] if reference_video else [])
        reference_video = videos[0] if videos else None      # the Kling fields read the first; Seedance sends every one
        if with_audio and canonical == "kling-video-o1":
            raise ProviderError("kling-video-o1 does not support generated sound (use kling-v3-omni or Seedance)",
                                code="unsupported_option")
        if reference_video and with_audio and family == "omni":
            raise ProviderError("Kling rejects a reference video together with generated sound (sound=on); turn "
                                "audio off or drop the reference video", code="unsupported_option")
        from .. import video_rules                       # W10: the model's rules, before any file is read or anything is sent
        if reference_audio and family != "seedance":
            raise ProviderError("âm thanh tham chiếu (khớp môi) chỉ có ở Seedance", code="unsupported_option")
        broken = video_rules.problems(canonical, float(duration_sec),
                                      resolution=(resolution or self.resolution) if family == "seedance" else None,
                                      kling_mode=(kling_mode or self.kling_mode) if family == "omni" else None,
                                      reference_video=bool(reference_video), with_audio=bool(with_audio),
                                      last_frame=bool(last_frame), audios=len(reference_audio or []))
        if broken:
            raise ProviderError("; ".join(broken), code="rule_violation")
        video_files: List[Tuple[str, bytes]] = []
        if reference_video:
            for rv in videos:
                if not os.path.exists(rv["path"]):
                    raise ProviderError(f"reference video not found: {rv['path']}", code="missing_video")
            infos = []
            for rv in videos:
                info = _probe_video(rv["path"])
                if "duration" not in info:           # ffprobe missing / file odd: the old length check still runs
                    from ..ffmpeg_studio import probe_duration
                    got = probe_duration(rv["path"])
                    if got is not None:
                        info["duration"] = got
                infos.append(info)
            problems = reference_video_problems(family, canonical, infos)
            if problems:
                raise ProviderError("video tham chiếu không đạt luật ClipAI: " + "; ".join(problems), code="rule_violation")
            for rv in videos:
                with open(rv["path"], "rb") as f:
                    vcontent = f.read()
                video_files.append((_upload_name(rv["path"], vcontent), vcontent))
        audio_files: List[Tuple[str, bytes]] = []
        for apath in reference_audio or []:
            if not os.path.exists(apath):
                raise ProviderError(f"reference audio not found: {apath}", code="missing_audio")
            with open(apath, "rb") as f:
                audio_files.append((os.path.basename(apath), f.read()))
        text = prompt.strip()
        if self.negative == "append" and negative_prompt:
            text += f"\nAvoid: {negative_prompt}"
        extra_files: List[Tuple[str, bytes]] = []
        content_refs: List[Dict] = []                     # [{"note_label", "note_role"}] in the order attached, for the @Image note
        if last_frame:                                    # first + last frame clip: the two frames carry the characters
            text += " The clip starts on the first image and must end exactly on the last image (same people, place and light)."
        elif family == "seedance" and SEEDANCE_REFS_WITH_FIRST_FRAME and reference_only is None:   # reference-only names its own pictures
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
        if len(text) > limit and not (multi_prompt and family == "omni"):     # M19: multi-shot sends each shot's prompt, not this one
            raise ProviderError(f"prompt is {len(text)} characters; {canonical} allows at most {limit}",
                                code="prompt_too_long")
        if reference_only is not None:
            if family != "seedance":
                raise ProviderError("chỉ ảnh tham chiếu (không khung đầu) chỉ có ở Seedance", code="unsupported_option")
            if last_frame or multi_prompt:
                raise ProviderError("chỉ ảnh tham chiếu không đi cùng khung cuối / multi-shot", code="unsupported_option")
            cap = 30 if canonical == "dreamina-seedance-2-5-260628" else 9
            if not reference_only or len(reference_only) > cap:
                raise ProviderError(f"cần 1–{cap} ảnh tham chiếu, có {len(reference_only)}", code="rule_violation")
            # S4.7: an entry is a local picture (path) or a Subject Library asset {"uri": "asset://…"} (already reviewed, sent by uri —
            # skill clipai 1.3.1 video.mjs). Order is kept: the server fills the empty urls from `image_files` in order, so @Image N is
            # the N-th entry whatever its kind.
            hosted = [r for r in reference_only if isinstance(r, dict)]
            for r in hosted:
                if not str(r.get("uri") or "").startswith("asset://"):
                    raise ProviderError(f"ảnh kho chủ thể phải là asset://…, có {r.get('uri')!r}", code="bad_input")
            local = [r for r in reference_only if not isinstance(r, dict)]
            sizes = []
            for ref in local:
                try:
                    from PIL import Image as _Im
                    with _Im.open(ref) as _i:
                        sizes.append(_i.size)
                except Exception:  # noqa: BLE001 - unreadable here: the file check below says it
                    sizes.append((0, 0))
            bad = reference_image_problems(family, sizes)
            if bad:
                raise ProviderError("ảnh tham chiếu không đạt luật ClipAI: " + "; ".join(bad), code="rule_violation")
            refs = []
            for ref in local:
                if not os.path.exists(ref):
                    raise ProviderError(f"reference image not found: {ref}", code="missing_image")
                with open(ref, "rb") as f:
                    data = f.read()
                refs.append((_upload_name(ref, data), data))
            ctx = {"model_name": canonical,
                   "content": [{"type": "text", "text": text}]
                   + [{"type": "image_url", "image_url": {"url": r["uri"] if isinstance(r, dict) else ""}, "role": "reference_image"}
                      for r in reference_only]
                   + [{"type": "video_url", "video_url": {"url": ""}, "role": "reference_video"} for _ in video_files]
                   + [{"type": "audio_url", "audio_url": {"url": ""}, "role": "reference_audio"} for _ in audio_files],
                   "resolution": resolution or self.resolution, "ratio": aspect_ratio or self.aspect_ratio,
                   "duration": effective_duration(canonical, family, duration_sec), "generate_audio": bool(with_audio),
                   "camera_fixed": False, "seed": -1, "video_num": 1}
            files = ([("image_files", name, data) for name, data in refs]
                     + [("video_files", name, data) for name, data in video_files]
                     + [("audio_files", name, data) for name, data in audio_files])
            if draft:
                ctx["draft"] = True
            data = self.client.post_multipart(PATH_SEEDANCE, {"ctx": json.dumps(ctx, ensure_ascii=False)}, files)
            return self._task_of(data, family)
        if not os.path.exists(image_path):
            raise ProviderError(f"reference image not found: {image_path}", code="missing_image")
        with open(image_path, "rb") as f:
            content = f.read()
        image = (_upload_name(image_path, content), content)
        if multi_prompt and family != "omni":
            raise ProviderError("multi-shot chỉ có ở Kling Omni", code="unsupported_option")
        end_image = None
        if last_frame and family == "omni" and multi_prompt:
            raise ProviderError("Kling multi-shot không nhận khung cuối", code="unsupported_option")
        if last_frame:
            if not os.path.exists(last_frame):
                raise ProviderError(f"last frame image not found: {last_frame}", code="missing_image")
            with open(last_frame, "rb") as f:
                end_bytes = f.read()
            end_image = (_upload_name(last_frame, end_bytes), end_bytes)
        if family == "omni":
            # Kling legacy Omni (the API ClipAI forwards): an image with no `type` is a reference picture, named <<<image_N>>> in the
            # prompt in list order (first frame = image_1). Limits: pictures (+ multi-image elements) ≤ 7, ≤ 4 with a reference video.
            kling_refs = [r for r in (image_references or []) if r.get("path") and os.path.exists(r["path"])] if kling_image_refs else []
            cap = (4 if reference_video else 7) - 1 - (1 if end_image else 0)
            if len(kling_refs) > cap:
                raise ProviderError(f"Kling nhận tối đa {cap} ảnh tham chiếu thêm ở lần gửi này (có {len(kling_refs)})", code="rule_violation")
            for r in kling_refs:
                with open(r["path"], "rb") as f:
                    data = f.read()
                extra_files.append((_upload_name(r["path"], data), data))
            ctx = {"model_name": canonical, "multi_shot": 0, "prompt": text, "sound": "on" if with_audio else "off",
                   "image_list": [{"image_url": "", "type": "first_frame"}]
                   + ([{"image_url": "", "type": "end_frame"}] if end_image else [])
                   + [{"image_url": ""} for _ in kling_refs], "mode": kling_mode or self.kling_mode,
                   "aspect_ratio": aspect_ratio or self.aspect_ratio, "duration": str(effective_duration(canonical, family, duration_sec)),
                   "video_num": 1}
            if reference_video:
                ctx["video_list"] = [{"video_url": "", "refer_type": reference_video.get("refer_type", "feature"),
                                      "keep_original_sound": "no"}]
            if multi_prompt:                   # experiment: several shots in one generation (reference.md Text2VideoO1SubmitRequest)
                avoid = f" Avoid: {negative_prompt}" if self.negative == "append" and negative_prompt else ""
                shots = [{"index": i, "prompt": _with_avoid(str(sh["prompt"]), avoid),
                          "duration": str(effective_duration(canonical, family, sh["duration"]))}
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
                   + [{"type": "video_url", "video_url": {"url": ""}, "role": "reference_video"} for _ in video_files]
                   + [{"type": "audio_url", "audio_url": {"url": ""}, "role": "reference_audio"} for _ in audio_files],
                   "resolution": resolution or self.resolution, "ratio": aspect_ratio or self.aspect_ratio,
                   "duration": effective_duration(canonical, family, duration_sec), "generate_audio": bool(with_audio),
                   "camera_fixed": False, "seed": -1, "video_num": 1}
            if canonical == "dreamina-seedance-2-5-260628":
                # Seedance 2.5 refuses a set ratio with a first frame: "[InvalidParameter.TaskTypeConstraint] … For first-frame or
                # first-last-frame generation, the output ratio follows the first-frame image" (real run S4.11, 2026-10-01; the web
                # app sends "adaptive" there too). The first frame is drawn in the project format, so the clip keeps it.
                ctx["ratio"] = "adaptive"
            path = PATH_SEEDANCE
        # B3 01/10: the first / last frame and the extra pictures obey the picture rules too (reference_only already checked its own):
        # Seedance refused a 3.74-wide skill sheet AFTER it was sent. Wrong → nothing is sent, nothing is paid.
        sent = [image[1]] + ([end_image[1]] if end_image else []) + [d for _, d in extra_files]
        bad = reference_image_problems(family, image_sizes_of(sent), sides=False)   # the ratio is the rule that bit; sides stay a reference_only check
        if bad:
            raise ProviderError("ảnh gửi kèm không đạt luật ClipAI: " + "; ".join(bad), code="rule_violation")
        files = ([("image_files", image[0], image[1])] + ([("image_files", end_image[0], end_image[1])] if end_image else [])
                 + [("image_files", name, data) for name, data in extra_files]
                + [("video_files", name, data) for name, data in video_files]
                + [("audio_files", name, data) for name, data in audio_files])
        if draft:
            ctx["draft"] = True
        data = self.client.post_multipart(path, {"ctx": json.dumps(ctx, ensure_ascii=False)}, files)
        return self._task_of(data, family)

    SAMPLE_MODEL = "dreamina-seedance-2-5-260628"

    def _check_sample_mode(self, canonical: str) -> None:
        from .. import features
        if not features.on("seedance_sample_mode"):
            raise ProviderError("Chế độ bản mẫu đang tắt (FEATURE_SEEDANCE_SAMPLE_MODE)", code="feature_off")
        if canonical != self.SAMPLE_MODEL:
            raise ProviderError("Chế độ bản mẫu chỉ có ở Seedance 2.5", code="unsupported_option")

    def submit_final_from_sample(self, sample_external_id: str) -> str:
        """Separately billed final. The caller checks successful draft, expiry and budget before this send."""
        self._check_sample_mode(self.SAMPLE_MODEL)
        family, _, task_id = sample_external_id.partition(":")
        if family != "seedance" or not task_id or ":" in task_id:
            raise ProviderError("không phải mã bản mẫu Seedance", code="bad_id")
        ctx = {"model_name": self.SAMPLE_MODEL, "content": [{"type": "draft_task", "draft_task": {"id": task_id}}],
               "resolution": "1080p", "video_num": 1}
        data = self.client.post_multipart(PATH_SEEDANCE, {"ctx": json.dumps(ctx, ensure_ascii=False)}, [])
        return self._task_of(data, "seedance")

    # ---- S4.12 video edit (Seedance 2.5) --------------------------------------------------------------------------------------------
    # Read from the ClipAI web app (2026-10-01, bundle 3634): a video edit is a Seedance 2.5 body with ONE source video (role
    # reference_video), `omni_reference_task_type: "edit"`, duration -1 and ratio adaptive — the web "Advanced Edit" frame notes only
    # help write that prompt (+ marked frames as reference pictures). S14.9 (06/10): the S4.11 Sample Mode (480p `draft` → 1080p
    # `draft_task` final, flag seedance_sample_mode) was removed; `task_usage` still reads a task's draft fields if ClipAI sends them.
    EDIT_MODEL = "dreamina-seedance-2-5-260628"

    def submit_video_edit(self, video_path: str, prompt: str, resolution: str = "480p",
                          reference_images: Optional[List[str]] = None) -> str:
        """Edit one existing clip instead of generating it again (S4.12): the clip is the only editing master, the prompt names the one
        thing to change ("Edit @Video 1 …"). Output length follows the source (duration -1), ratio adaptive. Billed on source + output
        seconds at the video-input rate (cost.seedance_estimate(..., input_video_s=source seconds))."""
        from .. import features
        if not features.on("seedance_video_edit"):
            raise ProviderError("Sửa clip (video edit) đang tắt (FEATURE_SEEDANCE_VIDEO_EDIT)", code="feature_off")
        if resolution not in ("480p", "720p"):
            raise ProviderError("Seedance 2.5 sửa clip chỉ 480p / 720p", code="rule_violation")
        if not os.path.exists(video_path):
            raise ProviderError(f"clip nguồn không có: {video_path}", code="missing_video")
        info = _probe_video(video_path)
        problems = video_edit_problems(info)
        if problems:
            raise ProviderError("clip nguồn không đạt luật sửa clip: " + "; ".join(problems), code="rule_violation")
        refs = list(reference_images or [])
        if len(refs) > 30:
            raise ProviderError("tối đa 30 ảnh tham chiếu", code="rule_violation")
        text = (prompt or "").strip()
        if not text:
            raise ProviderError("sửa clip cần câu nói rõ sửa gì", code="rule_violation")
        if len(text) > PROMPT_LIMITS[self.EDIT_MODEL]:
            raise ProviderError(f"prompt dài {len(text)} ký tự; tối đa {PROMPT_LIMITS[self.EDIT_MODEL]}", code="prompt_too_long")
        files = []
        for ref in refs:
            if not os.path.exists(ref):
                raise ProviderError(f"reference image not found: {ref}", code="missing_image")
            with open(ref, "rb") as f:
                data = f.read()
            files.append(("image_files", _upload_name(ref, data), data))
        with open(video_path, "rb") as f:
            vdata = f.read()
        files.append(("video_files", _upload_name(video_path, vdata), vdata))
        ctx = {"model_name": self.EDIT_MODEL,
               "content": [{"type": "text", "text": text}]
               + [{"type": "image_url", "image_url": {"url": ""}, "role": "reference_image"} for _ in refs]
               + [{"type": "video_url", "video_url": {"url": ""}, "role": "reference_video"}],
               "resolution": resolution, "ratio": "adaptive", "duration": -1, "omni_reference_task_type": "edit",
               "generate_audio": False, "video_num": 1}
        data = self.client.post_multipart(PATH_SEEDANCE, {"ctx": json.dumps(ctx, ensure_ascii=False)}, files)
        return self._task_of(data, "seedance")

    def task_usage(self, external_id: str) -> Optional[Dict]:
        """What ClipAI billed for one task, from its list row: tokens (extra_data.usage.total_tokens), whether it carried a video, the
        USD this makes, and the sample / final links. None when the task is not in the list (yet)."""
        from .. import cost
        task, _ = self._find_ex(external_id, pages=DEEP_PAGES)
        if task is None:
            return None
        extra = task.get("extra_data")
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except ValueError:
                extra = {}
        extra = extra or {}
        tokens = ((extra.get("usage") or {}).get("total_tokens"))
        video_in = bool(extra.get("has_video_input"))
        usd = cost.seedance_token_usd(task.get("model_name") or "", tokens, video_in) if tokens is not None else None
        return {"tokens": tokens, "has_video_input": video_in, "usd": usd, "resolution": extra.get("resolution") or task.get("resolution"),
                "duration": task.get("duration"), "is_draft": bool(task.get("is_draft")), "draft_expired_at": task.get("draft_expired_at"),
                "draft_video_id": task.get("draft_video_id"), "final_video_id": task.get("final_video_id"), "row_id": task.get("id"),
                "status": task.get("task_status"), "message": task.get("task_status_msg") or ""}

    @staticmethod
    def _task_of(data, family: str) -> str:
        tasks = (data or {}).get("tasks") or []
        if not tasks:
            raise ProviderError("create returned no task", code="bad_response")
        first = tasks[0]
        if _state(first.get("task_status", "submitted")) == "failed":
            message = first.get("task_status_msg") or "task creation failed"
            raise ProviderError(message, code=classify_failure(message))
        return f"{family}:{first['task_id']}"

    # ---- status ---------------------------------------------------------
    def _page(self, family: str, page: int) -> list:
        key = (family, page)
        hit = self._pages.get(key)
        if hit is not None and self.list_ttl > 0 and time.monotonic() - hit[0] < self.list_ttl:
            return hit[1]
        data = self.client.get(PATH_LIST, {"page": page, "pageSize": 50, "task_type": TASK_TYPE[family], "order_by_desc": 1})
        rows = (data or {}).get("data") or []
        self._pages[key] = (time.monotonic(), rows)
        return rows

    def attach_memory(self, memory) -> None:
        """Keep the per-task counters somewhere that outlives this object (core.runner.TaskMemory: the jobs table). The dashboard
        builds a new provider on every poll, so counters kept only in this object never reached the 'not created' verdict."""
        self.memory = memory

    def _find_ex(self, external_id: str, sent_at: Optional[float] = None, pages: Optional[int] = None):
        """(task or None, covered): `covered` = the pages read reach back to before the job was sent (or the list ended), so a task
        missing from them was really never created — not merely pushed down by newer tasks (a shared token, several projects)."""
        family, _, task_id = external_id.partition(":")
        if family not in TASK_TYPE or not task_id:
            raise ProviderError(f"malformed external id '{external_id}'", code="bad_id")
        for page in range(1, (pages or self.status_pages) + 1):
            rows = self._page(family, page)
            task = next((t for t in rows if str(t.get("task_id")) == task_id), None)
            if task is not None:
                return task, True
            if len(rows) < 50:
                return None, True
            times = [int(t["created_at"]) for t in rows if str(t.get("created_at") or "").isdigit()]
            if sent_at is not None and times and min(times) <= sent_at:
                return None, True
        return None, False

    def find_by_prompt(self, external_id: str, prompt: str, sent_at: Optional[float], taken=(), pages: int = 3) -> Optional[str]:
        """W12b (trial 2A, 2026-09-25): past its concurrency limit ClipAI answers a create with a short QUEUE id (12 digits); when a slot
        frees it creates the real task under a NEW id — the queue id never appears in the list. 8 of 10 paid clips were written off as
        "not found" that way (and the "not created" branch would even have resent them = paid twice). The real task is recognised by
        the very prompt that was sent, created after the job was sent, and not already tied to another job. Returns its external id.
        The WHOLE sent prompt must open the task's prompt (trial 2026-09-27: every shot prompt opened with the same 200+ character look sentence, so a
        200-character prefix tied 6 clips to the wrong shots); two or more matching tasks = ambiguous → None, never a guess."""
        family, _, old = external_id.partition(":")
        want = " ".join((prompt or "").split())
        if family not in TASK_TYPE or not want or sent_at is None:
            return None
        hits = []
        for page in range(1, pages + 1):
            rows = self._page(family, page)
            for t in rows:
                tid = str(t.get("task_id") or "")
                ext = f"{family}:{tid}"
                if not tid or tid == old or ext in taken:
                    continue
                if str(t.get("created_at") or "").isdigit() and int(t["created_at"]) + 5 < sent_at:
                    continue
                if " ".join(str(t.get("prompt") or "").split()).startswith(want):     # submit() may append (Avoid:, frame notes)
                    hits.append(ext)
            if len(rows) < 50:
                break
        return hits[0] if len(hits) == 1 else None

    def _find(self, external_id: str) -> Tuple[Optional[dict], str]:
        task, _ = self._find_ex(external_id)
        return task, external_id.partition(":")[2]

    def status(self, external_id: str) -> TaskStatus:
        seen, _, sent_at = self.memory.state(external_id)
        task, covered = self._find_ex(external_id, sent_at)
        if task is None:
            unseen = self.memory.unseen(external_id)
            if not seen and unseen >= _NOT_CREATED_LIMIT:
                if not covered:                               # newer tasks may hide it: look deeper once before deciding
                    task, covered = self._find_ex(external_id, sent_at, DEEP_PAGES)
                if task is None and covered:
                    return TaskStatus("failed", NOT_CREATED, "ClipAI trả mã task nhưng danh sách (đọc tới trước lúc gửi) không có task này "
                                                             "— lệnh không được tạo (không có gì để chờ, không bị tính tiền)")
            if task is None:
                if unseen >= _UNSEEN_LIMIT:
                    return TaskStatus("failed", "not_found", "không thấy task trong danh sách ClipAI — có thể vẫn đang chạy; "
                                                             "không tự gửi lại để tránh trả tiền 2 lần")
                return TaskStatus("running")
        self.memory.seen(external_id)
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
        task, _ = self._find_ex(external_id, pages=DEEP_PAGES)       # M17: a task beyond the first pages must really be cancelled
        if task is not None and task.get("id") is not None:
            self.client.post_json(PATH_DELETE, {"id": int(task["id"])})
