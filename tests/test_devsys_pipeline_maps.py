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
            assert f in features.FEATURES or f in (c.get("pending_flags") or {}), f   # cờ chưa có = phải ghi rõ chờ nhánh nào
    assert not m["unknown_flags"], m["unknown_flags"]                                 # C-DEVSYS-MAPS-FIX VỪA 3
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
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}), mock.patch("core.diag._write", side_effect=RuntimeError("đĩa đầy")):
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
        assert f'"{tool}"' in src and ("ui_step.cli(" in src or f'ui_step.run_cli("{tool}"' in src), rel


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


def test_measured_flag_rule_resolves_relative_imports_from_its_own_repo(tmp_path):
    from devsys import collect
    core_dir = tmp_path / "core"
    core_dir.mkdir()
    (core_dir / "before_run.py").write_text("PAID_FLAGS = {'fixture_paid'}\n", encoding="utf-8")
    (core_dir / "features.py").write_text(
        "def on(name):\n    from . import before_run\n    return name not in before_run.PAID_FLAGS\n",
        encoding="utf-8")
    with mock.patch.object(os, "environ", {}):
        rule, problem = collect._features_rule(str(tmp_path), {})
        assert not problem
        assert rule("fixture_paid")[0] is False
        assert rule("fixture_free")[0] is True


def test_measured_flag_rule_refreshes_relative_dependency_after_edit(tmp_path):
    from devsys import collect
    core_dir = tmp_path / "core"
    core_dir.mkdir()
    dependency = core_dir / "before_run.py"
    dependency.write_text("PAID_FLAGS = {'fixture_paid'}\n", encoding="utf-8")
    (core_dir / "features.py").write_text(
        "def on(name):\n    from . import before_run\n    return name not in before_run.PAID_FLAGS\n",
        encoding="utf-8")
    with mock.patch.object(os, "environ", {}):
        first, _ = collect._features_rule(str(tmp_path), {})
        assert first("fixture_paid")[0] is False
        dependency.write_text("PAID_FLAGS = {}\n", encoding="utf-8")
        second, _ = collect._features_rule(str(tmp_path), {})
        assert second("fixture_paid")[0] is True


def test_measured_flag_rule_refreshes_same_size_same_mtime_dependency(tmp_path):
    from devsys import collect
    core_dir = tmp_path / "core"
    core_dir.mkdir()
    dependency = core_dir / "before_run.py"
    dependency.write_text("PAID_FLAGS = {'fixture_paid'}\n", encoding="utf-8")
    (core_dir / "features.py").write_text(
        "def on(name):\n    from . import before_run\n    return name not in before_run.PAID_FLAGS\n",
        encoding="utf-8")
    with mock.patch.object(os, "environ", {}):
        first, _ = collect._features_rule(str(tmp_path), {})
        assert first("fixture_paid")[0] is False
        original = dependency.stat()
        dependency.write_text("PAID_FLAGS = {'fixture_free'}\n", encoding="utf-8")
        os.utime(dependency, ns=(original.st_atime_ns, original.st_mtime_ns))
        second, _ = collect._features_rule(str(tmp_path), {})
        assert second("fixture_paid")[0] is True
        assert first("fixture_paid")[0] is False


