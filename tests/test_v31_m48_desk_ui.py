"""C-M48-DESK-UI (22/10): Bàn đạo diễn 3D Đợt 1 — hàng nút trong expander từng cảnh của màn XEM (dashboard/stage_desk_ui.py), cờ
`stage_desk_ui` (TẮT, verified False, không costs, REQUIRES stage_view_ui). Mỗi nút gọi đúng hàm core/stage_desk (ở đây MOCK — không
Blender, không CSDL thật, 0 USD); chỉ Executive Producer (người) thấy Duyệt / Trả lại; thao tác đổi dữ liệu phải xác nhận; đang chạy → khóa
nút + hiện tiến độ. Kế hoạch docs/KE_HOACH_BAN_DAO_DIEN_3D_DASHBOARD_2026-10-21.md mục 3, 4, 9, 10."""
import inspect
import json
import os
import pathlib
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

ROOT = pathlib.Path(__file__).resolve().parent.parent
ON = {"FEATURE_STAGE_VIEW_UI": "1", "FEATURE_STAGE_DESK_UI": "1"}
OFF = {"FEATURE_STAGE_VIEW_UI": "1", "FEATURE_STAGE_DESK_UI": ""}
PID, DATA, SCENE = 7, "D:/khong_dung/data", "3"


def _status(phase="duyet", buttons=("N2", "N1", "N5", "N6", "N7", "N8"), **kw):
    s = {"scene": SCENE, "seg_id": "doan_3", "stage": "me_cung", "shots": [10, 11], "phase": phase, "label": "chờ Executive Producer duyệt",
         "k1": True, "inputs_changed": False, "inputs_known": True, "marks": {10: "m10", 11: None}, "approved_by": None, "n_returns": 0,
         "cams": [], "cams_this_stage": [], "bad": {}, "round": None, "sheet": None, "drawn": [], "revs": {10: 1, 11: 1}, "lock": None,
         "progress": None, "running": False, "user_approves": True, "buttons": list(buttons), "reset": None, "reset_stale": None}
    s.update(kw)
    return s


def _page():
    import types
    from dashboard import stage_desk_ui
    p = types.SimpleNamespace(conn="CONN")
    stage_desk_ui.render_scene(p, 7, "D:/khong_dung/data", "3")


class Desk:
    """Mock toàn bộ API lõi core.stage_desk + danh tính phiên (common.access_user / me / op_source)."""

    def __init__(self, status=None, ep=True, source="nguoi", email="ep@x.vn", user="mac_dinh", env=None):
        from core import stage_desk
        self.sd = stage_desk
        self.status = status or _status()
        self.op = mock.MagicMock(return_value=source)
        ep_patch = (mock.patch.object(stage_desk, "is_executive_producer", side_effect=ep) if callable(ep)
                    else mock.patch.object(stage_desk, "is_executive_producer", return_value=ep))
        self.patches = [mock.patch.dict(os.environ, dict(ON, **(env or {}))),
                        mock.patch.object(stage_desk, "scene_status", return_value=self.status),
                        ep_patch,
                        mock.patch("dashboard.common.access_user",
                                   return_value={"email": email, "role": "member"} if user == "mac_dinh" else user),
                        mock.patch("dashboard.common.me", return_value={"email": email}),
                        mock.patch("dashboard.common.op_source", self.op)]
        self.calls = {}
        for name in ("check_inputs", "estimate", "write_prompt", "load_answer", "build_sheet", "approve", "return_", "reset", "rerender",
                     "score", "render_plates"):
            m = mock.MagicMock(return_value={"ok": True, "started": True})
            self.calls[name] = m
            self.patches.append(mock.patch.object(stage_desk, name, m))

    def __enter__(self):
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *a):
        for p in reversed(self.patches):
            p.stop()

    def app(self):
        at = AppTest.from_function(_page, default_timeout=30)
        at.run()
        assert not at.exception, at.exception
        return at


def _btn(at, code):
    return next((b for b in at.button if b.key == f"desk_{PID}_{SCENE}_{code}"), None)


