"""Self-tuning limit on provider jobs running at the same time (all projects together).

We do not know Deepix / Clip AI concurrency limits and measuring them costs credit. So we learn them from normal
work: start low, add one slot after a run of clean successes, halve the limit when the provider answers "rate
limited" (HTTP 429). A rate-limited submit is rejected before anything is generated, so it costs nothing and the job
just waits in the queue (see `runner.submit_pending`).

The learned value lives in memory (it restarts from the start value with the server; cheap to relearn).
"""
import os
import threading
import time
from typing import Dict


def _env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Throttle:
    def __init__(self, start=None, maximum=None, up_every=None):
        self.start = start if start is not None else _env("THROTTLE_START", 4)
        self.maximum = maximum if maximum is not None else _env("THROTTLE_MAX", 20)
        self.up_every = up_every if up_every is not None else _env("THROTTLE_UP_EVERY", 5)
        self._lock = threading.Lock()
        self._limit: Dict[str, int] = {}
        self._streak: Dict[str, int] = {}
        self._hits: Dict[str, int] = {}
        self._peak_ok: Dict[str, int] = {}
        self._last_hit: Dict[str, float] = {}

    def enabled(self) -> bool:
        return self.maximum > 0

    def limit(self, kind: str) -> int:
        with self._lock:
            return self._limit.get(kind, self.start)

    def allow(self, kind: str, running_now: int) -> bool:
        return not self.enabled() or running_now < self.limit(kind)

    def on_success(self, kind: str, running_at_submit: int = 0) -> None:
        with self._lock:
            self._streak[kind] = self._streak.get(kind, 0) + 1
            if self._streak[kind] >= self.up_every:
                self._streak[kind] = 0
                self._limit[kind] = min(self.maximum, self._limit.get(kind, self.start) + 1)

    def on_rate_limited(self, kind: str) -> None:
        with self._lock:
            self._limit[kind] = max(1, self._limit.get(kind, self.start) // 2)
            self._streak[kind] = 0
            self._hits[kind] = self._hits.get(kind, 0) + 1
            self._last_hit[kind] = time.time()

    def info(self, kind: str) -> Dict:
        with self._lock:
            return {"limit": self._limit.get(kind, self.start), "hits": self._hits.get(kind, 0),
                    "last_hit": self._last_hit.get(kind)}

    def reset(self) -> None:
        with self._lock:
            for d in (self._limit, self._streak, self._hits, self._peak_ok, self._last_hit):
                d.clear()


THROTTLE = Throttle()
