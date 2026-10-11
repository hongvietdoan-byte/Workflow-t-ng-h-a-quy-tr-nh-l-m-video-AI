"""Chạy Dashboard + vòng nền NGAY khi máy chủ lên (11/10, #24: job 'queued' nằm im sau khi khởi động lại mà chưa mở trình duyệt).

Gốc lỗi: core/bg_poll.start chỉ được gọi trong dashboard/app.main — Streamlit chỉ chạy app.py khi có một phiên trình duyệt (và trước
11/10 còn chỉ sau khi đã chọn dự án). Khởi động lại máy chủ khi không ai mở trang → không hỏi / tải / gửi job nào.

Cách sửa: tiến trình máy chủ bắt đầu vòng nền trước rồi mới chạy Streamlit — CÙNG một tiến trình, nên app.py gọi bg_poll.start lần
nữa thì nhận "đã chạy" (một luồng 'bg-poll' còn sống), không có vòng thứ hai gửi trùng job. Không đổi gì khác của Streamlit.

    py -m dashboard.serve --server.port 8501 --server.headless true …   (tools/launch_dashboard.ps1 dùng lệnh này)
"""
import os
import sys
from typing import Callable, List, Optional

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")


def start_background(db: Optional[str] = None, data: Optional[str] = None) -> bool:
    """Bắt đầu vòng nền với cùng CSDL / thư mục dữ liệu app.py dùng (PIPELINE_DB / PIPELINE_DATA, mặc định data/…)."""
    from core import bg_poll
    db = db or os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))
    data = data or os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))
    os.makedirs(os.path.dirname(db) or ".", exist_ok=True)
    _blender_reporter(db)
    return bg_poll.start(db, data)


def _blender_reporter(db: str) -> None:
    """Như app.start_background_watch: khóa Blender cũ bị chiếm lại được ghi vào diag cả khi chưa ai mở trang."""
    import re
    try:
        from core import diag, plates3d
        from core.db import connect
    except Exception:  # noqa: BLE001 - thiếu module phụ không chặn máy chủ
        return

    def report(msg: str, code: str, owner: str) -> None:
        m = re.search(r"#(\d+)", owner or "")
        conn = connect(db)
        try:
            diag.record(conn, "system", "warn", msg, code, project_id=int(m.group(1)) if m else None)
        finally:
            conn.close()
    plates3d.set_reporter(report)


def main(argv: Optional[List[str]] = None, run: Optional[Callable[[], object]] = None) -> object:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        started = start_background()
        print(f"vòng nền: {'đã bắt đầu' if started else 'không bắt đầu (đã chạy, tiến trình khác giữ, hoặc BG_POLL=0)'}", flush=True)
    except Exception as e:  # noqa: BLE001 - vòng nền hỏng không được chặn máy chủ; app.py thử lại khi có phiên
        print(f"vòng nền: lỗi khởi động {type(e).__name__}: {e} — máy chủ vẫn chạy", flush=True)
    sys.argv = ["streamlit", "run", APP] + argv
    if run is None:
        from streamlit.web import cli
        run = cli.main
    return run()


if __name__ == "__main__":
    sys.exit(main())
