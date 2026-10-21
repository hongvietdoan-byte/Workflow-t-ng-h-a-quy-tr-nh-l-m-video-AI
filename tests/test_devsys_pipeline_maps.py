"""C-DEVSYS-MAPS (cloud-C 21/10): 3 sơ đồ dây chuyền SỐNG trên AI Dev System (8502) — dữ liệu devsys/pipeline_maps.json, màu TÍNH
(bằng chứng tệp + chữ, cờ hiệu lực, việc kế hoạch, sổ lỗi), lịch sử thay đổi devsys/data/pipeline_maps_history.jsonl, tô theo DỰ ÁN từ
sự kiện ui_step / cli_step (core/ui_step, cờ ui_step_log TẮT = Dashboard không ghi gì). CSDL thật chỉ đọc mode=ro."""
import ast
import hashlib
import json
import os
import sqlite3
from unittest import mock

import pytest

from devsys import pipeline_maps as PM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _on(*names):
    return lambda n: "on" if n in names else "off"


@pytest.fixture
def mini(tmp_path):
    """Repo nhỏ: một tệp bằng chứng + một ô Dashboard, một nút trường, một khâu."""
    (tmp_path / "dashboard").mkdir()
    (tmp_path / "dashboard" / "x.py").write_text("def render():\n    st.button('Gói sẽ gửi')\n", encoding="utf-8")
    doc = {"dashboard": {"title": "t", "screens": [{"id": "storyboard", "title": "② STORYBOARD", "src": "", "color": "#3ca9ff"}],
                         "cells": [{"id": "c1", "screen": "storyboard", "label": "Xem gói", "desc": [], "moc": "R", "khau": ["L8"],
                                    "plan": ["M4.7"], "flags": ["send_preview_panel"],
                                    "evidence": [{"glob": "dashboard/*.py", "text": "Gói sẽ gửi"}], "ui": ["gen_images"],
                                    "cli": ["replay_payload"]},
                                   {"id": "c2", "screen": "storyboard", "label": "Gen ảnh", "desc": [], "moc": "G", "khau": ["L9"],
                                    "plan": [], "flags": [], "evidence": [{"glob": "dashboard/*.py", "text": "def render"}], "ui": ["approve"]}],
                         "outside": [{"id": "o1", "tool": "stage_auto", "screen": "storyboard", "label": "tools/stage_auto.py"}]},
           "khau": {"title": "k", "rows": []},
           "truong": {"title": "f", "columns": [{"id": "goi", "title": "GÓI"}],
                      "nodes": [{"id": "n1", "col": "goi", "label": "GÓI", "desc": [], "moc": "G", "khau": ["L8"], "plan": [], "flags": [],
                                 "evidence": [{"glob": "dashboard/*.py", "text": "def render"}]}], "edges": []}}
    return tmp_path, doc


def _model(root, doc, state, plan=None, history=None):
    return PM.build_model(doc, root=str(root), state=state, plan_status=plan if plan is not None else {"M4.7": "✅"},
                          stage_rows=[], plan_khau={}, open_errors={})


def _cell(m, cid):
    return next(c for c in m["dashboard"]["cells"] if c["id"] == cid)


def test_evidence_and_flag_on_and_plan_done_is_green(mini):
    root, doc = mini
    c = _cell(_model(root, doc, _on("send_preview_panel")), "c1")
    assert c["color"] == "xanh" and c["moc"] == "do"


def test_flag_off_is_yellow_with_the_reason(mini):
    root, doc = mini
    c = _cell(_model(root, doc, _on()), "c1")
    assert c["color"] == "vang" and any("send_preview_panel" in w for w in c["why"])


def test_missing_evidence_is_red(mini):
    root, doc = mini
    (root / "dashboard" / "x.py").write_text("def render():\n    pass\n", encoding="utf-8")
    c = _cell(_model(root, doc, _on("send_preview_panel")), "c1")
    assert c["color"] == "do" and any("Gói sẽ gửi" in w for w in c["why"])


def test_plan_in_progress_is_purple_and_not_done_is_yellow(mini):
    root, doc = mini
    assert _cell(_model(root, doc, _on("send_preview_panel"), {"M4.7": "🔄"}), "c1")["color"] == "tim"
    assert _cell(_model(root, doc, _on("send_preview_panel"), {"M4.7": "⬜"}), "c1")["color"] == "vang"


