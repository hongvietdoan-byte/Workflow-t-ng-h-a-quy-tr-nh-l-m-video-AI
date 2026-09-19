"""Provider interface for external generation services (Clip AI / Kling, later Deepix).

A real adapter only has to implement `VideoProvider`; the runner, state machine and dashboard
stay unchanged. `MockVideoProvider` simulates behaviour (delays, risk-control failures,
transient errors) for tests and demos.
"""
from dataclasses import dataclass
from typing import Dict, Optional, Protocol

RISK_CONTROL = "risk_control"


@dataclass
class TaskStatus:
    state: str  # 'running' | 'succeeded' | 'failed'
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    transient: bool = False


class VideoProvider(Protocol):
    name: str

    def submit(self, image_path: str, prompt: str, negative_prompt: Optional[str],
               duration_sec: float) -> str: ...

    def status(self, task_id: str) -> TaskStatus: ...

    def download(self, task_id: str, dest_path: str) -> str: ...

    def cancel(self, task_id: str) -> None: ...


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

    def submit(self, image_path, prompt, negative_prompt, duration_sec) -> str:
        self._counter += 1
        task_id = f"mock-{self._counter}"
        self._tasks[task_id] = {"prompt": prompt.lower(), "polls": 0}
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