def _text(at):
    return "\n".join([m.value for m in at.markdown] + [w.value for w in at.warning] + [w.value for w in at.info]
                     + [w.value for w in at.error] + [w.value for w in at.success] + [c.value for c in at.caption])


# ---- cờ ---------------------------------------------------------------------------------------------------------------------
def test_flag_registered_off_no_costs_requires_view_golden_and_areas():
    from core import features
    from dashboard import stage_desk_ui as U
    f = features.FEATURES["stage_desk_ui"]
    assert U.FLAG == "stage_desk_ui" and f["verified"] is False and not f.get("costs")
    assert features.REQUIRES["stage_desk_ui"] == ("stage_view_ui",)
    assert "Bàn đạo diễn 3D" in f["label"] and "0 USD" in f["label"]
    with mock.patch.dict(os.environ, OFF):
        assert not U.enabled()
    with mock.patch.dict(os.environ, {"FEATURE_STAGE_VIEW_UI": "", "FEATURE_STAGE_DESK_UI": "1"}):
        assert not U.enabled()                                   # REQUIRES: không có màn XEM thì không có bàn
    golden = json.loads((ROOT / "tests" / "golden" / "package_inputs.json").read_text(encoding="utf-8"))
    assert all(golden[k]["flags"]["stage_desk_ui"] is False for k in ("image", "video"))
    areas = json.loads((ROOT / "devsys" / "areas.json").read_text(encoding="utf-8"))
    step2 = next(a for a in areas["areas"] if a["id"] == "step2")
    assert "dashboard/stage_desk_ui.py" in step2["code"] and "tests/test_v31_m48_desk_ui.py" in step2["tests"]
    assert "stage_desk_ui" in step2["flags"]


def test_flag_off_calls_nothing():
    from core import stage_desk
    from dashboard import stage_desk_ui as U
    with mock.patch.dict(os.environ, OFF), mock.patch.object(U, "st") as st, \
         mock.patch.object(stage_desk, "scene_status", side_effect=AssertionError("đọc khi cờ tắt")):
        U.render_scene(mock.Mock(), PID, DATA, SCENE)
    assert st.mock_calls == []


def test_view_calls_desk_once_inside_the_scene_expander():
    src = (ROOT / "dashboard" / "stage_view_ui.py").read_text(encoding="utf-8")
    assert src.count("stage_desk_ui.render_scene(") == 1
    body = src[src.index("with st.expander("):]
    line = next(x for x in body.splitlines() if "stage_desk_ui.render_scene(" in x)
    assert line.startswith(" " * 12) and "sc[\"scene\"]" in line          # trong khối expander (thụt 12), theo cảnh


def test_view_with_desk_off_draws_no_button(tmp_path):
    """Cờ bàn TẮT, màn XEM BẬT: render của màn XEM không gọi st.button nào (Bước 2 như cũ)."""
    from dashboard import stage_desk_ui as U, stage_view_ui as V
    sc = {"scene": "1", "shots": [], "warnings": [], "missing": [], "files": {"blockout": [], "top_cut": [], "clay": []}, "world": None,
          "dummies": None}
    with mock.patch.dict(os.environ, OFF), mock.patch.object(V, "collect", return_value=[sc]), mock.patch.object(V, "st") as st, \
         mock.patch.object(U, "st") as ust:
        V.render(mock.Mock(), PID, str(tmp_path))
    assert not any(c[0].endswith("button") for c in st.mock_calls) and ust.mock_calls == []


# ---- nút theo trạng thái + gọi đúng hàm -------------------------------------------------------------------------------------
def test_buttons_follow_core_list_and_each_calls_its_function():
    with Desk() as d:
        at = d.app()
        for code in ("N1", "N2", "N5", "N6", "N7", "N8"):
            assert _btn(at, code) is not None, code
        assert _btn(at, "N9") is None and _btn(at, "N11") is None
        _btn(at, "N1").click().run()
        args = d.calls["check_inputs"].call_args
        assert args.args[:4] == ("CONN", PID, DATA, SCENE)
        assert args.args[4] == {"kind": "human", "who": "ep@x.vn"}
        _btn(at, "N5").click().run()
        assert d.calls["build_sheet"].call_args.args[:4] == ("CONN", PID, DATA, SCENE)
        d.calls["estimate"].return_value = {"ok": True, "usd": 0.42, "usd_max": 2.1, "crew": True}
        _btn(at, "N2").click().run()
        assert d.calls["estimate"].called and "0.42" in _text(at)


