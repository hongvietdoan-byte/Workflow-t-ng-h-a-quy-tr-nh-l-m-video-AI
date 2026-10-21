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

ON = {"FEATURE_GEN_AUTH_SHADOW": "1"}
OFF = {"FEATURE_GEN_AUTH_SHADOW": "0"}
PRICING = {"per_image": {"m": 1.0, "x": 1.0}, "per_video_second": {}, "per_video_clip": {}}


@pytest.fixture(autouse=True)
def _fresh_pricing_cache():
    """Bảng giá cache 60 s ở cấp module (C-M63-FIX) — mỗi test bắt đầu sạch để mock load_pricing có hiệu lực. C-M63-FIX2: dọn cả lỗi /
    mã autoqc toàn cục của dự án giả 78 / 79 (không rò sang test khác)."""
    G._PRICING_CACHE.clear()
    yield
    G._PRICING_CACHE.clear()
    from core import autoqc
    for pid in (78, 79):
        autoqc._errors.pop(pid, None)
        autoqc._video_errors.pop(pid, None)
        for kind in ("image", "video"):
            autoqc._codes.pop((kind, pid), None)


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
         reject=None, note=None, tier=None, draft=None, parent=None, usd_q=None, call=None):
    """Một job đã có (lượt cũ) — created_at tăng dần."""
    _T[0] += 1
    at = f"2026-10-21T10:{_T[0]:02d}:00"
    cur = p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, retry_count, escalated, created_at, updated_at, task_seen,"
                         " task_unseen, external_id, origin, model, retry_reason, reject_reason, quality_tier, draft_job_id, parent_job_id,"
                         " sent_package) VALUES (?,?,?,?,?,0,?,?,0,0,?,?,?,?,?,?,?,?,?)",
                         (pid, sid, kind, state, retry_count, at, at, ext, origin, model, reason, reject, tier, draft, parent,
                          json.dumps({"call": call}) if call else None))
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
    _job(p, pid, sid, kind="video_gen", model="seedance25", tier="final", draft=draft, call="submit_final_from_sample")   # Q1: nâng
    d = _auth(p, _job(p, pid, sid, kind="video_gen", ext=None, state="queued", model="seedance25"), tmp_path)
    assert d.attempts_used == 1 and "ATTEMPTS_EXHAUSTED" not in d.codes
    _job(p, pid, sid, kind="video_gen", model="seedance25")
    up = _job(p, pid, sid, kind="video_gen", ext=None, state="queued", model="seedance25", tier="final", draft=draft)
    d = _auth(p, up, tmp_path, upgrade=True)                                                   # runner: upgrade = có _from_sample
    assert "ATTEMPTS_EXHAUSTED" not in d.codes and d.counted is False
    again = _job(p, pid, sid, kind="video_gen", ext=None, state="queued", model="seedance25")
    assert _auth(p, again, tmp_path).code == "ATTEMPTS_EXHAUSTED"


def test_final_made_new_is_a_counted_attempt(tmp_path):
    """Rà: bản cao gen MỚI (nháp không nâng được) là lượt đắt nhất — có tính, không phải 'nâng nháp'."""
    p, pid, (sid,) = _setup(tmp_path)
    draft = _job(p, pid, sid, kind="video_gen", model="seedance25", tier="draft")
    _job(p, pid, sid, kind="video_gen", model="seedance25", tier="final", draft=draft, call="submit")
    assert len(G.attempts(p.conn, sid, "video_gen")) == 2
    new_final = _job(p, pid, sid, kind="video_gen", ext=None, state="queued", model="seedance25", tier="final", draft=draft)
    d = _auth(p, new_final, tmp_path, upgrade=False)
    assert d.code == "ATTEMPTS_EXHAUSTED" and d.counted is True


