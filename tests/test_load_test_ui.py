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
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CLIPAI_TOKEN", "x")
    monkeypatch.setenv("IMAGE_PROVIDER", "deepix")
    env = L.app_env("db", "data", str(tmp_path), 0.1, "probe")
    assert all(env[k] == "mock" for k in ("IMAGE_PROVIDER", "VIDEO_PROVIDER", "AUDIO_PROVIDER", "LLM_PROVIDER", "SUBJECT_PROVIDER"))
    assert "ANTHROPIC_API_KEY" not in env and "CLIPAI_TOKEN" not in env
    assert env["PYTHONPATH"].split(os.pathsep)[0] == "probe" and env["FEATURE_BASELINE"] == "0"


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
    s = L.summarize([_level(10, 1.0, storyboard=3.0, waits=5, wait_max=2.0)])
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
    assert all(sess["steps"][s] is not None for s in L.STEPS)
    assert got["levels"][0]["probe"].get("writes")                     # đầu dò chạy trong tiến trình Streamlit


def test_summary_flags_a_saturated_measuring_machine():
    lv = _level(10, 4.0, cpu=99)
    lv["server"]["sys_cpu_peak"] = 99.0
    s = L.summarize([lv])
    assert "CẢ MÁY" in s["bottleneck"]["note"]
    assert "| 99.0 |" in L.markdown(s, {"latency": 0})
