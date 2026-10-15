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
    p, _, sid = _pipeline_with_shot({"difficulty": "easy"})
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


CHECKS = {k: v for k, v in globals().items() if k.startswith("check_") and callable(v)}


# ---- sổ hợp lệ -----------------------------------------------------------------------------------------------------------------
def test_ledger_in_git_tree_and_valid():
    assert os.path.abspath(D.PATH) == os.path.join(ROOT, "data", "decisions.json")
    assert D.problems(LEDGER) == []
    assert any(i["status"] == "active" for i in LEDGER["items"])


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
