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


def measured_connection(timings):
    """Tách SQLite execute/fetch, không giữ SQL/binds trong kết quả.

    Execute bao gồm thời gian chờ bên trong SQLite (có thể có lock), không phải
    phép đo lock độc lập. Không cộng các dòng thành CPU hay latency màn.
    """
    def timed(phase, statement, fn):
        start = time.perf_counter()
        try:
            return fn()
        finally:
            safe = Timings()
            safe.sql(statement, time.perf_counter() - start)
            for label, values in safe.values.items():
                timings.add(phase + " " + label, values[0])

    class Cursor(sqlite3.Cursor):
        _statement_label = "UNKNOWN"

        def _execute(self, phase, statement, fn):
            # Store only sanitized label, never the query or parameter values.
            safe = Timings()
            safe.sql(statement, 0)
            self._statement_label = next(iter(safe.values))
            return timed(phase, statement, fn)

        def execute(self, statement, parameters=()):
            return self._execute("cursor.execute", statement, lambda: super(Cursor, self).execute(statement, parameters))

        def executemany(self, statement, parameters):
            return self._execute("cursor.executemany", statement, lambda: super(Cursor, self).executemany(statement, parameters))

        def executescript(self, script):
            return self._execute("cursor.executescript", "SCRIPT", lambda: super(Cursor, self).executescript(script))

        def _fetch(self, method, fn):
            start = time.perf_counter()
            try:
                return fn()
            finally:
                timings.add("cursor." + method + " " + self._statement_label, time.perf_counter() - start)

        def fetchone(self):
            return self._fetch("fetchone", super().fetchone)

        def fetchmany(self, *args, **kwargs):
            return self._fetch("fetchmany", lambda: super(Cursor, self).fetchmany(*args, **kwargs))

        def fetchall(self):
            return self._fetch("fetchall", super().fetchall)

        def __next__(self):
            return self._fetch("next", super().__next__)

    class Connection(sqlite3.Connection):
        def cursor(self, factory=None):
            if factory not in (None, Cursor):
                raise ValueError("M60_UNMEASURED_CURSOR_FACTORY")
            return super().cursor(factory=Cursor)

        def _execute(self, phase, statement, parameters=None):
            cursor = self.cursor()
            # Call base directly: connection shortcut must not be counted twice.
            if phase == "executescript":
                return cursor._execute("connection." + phase, "SCRIPT", lambda: sqlite3.Cursor.executescript(cursor, statement))
            fn = getattr(sqlite3.Cursor, phase)
            return cursor._execute("connection." + phase, statement, lambda: fn(cursor, statement, parameters))

        def execute(self, statement, parameters=()):
            return self._execute("execute", statement, parameters)

        def executemany(self, statement, parameters):
            return self._execute("executemany", statement, parameters)

        def executescript(self, script):
            return self._execute("executescript", script)

    return Connection


def coverage_manifest(root, function_rows):
    """Inventory hàm và block AST; vào hàm KHÔNG chứng minh mọi nhánh đã chạy."""
    import ast
    root = pathlib.Path(root)
    hits = {r["label"]: r["calls"] for r in function_rows}
    out = []
    for path in sorted((root / "dashboard").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Profile reports the first decorator line for decorated functions.
                line = min([node.lineno] + [d.lineno for d in node.decorator_list])
                source = f"{rel}:{line}:{node.name}"
                out.append({"source": source, "kind": "function", "status": "EXECUTED" if source in hits else "NOT_REACHED",
                            "calls": hits.get(source, 0)})
            elif isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.Match)):
                out.append({"source": f"{rel}:{node.lineno}:{type(node).__name__}", "kind": "conditional_or_context",
                            "status": "BRANCH_NOT_PROVEN", "calls": None})
    return out