def test_phase_xong_buttons_and_confirm_before_data_change():
    st_ = _status(phase="xong", buttons=["N2", "N1", "N5", "N8", "N9", "N10", "N11"], label="đã chốt")
    with Desk(st_) as d:
        at = d.app()
        assert _btn(at, "N6") is None and _btn(at, "N7") is None
        _btn(at, "N10").click().run()
        assert d.calls["score"].called
        _btn(at, "N9").click().run()                    # đổi máy → chưa xác nhận thì không gọi
        assert not d.calls["rerender"].called
        at.checkbox(key=f"desk_{PID}_{SCENE}_N9_ok").check().run()
        _btn(at, "N9").click().run()
        assert d.calls["rerender"].call_args.kwargs.get("confirm_drawn") is False
        _btn(at, "N11").click().run()
        assert not d.calls["render_plates"].called
        at.checkbox(key=f"desk_{PID}_{SCENE}_N11_ok").check().run()
        _btn(at, "N11").click().run()
        assert d.calls["render_plates"].called


def test_approve_needs_confirm_and_sends_marks_and_user():
    with Desk() as d:
        at = d.app()
        _btn(at, "N6").click().run()
        assert not d.calls["approve"].called
        at.checkbox(key=f"desk_{PID}_{SCENE}_N6_ok").check().run()
        _btn(at, "N6").click().run()
        kw = d.calls["approve"].call_args.kwargs
        assert kw["user"] == {"email": "ep@x.vn", "role": "member"}
        assert kw["expected_marks"] == {10: "m10", 11: None} and kw["confirm_drawn"] is False
        assert d.calls["approve"].call_args.args[4] == {"kind": "human", "who": "ep@x.vn"}


def test_approve_with_drawn_shots_asks_a_second_confirmation():
    with Desk(_status(drawn=[11])) as d:
        at = d.app()
        at.checkbox(key=f"desk_{PID}_{SCENE}_N6_ok").check().run()
        _btn(at, "N6").click().run()
        assert not d.calls["approve"].called                # chưa xác nhận shot đã vẽ
        at.checkbox(key=f"desk_{PID}_{SCENE}_N6_drawn").check().run()
        _btn(at, "N6").click().run()
        assert d.calls["approve"].call_args.kwargs["confirm_drawn"] is True


def test_return_sends_intents_per_shot():
    with Desk() as d:
        at = d.app()
        _btn(at, "N7").click().run()
        assert not d.calls["return_"].called                # không ý đồ nào → không gửi
        assert "ý đồ" in _text(at)
        at.text_input(key=f"desk_{PID}_{SCENE}_N7_y_10").set_value("Kelly lùi 1 m").run()
        _btn(at, "N7").click().run()
        c = d.calls["return_"].call_args
        assert c.args[4] == [{"shot": 10, "y_do": "Kelly lùi 1 m"}]
        assert c.kwargs["user"] == {"email": "ep@x.vn", "role": "member"} and c.args[5] == {"kind": "human", "who": "ep@x.vn"}


def test_not_ep_does_not_see_approve_or_return():
    with Desk(ep=False) as d:
        at = d.app()
        assert _btn(at, "N6") is None and _btn(at, "N7") is None
        assert _btn(at, "N5") is not None
        assert "Executive Producer" in _text(at)


def test_claude_session_cannot_approve_and_acts_as_ai():
    with Desk(source="claude") as d:
        at = d.app()
        assert _btn(at, "N6") is None and _btn(at, "N7") is None
        _btn(at, "N1").click().run()
        assert d.calls["check_inputs"].call_args.args[4]["kind"] == "ai"