def test_measured_flag_rule_overlapping_snapshots_do_not_purge_imports(tmp_path):
    import sys
    import threading
    import types
    from devsys import collect
    coordination = types.ModuleType("_devsys_fixture_coordination")
    coordination.entered = threading.Event()
    coordination.release = threading.Event()
    core_dir = tmp_path / "core"
    core_dir.mkdir()
    (core_dir / "before_run.py").write_text(
        "import threading\nimport _devsys_fixture_coordination as coordination\n"
        "if threading.current_thread().name == 'devsys-first':\n"
        "    coordination.entered.set()\n    coordination.release.wait(10)\n"
        "PAID_FLAGS = {'fixture_paid'}\n", encoding="utf-8")
    (core_dir / "features.py").write_text(
        "from . import before_run\ndef on(name):\n    return name not in before_run.PAID_FLAGS\n",
        encoding="utf-8")
    results = []
    errors = []

    def load_first():
        try:
            rule, problem = collect._features_rule(str(tmp_path), {})
            results.append(not problem and rule("fixture_paid")[0] is False)
        except Exception:
            errors.append(True)

    with mock.patch.object(os, "environ", {}), mock.patch.dict(
            sys.modules, {coordination.__name__: coordination}):
        worker = threading.Thread(target=load_first, name="devsys-first")
        worker.start()
        try:
            assert coordination.entered.wait(10)
            second, problem = collect._features_rule(str(tmp_path), {})
            assert not problem
            assert second("fixture_paid")[0] is False
        finally:
            coordination.release.set()
            worker.join(10)
        assert not worker.is_alive()
        assert not errors
        assert results == [True]


def test_devsys_page_renders_four_tabs_and_three_maps(tmp_path):
    from streamlit.testing.v1 import AppTest
    with mock.patch.object(PM, "HISTORY_FILE", str(tmp_path / "h.jsonl")), \
            mock.patch.object(os, "environ", {"PIPELINE_DB": str(tmp_path / "khong_co.sqlite"),
                                            "HOME": str(tmp_path), "USERPROFILE": str(tmp_path),
                                            "TEMP": str(tmp_path), "TMP": str(tmp_path)}):
        at = AppTest.from_file(os.path.join(ROOT, "devsys", "app.py"), default_timeout=120)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        # Trang kế hoạch có radio trả lời trong thân trang, đứng trước sidebar trong AppTest.
        navigation = next(r for r in at.sidebar.radio if r.label == "Trang")
        navigation.set_value("🧭 Sơ đồ dây chuyền").run()
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
    assert conn.execute("SELECT severity FROM diag_events WHERE code='ui_step:gen_anh'").fetchone()[0] == "error"  # C-DEVSYS-MAPS-FIX: bỏ qua cổng = ĐỎ (đề mục 6) — vẫn ngoài bảng chẩn đoán
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
    assert "if not (beats_mode or a.score or a.prompt_out or a.dry)" in src   # --beats/--beats-crew = chế độ chỉ đọc (BEATS-CLI)
    assert "beats_mode = a.beats is not None or bool(a.beats_crew)" in src
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


# ---- C-DEVSYS-MAPS-FIX (rà phiên chính 21/10) ------------------------------------------------------------------------------------
def test_skip_is_red_with_a_code_and_the_pregate_cell_turns_red(tmp_path):
    """VỪA 1 (đề mục 6): bỏ qua cổng = ĐỎ kèm mã. Bấm gen khi cổng chặn (step=skip) → ô sb.pregate của sơ đồ thật ĐỎ, có mã."""
    from dashboard import common as C
    db = str(tmp_path / "m.sqlite")
    from core.db import connect
    connect(db).close()
    with mock.patch.object(C, "DB", db), mock.patch.object(C, "me", return_value={"email": "a@b.c"}), \
            mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        C.log_ui(None, "gen_anh", page="storyboard", project_id=31, result=True, step="skip",
                 step_note="vẫn gen dù cổng chặn: nền cũ", error_code="gate_skipped")
        C.log_over_limit(None, "video", 31, {"id": 77}, True, True)
        C.log_over_limit(None, "storyboard", 31, {"id": 78}, True, False)       # dừng vì gen lại y nguyên, không phải vượt trần
    ev = PM.project_events(db, 31)
    assert [(e["key"], e["severity"]) for e in ev] == [("gen_anh", "error"), ("lam_lai_video", "error"), ("lam_lai_anh", "error")]
    assert "[gate_skipped]" in ev[0]["message"] and "[regen_over_limit]" in ev[1]["message"] and "[regen_same_input]" in ev[2]["message"]
    ov = PM.overlay(PM.build_model(), ev)
    assert ov["cells"]["sb.pregate"]["color"] == "do" and "gate_skipped" in ov["cells"]["sb.pregate"]["last"]
    assert ov["cells"]["vd.gen"]["color"] == "do" and ov["cells"]["sb.card"]["color"] == "do"     # vượt trần LÊN sơ đồ
    src = open(os.path.join(ROOT, "dashboard", "steps", "step2.py"), encoding="utf-8").read()
    assert 'error_code="gate_skipped" if _ok and forced and gates["block"]' in src
    for rel in ("dashboard/steps/step2.py", "dashboard/steps/step4.py", "dashboard/design/screens/storyboard_cards.py"):
        src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        assert src.count("p.restart_job(jid)") == src.count("C.log_over_limit(") == src.count("C.retries_exhausted(p, j)"), rel
    src = open(os.path.join(ROOT, "dashboard", "steps", "step4.py"), encoding="utf-8").read()
    assert '_why[0].startswith("không gen lại:")' in src                       # mã lấy từ lỗi THẬT của lượt, không đoán lại


