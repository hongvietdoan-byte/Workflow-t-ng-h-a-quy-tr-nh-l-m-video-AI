"""C3 (người dùng duyệt 15/10, docs/handoff/RA_QUYET_DINH_LOI_LAP_2026-10-15.md mục C3): sổ quyết định MỘT nguồn `data/decisions.json`.

Mỗi mục `active` phải được thi hành: cờ đúng trạng thái ở MẶC ĐỊNH CODE (tệp cài đặt rỗng, không FEATURE_<NAME>) và mỗi check code
(hàm `check_*` trong file này) chạy đúng. Check có `pending` (chờ nhánh khác gộp) → xfail strict: nhánh gộp xong mà quên bỏ `pending`
thì đỏ (sổ phải theo code). Mục `replaced` phải có mục mới `replaces` nó; id trùng / `replaces` trỏ id không có → đỏ.
Các check chỉ dựng CSDL tạm + mock, 0 USD, không gọi mạng."""
import json
import os
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

from core import decisions as D
from core import features

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = D.load()


# ---- check code (tên hàm = enforced_by[].check) -------------------------------------------------------------------------------
def _pipeline_with_shot(data):
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect())
    pid = p.create_project("decisions")
    idx = p.add_scene_next(pid, "s1")
    sid = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()[0]
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
    p.conn.commit()
    return p, pid, sid


def _only_flag_on(*names):
    real = features.on
    return mock.patch.object(features, "on", lambda n: True if n in names else real(n))


def check_simple_shot_direct_720p():
    """Shot đơn giản (Đạo diễn gắn 'easy') ở chế độ 2 bậc → gen thẳng (Seedance 2.5 720p rồi phóng ffmpeg 1080), không vào nháp 480."""
    from core import quality_tier
    p, _, sid = _pipeline_with_shot({"difficulty": "easy", "difficulty_by": "director", "difficulty_why": "1 nhân vật đứng yên, máy tĩnh"})
    with _only_flag_on("two_tier_quality"):
        assert quality_tier.path(p.conn, sid) == "direct", "shot đơn giản vẫn đi nháp 480p"
    p2, _, sid2 = _pipeline_with_shot({"difficulty": "complex"})
    with _only_flag_on("two_tier_quality"):
        assert quality_tier.path(p2.conn, sid2) == "draft_first", "shot khó phải nháp 480p trước"


def check_no_480p_in_delivery():
    """Bản giao khung 1080: clip 480p (cạnh ngắn < 720) bị chặn, không phóng lên giao."""
    from core import final_cut
    rows = [{"path": "shot1.mp4", "title": "s1", "idx": 1}]
    with mock.patch.object(final_cut, "measured_size", return_value=(480, 854)):
        with pytest.raises(ValueError):
            final_cut.require_delivery_resolution(rows, (1080, 1920))
    with mock.patch.object(final_cut, "measured_size", return_value=(720, 1280)):
        final_cut.require_delivery_resolution(rows, (1080, 1920))          # 720p được phóng 1080 (quyết định 13/10)


def check_draft_never_auto_approved():
    """Chạy tự động không bao giờ tự duyệt bản NHÁP video — người duyệt (qua chat)."""
    from core import autopilot, quality_tier
    p, pid, sid = _pipeline_with_shot({})
    now = "2026-10-15T00:00:00Z"
    cur = p.conn.execute("INSERT INTO jobs(project_id, scene_id, type, state, created_at, updated_at, quality_tier) "
                         "VALUES (?, ?, 'video_gen', 'pending_review', ?, ?, 'draft')", (pid, sid, now, now))
    p.conn.commit()
    with mock.patch.object(quality_tier, "enabled", return_value=True):
        autopilot._approve_unflagged(p, pid, "video_gen")
    assert p.conn.execute("SELECT state FROM jobs WHERE id=?", (cur.lastrowid,)).fetchone()[0] == "pending_review"


