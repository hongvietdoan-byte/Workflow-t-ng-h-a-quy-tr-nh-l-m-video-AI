"""Provider interface for external generation services (Clip AI / Kling, later Deepix).

A real adapter only has to implement `VideoProvider`; the runner, state machine and dashboard
stay unchanged. `MockVideoProvider` simulates behaviour (delays, risk-control failures,
transient errors) for tests and demos.
"""
import base64
import os
import subprocess
from dataclasses import dataclass
from typing import Dict, Optional, Protocol

RISK_CONTROL = "risk_control"


class ProviderError(Exception):
    """Failure talking to (or reported by) a generation provider. Never contains credentials."""

    def __init__(self, message: str, code: Optional[str] = None, transient: bool = False):
        super().__init__(message)
        self.code = code
        self.transient = transient


@dataclass
class TaskStatus:
    state: str  # 'running' | 'succeeded' | 'failed'
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    transient: bool = False


class VideoProvider(Protocol):
    name: str

    def submit(self, image_path: str, prompt: str, negative_prompt: Optional[str],
               duration_sec: float, model: Optional[str] = None, with_audio: bool = False,
               subjects: Optional[list] = None, image_references: Optional[list] = None,
               reference_video: Optional[dict] = None) -> str: ...

    def status(self, task_id: str) -> TaskStatus: ...

    def download(self, task_id: str, dest_path: str) -> str: ...

    def cancel(self, task_id: str) -> None: ...


class ImageProvider(Protocol):
    name: str

    def submit(self, prompt: str, references=None) -> str: ...

    def status(self, task_id: str) -> TaskStatus: ...

    def download(self, task_id: str, dest_path: str) -> str: ...

    def cancel(self, task_id: str) -> None: ...


_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def _real_media() -> bool:
    """MOCK_REAL_MEDIA=1 (demo / walkthrough): the simulators write a small real picture / video in the project's frame
    instead of a 1x1 PNG / fake MP4, so render, subtitles, end card and exports can be tried end to end without credit."""
    return os.environ.get("MOCK_REAL_MEDIA", "").lower() in ("1", "true", "yes")


_COLOURS = [(72, 94, 140), (140, 88, 72), (70, 128, 96), (120, 80, 140), (150, 130, 60)]


