"""V3.1 M6.3 Generation Authorization SHADOW (cloud-C, Gói M6-A — sổ v31-ep-m6-pack-a-approved-2026-10-21): `core/gen_auth.shadow` gọi
NGAY trước provider.submit trong runner._submit_pending, chỉ GHI quyết định (cho phép / sẽ chặn + lý do) vào
<data>/<pid>/crew/gen_auth_shadow.jsonl — không chặn, không ghi CSDL, không đổi gói gửi. Bộ đếm lượt không đặt lại khi sửa prompt /
đổi model / restart / người bấm. Không API: provider giả."""
import json
import os
from unittest import mock

import pytest

from core import gen_auth as G
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockImageProvider
from core.runner import ImageRunner

ON = {"FEATURE_GENERATION_AUTHORIZATION": "1"}
OFF = {"FEATURE_GENERATION_AUTHORIZATION": "0"}
PRICING = {"per_image": {"m": 1.0, "x": 1.0}, "per_video_second": {}, "per_video_clip": {}}


def _setup(tmp_path, shots=1):
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("#63 thử")
    p.conn.execute("UPDATE projects SET image_model='m' WHERE id=?", (pid,))
    sids = []
    for i in range(1, shots + 1):
        sid = p.create_scene(pid, i, f"S{i}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": f"a hero on a rooftop {i}"}), sid))
        sids.append(sid)
    p.conn.commit()
    return p, pid, sids


_T = [0]


def _job(p, pid, sid, *, kind="image_gen", ext="t", state="approved", origin=None, model="m", retry_count=0, reason=None,
         reject=None, note=None, tier=None, draft=None, parent=None, usd_q=None):
    """Một job đã có (lượt cũ) — created_at tăng dần."""
    _T[0] += 1
    at = f"2026-10-21T10:{_T[0]:02d}:00"
    cur = p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, retry_count, escalated, created_at, updated_at, task_seen,"
                         " task_unseen, external_id, origin, model, retry_reason, reject_reason, quality_tier, draft_job_id, parent_job_id)"
                         " VALUES (?,?,?,?,?,0,?,?,0,0,?,?,?,?,?,?,?,?)",
                         (pid, sid, kind, state, retry_count, at, at, ext, origin, model, reason, reject, tier, draft, parent))
    jid = cur.lastrowid
    if note:
        p.conn.execute("INSERT INTO job_events (job_id, from_state, to_state, actor, note, at) VALUES (?,?,?,?,?,?)",
                       (jid, "running", "failed", "system", note, at))
    if usd_q is not None:
        p.conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at) "
                       "VALUES (?,?,'image','deepix',?,'',?,'image',?)", (jid, pid, model, usd_q, at))
    p.conn.commit()
    return jid


def _auth(p, jid, tmp_path, **kw):
    with mock.patch.object(G, "_pricing", return_value=PRICING):
        return G.authorize(p.conn, p.job(jid), data_dir=str(tmp_path / "data"), **kw)