def check_image_default_gpt25():
    """Ảnh mặc định GPT Image 2.5: dashboard.env.example (gốc cài máy mới) đặt DEEPIX_MODEL là một model gpt-image-2.5 có luật trong
    data/provider_rules.json, và dự án không chọn riêng thì dùng đúng model đó."""
    from core import image_models
    value = None
    with open(os.path.join(ROOT, "dashboard.env.example"), encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("DEEPIX_MODEL="):
                value = line.split("=", 1)[1].strip()
    assert value and value.startswith("gpt-image-2.5"), f"dashboard.env.example DEEPIX_MODEL = {value!r}"
    assert value in image_models.models(), f"{value} không có trong data/provider_rules.json"
    with mock.patch.dict(os.environ, {"DEEPIX_MODEL": value}):
        assert image_models.of_project(None) == value


def check_no_budget_lock_gate():
    """15/10 người dùng bỏ cổng 'Tự chạy trong trần' (duyệt & khóa trần trước khi gen ảnh): needs_lock không bao giờ đòi."""
    from core import automation, project_budget
    with mock.patch.object(project_budget, "enabled", return_value=True), \
            mock.patch.object(automation, "effective_mode", return_value="auto"):
        assert project_budget.needs_lock(None, 1) is False, "cổng khóa ngân sách 'Tự chạy trong trần' vẫn còn"
    for gone in ("gate_reason", "approval_pending", "run_over"):           # the run's waits on the budget are gone too
        assert not hasattr(project_budget, gone), f"project_budget.{gone} (cổng chờ ngân sách) vẫn còn"
    from core import autopilot
    assert not hasattr(autopilot, "_cap_wait"), "autopilot._cap_wait (chờ khi chạm trần) vẫn còn"


def check_byd_missing_shot_auto_numbered():
    """15/10: BYĐ thiếu số shot → hệ thống tự điền số thứ tự (shot_no / vị trí), không gọi lượt sửa trả tiền, có ghi ⚙ Chẩn đoán."""
    from core import director_byd, llm_runner
    from tests.test_director_byd import KHO, _project

    class _NoCall:
        calls = 0

        def complete(self, prompt, images=()):
            _NoCall.calls += 1
            return llm_runner.LlmReply('{"byd": []}', 1, 1)
    byd = {"thanh_phan": [{"vat": "KELLY", "vai": "chinh"}],
           "may": {"co": "MS", "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"},
           "noi_chon": {"kho_id": KHO, "thoi_gian": "day", "thoi_tiet": "clear"}}
    with mock.patch.dict(os.environ, {"FEATURE_SHOT_INTENT": "1"}):
        p, pid = _project()
        obj = {"scenes": [{"idx": 8, "shots": [{"characters": ["KELLY"], "byd": dict(byd)},
                                               {"characters": ["KELLY"], "byd": dict(byd)}]}]}
        with mock.patch.object(director_byd.diag, "record") as rec:
            director_byd.settle(p.conn, pid, obj, _NoCall())
    assert _NoCall.calls == 0, "BYĐ chỉ thiếu số shot mà vẫn gọi lượt sửa trả tiền"
    assert [s["byd"]["shot"] for s in obj["scenes"][0]["shots"]] == [1, 2]
    assert "2 BYĐ thiếu `shot`" in rec.call_args[0][3], "⚙ Chẩn đoán không ghi số shot tự điền"


def check_stage_auto_plan():
    """15/10 kế hoạch sân khấu 3D tự động (Q1/Q4, sân khấu = mô hình): cờ stage_auto có, mặc định TẮT chưa thử thật, tốn tiền khai báo;
    bước sân khấu chạy trước nền 3D; máy chỉ ở ô đi tới được từ O; cảnh đã có máy sân khấu không lập G0."""
    import inspect
    from core import autopilot, camera_plan, features, stage_solver
    meta = features.FEATURES.get("stage_auto") or {}
    assert meta and meta.get("costs") is True and not meta.get("verified"), "cờ stage_auto thiếu / sai khai báo"
    src = inspect.getsource(autopilot)
    assert src.index('("stage", _stage_phase)') < src.index('("plates", _plates_phase)'), "bước sân khấu phải trước nền 3D"
    assert "reach" in inspect.signature(stage_solver.solve_scene).parameters, "bộ giải thiếu luật ô đi tới được"
    assert "stage_auto.FIELD" in inspect.getsource(camera_plan.todo_groups), "G0 không bỏ qua cảnh đã có máy sân khấu"
    assert 'features.on("stage_camera")' in inspect.getsource(camera_plan.todo_groups),         "G0 phải bỏ shot đã có máy sân khấu theo cờ stage_camera (nền 3D dùng máy đó), không theo stage_auto (16/10 #31)"


def check_stage_crew_plan():
    """16/10 kế hoạch chia vai sân khấu: cờ stage_crew tốn tiền, chưa thử thật, KHÔNG bật mặc định (API đo chi phí rồi mới quyết);
    duyệt chốt do người dùng mặc định; luồng tự động dùng chia vai khi cờ bật; đề nghị dời người chỉ hỏi Đạo diễn MỘT lần (Đạo diễn
    thắng — hỏi lại thành chưa giải quyết, không vòng)."""
    import inspect
    from core import features, stage_auto, stage_crew
    meta = features.FEATURES.get("stage_crew") or {}
    assert meta.get("costs") is True and not meta.get("verified") and not meta.get("default_on"), "cờ stage_crew sai khai báo"
    assert (features.FEATURES.get("stage_crew_user_approve") or {}).get("default_on") is True, "duyệt chốt phải do người dùng"
    assert "stage_crew" in features.OPT_IN_ONLY, "preset Thử nghiệm không được tự bật chia vai qua API (quyết định 3)"
    assert "run_segment_crew if stage_crew.enabled()" in inspect.getsource(stage_auto.run), "run() chưa dùng chia vai khi cờ bật"
    src = inspect.getsource(stage_crew._ingest)
    assert 'state["asked"]' in src and "unresolved" in src, "đề nghị dời người phải chỉ hỏi Đạo diễn một lần"



def check_stage_handheld_new_scenes():
    """16/10: cờ stage_handheld_props chỉ cho cảnh MỚI — đoạn đã dàn không có đồ cầm tay giữ đầu vào (vân tay) cũ; không bật qua preset."""
    import inspect
    from core import features, stage_auto
    assert "stage_handheld_props" in features.OPT_IN_ONLY, "preset không được tự bật đồ cầm tay"
    assert "not placed_without_handheld(k1_dir, seg)" in inspect.getsource(stage_auto.inputs_for), "cảnh đã duyệt bị đổi đầu vào"
    assert "weapon_size_from_scale" in inspect.getsource(stage_auto.inputs_for), "chưa suy cỡ vũ khí từ câu tỉ lệ Kho"

def check_time_weather_single_source():
    """17/10 (#31 shot 27–30): đổi time / weather bằng BẤT KỲ đường ghi nào → byd.noi_chon chép theo; việc chép không là thay đổi để rà."""
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect())
    conn = p.conn
    sid = p.create_scene(p.create_project("t"), 1, "s")
    data = {"time": "dawn", "weather": "clear", "byd": {"noi_chon": {"kho_id": 1, "thoi_gian": "dawn", "thoi_tiet": "clear"}}}
    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data), sid))
    conn.execute("DELETE FROM change_events")
    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(dict(data, time="night", weather="fog")), sid))   # SQL tay
    nc = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()[0])["byd"]["noi_chon"]
    assert (nc["thoi_gian"], nc["thoi_tiet"], nc["kho_id"]) == ("night", "fog", 1), nc
    assert conn.execute("SELECT COUNT(*) FROM change_events WHERE scene_id=?", (sid,)).fetchone()[0] == 1, "việc chép tạo thêm thay đổi"