def test_reset_shows_preview_then_confirms():
    with Desk() as d:
        d.calls["reset"].side_effect = lambda *a, **k: (
            {"ok": True} if k.get("confirm") else
            {"ok": False, "needs_confirm": True, "preview": {"say": "máy cũ của shot 10 giữ tới khi duyệt lượt mới", "cams_kept": [10]},
             "errors": ["cần xác nhận"]})
        at = d.app()
        _btn(at, "N8").click().run()
        assert d.calls["reset"].call_args.kwargs.get("confirm") is False
        assert "máy cũ của shot 10" in _text(at)
        go = next(b for b in at.button if b.key == f"desk_{PID}_{SCENE}_N8_go")
        go.click().run()
        assert d.calls["reset"].call_args.kwargs.get("confirm") is True


def test_load_answer_parses_json_and_refuses_bad_json():
    st_ = _status(phase="quay_phim", buttons=["N2", "N1", "N3", "N4", "N8"], label="đang ở vai Quay phim")
    with Desk(st_) as d:
        at = d.app()
        _btn(at, "N3").click().run()
        assert d.calls["write_prompt"].called
        at.text_area(key=f"desk_{PID}_{SCENE}_N4_json").set_value("{không phải json").run()
        at.checkbox(key=f"desk_{PID}_{SCENE}_N4_ok").check().run()
        _btn(at, "N4").click().run()
        assert not d.calls["load_answer"].called and "JSON" in _text(at)
        at.text_area(key=f"desk_{PID}_{SCENE}_N4_json").set_value('{"shots": []}').run()
        _btn(at, "N4").click().run()
        assert d.calls["load_answer"].call_args.args[4] == {"shots": []}


def test_running_locks_buttons_and_shows_progress():
    pr = {"state": "running", "label": "🔍 Kiểm đầu vào", "step": "đo / đọc K1", "log": ["đo / đọc K1"]}
    with Desk(_status(buttons=["N2"], progress=pr, running=True)) as d:
        at = d.app()
        assert "đo / đọc K1" in _text(at)
        assert _btn(at, "N2") is not None and _btn(at, "N6") is None


def test_lock_held_by_other_disables_and_says_who():
    lock = {"action": "N9", "owner": "autopilot", "since": "10:00"}
    with Desk(_status(buttons=["N2", "N1", "N5", "N6", "N7", "N8"], lock=lock)) as d:
        at = d.app()
        assert "autopilot" in _text(at)
        assert all(b.disabled for b in at.button if b.key and b.key.startswith(f"desk_{PID}_{SCENE}_N") and not b.key.endswith("N2"))


def test_errors_are_said_not_swallowed():
    with Desk() as d:
        d.calls["build_sheet"].return_value = {"ok": False, "errors": ["chưa có lượt đã lưu / lần đo nào để dựng tấm ghép"]}
        at = d.app()
        _btn(at, "N5").click().run()
        assert any("chưa có lượt đã lưu" in e.value for e in at.error)


def test_finished_and_failed_progress_are_said():
    for pr, want in (({"state": "done", "label": "🖼 Dựng tấm ghép", "step": "vẽ nhịp + ghép"}, "xong"),
                     ({"state": "error", "label": "🖼 Dựng tấm ghép", "error": "BlenderError: không tìm thấy Blender"}, "không tìm thấy Blender"),
                     ({"state": "interrupted", "label": "N9", "error": "tác vụ bị ngắt lúc 10:00"}, "bị ngắt")):
        with Desk(_status(progress=pr)) as d:
            assert want in _text(d.app())


def test_k1_missing_suggests_check_inputs_first():
    with Desk(_status(k1=False)) as d:
        assert "K1" in _text(d.app())


def test_source_has_no_env_flag_writes_no_api_no_sql():
    from dashboard import stage_desk_ui as U
    src = inspect.getsource(U)
    for word in ("os.environ", "FEATURE_", "anthropic", "llm_runner", "claude_cli", "UPDATE ", "INSERT ", "DELETE ", ".commit("):
        assert word not in src, word
    assert "core.stage_desk" in src or "from core import stage_desk" in src


