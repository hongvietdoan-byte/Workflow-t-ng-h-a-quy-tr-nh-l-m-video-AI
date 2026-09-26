"""Small caches that keep the dashboard fast without ever showing stale data.

1. `per_rerun()` + `cached(conn, key, compute)`: one Streamlit rerun asks the same question many times (lineage.scan ~5 times at
   Bước 2, assets.project_assets 100+ times at Bước 1/2). Inside `with per_rerun():` the answer is computed once and handed out as a
   copy; it is recomputed as soon as the database changed — by this connection (`total_changes`) or by any other connection /
   process (`PRAGMA data_version`). Outside the block (autopilot, runner threads, tests, tools) nothing is cached.
   The memo is per thread: every Streamlit session runs its script in its own thread.
2. `read_json(path)`: a JSON file parsed once and reused while its modification time and size stay the same. A file changed in the
   last few seconds is always read again (file clocks are coarse); a file that cannot be read or parsed raises as before and is
   never cached.
"""
import copy
import json
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Hashable, Tuple

_local = threading.local()


@contextmanager
def per_rerun():
    """Turn the memo on for this thread until the block ends (nested blocks share the outer memo)."""
    outer = getattr(_local, "memo", None) is not None
    if not outer:
        _local.memo = {}
    try:
        yield
    finally:
        if not outer:
            _local.memo = None


def active() -> bool:
    return getattr(_local, "memo", None) is not None


def _stamp(conn) -> Tuple[int, int]:
    return conn.total_changes, conn.execute("PRAGMA data_version").fetchone()[0]


def _copy(value):
    try:
        return copy.deepcopy(value)
    except Exception:  # noqa: BLE001 - an uncopyable value (never expected) is handed out as is
        return value


def cached(conn, key: Hashable, compute: Callable[[], Any]):
    """compute() once per rerun and database state; a fresh copy on every call so a caller may change what it gets."""
    memo = getattr(_local, "memo", None)
    if memo is None:
        return compute()
    try:
        stamp = _stamp(conn)
    except Exception:  # noqa: BLE001 - a closed / odd connection: no caching
        return compute()
    slot = memo.get((id(conn), key))
    if slot is not None and slot[0] is conn and slot[1] == stamp:
        return _copy(slot[2])
    value = compute()
    memo[(id(conn), key)] = (conn, stamp, value)      # the stamp from BEFORE compute: a change during compute only misses
    return _copy(value)


# ---- JSON files ---------------------------------------------------------------------------------------------------------
RECENT_SEC = 3.0                        # a file written this recently is always re-read (two writes can share one mtime)
_json_cache: Dict[str, Tuple[int, int, Any]] = {}
_json_lock = threading.Lock()


def read_json(path: str):
    """json.load(path) with a cache keyed by (mtime, size). Raises OSError / ValueError exactly like open() + json.load()."""
    st = os.stat(path)
    key = os.path.normcase(os.path.abspath(path))
    with _json_lock:
        slot = _json_cache.get(key)
    if slot is not None and slot[0] == st.st_mtime_ns and slot[1] == st.st_size and time.time() - st.st_mtime > RECENT_SEC:
        return copy.deepcopy(slot[2])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    with _json_lock:
        _json_cache[key] = (st.st_mtime_ns, st.st_size, data)
    return copy.deepcopy(data)


def forget_json(path: str) -> None:
    """Drop one file from the cache (after writing it)."""
    with _json_lock:
        _json_cache.pop(os.path.normcase(os.path.abspath(path)), None)