def check_no_kling_for_face_closeups():
    """18/10 (#31 G24): cờ closeup_start_frame đã gỡ (features.REMOVED) — shot cận thấy mặt không tự đi Kling; Kling chỉ là đường lùi."""
    import inspect
    from core import features, model_router, seedance_refs
    assert "closeup_start_frame" in features.REMOVED and "closeup_start_frame" not in features.FEATURES, "cờ cận→Kling vẫn còn"
    assert not hasattr(seedance_refs, "face_closeup"), "còn đường cận thấy mặt ra khỏi nhóm tham chiếu"
    assert "closeup_start_frame" not in inspect.getsource(model_router), "bộ chọn model còn nhánh Kling cho cận mặt"


def check_video_sends_form_picture():
    """19/10 (#31 G27): gói video có ảnh dạng + ảnh vật Kho; thiếu ảnh dạng → lint ĐỎ."""
    import inspect
    from core import runner, seedance_refs
    assert hasattr(seedance_refs, "form_and_object_pictures") and seedance_refs.FORM_TAG and seedance_refs.OBJECT_TAG
    assert "form_and_object_pictures" in inspect.getsource(seedance_refs.identity_pictures), "identity_pictures không thêm ảnh dạng/vật"
    assert "thiếu ảnh dạng" in inspect.getsource(runner.VideoRunner._ref_lint), "lint không chặn khi thiếu ảnh dạng"


