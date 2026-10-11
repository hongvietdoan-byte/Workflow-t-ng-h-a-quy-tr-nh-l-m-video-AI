"""Rà tích hợp 11/10 (dashboard/serve.py): vòng nền là MỘT trên mỗi CSDL cả khi có hai tiến trình Dashboard (tiến trình cũ còn sống,
cấu hình launch.json khác) — hai vòng cùng gửi một job 'queued' = trả tiền hai lần. Lỗi khởi động vòng nền không được chặn máy chủ."""
import json
import os
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLD = ("import sys,time; sys.path.insert(0, sys.argv[1]); from core import bg_poll;"
        "print(bg_poll._acquire_process_lock(sys.argv[2]), flush=True); time.sleep(float(sys.argv[3]))")


def test_second_process_on_same_db_does_not_start_a_second_round(tmp_path, monkeypatch):
    from core import bg_poll
    db = str(tmp_path / "m.sqlite")
    holder = subprocess.Popen([sys.executable, "-c", HOLD, ROOT, db, "30"], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "True"       # tiến trình kia giữ vòng nền của CSDL này
        monkeypatch.setenv("BG_POLL", "1")
        monkeypatch.setattr(bg_poll, "_started", False)
        monkeypatch.setattr(bg_poll, "running", lambda: False)
        started = []
        monkeypatch.setattr(bg_poll.threading, "Thread", lambda *a, **k: started.append(k) or threading.Thread(target=lambda: None))
        assert bg_poll.start(db, str(tmp_path)) is False
        assert started == []
    finally:
        holder.kill()
        holder.wait()


def test_lock_is_free_again_when_the_holder_dies(tmp_path):
    from core import bg_poll
    db = str(tmp_path / "m2.sqlite")
    out = subprocess.run([sys.executable, "-c", HOLD, ROOT, db, "0"], capture_output=True, text=True)
    assert out.stdout.strip() == "True"
    assert bg_poll._acquire_process_lock(db) is True             # tiến trình chết = khóa tự nhả (không có khóa mồ côi)
    assert bg_poll._acquire_process_lock(db) is True             # cùng tiến trình gọi lại: vẫn là của mình


def test_serve_still_starts_streamlit_when_the_background_round_fails(monkeypatch):
    from core import bg_poll
    from dashboard import serve

    def boom(db, data):
        raise OSError("ổ đầy")
    monkeypatch.setattr(bg_poll, "start", boom)
    monkeypatch.setattr(sys, "argv", list(sys.argv))
    ran = []
    assert serve.main(["--server.port", "8598"], run=lambda: ran.append(1) or 0) == 0
    assert ran == [1]


def test_launch_json_dashboards_on_the_real_db_use_serve():
    cfg = json.load(open(os.path.join(ROOT, ".claude", "launch.json"), encoding="utf-8"))
    for c in cfg["configurations"]:
        cmd = " ".join(c.get("runtimeArgs", []))
        if "dashboard/app.py" in cmd or "dashboard.serve" in cmd:
            if "PIPELINE_DB=" in cmd:
                continue                                         # bản demo dùng CSDL riêng
            assert "py -m dashboard.serve" in cmd and "streamlit run dashboard/app.py" not in cmd, c["name"]