def test_not_created_is_not_counted_submit_unknown_is(tmp_path):
    """Rà: job not_created / submit_unknown sau resend thành CANCELLED — vẫn đọc ghi chú hỏng (mọi trạng thái)."""
    p, pid, (sid,) = _setup(tmp_path)
    nc = _job(p, pid, sid, state="cancelled", note="not_created: provider không tạo task")      # còn external_id provider trả
    _job(p, pid, sid, state="queued", ext=None, parent=nc, reason="gửi lại: nhà cung cấp không tạo task (1/2)")
    unknown = _job(p, pid, sid, ext=None, state="cancelled", note="submit_unknown: ConnectionError")
    assert [r["id"] for r in G.attempts(p.conn, sid, "image_gen")] == [unknown]             # chỉ job submit_unknown


def test_not_created_through_the_real_runner_path(tmp_path):
    from core.runner import ImageRunner as IR
    p, pid, (sid,) = _setup(tmp_path)
    jid = p.create_job(sid, "image_gen")
    r = IR(p, MockImageProvider(), str(tmp_path / "data"))
    r.submit_pending(pid)
    r._not_created(p.job(jid), "task never created")
    assert G.attempts(p.conn, sid, "image_gen") == []                                        # resend → cancelled, không tính


def test_relinked_send_counts_once(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    old = _job(p, pid, sid, ext="t-mat", state="cancelled", note="not_found: task không thấy")
    new = _job(p, pid, sid, ext="t-that", parent=old, reason="gửi lại: nhà cung cấp không tạo task (nối lại task thật t-that)")
    assert [r["id"] for r in G.attempts(p.conn, sid, "image_gen")] == [new]


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
    first1 = _job(p, pid, sids[1], usd_q=1, reject="mat_sai")
    _job(p, pid, sids[0], usd_q=0.5, origin="auto")                         # làm lại TỰ ĐỘNG đã chi 0,5
    _job(p, pid, sids[0], usd_q=3, retry_count=0)                           # EP tự bấm 3 USD: KHÔNG ăn ngân sách tự sửa (4d)
    new = _job(p, pid, sids[1], ext=None, state="queued", origin="auto", parent=first1)
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
    """reject_reason nằm trên job BỊ loại (cha) — lượt làm lại đọc nguyên nhân từ cha (rà: trước đọc job mới → luôn rỗng)."""
    p, pid, sids = _setup(tmp_path, shots=3)
    firsts = [_job(p, pid, sid, usd_q=1, state="rejected", reject="mat_sai") for sid in sids]
    for sid, f in zip(sids[:2], firsts[:2]):
        _job(p, pid, sid, origin="auto", parent=f, ext=None, state="queued")
    new = _job(p, pid, sids[2], ext=None, state="queued", origin="auto", parent=firsts[2])
    d = _auth(p, new, tmp_path)
    assert "SAME_CAUSE_STREAK" in d.codes and "NO_CAUSE" not in d.codes
    other_first = _job(p, pid, sids[2], usd_q=1, state="failed", note="tay_sai: 6 ngón")
    other = _job(p, pid, sids[2], ext=None, state="queued", origin="auto", parent=other_first)
    assert "SAME_CAUSE_STREAK" not in _auth(p, other, tmp_path).codes


def test_unverified_submit_duplicate_locked_change_no_cause_model(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    _job(p, pid, sid, usd_q=1)
    _job(p, pid, sid, ext=None, state="failed", note="submit_unknown: timeout")
    _job(p, pid, sid, ext="t2", state="running")
    p.conn.execute("INSERT INTO change_events (at, kind, project_id, scene_id, state, cost_usd, before, after) VALUES "
                   "('2026-10-21T12:00:00.000Z','scene',?,?,'reviewed',0,?,?)",
                   (pid, sid, json.dumps({"byd": {"y_do": "a"}}), json.dumps({"byd": {"y_do": "b"}})))
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
    def _no_at(raw):                                                                         # "at" = giờ gửi (khác giây giữa 2 lần) — so phần còn lại
        import json as _j
        d = _j.loads(raw); d.pop("at", None); return d
    assert _no_at(p1.job(j1)["sent_package"]) == _no_at(p2.job(j2)["sent_package"])          # giữ byte gói gửi (trừ giờ gửi)
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


def test_prompt_rewrite_by_the_repair_loop_is_not_a_locked_change(tmp_path):
    """Rà: trigger ghi change_events cho MỌI lần ghi scenes.data — Đạo diễn viết lại image_prompt (chính bước tự sửa) không phải
    đổi ý đồ."""
    p, pid, (sid,) = _setup(tmp_path)
    first = _job(p, pid, sid, usd_q=1, state="rejected", reject="mat_sai")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "rewritten by the Director"}), sid))
    p.conn.commit()
    new = _job(p, pid, sid, ext=None, state="queued", origin="auto", parent=first)
    assert "LOCKED_CHANGE" not in _auth(p, new, tmp_path).codes
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "x", "byd": {"y_do": "khác"}}), sid))
    p.conn.commit()
    d = _auth(p, new, tmp_path)
    assert "LOCKED_CHANGE" in d.codes and "byd" in d.reason_vi


