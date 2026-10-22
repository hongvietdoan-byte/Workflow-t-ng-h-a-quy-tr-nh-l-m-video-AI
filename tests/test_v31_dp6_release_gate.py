"""DP6 — V3.1 M5.2 (cloud-C 20/10): cổng phát hành — checklist 8 mục → ĐẠT / CHƯA ĐẠT kèm lý do; cờ `release_gate` TẮT; bật chỉ CẢNH BÁO
(không chặn nút xuất). Dự án giả đủ / thiếu từng điều kiện. 0 USD, chỉ đọc."""
import json
import os
from unittest import mock

import pytest

from core import release_gate as G
from core.db import connect
from core.pipeline import Pipeline, SUBMIT_UNKNOWN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def world(tmp_path):
    p = Pipeline(connect(str(tmp_path / "m.sqlite")))
    pid = p.create_project("dp6")
    sids = [p.create_scene(pid, i, f"S{i}") for i in (1, 2)]
    return p, pid, sids, str(tmp_path)


def _clips(states):
    return [{"idx": i + 1, "state": s, "extra": False, "path": f"/x/{i}.mp4"} for i, s in enumerate(states)]


GOOD = {
    "final_cut.collect_clips": _clips(["approved", "approved"]),
    "final_qc.run": {"ok": True, "blocks": 0, "warns": 1, "issues": [{"code": "silence", "level": "warn", "msg": "lặng"}]},
    "delivery.status": {"final": {"state": "fresh", "reasons": []}, "layers": [{"kind": "subtitle", "stale": None}]},
}


def _run(world, errors=None, **over):
    p, pid, sids, data = world
    vals = dict(GOOD, **over)
    errs = os.path.join(data, "errors.json")
    with open(errs, "w", encoding="utf-8") as f:
        json.dump({"items": errors or []}, f)
    with mock.patch("core.final_cut.collect_clips", return_value=vals["final_cut.collect_clips"]), \
         mock.patch("core.final_qc.run", return_value=vals["final_qc.run"]), \
         mock.patch("core.delivery.status", return_value=vals["delivery.status"]):
        return G.check(p, pid, data, errors_path=errs)


def _final(p, pid, timeline=True):
    p.conn.execute("INSERT INTO outputs (project_id, kind, path, manifest, created_at) VALUES (?, 'final', '/x/final.mp4', ?, '2026-10-20')",
                   (pid, json.dumps({"timeline": [{"idx": 1, "seconds": 2}]} if timeline else {})))
    p.conn.commit()


def _state(res, gid):
    return next(i for i in res["items"] if i["id"] == gid)["state"]


def test_flag_off_by_default():
    from core import features
    assert G.FLAG in features.FEATURES
    with mock.patch.dict(os.environ, {"FEATURE_RELEASE_GATE": ""}):
        assert not G.enabled()


def test_everything_measurable_passes_but_cost_is_unknown_so_not_ok(world):
    p, pid, sids, data = world
    _final(p, pid)
    res = _run(world)
    assert [(_state(res, g)) for g in ("G1", "G2", "G3", "G5", "G6", "G7", "G8")] == ["dat"] * 7
    assert _state(res, "G4") == "khong_ro" and "clipai_cost_reconcile" in res["items"][3]["why"]
    assert res["ok"] is False                                          # KHÔNG RÕ không bao giờ là đạt


def test_g1_unapproved_shot(world):
    res = _run(world, **{"final_cut.collect_clips": _clips(["approved", "pending_review"])})
    assert _state(res, "G1") == "chua_dat" and "2 (pending_review)" in res["items"][0]["why"]


def test_g2_final_qc_block(world):
    res = _run(world, **{"final_qc.run": {"ok": False, "blocks": 1, "warns": 0,
                                         "issues": [{"code": "peak", "level": "block", "msg": "đỉnh âm -0.2 dBTP"}]}})
    assert _state(res, "G2") == "chua_dat" and "đỉnh âm" in res["items"][1]["why"]


def test_g3_stale_layer(world):
    res = _run(world, **{"delivery.status": {"final": {"state": "fresh"}, "layers": [{"kind": "subtitle", "stale": "phụ đề cũ"}]}})
    assert _state(res, "G3") == "chua_dat" and "phụ đề cũ" in res["items"][2]["why"]


def test_g4_unpriced_ledger_rows_fail_at_once(world):
    p, pid, sids, data = world
    p.conn.execute("INSERT INTO usage_events (project_id, kind, provider, model, tier, quantity, unit, at) "
                   "VALUES (?, 'video', 'clipai', 'model-không-có-giá', 'x', 5, 'second', '2026-10-20')", (pid,))
    p.conn.commit()
    assert _state(_run(world), "G4") == "chua_dat"


def test_g5_unreconciled_unknown_send(world):
    p, pid, sids, data = world
    j = p.create_job(sids[0], "video_gen")
    p.start(j)
    p.fail(j, f"{SUBMIT_UNKNOWN}: TimeoutError")
    res = _run(world)
    assert _state(res, "G5") == "chua_dat" and f"#{j}" in res["items"][4]["why"]
    k = p.create_job(sids[0], "video_gen")                             # đối soát xong: có clip mới của shot đó
    p.start(k)
    p.succeed(k)
    assert _state(_run(world), "G5") == "dat"


