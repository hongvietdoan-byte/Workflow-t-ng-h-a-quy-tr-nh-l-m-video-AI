"""C-M83-TOOL (M8.3): tools/load_test_ui.py — phần không cần trình duyệt (dữ liệu giả, sao CSDL mode=ro, đầu dò, tổng hợp, bảng);
một lượt thật N=1 bằng Chromium đánh dấu slow."""
import json
import os
import sqlite3
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import load_test_ui as L  # noqa: E402


def test_fake_data_has_projects_times_shots(tmp_path):
    made = L.build_data(str(tmp_path / "d"), projects=3, shots=20)
    conn = sqlite3.connect(made["db"])
    counts = [r[0] for r in conn.execute("SELECT COUNT(*) FROM scenes GROUP BY project_id ORDER BY project_id")]
    jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE type='image_gen' AND state IN ('succeeded', 'pending_review')").fetchone()[0]
    conn.close()
    assert counts == [20, 20, 20]
    assert jobs > 0                                                      # có ảnh chờ duyệt để phiên đo bấm "✔ Duyệt"
    assert len(made["projects"]) == 3 and os.listdir(os.path.join(made["data"], str(made["projects"][1][0]), "images"))


def test_copy_db_opens_the_source_with_mode_ro_even_with_special_characters(tmp_path, monkeypatch):
    src = tmp_path / "a b#%?x" / "real.sqlite"
    src.parent.mkdir()
    c = sqlite3.connect(src)
    c.execute("CREATE TABLE projects(id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("INSERT INTO projects(name) VALUES ('A')")
    c.commit()
    c.close()
    seen = []
    real = sqlite3.connect

    def spy(*a, **k):
        seen.append((a[0] if a else k.get("database"), k.get("uri")))
        return real(*a, **k)
    monkeypatch.setattr(L.sqlite3, "connect", spy)
    made = L.copy_db(str(src), str(tmp_path / "out"))
    assert made["projects"] == [(1, "A", "copy")]
    first, uri = seen[0]
    assert uri and str(first).startswith("file:") and str(first).endswith("?mode=ro")


def test_copy_db_neutralizes_paths_to_real_files_and_real_claude(tmp_path):
    src = tmp_path / "real.sqlite"
    c = sqlite3.connect(src)
    c.executescript("""
        CREATE TABLE projects(id INTEGER PRIMARY KEY, name TEXT, llm_provider TEXT);
        CREATE TABLE jobs(id INTEGER PRIMARY KEY, llm_provider TEXT);
        CREATE TABLE asset_images(id INTEGER PRIMARY KEY, path TEXT, status TEXT);
        CREATE TABLE asset_sources(id INTEGER PRIMARY KEY, auto INTEGER);
        CREATE TABLE sound_sources(id INTEGER PRIMARY KEY, auto INTEGER);
        CREATE TABLE sounds(id INTEGER PRIMARY KEY, tags TEXT, heard TEXT);
        INSERT INTO sounds(tags, heard) VALUES (NULL, NULL), ('rain', '[]');
        INSERT INTO projects(name, llm_provider) VALUES ('A', 'claude_cli');
        INSERT INTO jobs(llm_provider) VALUES ('anthropic'), (NULL);
        INSERT INTO asset_images(path, status) VALUES ('/real/x.png', 'removed'), ('/real/y.png', 'active');
        INSERT INTO asset_sources(auto) VALUES (1); INSERT INTO sound_sources(auto) VALUES (1);
    """)
    c.commit()
    c.close()
    before = src.read_bytes()
    made = L.copy_db(str(src), str(tmp_path / "out"))
    d = sqlite3.connect(made["db"])
    assert d.execute("SELECT llm_provider FROM projects").fetchone()[0] is None
    assert [r[0] for r in d.execute("SELECT llm_provider FROM jobs ORDER BY id")] == ["mock", None]
    assert [r[0] for r in d.execute("SELECT status FROM asset_images")] == ["active"]    # dọn rác Kho không xóa file thật
    assert d.execute("SELECT auto FROM asset_sources").fetchone()[0] == 0
    assert d.execute("SELECT auto FROM sound_sources").fetchone()[0] == 0
    assert not d.execute("SELECT 1 FROM sounds WHERE tags IS NULL OR heard IS NULL").fetchone()   # không phân tích / nghe lại N lần
    assert d.execute("SELECT tags FROM sounds WHERE id=2").fetchone()[0] == "rain"
    d.close()
    assert src.read_bytes() == before


def test_copy_db_reads_the_original_read_only(tmp_path):
    src = tmp_path / "real.sqlite"
    conn = sqlite3.connect(src)
    conn.execute("CREATE TABLE projects(id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO projects(name) VALUES ('A'), ('B')")
    conn.commit()
    conn.close()
    os.chmod(src, 0o444)                                                 # bản gốc chỉ đọc vẫn sao được (mode=ro)
    before = src.read_bytes()
    made = L.copy_db(str(src), str(tmp_path / "out"))
    assert [p[1] for p in made["projects"]] == ["A", "B"]
    assert src.read_bytes() == before and not os.path.exists(str(src) + "-wal")
    c = sqlite3.connect(made["db"])
    c.execute("INSERT INTO projects(name) VALUES ('C')")                 # bản sao ghi được, gốc không đổi
    c.commit()
    c.close()
    assert src.read_bytes() == before


def test_app_env_is_mock_only_and_drops_api_keys(tmp_path, monkeypatch):
    for k in ("SYNC_API_KEY", "MESHY_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_OAUTH_TOKEN",
              "DASHBOARD_OWNER_PASSCODE", "SOME_SECRET"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setenv("DASHBOARD_SYNC_BACKGROUND", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CLIPAI_TOKEN", "x")
    monkeypatch.setenv("IMAGE_PROVIDER", "deepix")
    env = L.app_env("db", "data", str(tmp_path), 0.1, "probe")
    assert all(env[k] == "mock" for k in ("IMAGE_PROVIDER", "VIDEO_PROVIDER", "AUDIO_PROVIDER", "LLM_PROVIDER", "SUBJECT_PROVIDER"))
    assert "ANTHROPIC_API_KEY" not in env and "CLIPAI_TOKEN" not in env
    assert env["PYTHONPATH"].split(os.pathsep)[0] == "probe" and env["FEATURE_BASELINE"] == "0"
    assert not [k for k in env if k.endswith(("_KEY", "_TOKEN", "_SECRET", "PASSCODE")) or k.startswith(("ANTHROPIC_", "CLAUDE_CODE_"))]
    assert "DASHBOARD_SYNC_BACKGROUND" not in env                         # đồng bộ đầu phiên chạy nền như sản xuất
    db = str(tmp_path / "data" / "manifest.sqlite")
    env = L.app_env(db, "data", str(tmp_path), 0.1, "probe")
    assert env["ASSET_DIR"].startswith(str(tmp_path)) and env["SOUND_MODEL_DIR"].startswith(str(tmp_path))
    assert env["FF_SITE_AUTO"] == "0" and env["PLATES3D_LOCK"].startswith(str(tmp_path))
    assert env["BLENDER_PATH"].startswith(str(tmp_path)) and not os.path.exists(env["BLENDER_PATH"])


def test_probe_counts_sqlite_lock_waits_and_threads(tmp_path):
    probe = tmp_path / "probe"
    L.write_probe(str(probe))
    out = tmp_path / "probe.json"
    db = tmp_path / "x.sqlite"
    code = f"""
import sqlite3, threading, time
a = sqlite3.connect({str(db)!r}, timeout=5, check_same_thread=False); a.execute("CREATE TABLE t(x)"); a.commit()
a.execute("BEGIN IMMEDIATE"); a.execute("INSERT INTO t VALUES (1)")
def free():
    time.sleep(0.3); a.commit()
threading.Thread(target=free).start()
b = sqlite3.connect({str(db)!r}, timeout=5)
b.execute("INSERT INTO t VALUES (2)"); b.commit()
b.execute("SELECT * FROM t").fetchall()
time.sleep(1.2)
"""
    env = dict(os.environ, LOAD_PROBE_OUT=str(out), PYTHONPATH=str(probe))
    subprocess.run([sys.executable, "-c", code], env=env, check=True, timeout=60)
    snap = json.loads(out.read_text(encoding="utf-8"))
    assert snap["connects"] == 2 and snap["writes"] >= 4 and snap["reads"] >= 1
    assert snap["waits"] >= 1 and snap["wait_max"] >= 0.2                # b chờ a nhả khóa ghi ~0.3 s
    assert snap["thread_names"].get("load-probe-dump") == 1


def test_probe_hides_its_output_from_child_processes_and_chains_the_original_sitecustomize(tmp_path):
    probe = tmp_path / "probe"
    L.write_probe(str(probe))
    other = tmp_path / "other"
    other.mkdir()
    (other / "sitecustomize.py").write_text("import builtins; builtins.__orig_site__ = True\n", encoding="utf-8")
    env = dict(os.environ, LOAD_PROBE_OUT=str(tmp_path / "p.json"), PYTHONPATH=os.pathsep.join([str(probe), str(other)]))
    r = subprocess.run([sys.executable, "-c", "import os, builtins; print(os.environ.get('LOAD_PROBE_OUT'), "
                        "getattr(builtins, '__orig_site__', False))"], env=env, capture_output=True, text=True, check=True, timeout=60)
    assert r.stdout.split() == ["None", "True"]


def test_probe_chains_once_even_with_two_probe_folders(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    L.write_probe(str(a))
    L.write_probe(str(b))
    env = dict(os.environ, LOAD_PROBE_OUT=str(tmp_path / "p.json"), PYTHONPATH=os.pathsep.join([str(a), str(b)]))
    r = subprocess.run([sys.executable, "-c", "import sys; print(getattr(sys, '_load_probe_chained', False))"], env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == "True" and "Recursion" not in r.stderr


def test_probe_keeps_the_signature_of_slowed_mock_methods(tmp_path):
    probe = tmp_path / "probe"
    L.write_probe(str(probe))
    code = ("import sys, time, inspect; sys.path.insert(0, %r); import core.providers as P; time.sleep(1.0); "
            "print(P.MockImageProvider.submit.__name__, list(inspect.signature(P.MockImageProvider.submit).parameters)[:2])") % ROOT
    env = dict(os.environ, LOAD_PROBE_OUT=str(tmp_path / "p.json"), LOAD_MOCK_LATENCY="0.01", PYTHONPATH=str(probe))
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True, timeout=60, cwd=ROOT)
    assert r.stdout.split()[0] == "submit" and "'prompt'" in r.stdout


def test_refuses_production_and_busy_ports(tmp_path):
    import socket
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        sk.listen()
        busy = sk.getsockname()[1]
        assert not L.port_free(busy)
        args = type("A", (), {"port": busy, "latency": 0, "keep": False, "chrome": None, "out": None})()
        tpl = L.build_data(str(tmp_path / "d"), projects=1, shots=20)
        with pytest.raises(RuntimeError, match="bận"):
            L.run_level(1, tpl, args, print)
        args.port = 8501
        with pytest.raises(RuntimeError, match="Dashboard thật"):
            L.run_level(1, tpl, args, print)


def test_port_free_trusts_a_listener_on_any_address(monkeypatch):
    monkeypatch.setattr(L, "_listening", lambda port: True)                # vd. Dashboard chỉ nghe IPv6 / máy Windows: psutil quyết
    assert not L.port_free(45678)


class FakePage:
    """Trang giả cho settle(): `states` = trạng thái mỗi lần hỏi; bộ đếm lượt chạy lại tăng khi chuyển sang bận."""

    def __init__(self, states, origin=1.0):
        self.states, self.k, self.count, self.prev, self.origin = list(states), 0, 0, "notRunning", origin

    async def evaluate(self, js):
        if "__ltRuns" in js:
            return [self.origin, self.count]
        st = self.states[min(self.k, len(self.states) - 1)]
        self.k += 1
        if st in L.BUSY_STATES and self.prev not in L.BUSY_STATES:
            self.count += 1
        self.prev = st
        return st in L.BUSY_STATES


def test_settle_waits_for_the_rerun_requested_after_a_click():
    import asyncio
    # server tải nặng: sau cú bấm vẫn yên vài nhịp rồi mới 'rerunRequested' → 'running' → yên. Trước: trả ngay ở nhịp yên đầu
    pg = FakePage(["notRunning"] * 5 + ["rerunRequested"] * 3 + ["running"] * 4 + ["notRunning"] * 5)
    assert asyncio.run(L.settle(pg, 0)) is True
    assert pg.k >= 15


def test_settle_ignores_a_fragment_rerun_until_the_step_is_really_done(monkeypatch):
    import asyncio
    # rà lần 2: ô hỏi job (st.fragment run_every) chạy lại ngay sau cú bấm → bộ đếm tăng nhưng màn đích chưa vẽ; chỉ xong khi điều kiện hậu đúng
    pg = FakePage(["running"] * 2 + ["notRunning"] * 6 + ["running"] * 3 + ["notRunning"] * 5)
    state = {"asked": 0}

    async def done():
        state["asked"] += 1
        return pg.k >= 12                                                 # màn đích chỉ có sau lượt chạy lại thứ hai
    assert asyncio.run(L.settle(pg, (1.0, 0), done)) is True
    assert pg.k >= 14 and state["asked"] >= 2


def test_settle_treats_a_reloaded_page_as_a_fresh_counter():
    import asyncio
    pg = FakePage(["running"] * 2 + ["notRunning"] * 4, origin=2.0)      # trang tải lại: mốc đổi, bộ đếm mới = 1 < before cũ (5)
    assert asyncio.run(L.settle(pg, (1.0, 5))) is True


def test_settle_reports_a_click_without_rerun(monkeypatch):
    import asyncio
    monkeypatch.setattr(L, "NO_RERUN_S", 0.3)
    assert asyncio.run(L.settle(FakePage(["notRunning"]), 0)) is False


def test_errors_count_as_slow_and_fail_the_run():
    lv = _level(5, 0.5)
    for s_ in lv["sessions"]:
        s_["steps"]["home"] = None
        s_["errors"] = {"home": "TimeoutError"}
    s = L.summarize([lv])
    assert s["first_slow"] == {"n": 5, "steps": ["home"]} and s["errors"] == 5
    assert s["bottleneck"]["step"] == "home" and s["bottleneck"]["errors"] == 5
    assert "Tổng bước lỗi: 5" in L.markdown(s, {"latency": 0})


def test_find_chrome_picks_the_highest_version_numerically(tmp_path, monkeypatch):
    for v in ("999", "1194"):
        d = tmp_path / f"chromium-{v}" / "chrome-linux"
        d.mkdir(parents=True)
        (d / "chrome").write_text("")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    monkeypatch.setattr(L.os.path, "isdir", lambda p: str(p) == str(tmp_path))
    assert "chromium-1194" in L.find_chrome(None)


def test_probe_is_inert_without_the_output_variable(tmp_path):
    probe = tmp_path / "probe"
    L.write_probe(str(probe))
    env = {k: v for k, v in os.environ.items() if k != "LOAD_PROBE_OUT"}
    env["PYTHONPATH"] = str(probe)
    r = subprocess.run([sys.executable, "-c", "import sqlite3; print(type(sqlite3.connect(':memory:')).__name__)"], env=env,
                       capture_output=True, text=True, check=True, timeout=60)
    assert r.stdout.strip() == "Connection"


def _level(n, home, storyboard=0.4, cpu=50, waits=0, wait_max=0.0, err=False):
    sessions = [{"steps": {"home": home + k * 0.1, "open": 1.0, "storyboard": storyboard, "approve": 1.0, "video": 0.8, "gen": 1.2},
                 "errors": ({"approve": "LookupError"} if err and k == 0 else {})} for k in range(n)]
    return {"n": n, "sessions": sessions, "server": {"cpu_peak": cpu, "sys_cpu_peak": 50, "rss_peak_mb": 120, "threads_base": 7, "threads_peak": 7 + 3 * n},
            "probe": {"writes": 10 * n, "waits": waits, "wait_s": wait_max * waits, "wait_max": wait_max, "locked_errors": 0,
                      "thread_names": {"ScriptRunner": n}}}


def test_summary_finds_first_slow_level_and_bottleneck():
    s = L.summarize([_level(1, 0.5), _level(2, 1.0), _level(5, 2.5, err=True), _level(10, 4.0, cpu=99)])
    assert [r["n"] for r in s["rows"]] == [1, 2, 5, 10]
    assert s["first_slow"] == {"n": 5, "steps": ["home"]}
    assert s["rows"][2]["steps"]["approve"]["errors"] == 1
    assert s["rows"][3]["threads_per_session"] == 3.0
    assert s["bottleneck"]["step"] == "home" and s["bottleneck"]["n"] == 10 and "CPU" in s["bottleneck"]["note"]
    md = L.markdown(s, {"when": "x", "host": "h", "python": "3", "data": "giả", "latency": 0.2})
    assert "| Trang chủ |" in md and "🐢" in md and "N=5" in md and "⚠1 lỗi" in md


def test_summary_blames_sqlite_when_lock_wait_dominates():
    s = L.summarize([_level(10, 1.0, storyboard=3.0, waits=30, wait_max=2.0)])
    assert s["bottleneck"]["step"] == "storyboard" and "SQLite" in s["bottleneck"]["note"]


def test_percentiles():
    assert L.pct([], 0.5) is None
    assert L.pct([None, 2.0], 0.95) == 2.0
    assert L.pct([1, 2, 3, 4], 0.5) == 2.5


@pytest.mark.slow
def test_real_run_one_session(tmp_path):
    pytest.importorskip("playwright")
    pytest.importorskip("psutil")
    if L.find_chrome(None) is None:
        pytest.skip("không có Chromium")
    rc = L.main(["--levels", "1", "--projects", "2", "--shots", "20", "--port", "8549", "--latency", "0", "--out", str(tmp_path)])
    assert rc == 0
    got = json.loads((tmp_path / "load_ui.json").read_text(encoding="utf-8"))
    sess = got["levels"][0]["sessions"][0]
    assert not sess["errors"], sess["errors"]
    assert all(sess["steps"][s] is not None or s in sess["skipped"] for s in L.STEPS)
    assert not sess["no_rerun"], sess["no_rerun"]                       # mỗi bước đo tới lượt vẽ lại thật của nó
    assert got["levels"][0]["probe"].get("writes")                     # đầu dò chạy trong tiến trình Streamlit


def test_summary_flags_a_saturated_measuring_machine():
    lv = _level(10, 4.0, cpu=99)
    lv["server"]["sys_cpu_peak"] = 99.0
    s = L.summarize([lv])
    assert "CẢ MÁY" in s["bottleneck"]["note"]
    assert "| 99.0 |" in L.markdown(s, {"latency": 0})


def test_a_screen_already_shown_is_reported_not_measured():
    lv = _level(2, 0.5)
    for s_ in lv["sessions"]:
        s_["steps"]["storyboard"] = None
        s_["skipped"] = ["storyboard"]
    s = L.summarize([lv])
    assert s["rows"][0]["steps"]["storyboard"]["skipped"] == 2 and not s["first_slow"] and s["errors"] == 0
    assert "đã hiện sẵn" in L.markdown(s, {"latency": 0})


def test_relocate_moves_every_real_path_into_the_copy(tmp_path):
    # C-FIX5 (rà VỪA): bản sao CSDL thật còn đường tới tệp THẬT (tuyệt đối / tương đối 'data/…', cả trong JSON) → đổi sang bản sao
    real = tmp_path / "real" / "data"
    db = tmp_path / "copy.sqlite"
    win = str(real).replace("/", "\\")
    c = sqlite3.connect(db)
    c.executescript("CREATE TABLE jobs(id INTEGER PRIMARY KEY, result_path TEXT, n INTEGER); CREATE TABLE scenes(id INTEGER PRIMARY KEY, data TEXT)")
    c.execute("INSERT INTO jobs(result_path, n) VALUES (?, 1), (?, 2), (?, 3), (?, 4)",
              (str(real / "projects" / "1" / "images" / "a.png"), "data/projects/1/videos/b.mp4", win + "\\projects\\1\\c.png",
               "/khac/data/x.png"))
    c.execute("INSERT INTO scenes(data) VALUES (?)", (json.dumps({"sent_package": str(real / "projects" / "1" / "sent"), "ref": win + "\\assets\\k.png",
                                                                "rel": "data/assets/z.png", "word": "metadata/khong"}),))
    c.commit()
    c.close()
    new = tmp_path / "work" / "data"
    changed = L.relocate(str(db), [str(real)], str(new))
    assert changed == {"jobs.result_path": 3, "scenes.data": 1}
    c = sqlite3.connect(db)
    paths = [r[0] for r in c.execute("SELECT result_path FROM jobs ORDER BY id")]
    data = json.loads(c.execute("SELECT data FROM scenes").fetchone()[0])
    c.close()
    root = str(new).replace("\\", "/")
    assert paths[0] == f"{root}/projects/1/images/a.png" and paths[1] == f"{root}/projects/1/videos/b.mp4"
    assert paths[2].startswith(root) and paths[3] == "/khac/data/x.png"                     # đường không thuộc data thật giữ nguyên
    assert data["sent_package"].startswith(root) and data["ref"].startswith(root) and data["rel"] == f"{root}/assets/z.png"
    assert data["word"] == "metadata/khong"
    blob = json.dumps([paths, data])
    assert str(real) not in blob and win not in blob


def test_copy_db_names_the_real_homes(tmp_path):
    src = tmp_path / "data" / "manifest.sqlite"
    src.parent.mkdir()
    c = sqlite3.connect(src)
    c.execute("CREATE TABLE projects(id INTEGER PRIMARY KEY, name TEXT)")
    c.commit()
    c.close()
    made = L.copy_db(str(src), str(tmp_path / "out"), str(tmp_path / "data" / "projects"))
    homes = dict(made["real_homes"])
    assert homes[os.path.abspath(str(tmp_path / "data"))] == ""
    assert homes[os.path.abspath(str(tmp_path / "data" / "projects"))] == "projects"
    assert homes[os.path.join(L.ROOT, "data")] == ""                                          # data/ của repo luôn tính (rà VỪA-4)


def test_relocate_on_the_real_schema_fires_no_trigger_and_survives_append_only_tables(tmp_path):
    # rà C-FIX5 VỪA-1 / VỪA-2: UPDATE scenes.data kích trg_change_scene (thay đổi chờ rà giả), ticket_events chặn UPDATE (ABORT)
    from core.db import connect
    real = tmp_path / "real" / "data"
    db = str(tmp_path / "copy.sqlite")
    from core.pipeline import Pipeline
    pp = Pipeline(connect(db))
    c = pp.conn
    pid = pp.create_project("p")
    sid = pp.create_scene(pid, 1, "s")
    c.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"ref": str(real / "projects" / "1" / "a.png")}), sid))
    c.commit()
    c.execute("UPDATE change_events SET state='skipped'")
    tick = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_events'")]
    c.commit()
    triggers = sorted(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='trigger'"))
    before = c.execute("SELECT COUNT(*) FROM change_events").fetchone()[0]
    c.close()
    out = L.relocate(db, [(str(real), "")], str(tmp_path / "work" / "data"))
    assert out.get("scenes.data") == 1 and not out.get("_leaks")
    c = sqlite3.connect(db)
    assert c.execute("SELECT COUNT(*) FROM change_events").fetchone()[0] == before                 # không sinh thay đổi chờ rà
    assert sorted(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='trigger'")) == triggers   # trigger tạo lại đủ
    c.close()
    assert tick                                                                               # bảng chỉ-thêm có thật trong schema


def test_relocate_respects_path_boundaries_roots_and_prose(tmp_path):
    real = str(tmp_path / "x" / "data")
    db = str(tmp_path / "c.sqlite")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE t(v TEXT, n INTEGER)")
    for v in (real + "2/a.png", real + "base/b", "xem data/ trong câu", real + "/ok.png", real.upper() + "/hoa.png"):
        c.execute("INSERT INTO t(v) VALUES (?)", (v,))
    c.execute("INSERT INTO t(n) VALUES ('" + real + "/so.png')")                              # chữ trong cột INTEGER
    c.commit()
    c.close()
    L.relocate(db, [(real, ""), ("/", ""), ("", "")], str(tmp_path / "w"))                  # gốc / và rỗng bị bỏ
    c = sqlite3.connect(db)
    vals = [r[0] for r in c.execute("SELECT v FROM t WHERE v IS NOT NULL ORDER BY rowid")]
    num = c.execute("SELECT n FROM t WHERE n IS NOT NULL").fetchone()[0]
    c.close()
    w = str(tmp_path / "w").replace("\\", "/")
    assert vals[0] == real + "2/a.png" and vals[1] == real + "base/b" and vals[2] == "xem data/ trong câu"
    assert vals[3] == w + "/ok.png"
    assert (vals[4] == w + "/hoa.png") == (os.name == "nt")                                  # Windows: không phân biệt hoa / thường
    assert num == w + "/so.png"


def test_relocate_maps_the_projects_folder_onto_the_copy_projects(tmp_path):
    db = str(tmp_path / "c.sqlite")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE jobs(result_path TEXT)")
    c.execute("INSERT INTO jobs VALUES (?)", (str(tmp_path / "proj" / "1" / "images" / "a.png"),))
    c.commit()
    c.close()
    L.relocate(db, [(str(tmp_path), ""), (str(tmp_path / "proj"), "projects")], str(tmp_path / "w" / "data"))
    c = sqlite3.connect(db)
    got = c.execute("SELECT result_path FROM jobs").fetchone()[0]
    c.close()
    assert got == str(tmp_path / "w" / "data" / "projects" / "1" / "images" / "a.png").replace("\\", "/")


@pytest.mark.slow
def test_a_measured_run_on_a_real_copy_never_touches_the_real_files(tmp_path):
    # C-FIX5: sau một lượt đo trên bản sao (--db / --data), danh sách + mtime tệp của thư mục dữ liệu thật không đổi
    pytest.importorskip("playwright")
    pytest.importorskip("psutil")
    if L.find_chrome(None) is None:
        pytest.skip("không có Chromium")
    made = L.build_data(str(tmp_path / "real"), projects=1, shots=20)
    c = sqlite3.connect(made["db"])
    for jid, sid in c.execute("SELECT j.id, j.scene_id FROM jobs j WHERE j.type='image_gen'").fetchall():
        pid = c.execute("SELECT project_id FROM scenes WHERE id=?", (sid,)).fetchone()[0]
        p = os.path.join(made["data"], str(pid), "images", f"job_{jid}.png")
        if os.path.exists(p):
            c.execute("UPDATE jobs SET result_path=? WHERE id=?", (os.path.abspath(p), jid))      # đường TUYỆT ĐỐI tới tệp thật
    c.commit()
    c.close()

    def snap():
        return sorted((os.path.relpath(os.path.join(r, f), made["data"]), os.stat(os.path.join(r, f)).st_mtime_ns)
                      for r, _d, fs in os.walk(made["data"]) for f in fs)
    before = snap()
    import glob
    import tempfile
    old = set(glob.glob(os.path.join(tempfile.gettempdir(), "load_ui_n1_*")))
    rc = L.main(["--levels", "1", "--db", made["db"], "--data", made["data"], "--port", "8548", "--latency", "0", "--out", str(tmp_path / "o"),
                 "--keep"])
    assert rc in (0, 1)
    assert snap() == before                                                                   # tệp thật không đổi
    work = sorted(set(glob.glob(os.path.join(tempfile.gettempdir(), "load_ui_n1_*"))) - old)
    assert len(work) == 1
    try:
        c = sqlite3.connect(os.path.join(work[0], "data", "manifest.sqlite"))
        blob = json.dumps([list(map(str, r)) for r in c.execute("SELECT result_path FROM jobs")] +
                          [r[0] for r in c.execute("SELECT data FROM scenes")])
        c.close()
        assert os.path.abspath(made["data"]) not in blob and work[0] in blob                  # bản sao chỉ trỏ vào thư mục của nó
    finally:
        import shutil
        shutil.rmtree(work[0], ignore_errors=True)