@contextlib.contextmanager
def isolated_network():
    """Deny network calls; allow only socketpair owned by this harness.

    Không phải OS sandbox. Không mở tạm global connect khi AppTest đa luồng.
    """
    import socket
    from unittest.mock import patch
    original_connect = socket.socket.connect

    def denied(*args, **kwargs):
        raise RuntimeError("M60_EXTERNAL_OPERATION_BLOCKED")

    def owned_pair(family=None, type=socket.SOCK_STREAM, proto=0):
        if type != socket.SOCK_STREAM or proto != 0:
            raise ValueError("M60_UNSUPPORTED_SOCKETPAIR")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client, server = None, None
        try:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Only original unpatched method on our new client to exact owned endpoint.
            original_connect(client, listener.getsockname())
            server, _ = listener.accept()
            return client, server
        except BaseException:
            if client is not None:
                client.close()
            if server is not None:
                server.close()
            raise
        finally:
            listener.close()

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", denied))
        stack.enter_context(patch.object(socket.socket, "connect_ex", denied))
        stack.enter_context(patch.object(socket, "create_connection", denied))
        for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
            stack.enter_context(patch.object(socket, name, denied))
        stack.enter_context(patch.object(socket, "socketpair", owned_pair))
        yield


def validate_output(root, output):
    """Harness chỉ ghi báo cáo trong docs của checkout được đo."""
    root = pathlib.Path(root).resolve(strict=True)
    output = pathlib.Path(output).resolve()
    docs = (root / "docs").resolve(strict=True)
    if not output.is_relative_to(docs) or output.suffix != ".json":
        raise ValueError("M60_REPORT_OUTSIDE_DOCS")
    return output


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
    """7 màn + Motion/default/expert AppTest trên bản sao fixture phong phú.

    Đây là đo server Python có overhead probe, không benchmark browser/production.
    Không bấm nút, không đo mọi nhánh cờ/expander hay callback.
    """
    import json
    import os
    import hashlib
    import subprocess
    import tempfile
    from unittest.mock import patch
    root = pathlib.Path(root).resolve()
    output = validate_output(root, output)
    source_paths = [path for folder in ("dashboard", "core") for path in sorted((root / folder).rglob("*.py"))]
    source_paths += [root / "tools" / name for name in ("m60_profile.py", "ui_snapshot.py", "seed_demo.py")]
    source_rows = [{"source": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                   for path in source_paths]
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
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(os, "environ", env))
            stack.enter_context(isolated_network())
            stack.enter_context(patch.object(subprocess, "Popen", denied))
            try:
                import winreg
                for name in ("OpenKey", "QueryValueEx"):
                    stack.enter_context(patch.object(winreg, name, denied))
            except ImportError:
                pass
            from core import db, lineage, bg_poll, ff_site, research, llm_runner, music
            from core.adapters import factory
            from streamlit.testing.v1 import AppTest
            for mod, name in ((bg_poll, "start"), (ff_site, "maybe_monthly"), (research, "maybe_run_in_background"),
                              (llm_runner, "client_from_env"), (music, "audio_provider"),
                              (factory, "image_provider"), (factory, "video_provider"), (factory, "subject_library")):
                stack.enter_context(patch.object(mod, name, return_value=None))
            # Audited builder is not its browser/main entrypoint. It rmtree's an
            # existing out_dir: supply a fresh child which MUST NOT exist.
            from tools.ui_snapshot import build_sample_data
            sample_dir = tmp / "synthetic-source"
            if sample_dir.exists():
                raise ValueError("M60_FIXTURE_PATH_EXISTS")
            sample = build_sample_data(str(sample_dir), n_projects=projects, scenes_primary=shots,
                                       images=True, rich_others=shots)
            source = pathlib.Path(sample["db"])
            before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            copy_database(source, tmp / "copy.sqlite")
            env["PIPELINE_DATA"] = sample["data"]
            # The rich builder has locked Bible, approved/rejected/pending QC,
            # image PNG placeholders, motion prompts, queued/running/video jobs.
            # No real video, TTS waveform or Stage-A approved geometry is invented.
            sql = Timings()
            MeasuredConnection = measured_connection(sql)
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
            cases = [(code, False) for code in ("home", "1", "2", "3", "4", "5", "team", "monitor")]
            cases += [(code, True) for code in ("1", "2", "3", "5")]
            for code, expert in cases:
                sql.values.clear()
                case_functions = Timings()
                at = AppTest.from_file(str(root / "dashboard/app.py"), default_timeout=90)
                at.query_params["step"] = code
                at.session_state["global_pid"] = sample["projects"][0][0]
                at.session_state["expert_mode"] = expert
                # Avoid bootstrap housekeeping, auto-sync and auto-scan callbacks.
                for key in ("assets_synced", "sounds_scanned", "ff_site_checked", "research_checked", "asset_files_checked"):
                    at.session_state[key] = True
                with function_probe(root, case_functions):
                    begin = time.perf_counter()
                    at.run()
                    cold = time.perf_counter() - begin
                    cold_errors = len(at.exception)
                    begin = time.perf_counter()
                    at.run()
                    warm = time.perf_counter() - begin
                    warm_errors = len(at.exception)
                for label, values in case_functions.values.items():
                    for value in values:
                        functions.add(label, value)
                screens.append({"screen": code, "expert": expert, "cold_ms": round(cold*1000, 3), "warm_ms": round(warm*1000, 3),
                                "cold_exception_count": cold_errors, "warm_exception_count": warm_errors,
                                "exception_count": cold_errors + warm_errors, "sql_operations": sql.rows(),
                                "functions_inclusive": case_functions.rows()})
            # Isolated explicit lineage call; do not merge with UI thread measurements.
            c = db.connect(str(tmp / "copy.sqlite"))
            t = Timings()
            t.measure("lineage.summary", lambda: lineage.summary(c, 1))
            c.close()
            from datetime import datetime, timezone
            if any(item["sha256"] != hashlib.sha256((root / item["source"]).read_bytes()).hexdigest() for item in source_rows):
                raise RuntimeError("M60_SOURCE_CHANGED_DURING_RUN")
            source_hash = hashlib.sha256(json.dumps(source_rows, sort_keys=True).encode()).hexdigest()
            result = {"schema": 2, "measured_at": datetime.now(timezone.utc).isoformat(),
                      "source_snapshot_sha256": source_hash, "source_manifest": source_rows,
                      "fixture": {"projects": projects, "shots_per_project": shots, "copied": True,
                                  "kind": "ui_snapshot.rich", "image_pngs": len(list(sample_dir.rglob("*.png"))),
                                  "source_database_unchanged": before_hash == hashlib.sha256(source.read_bytes()).hexdigest()},
                      "screens": screens, "functions_inclusive": functions.rows(), "lineage": t.rows(), "errors": t.errors,
                      "coverage": coverage_manifest(root, functions.rows()),
                      "limitations": ["synthetic image/Bible/QC/motion fixtures, not production or real video/audio",
                                      "Python server inclusive wall-time with probe overhead; samples cold+warm once per case",
                                      "SQLite execute/fetch measured separately; no CPU or independent lock contention measurement",
                                      "AppTest renders tab/popover/expander server bodies without browser visibility proof",
                                      "no buttons/callbacks clicked; conditional AST branches remain explicitly unproven",
                                      "feature defaults only, expert session cases do not prove all flags/ACL/Stage-A geometry branches",
                                      "source DB hash checked, assets are synthetic; do not infer production integrity or max throughput"]}
            # AppTest caches resources across reruns; close only connections this
            # harness owns before deleting its temporary SQLite copy on Windows.
            for owned in opened:
                owned.close()
    save_report(output, result)
    return result


def main(argv=None):
    """CLI chỉ dựng fixture riêng; không nhận đường DB, root hay data thật."""
    import argparse
    import datetime
    import json
    parser = argparse.ArgumentParser(description="M60 AppTest synthetic profile, 0 USD")
    parser.add_argument("--out", default=f"docs/M6_0_PROFILE_RICH_{datetime.date.today().isoformat()}.json")
    parser.add_argument("--projects", type=int, default=5)
    parser.add_argument("--shots", type=int, default=40)
    args = parser.parse_args(argv)
    root = pathlib.Path(__file__).resolve().parents[1]
    try:
        output = validate_output(root, root / args.out)
        if not 1 <= args.projects <= 10 or not 1 <= args.shots <= 100:
            raise ValueError("M60_FIXTURE_LIMIT")
        result = profile_fixture(root, output, projects=args.projects, shots=args.shots)
        errors = sum(s["exception_count"] for s in result["screens"]) + len(result.get("errors", []))
        print(json.dumps({"cases": len(result["screens"]),
                          "exceptions": errors,
                          "output": output.relative_to(root).as_posix()}))
        return 1 if errors else 0
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