CHECKS = {k: v for k, v in globals().items() if k.startswith("check_") and callable(v)}


# ---- sổ hợp lệ -----------------------------------------------------------------------------------------------------------------
def test_ledger_in_git_tree_and_valid():
    assert os.path.abspath(D.PATH) == os.path.join(ROOT, "data", "decisions.json")
    assert D.problems(LEDGER) == []
    assert any(i["status"] == "active" for i in LEDGER["items"])


V31_DIRECTION = {"v31-kho-forms-direction-2026-10-20": "ĐỊNH HƯỚNG", "v31-user-edit-protection-direction-2026-10-20": "ĐỊNH HƯỚNG",
                 "v31-scene-world-map-trial-2026-10-20": "THỬ NGHIỆM", "v31-pilot-three-rounds-2026-10-20": "CHƯA DUYỆT CHI PHÍ",
                 "v31-permission-tiers-2026-10-20": "Cấp 3"}


V31_REPLACED_BY = {"v31-user-edit-protection-direction-2026-10-20": "v31-d04-field-level-write-guard-2026-10-20",
                   "v31-kho-forms-direction-2026-10-20": "v31-d05-kho-structured-forms-2026-10-20",
                   "v31-scene-world-map-trial-2026-10-20": "v31-d06-scene-world-map-flexible-2026-10-20"}


def test_v31_direction_decisions_say_they_are_not_implementation_approval():
    """20/10 (người dùng, văn bản quyết định V3.1): M2.3 / M2.5 / M3.1 / M5.3 chỉ duyệt định hướng / quy trình — mục sổ phải nói rõ chưa
    được triển khai (sổ chưa có trạng thái nhiều cấp; đề xuất mở rộng ở docs/KE_HOACH_V3_1_MASTER_BUILD_2026-10-20.md mục 4b). Ba mục
    định hướng đã được D04 / D05 / D06 thay (cùng ngày, chi tiết hơn) — giữ lịch sử, status replaced."""
    items = {i["id"]: i for i in LEDGER["items"]}
    for iid, must in V31_DIRECTION.items():
        assert iid in items, iid
        assert must in items[iid]["text"], iid
        assert "Cấp" in items[iid]["changes"] or iid == "v31-permission-tiers-2026-10-20", iid
        want = "replaced" if iid in V31_REPLACED_BY else "active"
        assert items[iid]["status"] == want, iid
    for old, new in V31_REPLACED_BY.items():
        assert items[new]["replaces"] == old and items[new]["status"] == "active", new


def test_v31_d01_to_d10_recorded_as_policy_not_implementation():
    """20/10 người dùng duyệt D01–D10 (văn bản 'PHÊ DUYỆT D01–D10'): đủ 10 mục active, mỗi mục ghi lựa chọn và nói rõ là chính sách /
    định hướng — không phải lệnh triển khai code (Cấp 2) hay chi phí (Cấp 3)."""
    import re
    got = {}
    for i in LEDGER["items"]:                       # mục sửa sau (vd. v31-d03b-…, người dùng 20/10) thay mục gốc: lấy mục active
        m = re.match(r"v31-d(0[1-9]|10)[a-z]?-", i["id"])
        if m and (i["status"] == "active" or int(m.group(1)) not in got):
            got[int(m.group(1))] = i
    assert sorted(got) == list(range(1, 11))
    choice = {1: "A", 2: "A", 3: "A", 4: "B", 5: "A", 6: "B", 7: "A", 8: "A", 9: "C", 10: "A"}
    for n, it in got.items():
        assert it["status"] == "active", it["id"]
        assert f"chọn {choice[n]}" in it["text"], it["id"]
        assert "không phải lệnh triển khai" in it["changes"], it["id"]


def test_problems_catch_duplicate_dangling_and_orphan_replaced():
    doc = {"items": [
        {"id": "a", "date": "2026-10-01", "by": "người dùng", "text": "x", "keeps": "", "changes": "", "replaces": None,
         "enforced_by": [], "status": "replaced"},
        {"id": "b", "date": "2026-10-02", "by": "người dùng", "text": "y", "keeps": "", "changes": "", "replaces": "zz",
         "enforced_by": [{"kind": "flag", "name": "no_such_flag", "on": True}], "status": "active"},
        {"id": "b", "date": "2026-10-03", "by": "người dùng", "text": "z", "keeps": "", "changes": "", "replaces": None,
         "enforced_by": [{"kind": "code", "check": "check_missing"}], "status": "active"}]}
    text = " ".join(D.problems(doc, checks=set(CHECKS)))
    assert "trùng" in text and "zz" in text and "'a'" in text and "no_such_flag" in text and "check_missing" in text