# ---- rà kỹ 22/10 (vòng sửa): mỗi lỗi một test ---------------------------------------------------------------------------------
def test_ra1_confirmation_is_unticked_after_each_data_change():
    """Mục 1: ô xác nhận bỏ tích sau khi bấm — lần bấm sau phải xác nhận lại (không chạy lại N9 / N11 / N6 lặng lẽ)."""
    st_ = _status(phase="xong", buttons=["N2", "N1", "N5", "N8", "N9", "N10", "N11"], label="đã chốt")
    with Desk(st_) as d:
        at = d.app()
        at.checkbox(key=f"desk_{PID}_{SCENE}_N9_ok").check().run()
        _btn(at, "N9").click().run()
        assert d.calls["rerender"].call_count == 1
        assert at.checkbox(key=f"desk_{PID}_{SCENE}_N9_ok").value is False
        _btn(at, "N9").click().run()
        assert d.calls["rerender"].call_count == 1                     # chưa xác nhận lại → không gọi lần 2
        at.checkbox(key=f"desk_{PID}_{SCENE}_N11_ok").check().run()
        _btn(at, "N11").click().run()
        _btn(at, "N11").click().run()
        assert d.calls["render_plates"].call_count == 1
    with Desk() as d:
        at = d.app()
        at.checkbox(key=f"desk_{PID}_{SCENE}_N6_ok").check().run()
        _btn(at, "N6").click().run()
        assert at.checkbox(key=f"desk_{PID}_{SCENE}_N6_ok").value is False
        _btn(at, "N6").click().run()
        assert d.calls["approve"].call_count == 1


def test_ra2_core_exception_is_said_not_crashing_step2():
    """Mục 2: lõi ném (segment / sqlite …) → câu lỗi trên bàn, trang không sập."""
    with Desk() as d:
        d.calls["build_sheet"].side_effect = RuntimeError("database is locked")
        at = d.app()
        _btn(at, "N5").click().run()
        assert not at.exception
        assert any("database is locked" in e.value for e in at.error)


def test_ra3_claude_session_latch_is_one_way():
    """Mục 3: đã là `?op=claude` thì đổi `?op=nguoi` không hiện lại Duyệt / Trả lại (chốt op_claude_seen)."""
    with Desk(source="claude") as d:
        at = d.app()
        assert _btn(at, "N6") is None
        d.op.return_value = "nguoi"
        at.run()
        assert _btn(at, "N6") is None and _btn(at, "N7") is None
        _btn(at, "N1").click().run()
        assert d.calls["check_inputs"].call_args.args[4]["kind"] == "ai"
    with Desk(source="nguoi") as d:                                    # phiên người từ đầu: vẫn thấy
        assert _btn(d.app(), "N6") is not None


def test_ra4_write_buttons_pass_the_signed_in_user_to_core():
    """Mục 4 (UI): N4 / N8 / N9 / N11 truyền user = common.access_user() để lõi kiểm quyền SỬA."""
    u = {"email": "ep@x.vn", "role": "member"}
    st_ = _status(phase="xong", buttons=["N2", "N1", "N5", "N8", "N9", "N10", "N11"], label="đã chốt")
    with Desk(st_) as d:
        d.calls["reset"].side_effect = lambda *a, **k: ({"ok": True} if k.get("confirm") else
                                                        {"ok": False, "needs_confirm": True, "preview": {"say": "x"}})
        at = d.app()
        at.checkbox(key=f"desk_{PID}_{SCENE}_N9_ok").check().run()
        _btn(at, "N9").click().run()
        assert d.calls["rerender"].call_args.kwargs["user"] == u
        at.checkbox(key=f"desk_{PID}_{SCENE}_N11_ok").check().run()
        _btn(at, "N11").click().run()
        assert d.calls["render_plates"].call_args.kwargs["user"] == u
        _btn(at, "N8").click().run()
        assert d.calls["reset"].call_args.kwargs["user"] == u
        next(b for b in at.button if b.key == f"desk_{PID}_{SCENE}_N8_go").click().run()
        assert d.calls["reset"].call_args.kwargs == {"confirm": True, "user": u}
    st_ = _status(phase="quay_phim", buttons=["N2", "N1", "N3", "N4", "N8"])
    with Desk(st_) as d:
        at = d.app()
        at.text_area(key=f"desk_{PID}_{SCENE}_N4_json").set_value('{"shots": []}').run()
        at.checkbox(key=f"desk_{PID}_{SCENE}_N4_ok").check().run()
        _btn(at, "N4").click().run()
        assert d.calls["load_answer"].call_args.kwargs["user"] == u