def test_broken_pricing_is_not_a_zero_budget(tmp_path):
    p, pid, (sid,) = _setup(tmp_path)
    first = _job(p, pid, sid, usd_q=1, state="rejected", reject="mat_sai")
    new = _job(p, pid, sid, ext=None, state="queued", origin="auto", parent=first)
    with mock.patch("core.cost.load_pricing", return_value={"_error": "hỏng"}):
        d = G.authorize(p.conn, p.job(new), data_dir=str(tmp_path / "data"))
    assert "BUDGET_EXCEEDED" not in d.codes


def test_video_runner_records_the_model_really_sent(tmp_path, monkeypatch):
    """Rà: video model nằm ở đối số thứ 5 của submit (jobs.model chỉ ghi SAU khi gửi)."""
    from core.llm_io import approve_motion_prompt, store_motion_prompts
    from core.providers import MockVideoProvider
    from core.runner import VideoRunner
    monkeypatch.setenv("FEATURE_VIDEO_PREGEN", "0")
    p = Pipeline(connect(str(tmp_path / "v.sqlite")))
    pid = p.create_project("#63 video")
    sid = p.create_scene(pid, 1, "S1")
    img = p.create_job(sid)
    p.start(img)
    p.succeed(img)
    p.approve(img)
    store_motion_prompts(p, pid, {"scenes": [{"idx": 1, "motion_prompt": "slow push-in"}]})
    approve_motion_prompt(p, sid)
    vid = p.create_job(sid, "video_gen")
    sent = []

    class Prov(MockVideoProvider):
        def submit(self, *a, **k):
            sent.append(a[4] if len(a) > 4 else k.get("model"))
            return super().submit(*a, **k)
    with mock.patch.dict(os.environ, ON):
        VideoRunner(p, Prov(), str(tmp_path / "data")).submit_pending(pid)
    rows = G.read_shadow(str(tmp_path / "data"), pid)
    assert sent and rows and rows[0]["job_id"] == vid and rows[0]["model"] == sent[0] and rows[0]["model"]


def test_group_send_records_each_shot(tmp_path):
    p, pid, sids = _setup(tmp_path, shots=2)
    for _ in range(3):
        _job(p, pid, sids[1])                         # shot đi kèm đã hết lượt
    lead = _job(p, pid, sids[0], ext=None, state="queued")
    with mock.patch.dict(os.environ, ON), mock.patch.object(G, "_pricing", return_value=PRICING):
        d = G.shadow(p.conn, p.job(lead), data_dir=str(tmp_path / "data"), group=[sids[1]])
    rows = G.latest_per_job(G.read_shadow(str(tmp_path / "data"), pid))
    assert d.allow and {(r["scene_id"], r["code"]) for r in rows} == {(sids[0], "OK"), (sids[1], "ATTEMPTS_EXHAUSTED")}


def test_runner_calls_shadow_right_before_submit():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "runner.py"), encoding="utf-8").read()
    i = src.index("gen_auth.shadow(")
    assert src.index("_paused_now(job):                # M1.3 (G36") < i < src.index("task_id = self.provider.submit(*args, **sent_kwargs)")
    assert src.count("gen_auth.shadow(") == 1


