"""Vòng hỏi nền (sau dự án Khủng Long Đỏ, 08/10): job ảnh/clip đã gửi ở nhà cung cấp được hỏi trạng thái và tải về cả khi KHÔNG
có tab nào mở và dự án không chạy tự động.

Trước đây chỉ hai nơi hỏi: khung tự cập nhật của trang (dashboard/widgets.py, chạy khi trang của dự án đang mở) và luồng chạy tự động
(core/autopilot.py). Đóng tab giữa chừng = clip đã xong (đã tính tiền) nằm ở nhà cung cấp tới lần mở trang sau.

Vòng này hỏi + tải (runner.poll_once — không tốn tiền), không chạy QC. Mỗi dự án và mỗi loại job một lượt riêng, bọc lỗi riêng: lỗi
một dự án ghi diag rồi qua dự án kế. Hỏi trùng với trang / chạy tự động đã được khóa lượt của runner (_turn, M3) chặn.

Lỗi A (08/10, #24 job 578–584 nằm 'queued' 22 phút sau khi render nền xong): job NGƯỜI DÙNG đã bấm gửi mà runner._wait giữ lại (chờ
render nền 3D, ảnh neo storyboard, ảnh toàn cảnh, ảnh/clip trước) trước đây chỉ đi khi có người bấm lại. Nay send_ready gửi chúng khi hết
lý do chờ — qua đúng runner.submit_pending của nút bấm (cổng tiền/hết credit, max_concurrent, throttle, khóa _turn, dự án tạm dừng). Không
gửi: job của chạy tự động (origin 'auto'), dự án tạm dừng / đã cất, dự án mà chạy tự động đang chạy / xếp hàng / chờ ở cổng (nó tự gửi),
khi lệnh dòng lệnh chạm trần (script_cap), job xếp hàng quá AUTO_SEND_MAX_AGE_H giờ (nói bằng diag, bấm ▶ Gen để gửi)."""
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


AUTO_SEND_MAX_AGE_H = 24
AUTOPILOT_OWNS = ("running", "queued", "waiting")     # core.autopilot RUNNING / QUEUED / WAITING: the run sends (or wakes) its own jobs


def queued_by_person(conn) -> Dict[Tuple[int, str], Dict[str, List[int]]]:
    """{(project, kind): {"send": [job ids], "old": [job ids]}} — queued jobs a person asked for that no task exists for yet, in projects
    where nothing else will send them (see the module note)."""
    rows = conn.execute(
        "SELECT j.id, j.project_id, j.type, j.created_at FROM jobs j JOIN projects p ON p.id=j.project_id "
        "WHERE j.state='queued' AND (j.external_id IS NULL OR j.external_id='') AND j.type IN ('image_gen','video_gen') "
        "AND COALESCE(j.origin,'')<>'auto' AND COALESCE(p.paused,0)=0 AND COALESCE(p.archived,0)=0 "
        "AND COALESCE(p.autopilot_state,'') NOT IN (" + ",".join("?" * len(AUTOPILOT_OWNS)) + ") ORDER BY j.id",
        AUTOPILOT_OWNS).fetchall()
    limit = time.time() - AUTO_SEND_MAX_AGE_H * 3600
    out: Dict[Tuple[int, str], Dict[str, List[int]]] = {}
    for r in rows:
        slot = out.setdefault((r["project_id"], KINDS[r["type"]]), {"send": [], "old": []})
        slot["old" if _epoch(r["created_at"]) < limit else "send"].append(r["id"])
    return out


def _epoch(stamp) -> float:
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0                                    # unreadable time: treated as old (never sent by itself)


def send_ready(conn, make_runner: Callable) -> Dict[Tuple[int, str], Dict]:
    """Lỗi A: send the person's queued jobs whose wait is over (runner._wait decides, as for the button). One project's problem is
    said (diag) and the others go on."""
    from . import script_cap
    cap = script_cap.active()
    if cap is not None and cap.stopped:
        return {}                                     # a command-line run hit its --max-usd: it cancels its own queue
    results: Dict[Tuple[int, str], Dict] = {}
    for (pid, kind), ids in queued_by_person(conn).items():
        if ids["old"]:
            diag.record(conn, kind, "warn", f"dự án #{pid}: {len(ids['old'])} job {kind} xếp hàng hơn {AUTO_SEND_MAX_AGE_H} giờ "
                        f"(job {', '.join(map(str, ids['old'][:8]))}) — vòng nền KHÔNG tự gửi job cũ; bấm ▶ Gen ở bước tương ứng nếu "
                        "vẫn muốn gửi, hoặc hủy", "bg_send_old", project_id=pid)
        if not ids["send"]:
            continue
        try:
            runner = make_runner(conn, kind)
            if runner is None:
                results[(pid, kind)] = {"skipped": "no_provider"}
                continue
            sent = runner.submit_pending(pid, only=set(ids["send"]))
            results[(pid, kind)] = {"sent": sent, "queued": len(ids["send"])}
            if sent:
                diag.record(conn, kind, "info", f"vòng nền tự gửi {sent}/{len(ids['send'])} job {kind} dự án #{pid} bạn đã bấm gửi — "
                            "lý do chờ đã hết (render nền / ảnh neo / ảnh trước xong)", "bg_auto_send", project_id=pid)
        except Exception as e:  # noqa: BLE001 - one project's problem must never stop the others
            results[(pid, kind)] = {"error": f"{type(e).__name__}: {e}"}
            try:
                diag.record(conn, kind, "warn", f"vòng nền tự gửi job dự án #{pid} ({kind}) lỗi: {type(e).__name__}: {e} — job giữ "
                                                "trong hàng đợi, vòng sau thử lại", "bg_send_error", project_id=pid)
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
        make = default_runner(data_dir)
        out = {}
        review = change_review_round(conn, data_dir)   # 10/10: rà thay đổi TRƯỚC khi tự gửi — mục đỏ kịp chặn gen
        if review:
            out[(0, "change_review")] = review
        out.update(poll_all(conn, make))
        out.update({(pid, f"{kind}_send"): r for (pid, kind), r in send_ready(conn, make).items()})   # lỗi A
        return out
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def change_review_round(conn, data_dir: str) -> Optional[Dict]:
    """Tổ rà soát tác động (cờ change_review): mọi thay đổi đang chờ → luật code + agent Claude (không trần — người dùng 10/10)."""
    from . import change_review
    if not change_review.enabled():
        return None
    client = None
    try:
        from . import llm_runner
        client = llm_runner.client_from_env(ledger=llm_runner.db_file(conn))
    except Exception as e:  # noqa: BLE001 - no Claude: the code rules still run, said once
        diag.record(conn, "system", "warn", f"Tổ rà soát tác động: không gọi được Claude ({type(e).__name__}) — chỉ chạy luật code",
                    "change_review_noclaude", None)
    return change_review.process_pending(conn, data_dir, client=client)


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
