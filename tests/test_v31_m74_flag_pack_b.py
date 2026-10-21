"""V3.1 M7.4 (C-M74, cloud-C 21/10) — Gói B sửa cờ (docs/KE_HOACH_SUA_20_CO_2026-10-21.md mục 2, bằng chứng docs/BANG_CHUNG_CHOT_CO_2026-10-21.md
2.4.3). KHÔNG khóa cờ nào. Mỗi cờ một commit + test. B7 (release_gate × final_black_freeze) ở tests/test_v31_dp6_release_gate.py."""
import os
from unittest import mock

import pytest

from core import before_run, features
from core.db import connect
from core.pipeline import Pipeline


@pytest.fixture
def conn(tmp_path):
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    return p.conn


# ---- B2: dialogue_take 🔒 cần lip_sync (mặc định TẮT) → khóa giả ---------------------------------------------------------------------
def test_b2_locked_flag_without_its_parent_is_said_before_the_run(conn, monkeypatch):
    monkeypatch.setattr(features, "_TEST_BYPASS", False)                    # khóa thật: dialogue_take 🔒 BẬT
    with mock.patch.dict(os.environ, {"FEATURE_LIP_SYNC": "0"}):
        items = before_run._cost_items(conn)
    hit = [i for i in items if "dialogue_take" in i["text"]]
    assert hit and hit[0]["level"] == "vang" and hit[0]["text"].startswith("🔒") and "lip_sync" in hit[0]["text"]
    assert "lip-sync-lock-after-real-run" in hit[0]["text"]
    with mock.patch.dict(os.environ, {"FEATURE_LIP_SYNC": "1"}):
        assert not [i for i in before_run._cost_items(conn) if "dialogue_take" in i["text"]]


def test_b2_no_flag_is_locked_on_top_of_an_unlocked_parent_except_the_decided_one():
    """Cờ 🔒 không được có cha trong REQUIRES chưa 🔒 — ngoại lệ đã ghi sổ: dialogue_take → lip_sync (khóa lip_sync chờ chạy thật)."""
    bad = {k: [n for n in needs if not features.FEATURES[n]["verified"]] for k, needs in features.REQUIRES.items()
           if features.FEATURES.get(k, {}).get("verified")}
    assert {k: v for k, v in bad.items() if v} == {"dialogue_take": ["lip_sync"]}


# ---- B8: travel_truth ↔ stage_camera — hai nguồn quyết máy vào plate_camera.plan_cameras; thứ tự chưa có test ------------------------
def _shot(sid, stage=None):
    d = {"size": "MS", "story_scene": 1, "action": "Kelly chạy từ cửa tới bàn"}
    if stage:
        d["stage_camera"] = stage
    return {"id": sid, "data": d}


def test_b8_approved_stage_camera_wins_over_the_travel_route():
    from core import plate_camera as pc
    stage = {"location": [0.0, -4.0, 1.5], "look_at": [0.0, 0.0, 1.2], "lens": 35, "source": "stage_v2"}
    route = {"mode": "lead", "a": [0.0, 0.0, 0.0], "b": [0.0, 6.0, 0.0]}
    cams = pc.plan_cameras([_shot(1, stage), _shot(2)], lambda s: ([0.0, 0.0, 0.0], 0.0), lambda s: 1.7,
                           stage_field=pc.STAGE_FIELD, travel_of=lambda s: route)
    assert cams[1]["camera"]["location"] == stage["location"]                 # máy sân khấu đã duyệt dùng NGUYÊN
    alone = pc.travel_camera(_shot(2)["data"], [0.0, 0.0, 0.0], route["a"], route["b"], route["mode"], 1.7, 9 / 16, name="shot_2")
    if alone is not None:
        assert cams[2]["camera"]["location"] == alone["camera"]["location"]   # shot không có máy sân khấu → theo đường chạy
    cams_off = pc.plan_cameras([_shot(1, stage)], lambda s: ([0.0, 0.0, 0.0], 0.0), lambda s: 1.7, stage_field=None,
                               travel_of=lambda s: route)
    assert cams_off[1]["camera"]["location"] != stage["location"]             # stage_camera TẮT → không dùng máy sân khấu


