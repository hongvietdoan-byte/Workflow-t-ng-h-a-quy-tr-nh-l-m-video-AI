"""M60: đầu dò số đo không xuất SQL literal/payload. Không tự chạy Dashboard.

Chỉ chạy harness trong dict môi trường giả. copy_database dùng backup WAL từ
mode=ro; bản sao còn phải cách ly tài nguyên trước khi mở Dashboard.
"""
import collections
import contextlib
import pathlib
import re
import sqlite3
import threading
import time


class Timings:
    def __init__(self):
        self.values = collections.defaultdict(list)
        self.errors = []
        self._lock = threading.Lock()

    def add(self, label, seconds):
        with self._lock:
            self.values[label].append(seconds)

    def sql(self, statement, seconds):
        # Chỉ tên bảng định danh thông thường; không giữ query, binds hay literal.
        statement = re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*.*?\*/", " ", statement, flags=re.S)
        op = re.match(r"\s*([A-Za-z]+)", statement)
        op = op.group(1).upper() if op else "UNKNOWN"
        table = re.search(r"\b(?:FROM|INTO|UPDATE|JOIN)\s+([A-Za-z_][A-Za-z_0-9]*)", statement, re.I)
        label = op + (" " + table.group(1) if table else "")
        self.add(label, seconds)

    def measure(self, label, fn):
        start = time.perf_counter()
        try:
            return fn()
        except Exception as exc:
            self.errors.append({"label": label, "type": type(exc).__name__})
        finally:
            self.add(label, time.perf_counter() - start)

    def rows(self):
        return sorted(({"label": k, "calls": len(v), "total_ms": round(sum(v)*1000, 3),
                        "max_ms": round(max(v)*1000, 3)} for k, v in self.values.items()),
                      key=lambda r: r["total_ms"], reverse=True)


def copy_database(source, destination):
    """Không bootstrap/migrate nguồn; không đè đích đã tồn tại (kể cả hardlink)."""
    source, destination = pathlib.Path(source).resolve(strict=True), pathlib.Path(destination)
    # Exclusive creation prevents replacing an existing file/link.
    with destination.open("xb"):
        pass
    try:
        with contextlib.closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            src.execute("PRAGMA query_only=ON")
            with contextlib.closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def save_report(output, result):
    """Atomic replace không đi theo hardlink/symlink đích; thư mục cha phải tin cậy."""
    import json
    import os
    import tempfile
    output = pathlib.Path(output)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix="m60-report-", suffix=".tmp", delete=False) as f:
            name = f.name
            json.dump(result, f, ensure_ascii=False, indent=2)
        os.replace(name, output)
    finally:
        if name is not None:
            pathlib.Path(name).unlink(missing_ok=True)


@contextlib.contextmanager
def function_probe(root, timings):
    """Wall-time inclusive của hàm Dashboard/core; không đọc locals/args/return.

    Dùng threading.setprofile cho ScriptRunner AppTest mới. Các interval lồng nhau
    không cộng thành tổng màn; không đo SQL fetch/lock riêng, CPU hay trình duyệt.
    """
    root = pathlib.Path(root).resolve()
    local = threading.local()
    names = {}

    def probe(frame, event, arg):
        if event not in ("call", "return"):
            return
        filename = frame.f_code.co_filename
        if filename not in names:
            try:
                rel = pathlib.Path(filename).resolve().relative_to(root)
                names[filename] = rel.as_posix() if rel.parts[0] in ("core", "dashboard") else None
            except (ValueError, OSError):
                names[filename] = None
        rel = names[filename]
        if rel is None:
            return
        key = id(frame)
        starts = getattr(local, "starts", None)
        if starts is None:
            starts = local.starts = {}
        if event == "call":
            starts[key] = time.perf_counter()
        elif key in starts:
            elapsed = time.perf_counter() - starts.pop(key)
            timings.add(f"{rel}:{frame.f_code.co_firstlineno}:{frame.f_code.co_name}", elapsed)

    old = threading.getprofile()
    threading.setprofile(probe)
    try:
        yield
    finally:
        threading.setprofile(old)