def _placeholder_png(dest_path: str, size: Optional[str], label: str, n: int) -> bool:
    """Write a placeholder picture at 1/8 of the requested size ("1152x2048"). False when Pillow is missing."""
    try:
        from PIL import Image, ImageDraw
        w, h = (int(v) for v in (size or "2048x1152").lower().split("x"))
        w, h = max(w // 8, 16), max(h // 8, 16)
        img = Image.new("RGB", (w, h), _COLOURS[n % len(_COLOURS)])
        ImageDraw.Draw(img).text((8, h // 2 - 6), label, fill=(255, 255, 255))
        img.save(dest_path, "PNG")
        return True
    except (ImportError, ValueError, OSError):
        return False


_CLIP_SIZE = {"9:16": (360, 640), "16:9": (640, 360), "1:1": (480, 480)}


def _placeholder_mp4(dest_path: str, image_path: Optional[str], aspect: Optional[str], seconds: float) -> bool:
    """A real short clip (still image + silent stereo track) made with ffmpeg. False when ffmpeg or the image is missing."""
    from .ffmpeg_studio import find_ffmpeg
    try:
        ffmpeg = find_ffmpeg()
    except Exception:
        return False
    w, h = _CLIP_SIZE.get(aspect or "16:9", (640, 360))
    src = ["-loop", "1", "-i", image_path] if image_path and os.path.exists(image_path) else \
        ["-f", "lavfi", "-i", f"color=c=0x485e8c:s={w}x{h}"]
    cmd = [ffmpeg, "-y", "-loglevel", "error", *src, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
           "-t", f"{max(float(seconds or 5), 1):g}", "-r", "24",
           "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},format=yuv420p",
           "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", dest_path]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


class MockImageProvider:
    """Simulated image generator: writes a 1x1 PNG. Never produces a real image."""
    name = "mock-image"
    supports_aspect = True

    def __init__(self, polls_to_finish: int = 1, transient_failures: int = 0):
        self.polls_to_finish = polls_to_finish
        self.transient_failures = transient_failures
        self._polls: Dict[str, int] = {}
        self._counter = 0
        self.prompts: Dict[str, str] = {}
        self.references: Dict[str, list] = {}
        self.sizes: Dict[str, Optional[str]] = {}
        self.cancelled = []

    def usage_info(self):
        return "mock-image", "default"

    def submit(self, prompt: str, references=None, size=None) -> str:
        self._counter += 1
        task_id = f"img-{self._counter}"
        self.sizes[task_id] = size
        self._polls[task_id] = 0
        self.prompts[task_id] = prompt
        self.references[task_id] = list(references or [])
        return task_id

    def status(self, task_id: str) -> TaskStatus:
        if task_id not in self._polls:
            raise ProviderError(f"unknown task {task_id} (the simulator forgets its tasks when the dashboard restarts)", code="not_found")
        self._polls[task_id] += 1
        if self.transient_failures > 0:
            self.transient_failures -= 1
            return TaskStatus("failed", "server_error", "temporary server error", transient=True)
        return TaskStatus("succeeded" if self._polls[task_id] >= self.polls_to_finish else "running")

    def download(self, task_id: str, dest_path: str) -> str:
        if _real_media() and _placeholder_png(dest_path, self.sizes.get(task_id), f"mock {task_id}", self._counter):
            return dest_path
        with open(dest_path, "wb") as f:
            f.write(_PNG_1X1)
        return dest_path

    def cancel(self, task_id: str) -> None:
        self.cancelled.append(task_id)


class MockVideoProvider:
    name = "mock"
    supports_aspect = True

    def __init__(self, polls_to_finish: int = 2, blocked_words=("wonder woman",),
                 transient_failures: int = 0):
        self.polls_to_finish = polls_to_finish
        self.blocked_words = tuple(w.lower() for w in blocked_words)
        self.transient_failures = transient_failures
        self._tasks: Dict[str, dict] = {}
        self._counter = 0
        self.cancelled = []

    def usage_info(self, model=None, duration=5, resolution=None):
        return "mock", resolution or "default", duration

    def submit(self, image_path, prompt, negative_prompt, duration_sec, model=None, with_audio=False, subjects=None,
              image_references=None, reference_video=None, aspect_ratio=None, resolution=None, multi_prompt=None,
              last_frame=None, kling_mode=None, reference_audio=None) -> str:
        self._counter += 1
        task_id = f"mock-{self._counter}"
        self._tasks[task_id] = {"prompt": prompt.lower(), "polls": 0, "model": model, "with_audio": with_audio,
                                  "subjects": subjects or [], "image_references": image_references or [],
                                  "reference_video": reference_video, "aspect_ratio": aspect_ratio,
                                  "resolution": resolution, "multi_prompt": multi_prompt,
                                  "image_path": image_path, "duration": duration_sec, "last_frame": last_frame,
                                  "kling_mode": kling_mode, "reference_audio": list(reference_audio or [])}
        return task_id

    def status(self, task_id: str) -> TaskStatus:
        if task_id not in self._tasks:
            raise ProviderError(f"unknown task {task_id} (the simulator forgets its tasks when the dashboard restarts)", code="not_found")
        task = self._tasks[task_id]
        task["polls"] += 1
        if any(w in task["prompt"] for w in self.blocked_words):
            return TaskStatus("failed", RISK_CONTROL, "Failure to pass the risk control system")
        if self.transient_failures > 0:
            self.transient_failures -= 1
            return TaskStatus("failed", "server_error", "temporary server error", transient=True)
        if task["polls"] >= self.polls_to_finish:
            return TaskStatus("succeeded")
        return TaskStatus("running")

    def download(self, task_id: str, dest_path: str) -> str:
        task = self._tasks.get(task_id) or {}
        if _real_media() and _placeholder_mp4(dest_path, task.get("image_path"), task.get("aspect_ratio"), task.get("duration") or 5):
            return dest_path
        with open(dest_path, "wb") as f:
            f.write(b"MOCK-MP4")
        return dest_path

    def cancel(self, task_id: str) -> None:
        self.cancelled.append(task_id)