# ---- two_tier_quality: nhãn theo quyết định 15/10 + nghiệm thu F-Q4 (±5 % đủ phát sinh + chất lượng) --------------------------------
def test_two_tier_label_no_longer_says_every_shot_is_drafted():
    label = features.FEATURES["two_tier_quality"]["label"]
    assert "MỌI shot" not in label and "DỄ đi thẳng 720p" in label and "two_tier_acceptance" in label


EST = {"usd": 10.0, "scenes": [{"scene_id": 1}, {"scene_id": 2}], "unknown": []}


def _jobs(*states_by_scene):
    out, jid = [], 1
    for sid, states in enumerate(states_by_scene, 1):
        for st in states:
            out.append({"id": jid, "scene_id": sid, "state": st})
            jid += 1
    return out


def test_acceptance_within_5_percent_with_retries_counted():
    from core import quality_tier as Q
    rows = [{"job_id": 1, "quality_tier": "final", "actual_usd": 5.1}, {"job_id": 2, "quality_tier": "final", "actual_usd": 4.3},
            {"job_id": 3, "quality_tier": "final", "actual_usd": 0.9}, {"job_id": 9, "quality_tier": "draft", "actual_usd": 3.0}]
    res = Q.acceptance(EST, rows, _jobs(["approved"], ["rejected", "approved"]))
    assert res["actual_usd"] == 10.3 and res["diff_pct"] == 3.0 and res["cost_ok"] is True       # nháp không tính; gen lại tính
    assert res["first_try_share"] == 0.5 and res["quality_ok"] is False and res["ok"] is False   # 1/2 cảnh duyệt ngay < 80 %


def test_acceptance_over_5_percent_fails_and_unknown_is_never_a_pass():
    from core import quality_tier as Q
    rows = [{"job_id": 1, "quality_tier": "final", "actual_usd": 12.4}]
    assert Q.acceptance(EST, rows, _jobs(["approved"], ["approved"]))["cost_ok"] is False         # +24 % (P33-A7)
    res = Q.acceptance(EST, [{"job_id": 1, "quality_tier": "final", "actual_usd": None}], _jobs(["approved"]))
    assert res["cost_ok"] is None and res["ok"] is False and res["cost_why"]
    res = Q.acceptance(dict(EST, unknown=[3]), rows, _jobs(["approved"]))
    assert res["cost_ok"] is None


def test_acceptance_regen_cap_and_all_good():
    from core import quality_tier as Q
    rows = [{"job_id": i, "quality_tier": "final", "actual_usd": 2.5} for i in range(1, 5)]
    assert Q.acceptance(EST, rows, _jobs(["rejected", "rejected", "approved"], ["approved"]))["over_regen_scenes"] == [1]
    good = Q.acceptance(EST, rows, _jobs(["approved"], ["approved"]))
    assert good["ok"] is True and good["diff_pct"] == 0.0


def test_acceptance_tool_snapshot_then_check(tmp_path, capsys):
    import json
    from core.db import connect
    from core.pipeline import Pipeline
    from tools import two_tier_acceptance as T
    db = str(tmp_path / "m.sqlite")
    p = Pipeline(connect(db))
    pid = p.create_project("t")
    p.conn.close()
    data = str(tmp_path / "projects")
    with mock.patch("core.quality_tier.final_estimate", return_value=dict(EST)):
        assert T.main(["--project", str(pid), "--db", db, "--data-dir", data, "--snapshot"]) == 0
    rec = tmp_path / "rec.json"
    rec.write_text(json.dumps({"rows": [{"project_id": pid, "job_id": 1, "quality_tier": "final", "actual_usd": 10.0}]}), encoding="utf-8")
    assert T.main(["--project", str(pid), "--db", db, "--data-dir", data, "--reconcile", str(rec)]) == 2   # chưa có job final → KHÔNG RÕ


# ---- motion_consistency_lint: luật VÀNG giu_yen (G51 — clip đơ / giữ tư thế mà lint không bắt) -------------------------------------
LINT_ON = {"FEATURE_MOTION_CONSISTENCY_LINT": "1"}


@pytest.mark.parametrize("prompt", [
    "Kelly raises the rifle, then holds still, poised, staring at the doorway.",
    "Max pauses for 2 seconds in the doorway.",
    "The soldier remains motionless behind the crate while smoke drifts.",
])
def test_giu_yen_long_hold_without_a_next_action_is_yellow(prompt):
    from core import prompt_formula as PF
    with mock.patch.dict(os.environ, LINT_ON):
        got = PF.hold_issues(prompt, {"duration_s": 5})
    assert got and got[0]["part"] == "giu_yen" and got[0]["level"] == "warn"


