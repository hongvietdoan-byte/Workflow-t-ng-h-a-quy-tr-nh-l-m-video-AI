"""C-DEVSYS-MAPS mục 5 (người dùng 21/10): ghi TỪNG BƯỚC BẤM để sơ đồ "Làm phim qua Dashboard" của AI Dev System tô theo DỰ ÁN THẬT.

Cờ `ui_step_log` (mặc định TẮT — tắt = không ghi gì, Dashboard y nguyên). Sự kiện chỉ-thêm vào bảng diag_events có sẵn:
  - stage `ui_step`: nút chính của Bước 1–5 — code `ui_step:<nút>`, message "<màn> · <kết quả>[: câu]", project_id; mức info (ok) / warn
    (cảnh báo / giữ) / error (lỗi, kèm mã lỗi sổ devsys/errors.json nếu biết);
  - stage `cli_step`: lệnh làm THAY Dashboard (tools/stage_auto.py, stage_previs.py, replay_payload.py, script sửa CSDL) — code
    `cli_step:<công cụ>`, message = việc.
Ghi log KHÔNG BAO GIỜ làm hỏng nút / lệnh: mọi lỗi bị nuốt (đây là quan sát, không phải điều khiển). Đếm lần lặp: diag.record gộp cùng
nội dung trong 10 phút thành một dòng có `count`. devsys đọc lại bằng `events()` (CSDL mở mode=ro ở phía devsys)."""
from typing import Dict, List, Optional

FLAG = "ui_step_log"
RESULTS = {"ok": "info", "warn": "warn", "hold": "warn", "error": "error", "skip": "warn"}   # skip = người chủ ý bỏ qua cổng: không phải lỗi


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def record(conn, project_id: Optional[int], screen: str, button: str, result: str = "ok", note: str = "",
           error_code: Optional[str] = None) -> None:
    """Một bước bấm trên Dashboard. result: ok · warn · hold (cổng giữ) · error · skip (bỏ qua cổng). Cờ tắt → không làm gì."""
    try:
        if conn is None or not enabled():
            return
        from . import diag
        res = result if result in RESULTS else "ok"
        msg = f"{screen} · {res}" + (f" [{error_code}]" if error_code else "") + (f": {note}" if note else "")
        diag.record(conn, "ui_step", RESULTS[res], msg, f"ui_step:{button}", project_id)
    except Exception:  # noqa: BLE001 - quan sát, không bao giờ là lý do nút hỏng
        pass


def cli(conn, tool: str, project_id: Optional[int], task: str, result: str = "ok") -> None:
    """Một lệnh làm thay Dashboard (công cụ dòng lệnh / script sửa CSDL). Cờ tắt → không làm gì."""
    try:
        if conn is None or not enabled():
            return
        from . import diag
        res = result if result in RESULTS else "ok"
        diag.record(conn, "cli_step", RESULTS[res], f"{tool} · {res}: {task}", f"cli_step:{tool}", project_id)
    except Exception:  # noqa: BLE001
        pass


def events(conn, project_id: int) -> List[Dict]:
    """Sự kiện ui_step / cli_step của dự án (cũ → mới): {kind, key, severity, message, count, at, last_at}. Chỉ đọc."""
    rows = conn.execute("SELECT stage, code, severity, message, count, at, last_at FROM diag_events WHERE project_id=? "
                        "AND stage IN ('ui_step', 'cli_step') ORDER BY id", (project_id,)).fetchall()
    out = []
    for r in rows:
        stage, code = r[0], str(r[1] or "")
        out.append({"kind": stage, "key": code.split(":", 1)[1] if ":" in code else code, "severity": r[2], "message": r[3],
                    "count": int(r[4] or 1), "at": r[5], "last_at": r[6]})
    return out