def test_g6_severe_open_error_of_this_project(world):
    p, pid, sids, data = world
    errs = [{"id": "P99-G1", "project_ids": [pid], "severity": "cao", "status": "OPEN"},
            {"id": "P99-G2", "project_ids": [pid], "severity": "cao", "status": "VERIFIED"},
            {"id": "P99-G3", "project_ids": [pid], "severity": "vua", "status": "OPEN"},
            {"id": "P98-G1", "project_ids": [pid + 1], "severity": "cao", "status": "OPEN"}]
    res = _run(world, errors=errs)
    assert _state(res, "G6") == "chua_dat" and "P99-G1" in res["items"][5]["why"] and "P99-G2" not in res["items"][5]["why"]


def test_g6_reads_the_real_registry():
    assert G._g6_severe_errors(31)["state"] in ("dat", "chua_dat")       # sổ thật đọc được (không KHÔNG RÕ)


def test_g7_escalated_job(world):
    p, pid, sids, data = world
    j = p.create_job(sids[1], "image_gen")
    p.start(j)
    p.succeed(j)
    p.conn.execute("UPDATE jobs SET escalated=1 WHERE id=?", (j,))
    p.conn.commit()
    assert _state(_run(world), "G7") == "chua_dat"


def test_g8_final_without_timeline(world):
    p, pid, sids, data = world
    assert _state(_run(world), "G8") == "chua_dat"                     # chưa có bản dựng
    _final(p, pid, timeline=False)
    assert _state(_run(world), "G8") == "chua_dat"


def test_one_item_crashing_is_unknown_not_pass(world):
    p, pid, sids, data = world
    with mock.patch.object(G, "_g3_layers_current", side_effect=RuntimeError("hỏng")):
        res = _run(world)
    assert _state(res, "G3") == "khong_ro" and res["ok"] is False


def test_summary_says_only_warning():
    res = {"ok": False, "dat": 6, "chua_dat": 1, "khong_ro": 1,
           "items": [{"id": "G1", "label": "x", "state": "chua_dat", "why": "1 shot chưa duyệt"}]}
    text = G.summary(res)
    assert "CHƯA ĐẠT" in text and "vẫn xuất được" in text and "G1" in text


def test_the_export_button_is_never_disabled_by_the_gate():
    src = open(os.path.join(ROOT, "dashboard", "steps", "step5.py"), encoding="utf-8").read()
    block = src[src.index("def _deliver_button"):src.index("def _deliver_button") + 2000]
    assert "release_gate.check(" in block and "release_gate.enabled()" in block
    assert 'disabled=not chosen, width="stretch"' in block                # nút không phụ thuộc kết quả cổng


# ---- M7.4 B7 (cloud-C 21/10): cổng không đọc video → trước đây KHÔNG BAO GIỜ thấy đen / đứng hình (final_black_freeze) -------------
def test_b7_black_freeze_unmeasured_is_not_passed(world):
    p, pid, sids, data = world
    _final(p, pid)
    with mock.patch.dict(os.environ, {"FEATURE_FINAL_BLACK_FREEZE": "1"}):
        res = _run(world)
    g2 = res["items"][1]
    assert g2["state"] == "chua_dat" and "CHƯA ĐO" in g2["why"]


def test_b7_black_freeze_of_this_render_is_shown(world):
    from core import final_qc
    p, pid, sids, data = world
    _final(p, pid)
    fid = p.conn.execute("SELECT MAX(id) FROM outputs WHERE project_id=? AND kind='final'", (pid,)).fetchone()[0]
    final_qc._save_full(data, pid, fid, [{"code": "freeze_frame", "level": "warn", "msg": "ĐỨNG HÌNH 2.1 s (3.0–5.1 s, shot 2)"}])
    with mock.patch.dict(os.environ, {"FEATURE_FINAL_BLACK_FREEZE": "1"}):
        res = _run(world)
    g2 = res["items"][1]
    assert g2["state"] == "dat" and "ĐỨNG HÌNH 2.1 s" in g2["why"] and g2["numbers"]["warns"] == 2
    final_qc._save_full(data, pid, fid + 99, [])                       # lần đo của bản dựng KHÁC → không tính
    with mock.patch.dict(os.environ, {"FEATURE_FINAL_BLACK_FREEZE": "1"}):
        assert _run(world)["items"][1]["state"] == "chua_dat"


def test_b7_flag_off_g2_unchanged(world):
    p, pid, sids, data = world
    _final(p, pid)
    with mock.patch.dict(os.environ, {"FEATURE_FINAL_BLACK_FREEZE": ""}):
        assert _run(world)["items"][1]["state"] == "dat"


def test_b7_full_check_saves_what_the_gate_reads(world, tmp_path):
    from core import final_qc
    p, pid, sids, data = world
    video = tmp_path / "final.mp4"
    video.write_bytes(b"x")
    p.conn.execute("INSERT INTO outputs (project_id, kind, path, manifest, created_at) VALUES (?, 'final', ?, '{}', '2026-10-21')",
                   (pid, str(video)))
    p.conn.commit()
    fid = p.conn.execute("SELECT MAX(id) FROM outputs WHERE project_id=? AND kind='final'", (pid,)).fetchone()[0]
    spans = {"black": [], "freeze": [(3.0, 5.5)]}
    with mock.patch.dict(os.environ, {"FEATURE_FINAL_BLACK_FREEZE": "1"}), \
            mock.patch("core.final_qc.black_freeze_spans", return_value=spans), \
            mock.patch("core.ffmpeg_studio.probe_duration", return_value=10.0), \
            mock.patch("core.final_qc.check_silence", return_value=[]), mock.patch("core.ffmpeg_studio.probe_size", return_value=None):
        final_qc.run(p, pid, data)
    got = final_qc.last_full(data, pid, fid)
    assert got and got[0]["code"] == "freeze_frame"