def test_every_logged_button_key_is_on_the_map():
    """Rà C-DEVSYS-MAPS-FIX: bước ghi mà không ô nào có key = đỏ không lên sơ đồ."""
    import glob
    import re
    keys = {k for c in PM.load()["dashboard"]["cells"] for k in c["ui"]}
    logged = set()
    for path in glob.glob(os.path.join(ROOT, "dashboard", "**", "*.py"), recursive=True):
        src = open(path, encoding="utf-8").read()
        logged |= set(re.findall(r'C\.log_step\("(\w+)"', src))
    logged |= {"lam_lai_anh", "lam_lai_video"}                                    # log_over_limit
    assert logged <= keys, sorted(logged - keys)


def test_pending_flags_expire_when_the_branch_lands():
    from core import features
    for c in PM.load()["dashboard"]["cells"] + PM.load()["truong"]["nodes"]:
        for f, branch in (c.get("pending_flags") or {}).items():
            assert f not in features.FEATURES, f"{c['id']}: cờ {f} đã có (nhánh {branch} đã gộp) — bỏ pending_flags"
            assert f in c["flags"], c["id"]


def test_error_mid_transaction_is_logged_not_self_locked(tmp_path):
    """Rà: lệnh lỗi khi kết nối của công cụ còn giữ giao dịch ghi → rollback rồi ghi error (không chờ chính nó, không mất dòng)."""
    import time
    from core import ui_step
    path, conn = _db(tmp_path)
    conn.commit()

    def loi(argv, step):
        step.update(conn=conn, project=31, task="dàn cảnh 4")
        conn.execute("UPDATE diag_events SET count=count WHERE 0")
        conn.execute("INSERT INTO diag_events (at, last_at, stage, severity, message) VALUES ('a','a','image','info','dở dang')")
        assert conn.in_transaction
        raise RuntimeError("hỏng giữa vòng lặp")

    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        t0 = time.monotonic()
        with pytest.raises(RuntimeError):
            ui_step.run_cli("stage_auto", loi)
        assert time.monotonic() - t0 < 0.8
    ev = PM.project_events(path, 31)
    assert [(e["key"], e["severity"]) for e in ev] == [("stage_auto", "error")] and "hỏng giữa vòng lặp" in ev[0]["message"]
    assert not os.path.exists(path + ".diag_lost.log")


def test_ok_with_an_open_transaction_writes_on_the_same_connection(tmp_path):
    from core import ui_step
    path, conn = _db(tmp_path)
    conn.commit()
    conn.execute("INSERT INTO diag_events (at, last_at, stage, severity, message) VALUES ('a','a','image','info','của công cụ')")
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        ui_step.run_cli("stage_auto", lambda argv, step: step.update(conn=conn, project=31, task="x"))
    assert [e["key"] for e in PM.project_events(path, 31)] == ["stage_auto"]
    assert not os.path.exists(path + ".diag_lost.log")


