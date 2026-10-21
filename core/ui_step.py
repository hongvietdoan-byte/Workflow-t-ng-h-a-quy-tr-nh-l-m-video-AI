"""C-DEVSYS-MAPS mục 5 (người dùng 21/10): ghi TỪNG BƯỚC BẤM để sơ đồ "Làm phim qua Dashboard" của AI Dev System tô theo DỰ ÁN THẬT.

Cờ `ui_step_log` (mặc định TẮT — tắt = không ghi gì, Dashboard y nguyên). Sự kiện chỉ-thêm vào bảng diag_events có sẵn:
  - stage `ui_step`: nút chính của Bước 1–5 — code `ui_step:<nút>`, message "<màn> · <kết quả>[: câu]", project_id; mức info (ok) / warn
    (cảnh báo / giữ) / error (lỗi, kèm mã lỗi sổ devsys/errors.json nếu biết);
  - stage `cli_step`: lệnh làm THAY Dashboard (tools/stage_auto.py, stage_previs.py, replay_payload.py, script sửa CSDL) — code
    `cli_step:<công cụ>`, message = việc.
Ghi log KHÔNG BAO GIỜ làm hỏng nút / lệnh: mọi lỗi bị nuốt (đây là quan sát, không phải điều khiển). Đếm lần lặp: cùng nội dung trong
10 phút = một dòng có `count` (diag._write). devsys đọc lại bằng `events()` (CSDL mở mode=ro ở phía devsys).
C-DEVSYS-MAPS-FIX (rà phiên chính 21/10):
  - skip (bỏ qua cổng / gen lại vượt trần) = ĐỎ kèm mã (đề mục 6) — mặc định mã `gate_skipped`;
  - KHÔNG đi qua diag.record (thử lại 3 lần × timeout 60 s của kết nối trang → CSDL khóa làm nút đứng tới ~3 phút): kết nối RIÊNG,
    busy_timeout BUSY_MS, ghi MỘT lần; không ghi được → bỏ, nói ra stderr + <db>.diag_lost.log (diag._keep_lost)."""
import sqlite3
from typing import Dict, List, Optional

FLAG = "ui_step_log"
RESULTS = {"ok": "info", "warn": "warn", "hold": "warn", "error": "error", "skip": "error"}   # skip: bỏ qua cổng = ĐỎ kèm mã
BUSY_MS = 1000
# mã sự kiện của bước bấm (không phải mã lỗi gốc của sổ devsys/errors.json — mã sổ truyền thẳng khi nút biết)
GATE_SKIPPED = "gate_skipped"          # vẫn gen dù cổng trước gen chặn
REGEN_SAME_INPUT = "regen_same_input"  # gen lại bị từ chối: đầu vào y nguyên lần trước (CHUAN_XAY_DUNG luật 3)
REGEN_OVER_LIMIT = "regen_over_limit"  # người làm lại job đã vượt trần gen lại tự động


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
        if res == "skip" and not error_code:
            error_code = GATE_SKIPPED
        msg = f"{screen} · {res}" + (f" [{error_code}]" if error_code else "") + (f": {note}" if note else "")
        _write(conn, "ui_step", RESULTS[res], msg, f"ui_step:{button}", project_id)
    except Exception:  # noqa: BLE001 - quan sát, không bao giờ là lý do nút hỏng
        pass


def _write(conn, stage: str, severity: str, message: str, code: str, project_id: Optional[int]) -> None:
    """MỘT lần ghi qua kết nối riêng (busy_timeout BUSY_MS) — không thử lại, không giữ nút; CSDL khóa / lỗi → diag._keep_lost."""
    from . import diag
    msg = diag.redact(message)[:400]
    path = diag._db_file(conn)
    own = None
    try:
        if path:
            own = sqlite3.connect(path, timeout=BUSY_MS / 1000)
            own.row_factory = sqlite3.Row
            own.execute(f"PRAGMA busy_timeout={BUSY_MS}")
        diag._write(own or conn, stage, severity, msg, code, project_id, None, None)   # CSDL trong bộ nhớ: chính kết nối đó
    except sqlite3.Error as e:
        try:
            (own or conn).rollback()
        except sqlite3.Error:
            pass
        diag._keep_lost(conn, f"{stage}/{severity}/{code} p{project_id or '-'}: {msg}", e)
    finally:
        if own is not None:
            own.close()


def cli(conn, tool: str, project_id: Optional[int], task: str, result: str = "ok", flag_checked: bool = False) -> None:
    """Một lệnh làm thay Dashboard (công cụ dòng lệnh / script sửa CSDL). Cờ tắt → không làm gì. Gọi SAU khi lệnh chạy xong (kết quả
    thật: ok / error). flag_checked=True: nơi gọi đã kiểm cờ của MÁY ghi (replay_payload: cờ ở tệp 🧪 của <main>, không phải repo chạy)."""
    try:
        if conn is None or not (flag_checked or enabled()):
            return
        res = result if result in RESULTS else "ok"
        _write(conn, "cli_step", RESULTS[res], f"{tool} · {res}: {task}", f"cli_step:{tool}", project_id)
    except Exception:  # noqa: BLE001
        pass


def run_cli(tool: str, fn, argv=None):
    """C-DEVSYS-MAPS-FIX: chạy main của công cụ dòng lệnh rồi ghi cli_step SAU khi chạy, theo KẾT QUẢ THẬT (lỗi / sys.exit khác 0 → error
    kèm lý do). fn(argv, step) điền step = {"conn", "project", "task"} khi lượt đó làm việc ghi CSDL; chế độ chỉ đọc không điền → không ghi."""
    step: Dict = {}
    try:
        out = fn(argv, step)
    except BaseException as e:  # noqa: BLE001 - ghi xong rồi ném lại nguyên vẹn
        ok = isinstance(e, SystemExit) and e.code in (None, 0)
        _cli_done(tool, step, ok, None if ok else (str(e) or type(e).__name__))
        raise
    _cli_done(tool, step, True)
    return out


def _cli_done(tool: str, step: Dict, ok: bool, why: Optional[str] = None) -> None:
    if step.get("conn") is not None:
        cli(step["conn"], tool, step.get("project"), str(step.get("task") or "") + (f" — lỗi: {why[:160]}" if why else ""),
            "ok" if ok else "error")


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
