"""Vòng hỏi nền (sau dự án Khủng Long Đỏ, 08/10): job ảnh/clip đã gửi ở nhà cung cấp được hỏi trạng thái và tải về cả khi KHÔNG
có tab nào mở và dự án không chạy tự động.

Trước đây chỉ hai nơi hỏi: khung tự cập nhật của trang (dashboard/widgets.py, chạy khi trang của dự án đang mở) và luồng chạy tự động
(core/autopilot.py). Đóng tab giữa chừng = clip đã xong (đã tính tiền) nằm ở nhà cung cấp tới lần mở trang sau.

Vòng này CHỈ hỏi + tải (runner.poll_once — không tốn tiền); không bao giờ gửi job mới (submit_pending), không chạy QC. Mỗi dự án và
mỗi loại job một lượt riêng, bọc lỗi riêng: lỗi một dự án ghi diag rồi qua dự án kế. Hỏi trùng với trang / chạy tự động đã được khóa
lượt của runner (_turn, M3) chặn: ai đang hỏi thì người kia bỏ lượt."""
import os
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from . import diag

INTERVAL_SEC = 30
KINDS = {"image_gen": "image", "video_gen": "video"}

_started = False
_start_lock = threading.Lock()
LAST: Dict = {"at": None, "results": {}, "error": None}


def projects_with_running(conn) -> List[Tuple[int, str]]:
    """(project, 'image'|'video') pairs that have a job sent to the provider and not answered yet."""
    rows = conn.execute("SELECT DISTINCT project_id, type FROM jobs WHERE state='running' AND external_id IS NOT NULL "
                        "AND external_id<>'' AND type IN ('image_gen','video_gen') ORDER BY project_id, type").fetchall()
    return [(r[0], KINDS[r[1]]) for r in rows]


def poll_all(conn, make_runner: Callable) -> Dict[Tuple[int, str], Dict]:
    """One round over every project with running jobs. make_runner(conn, kind) -> runner or None (no provider / no API key)."""
    results: Dict[Tuple[int, str], Dict] = {}
    for pid, kind in projects_with_running(conn):
        try:
            runner = make_runner(conn, kind)
            if runner is None:
                results[(pid, kind)] = {"skipped": "no_provider"}
                continue
            counts = runner.poll_once(pid)
            results[(pid, kind)] = counts
            if counts.get("succeeded") or counts.get("failed") or counts.get("retried"):
                diag.record(conn, kind, "info",
                            f"vòng hỏi nền (không cần mở trang): dự án #{pid} {kind} — {counts.get('succeeded', 0)} tải về, "
                            f"{counts.get('failed', 0)} lỗi, {counts.get('retried', 0)} gen lại; còn {counts.get('running', 0)} đang chạy",
                            "bg_poll_done", project_id=pid)
        except Exception as e:  # noqa: BLE001 - one project's problem must never stop the others
            results[(pid, kind)] = {"error": f"{type(e).__name__}: {e}"}
            try:
                diag.record(conn, kind, "warn", f"vòng hỏi nền dự án #{pid} ({kind}) lỗi: {type(e).__name__}: {e} — "
                                                "job giữ nguyên, vòng sau hỏi lại", "bg_poll_error", project_id=pid)
            except Exception:  # noqa: BLE001
                pass
    return results


def default_runner(data_dir: str) -> Callable:
    """The real runners with this computer's providers (same as the page's polling fragment)."""
    def make(conn, kind):
        from .adapters import factory
        from .pipeline import Pipeline
        from .providers import ProviderError
        from .runner import ImageRunner, VideoRunner
        try:
            provider = factory.image_provider() if kind == "image" else factory.video_provider()
        except ProviderError:
            return None
        if provider is None:
            return None
        return (ImageRunner if kind == "image" else VideoRunner)(Pipeline(conn), provider, data_dir)
    return make


def round_once(db_path: str, data_dir: str) -> Dict:
    from .db import connect
    conn = connect(db_path)
    try:
        return poll_all(conn, default_runner(data_dir))
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def loop(db_path: str, one_round: Callable[[str], object], interval: float = INTERVAL_SEC, max_rounds: Optional[int] = None,
         sleep: Callable[[float], None] = time.sleep) -> int:
    """Rounds forever (max_rounds for tests); a crashed round is remembered in LAST and the next round runs anyway."""
    n = 0
    while max_rounds is None or n < max_rounds:
        n += 1
        try:
            LAST["results"] = one_round(db_path) or {}
            LAST["error"] = None
        except Exception as e:  # noqa: BLE001
            LAST["error"] = f"{type(e).__name__}: {e}"
        LAST["at"] = time.time()
        if max_rounds is None or n < max_rounds:
            sleep(interval)
    return n


def start(db_path: str, data_dir: str, interval: float = INTERVAL_SEC) -> bool:
    """Start the one background round of this dashboard process (False = already running or switched off: BG_POLL=0)."""
    global _started
    if os.environ.get("BG_POLL", "1") == "0":
        return False
    with _start_lock:
        if _started:
            return False
        _started = True
    threading.Thread(target=loop, args=(db_path, lambda db: round_once(db, data_dir), interval), daemon=True,
                     name="bg-poll").start()
    return True