def test_write_failure_never_rolls_back_the_callers_work(tmp_path):
    from core import ui_step
    path, conn = _db(tmp_path)
    conn.commit()
    with mock.patch("sqlite3.connect", side_effect=sqlite3.OperationalError("không mở được")), \
            mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        ui_step.record(conn, 31, "storyboard", "gen_anh", "ok")
    assert os.path.exists(path + ".diag_lost.log")
    conn.execute("INSERT INTO diag_events (at, last_at, stage, severity, message) VALUES ('a','a','image','info','của trang')")
    with mock.patch("sqlite3.connect", side_effect=sqlite3.OperationalError("không mở được")), \
            mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        ui_step.record(conn, 31, "storyboard", "gen_anh", "ok")                 # đang giao dịch → ghi trên chính conn (không mở kết nối)
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM diag_events WHERE message='của trang'").fetchone()[0] == 1


def test_tool_says_warn_for_a_no_op_and_nothing_for_estimate_only(tmp_path):
    from core import ui_step
    path, conn = _db(tmp_path)
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        ui_step.run_cli("stage_auto", lambda argv, step: step.update(conn=conn, project=31, task="dàn cảnh 4", result="warn",
                                                                       why="có shot đã vẽ ảnh"))
        ui_step.run_cli("stage_auto", lambda argv, step: (step.update(conn=conn, project=31, task="x"), step.clear()))
    ev = PM.project_events(path, 31)
    assert [(e["key"], e["severity"]) for e in ev] == [("stage_auto", "warn")] and "có shot đã vẽ ảnh" in ev[0]["message"]
    src = open(os.path.join(ROOT, "tools", "stage_auto.py"), encoding="utf-8").read()
    i = src.index("Chưa chạy (thêm --yes")
    assert "step.clear()" in src[i:i + 300]
    assert src.count('step.update(result="warn"') == 5 and src.count('step.update(result="error"') == 2


def test_skip_without_a_code_gets_the_gate_code():
    from core import ui_step
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}), mock.patch.object(ui_step, "_write") as w:
        ui_step.record(object(), 1, "storyboard", "gen_anh", "skip")
    stage, sev, msg = w.call_args[0][1:4]
    assert (stage, sev) == ("ui_step", "error") and "[gate_skipped]" in msg


def test_locked_database_does_not_hold_the_button(tmp_path, capsys):
    """VỪA 2: CSDL bị khóa (BEGIN IMMEDIATE ở tiến trình khác) → ui_step.cli trả < 2 s, không ném lỗi; dòng mất ghi vào <db>.diag_lost.log."""
    import time
    from core import ui_step
    path, conn = _db(tmp_path)
    conn.commit()
    holder = sqlite3.connect(path)
    holder.execute("BEGIN IMMEDIATE")
    try:
        with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
            t0 = time.monotonic()
            ui_step.cli(conn, "stage_auto", 31, "dàn cảnh 4")
            ui_step.record(conn, 31, "storyboard", "gen_anh", "ok")
            took = time.monotonic() - t0
    finally:
        holder.rollback()
        holder.close()
    assert took < 4, took                                                       # 2 lần ghi × ≤ ~1 s busy_timeout (trước: tới ~3 phút)
    lost = open(path + ".diag_lost.log", encoding="utf-8").read()
    assert "cli_step:stage_auto" in lost and "ui_step:gen_anh" in lost
    assert conn.execute("SELECT COUNT(*) FROM diag_events").fetchone()[0] == 0