def test_history_writes_one_line_when_a_plan_task_turns_done(mini, tmp_path):
    root, doc = mini
    hist = tmp_path / "h.jsonl"
    m1 = _model(root, doc, _on("send_preview_panel"), {"M4.7": "⬜"})
    assert PM.record_history(m1, str(hist), now="2026-10-21T10:00:00") is True
    assert PM.record_history(m1, str(hist), now="2026-10-21T10:05:00") is False           # không đổi gì → không ghi
    m2 = _model(root, doc, _on("send_preview_panel"), {"M4.7": "✅"})
    assert PM.record_history(m2, str(hist), now="2026-10-21T11:00:00") is True
    lines = hist.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    ch = PM.changes(str(hist))
    assert [(c["id"], c["old"], c["new"]) for c in ch] == [("c1", "vang", "xanh")]
    assert any("M4.7" in w for w in ch[0]["why"])


def test_changes_against_the_17_10_mark(mini):
    root, doc = mini
    m = _model(root, doc, _on("send_preview_panel"))
    vs = {c["id"]: (c["old"], c["new"]) for c in PM.vs_moc(m)}
    assert vs["c1"] == ("do", "xanh") and "c2" not in vs


def test_moc_rebuilds_every_box_of_the_three_old_svgs():
    doc = PM.load()
    tree = ast.parse(open(os.path.join(ROOT, "docs", "so_do", "gen_dashboard.py"), encoding="utf-8").read())
    screens = next(n.value for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SCREENS")
    chips = sum(len(s.elts[3].elts) for s in screens.elts)
    outs = next(n.value for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "outs")
    assert len(doc["dashboard"]["cells"]) == chips == 28 and len(doc["dashboard"]["outside"]) == len(outs.elts) == 4
    tree = ast.parse(open(os.path.join(ROOT, "docs", "so_do", "gen_hien_trang_khau.py"), encoding="utf-8").read())
    rows = next(n.value for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "ROWS")
    assert [r["id"] for r in doc["khau"]["rows"]] == [r.elts[0].value for r in rows.elts]
    svg = open(os.path.join(ROOT, "docs", "so_do", "SO_DO_TRUONG_CAU_TRUC_2026-10.svg"), encoding="utf-8").read()
    for n in doc["truong"]["nodes"]:                                         # mỗi nút trường có nhãn trong SVG mốc
        assert n["label"].replace("&", "&amp;") in svg, n["label"]
    for c in doc["dashboard"]["cells"]:
        assert c["label"] in open(os.path.join(ROOT, "docs", "so_do", "gen_dashboard.py"), encoding="utf-8").read(), c["label"]


def test_real_map_builds_and_everything_named_exists():
    m = PM.build_model()
    assert len(m["dashboard"]["cells"]) == 28 and len(m["khau"]["rows"]) == 16 and m["truong"]["nodes"]
    from core import features
    for c in PM.load()["dashboard"]["cells"] + PM.load()["truong"]["nodes"]:
        for f in c.get("flags") or []:
            assert f in features.FEATURES or f in m["unknown_flags"], f
    assert all(c["color"] in PM.COLORS for c in m["dashboard"]["cells"] + m["khau"]["rows"] + m["truong"]["nodes"])


# ---- tô theo dự án ---------------------------------------------------------------------------------------------------------------
def _db(tmp_path):
    from core.db import connect
    path = str(tmp_path / "m.sqlite")
    conn = connect(path)
    return path, conn


def test_project_overlay_hold_is_yellow_error_is_red_untouched_is_grey(mini, tmp_path):
    from core import ui_step
    root, doc = mini
    path, conn = _db(tmp_path)
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        ui_step.record(conn, 31, "storyboard", "gen_images", "hold", "cổng trước gen giữ 2 shot")
        ui_step.record(conn, 31, "storyboard", "gen_images", "hold", "cổng trước gen giữ 2 shot")
        ui_step.record(conn, 33, "storyboard", "gen_images", "error", "gửi lỗi", error_code="P31-G6")
        ui_step.cli(conn, "stage_auto", 31, "dàn cảnh cảnh 4")
    conn.close()
    m = _model(root, doc, _on("send_preview_panel"))
    ov = PM.overlay(m, PM.project_events(path, 31))
    c1 = ov["cells"]["c1"]
    assert c1["color"] == "vang" and c1["count"] == 2 and "giữ 2 shot" in c1["last"]
    assert ov["cells"]["c2"]["color"] == "xam"
    virt = ov["virtual"]
    assert virt and virt[0]["screen"] == "storyboard" and virt[0]["tool"] == "stage_auto" and virt[0]["count"] == 1
    assert "THIẾU NÚT" in PM.svg_dashboard(m, ov) and 'stroke-dasharray' in PM.svg_dashboard(m, ov)
    ov33 = PM.overlay(m, PM.project_events(path, 33))
    assert ov33["cells"]["c1"]["color"] == "do" and "P31-G6" in ov33["cells"]["c1"]["last"]
    assert {a["id"] for a in ov33["alerts"]} == {"c1"}


def test_project_events_open_the_db_read_only(tmp_path):
    missing = str(tmp_path / "khong_co.sqlite")
    assert PM.project_events(missing, 1) == []
    assert not os.path.exists(missing)                                       # mode=ro: không tạo tệp
    path, conn = _db(tmp_path)
    conn.close()
    with mock.patch("sqlite3.connect", wraps=sqlite3.connect) as c:
        PM.project_events(path, 1)
    assert "mode=ro" in c.call_args[0][0]


def test_ui_step_flag_off_writes_nothing(tmp_path):
    from core import ui_step
    path, conn = _db(tmp_path)
    conn.commit()
    before = hashlib.sha256(open(path, "rb").read()).hexdigest()
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": ""}):
        ui_step.record(conn, 1, "storyboard", "gen_images", "hold", "x")
        ui_step.cli(conn, "stage_auto", 1, "y")
    conn.commit()
    assert hashlib.sha256(open(path, "rb").read()).hexdigest() == before
    assert conn.execute("SELECT COUNT(*) FROM diag_events").fetchone()[0] == 0


def test_ui_step_never_breaks_the_button():
    from core import ui_step
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}), mock.patch("core.diag.record", side_effect=RuntimeError("đĩa đầy")):
        ui_step.record(object(), 1, "s", "b", "ok")
        ui_step.cli(object(), "t", 1, "x")