@pytest.mark.parametrize("prompt", [
    "Kelly holds still for a beat, then sprints to the left and dives behind the wall.",
    "Kelly runs to the door. It ends with Kelly holding the rifle, poised.",
    "Max pauses for 1 second.",
])
def test_giu_yen_short_or_followed_hold_is_fine(prompt):
    from core import prompt_formula as PF
    with mock.patch.dict(os.environ, LINT_ON):
        assert PF.hold_issues(prompt, {"duration_s": 5}) == []


def test_giu_yen_flag_off_says_nothing():
    from core import prompt_formula as PF
    with mock.patch.dict(os.environ, {"FEATURE_MOTION_CONSISTENCY_LINT": "0"}):
        assert PF.hold_issues("Max remains motionless.", {"duration_s": 5}) == []


# ---- end_frames: khai tiền + why không còn nói "chỉ chạy bóng" khi máy chính BẬT thật -----------------------------------------------
def test_end_frames_declares_its_cost_and_its_two_modes():
    meta = features.FEATURES["end_frames"]
    assert meta["costs"] is True and meta["trainee"] is True
    assert "BẬT thật" in meta["why"] and "học việc" in meta["why"]
    assert before_run.costly_fix_flag("end_frames")                         # nút "Bật các cờ sửa lỗi" không bật hàng loạt


# ---- bg_autoqc (P31-G57: bg_autoqc_stuck 29 lần): lý do kẹt — Claude không dùng được / chờ đủ khung (im) / khác ------------------------
def _bg_project(tmp_path, shots=1):
    import json
    from core.db import connect as _c
    from core.pipeline import Pipeline as _P
    db = str(tmp_path / "bg.sqlite")
    p = _P(_c(db))
    pid = p.create_project("bg")
    for i in range(1, shots + 1):
        sid = p.create_scene(pid, i, f"s{i}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": 1, "shot_no": i}), sid))
        if i == 1:
            jid = p.create_job(sid, "image_gen")
            p.conn.execute("UPDATE jobs SET state='succeeded' WHERE id=?", (jid,))
    p.conn.commit()
    return db, p.conn, pid


def _bg_rounds(conn, db, n=4, err=None, scene_qc=False):
    from core import autoqc, bg_poll
    with mock.patch.dict(os.environ, {"FEATURE_BG_AUTOQC": "1"}), \
            mock.patch.object(autoqc, "start", lambda *a, **k: True), mock.patch.object(autoqc, "start_video", lambda *a, **k: False), \
            mock.patch.object(autoqc, "last_error", lambda pid: err), mock.patch("core.qc_scene.active", lambda: scene_qc):
        for _ in range(n):
            bg_poll.autoqc_round(conn, db, "/tmp/data")


def _codes(conn):
    return [r[0] for r in conn.execute("SELECT code FROM diag_events WHERE code LIKE 'bg_autoqc_%' ORDER BY id")]


def test_bg_autoqc_claude_down_is_said_as_such_once(tmp_path):
    db, conn, pid = _bg_project(tmp_path)
    _bg_rounds(conn, db, err="chưa có Claude: hết lượt gói tới 18:00")
    assert _codes(conn) == ["bg_autoqc_no_claude"]
    assert "hết lượt gói" in conn.execute("SELECT message FROM diag_events WHERE code='bg_autoqc_no_claude'").fetchone()[0]


def test_bg_autoqc_waiting_for_the_scene_frames_is_quiet(tmp_path):
    db, conn, pid = _bg_project(tmp_path, shots=2)                         # shot 2 của cùng cảnh chưa có ảnh
    _bg_rounds(conn, db, scene_qc=True)
    assert _codes(conn) == []


def test_bg_autoqc_other_reason_still_says_stuck_with_the_last_error(tmp_path):
    db, conn, pid = _bg_project(tmp_path)
    _bg_rounds(conn, db, err="JSON hỏng ở câu trả lời QC")
    assert _codes(conn) == ["bg_autoqc_stuck"]
    assert "JSON hỏng" in conn.execute("SELECT message FROM diag_events WHERE code='bg_autoqc_stuck'").fetchone()[0]