def profile_fixture(root, output, projects=5, shots=40):
    """7 màn AppTest trên bản sao fixture; không nhận đường DB/data sản xuất.

    Đây là đo server Python có overhead probe, không benchmark browser/production.
    Không bấm nút, không đo mọi nhánh cờ/expander hay callback.
    """
    import json
    import os
    import socket
    import subprocess
    import tempfile
    from unittest.mock import patch
    root = pathlib.Path(root).resolve()
    output = pathlib.Path(output)
    if not 1 <= projects <= 10 or not 1 <= shots <= 100:
        raise ValueError("fixture vượt giới hạn")
    with tempfile.TemporaryDirectory(prefix="m60-fixture-") as tmp:
        tmp = pathlib.Path(tmp)
        env = {"HOME": str(tmp), "USERPROFILE": str(tmp), "TEMP": str(tmp), "TMP": str(tmp),
               "DASHBOARD_AUTH": "off", "BG_POLL": "0", "FF_SITE_AUTO": "0",
               "DASHBOARD_SYNC_BACKGROUND": "0", "FEATURE_BASELINE_FILE": "",
               "FEATURE_SETTINGS_FILE": str(tmp / "flags.json"), "KNOWLEDGE_USER_DIR": str(tmp / "knowledge"),
               "PIPELINE_DATA": str(tmp / "projects"), "PIPELINE_DB": str(tmp / "copy.sqlite"),
               "ASSET_DIR": str(tmp / "assets"), "PYTHONUTF8": "1",
               "IMAGE_PROVIDER": "", "VIDEO_PROVIDER": "", "AUDIO_PROVIDER": "", "LLM_PROVIDER": ""}
        def denied(*args, **kwargs):
            raise RuntimeError("M60_EXTERNAL_OPERATION_BLOCKED")
        original_socket_connect = socket.socket.connect
        def local_self_pipe(sock, address):
            # Windows asyncio socketpair self-pipe uses an ephemeral loopback port.
            # Main dashboard ports and every remote address remain blocked.
            if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1") and 49152 <= address[1] <= 65535:
                return original_socket_connect(sock, address)
            return denied()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(os, "environ", env))
            stack.enter_context(patch.object(socket.socket, "connect", local_self_pipe))
            stack.enter_context(patch.object(socket, "create_connection", denied))
            stack.enter_context(patch.object(subprocess, "Popen", denied))
            try:
                import winreg
                stack.enter_context(patch.object(winreg, "QueryValueEx", denied))
            except ImportError:
                pass
            from core import db, lineage, bg_poll, ff_site, research, llm_runner
            from core.pipeline import Pipeline
            from streamlit.testing.v1 import AppTest
            for mod, name in ((bg_poll, "start"), (ff_site, "maybe_monthly"), (research, "maybe_run_in_background"),
                              (llm_runner, "client_from_env")):
                stack.enter_context(patch.object(mod, name, return_value=None))
            # Minimal synthetic source built only here. No supplied path is ever opened.
            conn = db.connect(str(tmp / "source.sqlite"))
            p = Pipeline(conn)
            for i in range(projects):
                pid = p.create_project(f"M60 fixture {i}")
                for n in range(shots):
                    sid = p.create_scene(pid, n + 1, f"Fixture {n + 1}")
                    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"text": "Fixture", "image_prompt": "fixture"}), sid))
                conn.commit()
            conn.close()
            copy_database(tmp / "source.sqlite", tmp / "copy.sqlite")
            sql = Timings()
            class MeasuredConnection(sqlite3.Connection):
                def execute(self, statement, parameters=()):
                    start = time.perf_counter()
                    try:
                        return super().execute(statement, parameters)
                    finally:
                        sql.sql(statement, time.perf_counter() - start)
            original_connect = sqlite3.connect
            opened = []
            def connect(*args, **kwargs):
                database = args[0] if args else kwargs.get("database", ":memory:")
                if str(database) != ":memory:":
                    # This wrapper owns only the private fixture copy. Never
                    # relax threading policy for live/external connections.
                    candidate = pathlib.Path(database).resolve()
                    if not candidate.is_relative_to(tmp.resolve()):
                        raise PermissionError("M60_EXTERNAL_DATABASE_BLOCKED")
                kwargs["factory"] = MeasuredConnection
                # AppTest ScriptRunner completes before cleanup on the harness
                # thread. Connections are private, no concurrent query use.
                kwargs["check_same_thread"] = False
                c = original_connect(*args, **kwargs)
                opened.append(c)
                stack.callback(c.close)
                return c
            stack.enter_context(patch.object(sqlite3, "connect", connect))
            screens, functions = [], Timings()
            for code in ("home", "1", "2", "4", "5", "team", "monitor"):
                sql.values.clear()
                at = AppTest.from_file(str(root / "dashboard/app.py"), default_timeout=90)
                at.query_params["step"] = code
                with function_probe(root, functions):
                    begin = time.perf_counter()
                    at.run()
                    cold = time.perf_counter() - begin
                    begin = time.perf_counter()
                    at.run()
                    warm = time.perf_counter() - begin
                screens.append({"screen": code, "cold_ms": round(cold*1000, 3), "warm_ms": round(warm*1000, 3),
                                "exception_count": len(at.exception), "sql_execute": sql.rows()})
            # Isolated explicit lineage call; do not merge with UI thread measurements.
            c = db.connect(str(tmp / "copy.sqlite"))
            t = Timings()
            t.measure("lineage.summary", lambda: lineage.summary(c, 1))
            c.close()
            result = {"fixture": {"projects": projects, "shots_per_project": shots, "copied": True},
                      "screens": screens, "functions_inclusive": functions.rows(), "lineage": t.rows(), "errors": t.errors,
                      "limitations": ["synthetic empty-media fixture", "Python server inclusive wall-time with probe overhead",
                                      "SQL execute only, not cursor fetch/CPU/lock", "no browser/click/expanded conditional branch coverage"]}
            # AppTest caches resources across reruns; close only connections this
            # harness owns before deleting its temporary SQLite copy on Windows.
            for owned in opened:
                owned.close()
    save_report(output, result)
    return result