def test_flag_registered_off_golden_and_areas():
    from core import features
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert features.FEATURES[G.FLAG]["verified"] is False
    with mock.patch.dict(os.environ, {"FEATURE_GEN_AUTH_SHADOW": ""}):
        assert features.default_state(G.FLAG) == "off"
    golden = json.load(open(os.path.join(root, "tests", "golden", "package_inputs.json"), encoding="utf-8"))
    assert all(golden[k]["flags"][G.FLAG] is False for k in ("image", "video"))
    areas = json.load(open(os.path.join(root, "devsys", "areas.json"), encoding="utf-8"))["areas"]
    a = next(a for a in areas if a["id"] == "core_infra")
    assert "core/gen_auth.py" in a["code"] and G.FLAG in a["flags"] and "tests/test_v31_m63_gen_auth.py" in a["tests"]


def test_flag_name_passes_the_golden_secret_filter():
    """Rà full suite: tên `generation_authorization` (đề bài) chứa 'authorization' → golden_capture._safe coi file cờ là trường nhạy
    cảm, từ chối CẢ bản chụp (test_golden_db_replay đỏ). Đổi tên gen_auth_shadow; mọi cờ trong catalog phải qua bộ lọc."""
    from core import features
    from tools.golden_capture import _safe
    _safe({name: False for name in features.FEATURES})


# ---- C-M63-FIX (rà phiên chính 22/10) ----------------------------------------------------------------------------------------------
def test_end_frames_send_writes_a_shadow_line(tmp_path):
    """Đường khung cuối gửi thẳng spend_gate.slot.send (không qua runner) — cờ bật: có dòng jsonl route end_frame, gửi vẫn đi."""
    import inspect
    from core import end_frames
    src = inspect.getsource(end_frames._tick)
    assert src.index("gen_auth.shadow_send(") < src.index("ext = slot.send(provider.submit")
    p, pid, (sid,) = _setup(tmp_path)
    with mock.patch.dict(os.environ, ON), mock.patch.object(G, "_pricing", return_value=PRICING):
        d = G.shadow_send(p.conn, project_id=pid, scene_id=sid, kind="image_gen", model="m", route="end_frame",
                          data_dir=str(tmp_path / "data"))
    rows = G.read_shadow(str(tmp_path / "data"), pid)
    assert d is not None and rows[-1]["route"] == "end_frame" and rows[-1]["scene_id"] == sid and rows[-1]["job_id"] is None
    with mock.patch.dict(os.environ, OFF):
        assert G.shadow_send(p.conn, project_id=pid, scene_id=sid, kind="image_gen", model="m", route="x",
                             data_dir=str(tmp_path / "data")) is None


def test_quality_sample_real_send_writes_a_shadow_line(tmp_path, monkeypatch):
    """Đường phép thử chất lượng (gửi thẳng, provider giả): cờ bật → dòng jsonl route quality_sample_draft TRƯỚC khi gửi; vẫn gửi."""
    from core import quality_samples as QS
    from core.providers import MockVideoProvider
    p, pid, (sid,) = _setup(tmp_path)
    monkeypatch.setenv("FEATURE_SEEDANCE_SAMPLE_MODE", "1")
    sent = []
    plan = {"image": str(tmp_path / "a.png"), "prompt": "p", "negative": None, "pictures": [], "reference_only": False}
    (tmp_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)

    class Prov(MockVideoProvider):
        def submit(self, *a, **k):
            sent.append(len(G.read_shadow(str(tmp_path / "data"), pid)))     # số dòng shadow lúc gửi
            return "task-1"
    with mock.patch.dict(os.environ, ON), mock.patch.object(G, "_pricing", return_value=PRICING), \
            mock.patch.object(QS, "plan", return_value=plan):
        QS.send(p, pid, sid, "draft", Prov(), str(tmp_path / "data"))
    rows = G.read_shadow(str(tmp_path / "data"), pid)
    assert sent == [1] and rows[0]["route"] == "quality_sample_draft" and rows[0]["scene_id"] == sid and rows[0]["kind"] == "video_gen"


def test_every_direct_paid_send_path_has_a_shadow_call():
    """Mọi `slot.send(provider.submit…)` thẳng (không qua runner) có gen_auth.shadow_send ngay trước trong cùng hàm."""
    import ast
    import inspect
    from core import costume, end_frames, experiments, lipsync, quality_samples, scene_establish
    for mod in (end_frames, quality_samples, lipsync, scene_establish, costume, experiments):
        src = inspect.getsource(mod)
        tree = ast.parse(src)
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            body = ast.get_source_segment(src, fn) or ""
            if "slot.send(provider.submit" in body:
                assert "gen_auth.shadow_send(" in body and body.index("gen_auth.shadow_send(") < body.index("slot.send(provider.submit"), \
                    (mod.__name__, fn.name)