def test_ra4_core_write_buttons_need_edit_right():
    """Mục 4 (lõi): có user mà chỉ XEM → N4 / N8 / N9 / N11 từ chối trước khi chạm đoạn; user None (CLI / autopilot / đăng nhập TẮT)
    hoặc người được SỬA → chạy như cũ."""
    from core import stage_desk as D
    from tests.test_decisions import _desk_project
    p, pid, _sids, _seg, data = _desk_project()
    conn = p.conn
    conn.execute("UPDATE projects SET created_by='tao@x' WHERE id=?", (pid,))
    for em, lv in (("xem@x", "view"), ("sua@x", "edit")):
        conn.execute("INSERT INTO project_watchers(project_id, email, level, added_at) VALUES (?,?,?,?)", (pid, em, lv, "2026-10-22"))
    who = {"kind": "human", "who": "xem@x"}
    calls = {"N4": lambda u: D.load_answer(conn, pid, data, "1", {}, who, user=u),
             "N8": lambda u: D.reset(conn, pid, data, "1", who, confirm=True, user=u),
             "N9": lambda u: D.rerender(conn, pid, data, "1", who, user=u),
             "N11": lambda u: D.render_plates(conn, pid, data, "1", who, user=u)}
    with mock.patch.dict(os.environ, {"DASHBOARD_AUTH": "on"}), \
            mock.patch.object(D, "segment", side_effect=RuntimeError("tới segment")):
        for code, fn in calls.items():
            r = fn({"email": "xem@x", "role": "member"})
            assert r["ok"] is False and "XEM" in r["errors"][0], code
            for u in (None, {"email": "sua@x", "role": "member"}):
                with pytest.raises(RuntimeError, match="tới segment"):
                    fn(u)


def test_ra5_desk_flag_is_opt_in_only_so_experimental_preset_keeps_it_off():
    from core import features
    assert "stage_desk_ui" in features.OPT_IN_ONLY
    with mock.patch.dict(os.environ, {"FEATURE_STAGE_DESK_UI": "", "FEATURE_STAGE_VIEW_UI": ""}):
        assert features._state("stage_desk_ui", {"preset": "experimental", "flags": {}, "modes": {}}) == "off"
        assert features._state("stage_desk_ui", {"preset": "experimental", "flags": {"stage_desk_ui": True}, "modes": {}}) == "on"


def test_ra6_result_shows_once_and_status_is_redrawn_after_action():
    """Mục 6: sau bấm vẽ lại theo trạng thái lõi MỚI (st.rerun) và câu kết quả không nằm mãi."""
    with Desk() as d:
        at = d.app()
        n = d.sd.scene_status.call_count
        d.calls["build_sheet"].return_value = {"ok": True, "path": "beats/x.png"}
        _btn(at, "N5").click().run()
        assert d.sd.scene_status.call_count >= n + 2                  # lượt bấm + lượt vẽ lại
        assert any("beats/x.png" in m.value for m in at.success)
        at.run()
        assert not any("beats/x.png" in m.value for m in at.success)


