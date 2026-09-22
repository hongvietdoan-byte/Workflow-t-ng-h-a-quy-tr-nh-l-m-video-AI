"""Provider interface for external generation services (Clip AI / Kling, later Deepix).

A real adapter only has to implement `VideoProvider`; the runner, state machine and dashboard
stay unchanged. `MockVideoProvider` simulates behaviour (delays, risk-control failures,
transient errors) for tests and demos.
"""
import base64
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
               subjects: Optional[list] = None, image_references: Optional[list] = None) -> str: ...

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


class MockImageProvider:
    """Simulated image generator: writes a 1x1 PNG. Never produces a real image."""
    name = "mock-image"

    def __init__(self, polls_to_finish: int = 1, transient_failures: int = 0):
        self.polls_to_finish = polls_to_finish
        self.transient_failures = transient_failures
        self._polls: Dict[str, int] = {}
        self._counter = 0
        self.prompts: Dict[str, str] = {}
        self.references: Dict[str, list] = {}
        self.cancelled = []

    def usage_info(self):
        return "mock-image", "default"

    def submit(self, prompt: str, references=None) -> str:
        self._counter += 1
        task_id = f"img-{self._counter}"
        self._polls[task_id] = 0
        self.prompts[task_id] = prompt
        self.references[task_id] = list(references or [])
        return task_id

    def status(self, task_id: str) -> TaskStatus:
        self._polls[task_id] += 1
        if self.transient_failures > 0:
            self.transient_failures -= 1
            return TaskStatus("failed", "server_error", "temporary server error", transient=True)
        return TaskStatus("succeeded" if self._polls[task_id] >= self.polls_to_finish else "running")

    def download(self, task_id: str, dest_path: str) -> str:
        with open(dest_path, "wb") as f:
            f.write(_PNG_1X1)
        return dest_path

    def cancel(self, task_id: str) -> None:
        self.cancelled.append(task_id)


class MockVideoProvider:
    name = "mock"

    def __init__(self, polls_to_finish: int = 2, blocked_words=("wonder woman",),
                 transient_failures: int = 0):
        self.polls_to_finish = polls_to_finish
        self.blocked_words = tuple(w.lower() for w in blocked_words)
        self.transient_failures = transient_failures
        self._tasks: Dict[str, dict] = {}
        self._counter = 0
        self.cancelled = []

    def usage_info(self, model=None, duration=5):
        return "mock", "default", duration

    def submit(self, image_path, prompt, negative_prompt, duration_sec, model=None, with_audio=False, subjects=None,
              image_references=None) -> str:
        self._counter += 1
        task_id = f"mock-{self._counter}"
        self._tasks[task_id] = {"prompt": prompt.lower(), "polls": 0, "model": model, "with_audio": with_audio,
                                  "subjects": subjects or [], "image_references": image_references or []}
        return task_id

    def status(self, task_id: str) -> TaskStatus:
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
        with open(dest_path, "wb") as f:
            f.write(b"MOCK-MP4")
        return dest_path

    def cancel(self, task_id: str) -> None:
        self.cancelled.append(task_id)