def test_group_clip_sent_by_the_first_shot_counts_for_the_other_shot(tmp_path):
    """Clip nhóm Seedance do shot đầu gửi (sent_group) mang phần của shot sau — tính lượt cho shot sau; job đi kèm cùng task không đếm 2."""
    p, pid, sids = _setup(tmp_path, shots=2)
    group = json.dumps([{"id": sids[0]}, {"id": sids[1]}])
    for i in range(2):
        lead = _job(p, pid, sids[0], kind="video_gen", model="seedance25", ext=f"g{i}")
        p.conn.execute("UPDATE jobs SET sent_group=? WHERE id=?", (group, lead))
    _job(p, pid, sids[1], kind="video_gen", model="seedance25", ext="g1")              # đi kèm, nhận task của leader lượt 2
    p.conn.commit()
    assert len(G.attempts(p.conn, sids[1], "video_gen")) == 2
    new = _job(p, pid, sids[1], kind="video_gen", ext=None, state="queued", model="seedance25")
    assert _auth(p, new, tmp_path).code == "ATTEMPTS_EXHAUSTED"


def test_group_budget_is_computed_once_per_send(tmp_path):
    """Rà: ngân sách tự sửa tính MỘT lần cho cả lượt gửi nhóm (leader + shot đi kèm), không N lần trong SPEND_LOCK."""
    p, pid, sids = _setup(tmp_path, shots=3)
    for sid in sids:
        _job(p, pid, sid, usd_q=1, state="rejected", reject="mat_sai")
    lead = _job(p, pid, sids[0], ext=None, state="queued", origin="auto", parent=1)
    with mock.patch.dict(os.environ, ON), mock.patch.object(G, "_pricing", return_value=PRICING), \
            mock.patch.object(G, "_repair_budget", wraps=G._repair_budget) as inner:
        G.shadow(p.conn, p.job(lead), data_dir=str(tmp_path / "data"), group=sids[1:])
    assert inner.call_count == 1


def test_leader_cost_is_counted_once_in_the_budget(tmp_path):
    """Rà: clip nhóm tính lượt cho nhiều shot — khoản chi của job leader chỉ vào lượt đầu, không vào cả làm lại của shot đi kèm."""
    p, pid, sids = _setup(tmp_path, shots=2)
    _job(p, pid, sids[1], kind="image_gen", usd_q=1)
    _job(p, pid, sids[1], usd_q=1)                                    # shot 2 đã có lượt riêng
    lead = _job(p, pid, sids[0], usd_q=2, origin="auto")
    p.conn.execute("UPDATE jobs SET sent_group=? WHERE id=?", (json.dumps([{"id": sids[0]}, {"id": sids[1]}]), lead))
    p.conn.commit()
    b = G.repair_budget(p.conn, pid, pricing=PRICING)
    assert b["first_usd"] + b["repair_usd"] <= 4.0 and b["repair_usd"] == 0.0     # leader (2 USD) chỉ ở lượt đầu


def test_direct_route_is_recorded_not_counted_and_sees_a_running_job(tmp_path):
    """Rà: đường gửi thẳng không phải lượt làm lại của shot → không ATTEMPTS / NO_CAUSE / BUDGET / MODEL giả (khớp môi model riêng);
    job đang chạy của shot → DUPLICATE_INFLIGHT (trước: job giả id None làm `id<>NULL` luôn sai)."""
    p, pid, (sid,) = _setup(tmp_path)
    for _ in range(3):
        _job(p, pid, sid, usd_q=1)
    _job(p, pid, sid, ext="t-run", state="running")
    with mock.patch.dict(os.environ, ON), mock.patch.object(G, "_pricing", return_value=PRICING):
        d = G.shadow_send(p.conn, project_id=pid, scene_id=sid, kind="video_gen", model="lipsync-2-pro", route="lipsync",
                          data_dir=str(tmp_path / "data"))
        e = G.shadow_send(p.conn, project_id=pid, scene_id=sid, kind="image_gen", model="m", route="end_frame",
                          data_dir=str(tmp_path / "data"))
    assert d.codes == [] and d.counted is False and not d.needs_ep
    assert e.codes == ["DUPLICATE_INFLIGHT"] and not e.needs_ep
    rows = G.latest_per_job(G.read_shadow(str(tmp_path / "data"), pid))
    assert {r["route"] for r in rows} == {"lipsync", "end_frame"}                 # không gộp theo (None, shot)