# ---- trần lượt: tính chung, không đặt lại ------------------------------------------------------------------------------------------
def test_fourth_image_attempt_would_be_blocked_and_counter_never_resets(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    for i in range(3):
        _job(p, pid, sid, model="m" if i < 2 else "x", retry_count=0, reason="người sửa prompt" if i else None)   # đổi model + người bấm
    new = _job(p, pid, sid, ext=None, state="queued", retry_count=0)                       # retry_count=0 (người bấm) — vẫn tính
    d = _auth(p, new, tmp_path)
    assert d.allow is False and d.code == "ATTEMPTS_EXHAUSTED" and d.attempts_used == 3 and d.attempts_limit == 3
    assert d.needs_ep and "EP xác nhận vượt" in d.reason_vi                                 # Q2: EP bấm → EP xác nhận vượt


def test_third_image_attempt_is_allowed(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    _job(p, pid, sid)
    _job(p, pid, sid)
    d = _auth(p, _job(p, pid, sid, ext=None, state="queued"), tmp_path)
    assert d.allow and d.code == "OK" and d.attempts_used == 2


def test_video_limit_two_and_upgrade_from_draft_not_counted(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    draft = _job(p, pid, sid, kind="video_gen", model="seedance25", tier="draft")
    _job(p, pid, sid, kind="video_gen", model="seedance25", tier="final", draft=draft)          # Q1: nâng 1080p — không tính
    d = _auth(p, _job(p, pid, sid, kind="video_gen", ext=None, state="queued", model="seedance25"), tmp_path)
    assert d.attempts_used == 1 and "ATTEMPTS_EXHAUSTED" not in d.codes
    _job(p, pid, sid, kind="video_gen", model="seedance25")
    up = _job(p, pid, sid, kind="video_gen", ext=None, state="queued", model="seedance25", tier="final", draft=draft)
    assert "ATTEMPTS_EXHAUSTED" not in _auth(p, up, tmp_path).codes and _auth(p, up, tmp_path).counted is False
    again = _job(p, pid, sid, kind="video_gen", ext=None, state="queued", model="seedance25")
    assert _auth(p, again, tmp_path).code == "ATTEMPTS_EXHAUSTED"


def test_not_created_is_not_counted_submit_unknown_is(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    _job(p, pid, sid, state="failed", note="not_created: provider không tạo task")
    unknown = _job(p, pid, sid, ext=None, state="failed", note="submit_unknown: ConnectionError")
    assert [r["id"] for r in G.attempts(p.conn, sid, "image_gen")] == [unknown]             # chỉ job submit_unknown


def test_ep_grant_starts_a_new_cycle(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    for _ in range(3):
        _job(p, pid, sid)
    folder = tmp_path / "data" / str(pid) / "crew"
    folder.mkdir(parents=True)
    (folder / "grants.jsonl").write_text(json.dumps({"scene_id": sid, "kind": "image_gen", "at": "2026-10-21T11:00:00", "by": "EP",
                                                     "reason": "đổi ý đồ"}) + "\n", encoding="utf-8")
    d = _auth(p, _job(p, pid, sid, ext=None, state="queued"), tmp_path)
    assert d.allow and d.attempts_used == 0


# ---- điều kiện tự sửa ------------------------------------------------------------------------------------------------------------------
def test_auto_repair_over_40_percent_budget(tmp_path):
    p, pid, sids = _setup(tmp_path, shots=2)
    _job(p, pid, sids[0], usd_q=1)                    # lượt đầu 2 × 1 USD = 2 USD → ngân sách 0,8 USD
    _job(p, pid, sids[1], usd_q=1)
    _job(p, pid, sids[0], usd_q=0.5, origin="auto", reject="mat_sai")       # làm lại đã chi 0,5
    new = _job(p, pid, sids[1], ext=None, state="queued", origin="auto", reject="mat_sai")
    d = _auth(p, new, tmp_path)
    assert "BUDGET_EXCEEDED" in d.codes and d.budget_left_usd == pytest.approx(0.3) and d.needs_ep
    b = G.repair_budget(p.conn, pid, pricing=PRICING)
    assert (b["first_usd"], b["repair_usd"], b["limit_usd"]) == (2.0, 0.5, 0.8)
    p.conn.execute("INSERT INTO app_settings (key, value) VALUES (?, '1.0')", (f"gen_auth_repair_pct:{pid}",))   # EP đổi tỷ lệ
    assert "BUDGET_EXCEEDED" not in _auth(p, new, tmp_path).codes


def test_person_click_is_not_budget_capped(tmp_path):
    """D01b: ngân sách tự sửa chỉ giới hạn việc TỰ ĐỘNG — EP bấm vẫn chỉ trừ lượt."""
    p, pid, (sid,) = _setup(tmp_path)
    _job(p, pid, sid, usd_q=1)
    _job(p, pid, sid, usd_q=5)
    d = _auth(p, _job(p, pid, sid, ext=None, state="queued"), tmp_path)
    assert d.allow and d.budget_left_usd is None


def test_three_shots_same_cause_stop_self_repair(tmp_path):
    p, pid, sids = _setup(tmp_path, shots=3)
    for sid in sids:
        _job(p, pid, sid, usd_q=1)
    for sid in sids[:2]:
        _job(p, pid, sid, origin="auto", parent=1, reject="mat_sai", ext=None, state="queued")
    new = _job(p, pid, sids[2], ext=None, state="queued", origin="auto", parent=1, reject="mat_sai")
    assert "SAME_CAUSE_STREAK" in _auth(p, new, tmp_path).codes
    other = _job(p, pid, sids[2], ext=None, state="queued", origin="auto", parent=1, reject="tay_sai")
    assert "SAME_CAUSE_STREAK" not in _auth(p, other, tmp_path).codes


def test_unverified_submit_duplicate_locked_change_no_cause_model(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    _job(p, pid, sid, usd_q=1)
    _job(p, pid, sid, ext=None, state="failed", note="submit_unknown: timeout")
    _job(p, pid, sid, ext="t2", state="running")
    p.conn.execute("INSERT INTO change_events (at, kind, project_id, scene_id, state, cost_usd) VALUES ('2026-10-21T12:00:00','scene',?,?,"
                   "'reviewed',0)", (pid, sid))
    p.conn.commit()
    new = _job(p, pid, sid, ext=None, state="queued", origin="auto", model="z")
    d = _auth(p, new, tmp_path)
    assert {"PROVIDER_UNVERIFIED", "DUPLICATE_INFLIGHT", "LOCKED_CHANGE", "NO_CAUSE", "MODEL_NOT_APPROVED"} <= set(d.codes)
    assert set(d.codes) <= set(G.CODES) and d.allow is False


# ---- đường gửi thật: shadow ghi, không chặn, không đổi gói ------------------------------------------------------------------------------
class Counting(MockImageProvider):
    def __init__(self):
        super().__init__()
        self.sent = 0

    def submit(self, *a, **k):
        self.sent += 1
        return super().submit(*a, **k)


def _send(tmp_path, env, prior=0):
    tmp_path.mkdir(parents=True, exist_ok=True)
    p, pid, (sid,) = _setup(tmp_path)
    for _ in range(prior):
        _job(p, pid, sid)
    jid = p.create_job(sid, "image_gen")
    prov = Counting()
    r = ImageRunner(p, prov, str(tmp_path / "data"))
    with mock.patch.dict(os.environ, env):
        r.submit_pending(pid)
    return p, pid, jid, prov


def test_flag_on_records_but_never_blocks_and_package_is_byte_identical(tmp_path):
    p1, pid1, j1, prov1 = _send(tmp_path / "off", OFF, prior=3)
    p2, pid2, j2, prov2 = _send(tmp_path / "on", ON, prior=3)
    assert prov1.sent == prov2.sent == 1                                                     # vượt trần vẫn GỬI (shadow)
    assert p1.job(j1)["sent_package"] == p2.job(j2)["sent_package"]                          # giữ byte gói gửi
    assert not (tmp_path / "off" / "data" / str(pid1) / "crew").exists()                     # cờ tắt: không ghi gì
    rows = G.read_shadow(str(tmp_path / "on" / "data"), pid2)
    assert len(rows) == 1 and rows[0]["job_id"] == j2 and rows[0]["code"] == "ATTEMPTS_EXHAUSTED" and rows[0]["allow"] is False


def test_shadow_failure_never_breaks_the_send(tmp_path, capsys):
    with mock.patch.object(G, "authorize", side_effect=RuntimeError("hỏng")):
        p, pid, jid, prov = _send(tmp_path, ON)
    assert prov.sent == 1 and p.job(jid)["external_id"] and "[gen_auth] shadow lỗi" in capsys.readouterr().err


def test_shadow_writes_no_database_row(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    jid = _job(p, pid, sid, ext=None, state="queued")
    before = p.conn.total_changes
    with mock.patch.dict(os.environ, ON), mock.patch.object(G, "_pricing", return_value=PRICING):
        d = G.shadow(p.conn, p.job(jid), data_dir=str(tmp_path / "data"))
    assert d is not None and d.allow and p.conn.total_changes == before


def test_runner_calls_shadow_right_before_submit():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "runner.py"), encoding="utf-8").read()
    i = src.index("gen_auth.shadow(")
    assert src.index("_paused_now(job):                # M1.3 (G36") < i < src.index("task_id = self.provider.submit(*args, **sent_kwargs)")
    assert src.count("gen_auth.shadow(") == 1


def test_flag_registered_off_golden_and_areas():
    from core import features
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert features.FEATURES[G.FLAG]["verified"] is False
    with mock.patch.dict(os.environ, {"FEATURE_GENERATION_AUTHORIZATION": ""}):
        assert features.FEATURES[G.FLAG].get("default", False) is False
    golden = json.load(open(os.path.join(root, "tests", "golden", "package_inputs.json"), encoding="utf-8"))
    assert all(golden[k]["flags"][G.FLAG] is False for k in ("image", "video"))
    areas = json.load(open(os.path.join(root, "devsys", "areas.json"), encoding="utf-8"))["areas"]
    a = next(a for a in areas if a["id"] == "core_infra")
    assert "core/gen_auth.py" in a["code"] and G.FLAG in a["flags"] and "tests/test_v31_m63_gen_auth.py" in a["tests"]