def test_cli_step_is_written_after_the_run_with_the_real_result(tmp_path):
    """THẤP: ghi SAU khi chạy; lỗi / sys.exit khác 0 → error kèm lý do; chế độ chỉ đọc (không điền step) → không ghi."""
    from core import ui_step
    path, conn = _db(tmp_path)

    def ok(argv, step):
        step.update(conn=conn, project=31, task="dàn cảnh 4")
        assert not conn.execute("SELECT COUNT(*) FROM diag_events WHERE stage='cli_step'").fetchone()[0]   # chưa ghi lúc đang chạy
        return 0

    def dung(argv, step):
        step.update(conn=conn, project=31, task="previs cảnh 4")
        raise SystemExit("DỪNG — không tìm được lối")

    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": "1"}):
        assert ui_step.run_cli("stage_auto", ok) == 0
        with pytest.raises(SystemExit):
            ui_step.run_cli("stage_previs", dung)
        ui_step.run_cli("stage_auto", lambda argv, step: None)                 # chỉ đọc: không điền step
    ev = PM.project_events(path, 31)
    assert [(e["key"], e["severity"]) for e in ev] == [("stage_auto", "info"), ("stage_previs", "error")]
    assert "không tìm được lối" in ev[1]["message"]


def test_stage_previs_plan_only_does_not_log_and_tools_use_run_cli():
    for rel, tool in (("tools/stage_auto.py", "stage_auto"), ("tools/stage_previs.py", "stage_previs")):
        src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        assert f'ui_step.run_cli("{tool}", _main, argv)' in src and "ui_step.cli(" not in src, rel
    src = open(os.path.join(ROOT, "tools", "stage_previs.py"), encoding="utf-8").read()
    i = src.index("step.update(conn=conn")
    assert "if not a.plan_only:" in src[i - 200:i]


def test_replay_payload_trusts_the_main_machine_flag(tmp_path):
    """THẤP: replay_payload kiểm cờ của <main> (_main_flag_on) — ui_step.cli không kiểm lại cờ của repo đang chạy lệnh."""
    from core.db import connect
    from tools import replay_payload as R
    main = tmp_path / "main"
    (main / "data").mkdir(parents=True)
    connect(str(main / "data" / "manifest.sqlite")).close()
    (main / "data" / "feature_settings.json").write_text(json.dumps({"flags": {"ui_step_log": True}}), encoding="utf-8")
    with mock.patch.dict(os.environ, {"FEATURE_UI_STEP_LOG": ""}):              # repo chạy lệnh: cờ TẮT
        R._cli_step(str(main), 31, "dựng lại gói gửi model shot 7")
    ev = PM.project_events(str(main / "data" / "manifest.sqlite"), 31)
    assert [(e["kind"], e["key"]) for e in ev] == [("cli_step", "replay_payload")]


def test_reports_leave_out_observation_events():
    for rel in ("tools/audit_run.py", "tools/kld_round_stats.py"):
        src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        assert "stage NOT IN ('ui_step', 'cli_step')" in src, rel


def test_pending_flag_is_waiting_not_unknown(mini):
    root, doc = mini
    doc["dashboard"]["cells"][0]["flags"] = ["co_chua_gop"]
    doc["dashboard"]["cells"][0]["pending_flags"] = {"co_chua_gop": "C-NHANH"}
    m = _model(root, doc, lambda n: "unknown")
    c = _cell(m, "c1")
    assert not m["unknown_flags"] and c["color"] == "vang" and any("chờ nhánh C-NHANH" in w for w in c["why"])


def test_evidence_names_a_function_or_a_button_key():
    """THẤP: bằng chứng không còn chung chung (chữ ngắn / glob dashboard/** / 'def ')."""
    doc = PM.load()
    for c in doc["dashboard"]["cells"] + doc["truong"]["nodes"]:
        for e in c.get("evidence") or []:
            assert e["text"].strip() not in ("def", "popup", "video", "Gen ảnh"), (c["id"], e)
            assert not (e["glob"].startswith("dashboard/**") and "(" not in e["text"] and "key=" not in e["text"]), (c["id"], e)