def test_pricing_is_loaded_once_per_ttl():
    G._PRICING_CACHE.clear()
    with mock.patch("core.cost.load_pricing", return_value=PRICING) as load:
        G._pricing()
        G._pricing()
    assert load.call_count == 1
    G._PRICING_CACHE.clear()


def test_autoqc_stop_code_is_cleared_by_a_new_run_and_by_clear():
    """M7.4 rà: mã dừng Claude không bao giờ xóa → mọi lần kẹt sau báo nhầm 'Claude không dùng được'."""
    from core import autoqc
    with mock.patch("core.diag.record"):
        autoqc._fail(None, 78, "hết hạn mức", code="usage_limit")
        assert autoqc.last_error_code("image", 78) == "usage_limit"
        autoqc._fail(None, 78, "JSON hỏng")                                         # dừng vì lỗi khác: không giữ mã cũ
        assert autoqc.last_error_code("image", 78) is None
    autoqc._codes[("video", 78)] = "usage_limit"                                      # C-M63-FIX2: _codes giữ CHUỖI
    autoqc.clear_video_error(78)
    assert autoqc.last_error_code("video", 78) is None
    autoqc._codes[("image", 79)] = "usage_limit"
    with mock.patch.object(autoqc, "connect", side_effect=RuntimeError("stop after the clear")), mock.patch("core.diag.record"):
        autoqc._work(":memory:", "data", 79, lambda: None)
    assert autoqc.last_error_code("image", 79) is None



# ---- C-M63-FIX2 (rà kỹ C-M63-FIX 22/10) --------------------------------------------------------------------------------------------
def test_attempts_reads_the_project_once_not_two_table_scans_per_shot(tmp_path):
    """VỪA 1: _repair_budget gọi attempts cho từng (shot, loại) — mỗi lần 2 câu quét toàn bảng jobs (không chỉ mục) trong SPEND_LOCK.
    Nay đọc job của dự án MỘT lần: số câu SQL không tăng theo số shot."""
    counts = {}
    for n in (2, 8):
        (tmp_path / f"n{n}").mkdir()
        p, pid, sids = _setup(tmp_path / f"n{n}", shots=n)
        for sid in sids:
            _job(p, pid, sid, usd_q=1)
            _job(p, pid, sid, usd_q=1, origin="auto")
        stmts = []
        p.conn.set_trace_callback(stmts.append)
        b = G.repair_budget(p.conn, pid, pricing=PRICING)
        p.conn.set_trace_callback(None)
        counts[n] = len([x for x in stmts if x.lstrip().upper().startswith("SELECT") and "FROM JOBS" in x.upper()])
        assert b["first_usd"] == n and b["repair_usd"] == n
    assert counts[8] == counts[2], counts


def test_group_resend_that_is_another_shots_first_take_counts_as_repair(tmp_path):
    """THẤP 4: clip nhóm gửi lại (tự động) của shot A mà là lượt đầu của shot B — trước vào 'lượt đầu' → ngân sách phình 40 %; nay
    vào bên làm lại (thận trọng tiền)."""
    p, pid, sids = _setup(tmp_path, shots=2)
    _job(p, pid, sids[0], kind="video_gen", usd_q=1)                                     # lượt đầu của A (riêng)
    regroup = _job(p, pid, sids[0], kind="video_gen", usd_q=1, origin="auto", ext="grp")  # A gửi lại cả nhóm: lượt 2 của A, lượt 1 của B
    p.conn.execute("UPDATE jobs SET sent_group=? WHERE id=?", (json.dumps([{"id": sids[0]}, {"id": sids[1]}]), regroup))
    _job(p, pid, sids[1], kind="video_gen", ext=None, state="queued")                    # B có job riêng (đi kèm, chưa nhận task)
    p.conn.commit()
    with mock.patch("core.budget.row_usd", side_effect=lambda pr, r: float(r["quantity"])):
        b = G.repair_budget(p.conn, pid, pricing=PRICING)
    assert b["repair_usd"] == 1.0 and b["first_usd"] == 1.0


