"""Self-tuning limit on provider jobs running at the same time (all projects together).

We do not know Deepix / Clip AI concurrency limits and measuring them costs credit. So we learn them from normal
work: start low, add one slot after a run of clean successes, halve the limit when the provider answers "rate
limited" (HTTP 429). A rate-limited submit is rejected before anything is generated, so it costs nothing and the job
just waits in the queue (see `runner.submit_pending`).

A known ceiling of a provider is a hard cap on top of the learned value (`caps`, env THROTTLE_CAP_<KIND>): ClipAI runs only
2 video tasks of one account at a time — a third one gets a temporary queue id and the real task appears later under a new
id (chạy thử 2A, W12b), forcing 8 gave `1130 Too many requests` — so video_gen is capped at 2 by default (0 = no cap).

The learned value is kept in app_settings (key 'throttle') by the runners (`state` / `restore`), so a restart does not
relearn it from the start value by hitting the provider again.
"""
import os
import threading
import time
from typing import Dict, Optional

DEFAULT_CAPS = {"video_gen": 2, "image_gen": 0}
SETTINGS_KEY = "throttle"


def _env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Throttle:
    def __init__(self, start=None, maximum=None, up_every=None, caps: Optional[Dict[str, int]] = None):
        self.start = start if start is not None else _env("THROTTLE_START", 4)
        self.maximum = maximum if maximum is not None else _env("THROTTLE_MAX", 20)
        self.up_every = up_every if up_every is not None else _env("THROTTLE_UP_EVERY", 5)
        self.caps: Dict[str, int] = dict(caps) if caps is not None else {
            k: _env(f"THROTTLE_CAP_{k.upper()}", v) for k, v in DEFAULT_CAPS.items()}
        self._lock = threading.Lock()
        self._limit: Dict[str, int] = {}
        self._streak: Dict[str, int] = {}
        self._hits: Dict[str, int] = {}
        self._peak_ok: Dict[str, int] = {}
        self._last_hit: Dict[str, float] = {}
        self.restored = False

    def enabled(self) -> bool:
        return self.maximum > 0

    def cap(self, kind: str) -> int:
        """The provider's known ceiling for this kind (0 = none known)."""
        return max(0, int(self.caps.get(kind, 0) or 0))

    def _learned(self, kind: str) -> int:
        return self._limit.get(kind, self.start)

    def limit(self, kind: str, capped: bool = True) -> int:
        """capped=False: a simulated provider (tests, demo) — the real provider's known ceiling does not apply to it."""
        with self._lock:
            learned, cap = self._learned(kind), self.cap(kind) if capped else 0
            return min(learned, cap) if cap else learned

    def allow(self, kind: str, running_now: int, capped: bool = True) -> bool:
        return not self.enabled() or running_now < self.limit(kind, capped)

    def on_success(self, kind: str, running_at_submit: int = 0) -> bool:
        """Returns True when the learned limit changed (worth saving)."""
        with self._lock:
            self._streak[kind] = self._streak.get(kind, 0) + 1
            if self._streak[kind] >= self.up_every:
                self._streak[kind] = 0
                before = self._learned(kind)
                self._limit[kind] = min(self.maximum, before + 1)
                return self._limit[kind] != before
            return False

    def on_rate_limited(self, kind: str) -> bool:
        with self._lock:
            self._limit[kind] = max(1, self._learned(kind) // 2)
            self._streak[kind] = 0
            self._hits[kind] = self._hits.get(kind, 0) + 1
            self._last_hit[kind] = time.time()
            return True

    def info(self, kind: str) -> Dict:
        with self._lock:
            learned, cap = self._learned(kind), self.cap(kind)
            return {"limit": min(learned, cap) if cap else learned, "learned": learned, "cap": cap,
                    "hits": self._hits.get(kind, 0), "last_hit": self._last_hit.get(kind)}

    def state(self) -> Dict:
        """What is worth keeping across a restart: the learned limits and the 429 history."""
        with self._lock:
            return {"limit": dict(self._limit), "hits": dict(self._hits), "last_hit": dict(self._last_hit)}

    def restore(self, saved: Optional[Dict]) -> None:
        with self._lock:
            self.restored = True
            if not saved:
                return
            for kind, value in (saved.get("limit") or {}).items():
                try:
                    v = int(value)
                except (TypeError, ValueError):
                    continue
                self._limit[kind] = max(1, min(self.maximum, v) if self.maximum else v)
            for kind, value in (saved.get("hits") or {}).items():
                self._hits[kind] = int(value or 0)
            for kind, value in (saved.get("last_hit") or {}).items():
                self._last_hit[kind] = value

    def reset(self) -> None:
        with self._lock:
            for d in (self._limit, self._streak, self._hits, self._peak_ok, self._last_hit):
                d.clear()


def save(conn, throttle: "Throttle") -> None:
    import json
    try:
        conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (SETTINGS_KEY, json.dumps(throttle.state())))
        conn.commit()
    except Exception:  # noqa: BLE001 - keeping the learned value is a convenience; never fail a job over it
        pass


def load(conn, throttle: "Throttle") -> None:
    """Once per process: take the learned limits saved by the last run."""
    if throttle.restored:
        return
    import json
    try:
        row = conn.execute("SELECT value FROM app_settings WHERE key=?", (SETTINGS_KEY,)).fetchone()
        throttle.restore(json.loads(row[0]) if row else None)
    except Exception:  # noqa: BLE001
        throttle.restore(None)


THROTTLE = Throttle()