def test_every_code_check_named_exists():
    names = [e["check"] for i in LEDGER["items"] for e in i["enforced_by"] if e["kind"] == "code"]
    assert names and all(n in CHECKS for n in names), [n for n in names if n not in CHECKS]


# ---- thi hành ------------------------------------------------------------------------------------------------------------------
FLAG_CASES = [(i["id"], e["name"], e["on"]) for i in LEDGER["items"] if i["status"] == "active"
              for e in i["enforced_by"] if e["kind"] == "flag"]
CODE_CASES = [pytest.param(i["id"], e["check"], id=f"{i['id']}:{e['check']}",
                           marks=[pytest.mark.xfail(reason=e["pending"], strict=True)] if e.get("pending") else [])
              for i in LEDGER["items"] if i["status"] == "active" for e in i["enforced_by"] if e["kind"] == "code"]


@pytest.mark.parametrize("item_id,name,want", FLAG_CASES)
def test_flag_matches_decision_at_code_default(item_id, name, want):
    """Không dựa tệp cài đặt máy chính: tệp cài đặt rỗng + không FEATURE_<NAME> → trạng thái theo mặc định code."""
    empty = os.path.join(tempfile.mkdtemp(), "none.json")
    env = {"FEATURE_" + k.upper(): "" for k in features.FEATURES}
    env["FEATURE_SETTINGS_FILE"] = empty
    with mock.patch.dict(os.environ, env):
        got = features.state(name)
    assert features.default_state(name) == got
    assert (got == "on") is bool(want), f"{item_id}: cờ {name} mặc định code '{got}', quyết định {'BẬT' if want else 'không bật'}"


@pytest.mark.parametrize("item_id,check", CODE_CASES)
def test_code_check(item_id, check):
    CHECKS[check]()


def test_cli_list_and_check_from_any_cwd():
    env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=ROOT)
    for cmd in ("list", "check"):
        out = subprocess.run([sys.executable, "-m", "core.decisions", cmd], cwd=tempfile.mkdtemp(), env=env,
                             capture_output=True, text=True, encoding="utf-8", timeout=180)
        assert out.returncode == 0, (cmd, out.stdout[-800:], out.stderr[-800:])
        assert "p27-fix-flags-on" in out.stdout


def test_v31_speedup_recorded():
    """20/10 người dùng 'áp dụng cả 3 cách rút ngắn': duyệt Cấp 2 theo milestone, gói Cấp 3 sớm, 3 làn — KHÔNG bỏ cấp quyền."""
    items = {i["id"]: i for i in LEDGER["items"]}
    it = items["v31-speedup-milestone-approval-2026-10-20"]
    assert it["status"] == "active" and it["replaces"] is None
    assert "MILESTONE" in it["text"] and "Cấp 3" in it["text"] and "v31-permission-tiers-2026-10-20" in it["keeps"]
    assert items["v31-permission-tiers-2026-10-20"]["status"] == "active"


def test_v31_cap2_cap3_approval_recorded():
    """20/10 'PHÊ DUYỆT GÓI CẤP 2 / CẤP 3 — V3.1': Cấp 2 duyệt theo milestone có điều kiện; Cấp 3 từng mục — C3-3 chỉ dry-run,
    C3-11 chưa duyệt chi tiêu; không thay cấp quyền gốc."""
    items = {i["id"]: i for i in LEDGER["items"]}
    c2 = items["v31-cap2-milestone-packages-approved-2026-10-20"]
    c3 = items["v31-cap3-items-decided-2026-10-20"]
    assert c2["status"] == c3["status"] == "active" and c2["replaces"] is None and c3["replaces"] is None
    for code in ("G2-1", "G2-2", "G2-3", "G2-4", "G2-5", "G2-6"):
        assert code in c2["text"], code
    for code in ("C3-0", "C3-1", "C3-2", "C3-3", "C3-4", "C3-5", "C3-11"):
        assert code in c3["text"], code
    assert "DRY-RUN" in c3["text"] and "CHƯA duyệt chi tiêu" in c3["text"]
    assert "không cấp quyền migration" in c2["keeps"]
    assert items["v31-permission-tiers-2026-10-20"]["status"] == "active"