def test_busy_sees_a_running_group_clip_carrying_this_shot(tmp_path):
    """THẤP 5: clip NHÓM đang chạy (shot đầu gửi, sent_group chứa shot này) = shot đang có job chạy (như runner._covered)."""
    p, pid, sids = _setup(tmp_path, shots=2)
    lead = _job(p, pid, sids[0], kind="video_gen", state="running", ext="g")
    p.conn.execute("UPDATE jobs SET sent_group=? WHERE id=?", (json.dumps([{"id": sids[0]}, {"id": sids[1]}]), lead))
    p.conn.commit()
    assert G._busy(p.conn, sids[1], "video_gen", None) == lead


def test_end_frames_flag_off_never_asks_the_provider_for_usage_info(tmp_path):
    """THẤP 2: model của dòng shadow (`_usage_model(provider)` = provider.usage_info()) chỉ tính khi cờ BẬT."""
    import inspect
    from core import end_frames
    src = inspect.getsource(end_frames._tick)
    i = src.index("gen_auth.shadow_send(")
    assert "if gen_auth.enabled():" in src[i - 200:i]


def test_quality_sample_shadow_error_never_leaves_the_entry_sending(tmp_path, monkeypatch):
    """THẤP 3: cổng shadow ném lỗi (vd đọc cờ hỏng) sau khi mục đã lưu 'sending' — trước: ném ra ngoài, mục kẹt + ăn trần 4 USD."""
    from core import quality_samples as QS
    from core.providers import MockVideoProvider
    p, pid, (sid,) = _setup(tmp_path)
    monkeypatch.setenv("FEATURE_SEEDANCE_SAMPLE_MODE", "1")
    plan = {"image": str(tmp_path / "a.png"), "prompt": "p", "negative": None, "pictures": [], "reference_only": False}
    (tmp_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)

    class Prov(MockVideoProvider):
        def submit(self, *a, **k):
            return "task-1"
    with mock.patch.object(G, "shadow_send", side_effect=RuntimeError("cờ hỏng")), mock.patch.object(QS, "plan", return_value=plan):
        entry = QS.send(p, pid, sid, "draft", Prov(), str(tmp_path / "data"))
    assert entry["state"] == "running" and entry["external_id"] == "task-1"


def test_end_frames_real_send_with_the_flag_on_writes_a_shadow_line(tmp_path):
    """Qua ĐƯỜNG GỬI THẬT (end_frames.tick, provider giả, cờ BẬT): dòng jsonl route end_frame TRƯỚC khi gửi; vẫn gửi."""
    import tempfile
    from core import end_frames, llm_runner
    from tests.test_end_frames import _shot_with_end_state
    from tests.test_v3 import _approve_all_images, kenta_project
    with mock.patch.dict(os.environ, {"FEATURE_SEEDANCE_REF_GROUPS": "0", "FEATURE_END_FRAMES": "1", **ON}):
        p, pid = kenta_project()
        llm_runner.run_director(p, pid, llm_runner.MockLlm())
        sid = _shot_with_end_state(p, pid)
        data = tempfile.mkdtemp()
        _approve_all_images(p, pid, data)
        assert sid in end_frames.queue(p, pid)
        seen = []

        class Prov(MockImageProvider):
            def submit(self, *a, **k):
                seen.append(len(G.read_shadow(data, pid)))
                return super().submit(*a, **k)
        end_frames.tick(p, pid, Prov(), data)
    rows = [r for r in G.read_shadow(data, pid) if r.get("route") == "end_frame"]
    assert seen and seen[0] >= 1 and rows and rows[0]["scene_id"] == sid