def test_flag_registered_off_golden_and_areas():
    from core import features
    assert features.FEATURES["ui_step_log"]["verified"] is False
    golden = json.load(open(os.path.join(ROOT, "tests", "golden", "package_inputs.json"), encoding="utf-8"))
    assert all(golden[k]["flags"]["ui_step_log"] is False for k in ("image", "video"))
    areas = json.load(open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8"))["areas"]
    dev = next(a for a in areas if a["id"] == "devsys")
    assert {"devsys/pipeline_maps.py", "devsys/pipeline_maps.json"} <= set(dev["code"])
    assert "tests/test_devsys_pipeline_maps.py" in dev["tests"]


def test_dashboard_main_buttons_log_and_cli_tools_log():
    src = open(os.path.join(ROOT, "dashboard", "common.py"), encoding="utf-8").read()
    i = src.index("def log_ui(")
    assert "ui_step.record(" in src[i:i + 3000]                          # MỘT hàm chung: nhật ký thao tác → sự kiện ui_step
    for rel, action in (("dashboard/steps/step2.py", "gen_anh"), ("dashboard/steps/step4.py", "gen_video"),
                        ("dashboard/steps/step1_director.py", "chay_dao_dien"), ("dashboard/steps/step3.py", "viet_motion"),
                        ("dashboard/steps/step5.py", "ban_giao")):
        src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        assert f'C.log_ui(p, "{action}"' in src or f'C.log_step("{action}"' in src, rel
    assert 'step=("skip" if forced' in open(os.path.join(ROOT, "dashboard", "steps", "step2.py"), encoding="utf-8").read()
    keys = {k for c in PM.load()["dashboard"]["cells"] for k in c["ui"]}
    assert {"gen_anh", "gen_video", "chay_dao_dien", "viet_motion"} <= keys
    for rel, tool in (("tools/stage_auto.py", "stage_auto"), ("tools/stage_previs.py", "stage_previs"),
                      ("tools/replay_payload.py", "replay_payload")):
        src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        assert f'"{tool}"' in src and "ui_step.cli(" in src, rel


def test_log_ui_writes_the_step_on_its_own_connection(tmp_path):
    from core.db import connect
    from dashboard import common as C
    db = str(tmp_path / "m.sqlite")
    connect(db).close()
    with mock.patch.object(C, "DB", db), mock.patch.object(C, "me", return_value={"email": "a@b.c"}), \
            mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        C.log_ui(None, "gen_anh", page="storyboard", project_id=31, result=True, step="hold", step_note="2 ảnh chờ điều kiện")
    ev = PM.project_events(db, 31)
    assert [(e["kind"], e["key"], e["severity"]) for e in ev] == [("ui_step", "gen_anh", "warn")] and "2 ảnh chờ" in ev[0]["message"]


def test_export_writes_three_svgs(tmp_path):
    assert PM.main([str(tmp_path)]) == 0
    names = sorted(os.listdir(tmp_path))
    assert names == ["so_do_dashboard.svg", "so_do_hien_trang_khau.svg", "so_do_truong_cau_truc.svg"]
    assert all(open(os.path.join(tmp_path, n), encoding="utf-8").read().startswith("<svg") for n in names)


def test_devsys_page_renders_four_tabs_and_three_maps(tmp_path):
    from streamlit.testing.v1 import AppTest
    with mock.patch.object(PM, "HISTORY_FILE", str(tmp_path / "h.jsonl")), \
            mock.patch.dict(os.environ, {"PIPELINE_DB": str(tmp_path / "khong_co.sqlite")}):
        at = AppTest.from_file(os.path.join(ROOT, "devsys", "app.py"), default_timeout=120)
        at.run()
        at.radio[0].set_value("🧭 Sơ đồ dây chuyền").run()
    assert not at.exception, [e.value for e in at.exception]
    assert [t.value for t in at.title] == ["🧭 Sơ đồ dây chuyền"]
    assert len(at.tabs) == 4 and sum("<svg" in md.value for md in at.markdown) == 3
    assert (tmp_path / "h.jsonl").exists()                                    # lần mở đầu ghi ảnh chụp


# ---- rà khâu C-DEVSYS-MAPS ------------------------------------------------------------------------------------------------------
def test_observation_events_stay_out_of_diagnostics_and_error_reports(tmp_path):
    from core import diag, ui_step
    path, conn = _db(tmp_path)
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        ui_step.record(conn, 31, "storyboard", "gen_anh", "skip", "vẫn gen dù cổng chặn")
        ui_step.cli(conn, "stage_auto", 31, "dàn cảnh")
    diag.record(conn, "image", "warn", "lỗi thật", "real_warn", 31)
    assert [r["code"] for r in diag.recent(conn)] == ["real_warn"]
    assert all(r["stage"] not in diag.OBSERVE for r in diag.repeated(conn, min_count=1))
    assert not any(r["stage"] == "other" for r in diag.stage_table(conn))
    assert conn.execute("SELECT severity FROM diag_events WHERE code='ui_step:gen_anh'").fetchone()[0] == "warn"   # skip ≠ lỗi
    conn.close()
    from tools import project_error_report as per
    src = open(per.__file__, encoding="utf-8").read()
    assert "\"ui_step\", \"cli_step\"" in src


def test_latest_click_decides_the_colour(mini, tmp_path):
    root, doc = mini
    m = _model(root, doc, _on("send_preview_panel"))
    ev = [{"kind": "ui_step", "key": "gen_images", "severity": "error", "message": "lỗi", "count": 1, "at": "a", "last_at": "2026-10-20T10:00"},
          {"kind": "ui_step", "key": "gen_images", "severity": "info", "message": "ok", "count": 3, "at": "b", "last_at": "2026-10-21T10:00"}]
    c = PM.overlay(m, ev)["cells"]["c1"]
    assert c["color"] == "xanh" and c["count"] == 3 and c["bad_total"] == 1


def test_read_only_cli_modes_do_not_log_and_replay_reads_the_main_flag(tmp_path):
    src = open(os.path.join(ROOT, "tools", "stage_auto.py"), encoding="utf-8").read()
    assert "if not (a.beats or a.score or a.prompt_out or a.dry)" in src
    from tools import replay_payload as rp
    main = tmp_path / "main"
    (main / "data").mkdir(parents=True)
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        (main / "data" / "feature_settings.json").write_text(json.dumps({"flags": {"ui_step_log": False}}), encoding="utf-8")
        assert rp._main_flag_on(str(main), "ui_step_log") is False          # máy chính tắt → không ghi dù repo này bật
    (main / "data" / "feature_settings.json").write_text(json.dumps({"flags": {"ui_step_log": True}}), encoding="utf-8")
    assert rp._main_flag_on(str(main), "ui_step_log") is True


def test_flag_is_opt_in_only():
    from core import features
    assert "ui_step_log" in features.OPT_IN_ONLY                             # preset Thử nghiệm không tự bật ghi mỗi bước bấm