def test_ra7_answer_file_message_uses_absolute_path():
    from core import stage_desk
    from dashboard import stage_desk_ui as U
    rel = os.path.join("data", "projects", "7", "doan_3")
    with mock.patch.object(stage_desk, "segment", return_value={"id": "S3"}), \
            mock.patch.object(stage_desk, "seg_dir", return_value=rel):
        obj, err = U._answer_obj("CONN", PID, "data/projects", SCENE, "quay_phim", "")
    assert obj is None and os.path.abspath(rel) in err


def test_ra8_view_header_drops_read_only_wording_when_desk_on(tmp_path):
    from dashboard import stage_desk_ui as U, stage_view_ui as V
    sc = {"scene": "1", "shots": [], "warnings": [], "missing": [], "files": {"blockout": [], "top_cut": [], "clay": []}, "world": None,
          "dummies": None}
    for env, want in ((OFF, "chỉ xem"), (ON, "Bàn đạo diễn 3D")):
        with mock.patch.dict(os.environ, env), mock.patch.object(V, "collect", return_value=[sc]), mock.patch.object(V, "st") as st, \
                mock.patch.object(U, "render_scene"):
            V.render(mock.Mock(), PID, str(tmp_path))
        head = st.markdown.call_args_list[0].args[0]
        assert want in head, head


def test_ra9_real_need_ep_path_auth_on_off_and_claude(tmp_path):
    """Mục 9: is_executive_producer + _need_ep THẬT (CSDL tệp tạm) qua giao diện — danh tính UI truyền đúng cái lõi kiểm."""
    from core import stage_desk as D
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(str(tmp_path / "desk.db")))
    pid = p.create_project("desk")
    conn = p.conn
    conn.execute("UPDATE projects SET created_by='tao@x' WHERE id=?", (pid,))
    conn.execute("INSERT INTO project_watchers(project_id, email, level, added_at) VALUES (?,?,?,?)", (pid, "sua@x", "edit", "2026-10-22"))
    conn.commit()
    db = conn.execute("PRAGMA database_list").fetchone()[2]
    assert db, "cần CSDL tệp (AppTest chạy kịch bản ở luồng khác)"

    def fresh():                                                       # sqlite: mỗi luồng một kết nối (AppTest chạy ở luồng khác)
        return connect(db)

    real_ep, real_need = D.is_executive_producer, D._need_ep
    seen = []

    def approve(_c, _pid, _d, _s, who, user=None, **_k):
        try:
            real_need(fresh(), pid, who, user, "Duyệt")
            seen.append(("ok", who))
            return {"ok": True}
        except D.DeskError as e:
            seen.append(("tu_choi", str(e)))
            return {"ok": False, "errors": [str(e)]}

    def ep(_c, _p, user):
        return real_ep(fresh(), pid, user)

    cases = (({"DASHBOARD_AUTH": "on"}, "tao@x", "mac_dinh", "nguoi", True),       # chủ dự án đăng nhập = EP
             ({"DASHBOARD_AUTH": "on"}, "sua@x", "mac_dinh", "nguoi", False),      # chỉ được sửa → không thấy Duyệt
             ({"DASHBOARD_AUTH": "off"}, "local", None, "nguoi", True),             # đăng nhập TẮT: chủ máy
             ({"DASHBOARD_AUTH": "on"}, "tao@x", "mac_dinh", "claude", False))      # phiên Claude dùng đăng nhập EP
    for env, email, user, src, sees in cases:
        seen.clear()
        with Desk(ep=ep, email=email, user=user, source=src, env=env) as d:
            d.calls["approve"].side_effect = approve
            at = d.app()
            assert (_btn(at, "N6") is not None) is sees, (email, src)
            if sees:
                at.checkbox(key=f"desk_{PID}_{SCENE}_N6_ok").check().run()
                _btn(at, "N6").click().run()
                assert seen and seen[0][0] == "ok", seen
                assert seen[0][1] == {"kind": "human", "who": email}
    with mock.patch.dict(os.environ, {"DASHBOARD_AUTH": "on"}), pytest.raises(D.DeskError):
        real_need(conn, pid, {"kind": "ai", "who": "phien_claude_dashboard"}, {"email": "tao@x", "role": "member"}, "Duyệt")
